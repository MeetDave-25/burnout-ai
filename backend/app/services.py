"""Shared lookups used by several routers."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Assessment, Group, Member, Organization, User
from .ml.forecast import forecast
from .ml.predictor import get_predictor
from .records import to_points
from .schemas import CheckIn, Forecast, TodayOut

WEEKLY_EVERY = timedelta(days=6, hours=12)  # the weekly measure comes round again after ~a week


def safe_zone(name: str | None) -> str:
    try:
        return ZoneInfo(name).key if name else "UTC"
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC"


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def user_member(session: Session, user: User) -> Member:
    """Every account has exactly one Member (its check-in subject); recreate defensively."""
    member = session.scalar(select(Member).where(Member.user_id == user.id))
    if member is None:
        member = Member(user_id=user.id, role_type="employee")
        session.add(member)
        session.commit()
    return member


def today_status(session: Session, user: User, member: Member, now: datetime | None = None) -> TodayOut:
    """One check-in per calendar day in the user's own timezone; the weekly measure when ~7 days have passed."""
    now = now or datetime.now(timezone.utc)
    tz = ZoneInfo(safe_zone(user.timezone))
    rows = history(session, member.id)
    last = rows[-1] if rows else None
    done = last is not None and _as_utc(last.created_at).astimezone(tz).date() == now.astimezone(tz).date()
    last_measured = next((a for a in reversed(rows) if a.measured_score is not None), None)
    weekly_due = last_measured is None or now - _as_utc(last_measured.created_at) >= WEEKLY_EVERY
    next_at = None
    if done:
        tomorrow = now.astimezone(tz).date() + timedelta(days=1)
        next_at = datetime.combine(tomorrow, time.min, tz).astimezone(timezone.utc)
    return TodayOut(done=done, weekly_due=weekly_due and not done, next_at=next_at)


def get_org(session: Session, org_id: int) -> Organization:
    org = session.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organisation not found")
    return org


def group_in_org(session: Session, org: Organization, group_id: int | None) -> Group | None:
    if group_id is None:
        return None
    group = session.get(Group, group_id)
    if not group or group.org_id != org.id:
        raise HTTPException(422, "group_id does not belong to this organisation")
    return group


def history(session: Session, member_id: int) -> list[Assessment]:
    return list(session.scalars(
        select(Assessment).where(Assessment.member_id == member_id).order_by(Assessment.created_at)
    ))


def latest_payload(session: Session, member: Member) -> dict:
    """The member's most recent check-in, re-explained with the current model."""
    rows = history(session, member.id)
    if not rows:
        raise HTTPException(404, "No check-ins yet")
    last = rows[-1]
    check_in = CheckIn(drivers=last.inputs, cbi_answers=last.cbi_answers)
    return {"created_at": last.created_at, "drivers": check_in.drivers, "prediction": get_predictor().assess(check_in)}


def member_forecast(session: Session, member: Member) -> Forecast:
    return forecast(to_points(history(session, member.id)))
