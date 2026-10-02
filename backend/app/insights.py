"""Aggregate, privacy-preserving insights for HR / school admins.

Rules:
  * Only a member's most recent assessment in the window counts toward "current" stats.
  * Any group (or weekly bucket) with fewer than `min_group_size` distinct respondents is
    suppressed, so no individual's answers can be inferred.
  * Individual forecasts are only ever exposed as counts inside non-suppressed groups.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import settings
from .db import Assessment, Member, Organization
from .ml.content import FEATURES, LEVELS
from .ml.forecast import driver_changes, forecast
from .records import to_points
from .schemas import Driver, GroupInsight, OrgInsights

CURRENT_WINDOW = timedelta(days=30)
TREND_WEEKS = 8
CHANGE_WINDOW = timedelta(weeks=2)  # compare the first vs. last 2 weeks of the trend window


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _levels(rows: list[Assessment]) -> dict[str, int]:
    counts = Counter(r.level for r in rows)
    return {lv["label"]: counts.get(lv["level"], 0) for lv in LEVELS}


def _top_drivers(rows: list[Assessment], n: int = 3) -> list[Driver]:
    totals: dict[str, float] = defaultdict(float)
    for r in rows:
        for c in r.contributions:
            totals[c["feature"]] += c["impact"]
    avg = {f: t / len(rows) for f, t in totals.items()}
    ranked = sorted((f for f in avg if avg[f] > 0), key=lambda f: -avg[f])[:n]
    return [Driver(feature=f, label=FEATURES[f]["label"], avg_impact=round(avg[f], 1)) for f in ranked]


def _bucket(rows: list[Assessment], start: datetime, end: datetime) -> list[Assessment]:
    return [r for r in rows if start < _as_utc(r.created_at) <= end]


def _weekly_trend(rows: list[Assessment], now: datetime, k: int) -> list[dict]:
    trend = []
    for w in range(TREND_WEEKS - 1, -1, -1):
        end = now - timedelta(weeks=w)
        bucket = _bucket(rows, end - timedelta(weeks=1), end)
        respondents = len({r.member_id for r in bucket})
        trend.append({
            "week_ending": end.date().isoformat(),
            "respondents": respondents,
            "avg_score": round(sum(r.score for r in bucket) / len(bucket), 1) if respondents >= k else None,
        })
    return trend


def _forecast_counts(history: dict[int, list[Assessment]], member_ids) -> tuple[int, int]:
    rising = warning = 0
    for m in member_ids:
        f = forecast(to_points(history[m]))
        rising += f.status == "rising"
        warning += f.early_warning
    return rising, warning


def org_insights(session: Session, org: Organization, now: datetime | None = None) -> OrgInsights:
    now = now or datetime.now(timezone.utc)
    k = settings.min_group_size
    trend_start = now - timedelta(weeks=TREND_WEEKS)

    rows = session.execute(
        select(Assessment, Member.group_id)
        .join(Member, Member.id == Assessment.member_id)
        .where(
            Member.org_id == org.id,
            Assessment.created_at > min(trend_start, now - CURRENT_WINDOW),
            # only check-ins made after the person started sharing with this organisation
            or_(Member.joined_at.is_(None), Assessment.created_at >= Member.joined_at),
        )
        .order_by(Assessment.created_at)
    ).all()

    by_group: dict[int, list[Assessment]] = defaultdict(list)
    history: dict[int, list[Assessment]] = defaultdict(list)
    latest: dict[int, Assessment] = {}
    group_of_member: dict[int, int] = {}
    for a, group_id in rows:
        by_group[group_id].append(a)
        history[a.member_id].append(a)
        group_of_member[a.member_id] = group_id
        if _as_utc(a.created_at) > now - CURRENT_WINDOW:
            latest[a.member_id] = a  # rows are time-ordered, so last write wins

    groups = []
    for g in org.groups:
        current = [a for m, a in latest.items() if group_of_member[m] == g.id]
        insight = GroupInsight(group_id=g.id, group_name=g.name, member_count=len(current), suppressed=len(current) < k)
        if not insight.suppressed:
            rows_g = by_group[g.id]
            early = _bucket(rows_g, trend_start, trend_start + CHANGE_WINDOW)
            recent = _bucket(rows_g, now - CHANGE_WINDOW, now)
            enough = min(len({r.member_id for r in early}), len({r.member_id for r in recent})) >= k
            insight.avg_score = round(sum(a.score for a in current) / len(current), 1)
            insight.level_distribution = _levels(current)
            insight.pattern_distribution = dict(Counter(a.burnout_pattern or "None" for a in current))
            insight.top_drivers = _top_drivers(current)
            insight.what_changed = driver_changes([r.contributions for r in early],
                                                  [r.contributions for r in recent]) if enough else []
            insight.rising_count, insight.early_warning_count = _forecast_counts(
                history, [a.member_id for a in current])
            insight.weekly_trend = _weekly_trend(rows_g, now, k)
        groups.append(insight)

    everyone = list(latest.values())
    show_org = len(everyone) >= k
    rising, warning = _forecast_counts(history, latest) if show_org else (None, None)
    return OrgInsights(
        org_id=org.id,
        org_name=org.name,
        min_group_size=k,
        respondents=len(everyone),
        avg_score=round(sum(a.score for a in everyone) / len(everyone), 1) if show_org else None,
        level_distribution=_levels(everyone) if show_org else {},
        top_drivers=_top_drivers(everyone) if show_org else [],
        rising_count=rising,
        early_warning_count=warning,
        groups=groups,
    )
