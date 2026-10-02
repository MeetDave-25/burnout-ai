"""Early-warning forecast from a person's check-in history.

A recency-weighted linear trend (half-life 4 weeks) over the headline burnout scores, projected
4 weeks ahead with a prediction interval. Deliberately simple and transparent: a person can see
exactly why they were flagged ("+3 points/week for 6 weeks"). An early warning fires when the
current score is still below 50 but the projection crosses it.

`what_changed` compares SHAP driver contributions in the earliest vs. the most recent check-ins,
so the trend comes with its reasons.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from ..schemas import DriverChange, Forecast
from .content import FEATURES, WARNING_THRESHOLD

HALF_LIFE_WEEKS = 4
HORIZON_WEEKS = 4
MIN_CHECK_INS = 3
TREND_SLOPE = 1.5  # points/week considered a meaningful trend
Z80 = 1.2816


@dataclass
class Point:
    at: datetime
    score: float
    contributions: list[dict]  # [{feature, impact}, ...]


def driver_changes(early: list[list[dict]], recent: list[list[dict]], top: int = 3) -> list[DriverChange]:
    def mean_impacts(groups):
        totals = defaultdict(float)
        for contribs in groups:
            for c in contribs:
                totals[c["feature"]] += c["impact"]
        return {f: t / len(groups) for f, t in totals.items()}

    a, b = mean_impacts(early), mean_impacts(recent)
    deltas = {f: b.get(f, 0) - a.get(f, 0) for f in set(a) | set(b)}
    ranked = sorted((f for f in deltas if abs(deltas[f]) >= 0.5), key=lambda f: -abs(deltas[f]))[:top]
    return [DriverChange(feature=f, label=FEATURES[f]["label"], change=round(deltas[f], 1)) for f in ranked]


def forecast(points: list[Point]) -> Forecast:
    points = sorted(points, key=lambda p: p.at)
    n = len(points)
    if n < MIN_CHECK_INS:
        return Forecast(status="insufficient_data", check_ins=n,
                        current=points[-1].score if points else None,
                        summary=f"Need at least {MIN_CHECK_INS} check-ins to show a trend ({n} so far).")

    last = points[-1].at
    t = np.array([(p.at - last).total_seconds() / 604800 for p in points])  # weeks, <= 0
    y = np.array([p.score for p in points])
    w = 0.5 ** (-t / HALF_LIFE_WEEKS)

    t_bar = np.average(t, weights=w)
    sxx = np.sum(w * (t - t_bar) ** 2)
    if sxx < 1e-9:  # all check-ins at the same moment
        return Forecast(status="insufficient_data", check_ins=n, current=float(y[-1]),
                        summary="Check-ins need to be spread over time to show a trend.")
    slope = float(np.sum(w * (t - t_bar) * (y - np.average(y, weights=w))) / sxx)
    intercept = float(np.average(y, weights=w) - slope * t_bar)

    resid = y - (intercept + slope * t)
    n_eff = w.sum() ** 2 / np.sum(w ** 2)
    sigma = float(np.sqrt(np.sum(w * resid ** 2) / w.sum() * n / max(n - 2, 1)))
    se = sigma * np.sqrt(1 + 1 / n_eff + (HORIZON_WEEKS - t_bar) ** 2 / sxx)

    current = float(np.clip(intercept, 0, 100))
    projected = float(np.clip(intercept + slope * HORIZON_WEEKS, 0, 100))
    interval = (round(float(np.clip(projected - Z80 * se, 0, 100)), 1), round(float(np.clip(projected + Z80 * se, 0, 100)), 1))
    status = "rising" if slope >= TREND_SLOPE else "improving" if slope <= -TREND_SLOPE else "stable"
    weeks_to = (WARNING_THRESHOLD - current) / slope if slope > 0 and current < WARNING_THRESHOLD else None
    early_warning = current < WARNING_THRESHOLD <= projected and status == "rising"

    third = max(1, n // 3)
    changes = driver_changes([p.contributions for p in points[:third]], [p.contributions for p in points[-third:]])

    span = -t[0]
    parts = [f"Over {span:.0f} weeks your score has been {status} ({slope:+.1f} points/week)."]
    if early_warning:
        when = "about a week" if weeks_to < 1.5 else f"about {weeks_to:.0f} weeks"
        parts.append(f"At this rate it reaches {WARNING_THRESHOLD} in {when} — this is an early warning.")
    elif status != "stable":
        parts.append(f"Projected in {HORIZON_WEEKS} weeks: {projected:.0f} (likely range {interval[0]:.0f}–{interval[1]:.0f}).")
    ups = [c for c in changes if c.change > 0]
    if ups and status == "rising":
        parts.append("Biggest changes: " + ", ".join(f"{c.label.lower()} ({c.change:+.0f})" for c in ups) + ".")

    return Forecast(
        status=status, check_ins=n, current=round(current, 1), slope_per_week=round(slope, 2),
        horizon_weeks=HORIZON_WEEKS, projected=round(projected, 1), projected_interval=interval,
        weeks_to_threshold=round(weeks_to, 1) if weeks_to is not None else None,
        early_warning=early_warning, what_changed=changes, summary=" ".join(parts),
    )
