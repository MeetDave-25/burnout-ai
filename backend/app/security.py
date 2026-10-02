"""One-time codes, rate limiting and signed unsubscribe links."""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import settings
from .db import OtpCode, RateEvent, User

CODE_TTL = timedelta(minutes=10)
RATE_LIMITS = os.getenv("RATE_LIMITS", "on") != "off"
MAX_CODE_ATTEMPTS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── One-time codes ───────────────────────────────────────────────

def _digest(user_id: int, purpose: str, code: str) -> str:
    return hmac.new(settings.secret_key.encode(), f"{user_id}:{purpose}:{code}".encode(), hashlib.sha256).hexdigest()


def issue_code(session: Session, user: User, purpose: str) -> str:
    """Create a fresh 6-digit code (older unused codes for the same purpose stop working)."""
    for old in session.scalars(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
                                                      OtpCode.used.is_(False))):
        old.used = True
    code = f"{secrets.randbelow(10**6):06d}"
    session.add(OtpCode(user_id=user.id, purpose=purpose, code_hash=_digest(user.id, purpose, code),
                        expires_at=_now() + CODE_TTL))
    session.commit()
    return code


def check_code(session: Session, user: User, purpose: str, code: str) -> None:
    """Raises a clear HTTP error unless `code` is the user's current, unexpired code. Consumes it on success."""
    otp = session.scalar(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
                                               OtpCode.used.is_(False)).order_by(OtpCode.id.desc()))
    if otp is None or _as_utc(otp.expires_at) < _now():
        raise HTTPException(400, "This code has expired. Request a new one")
    otp.attempts += 1
    if otp.attempts > MAX_CODE_ATTEMPTS:
        otp.used = True
        session.commit()
        raise HTTPException(429, "Too many wrong codes. Request a new one")
    if not hmac.compare_digest(otp.code_hash, _digest(user.id, purpose, code.strip())):
        session.commit()
        left = MAX_CODE_ATTEMPTS - otp.attempts
        raise HTTPException(400, f"That code isn’t right. {left} attempt{'s' if left != 1 else ''} left")
    otp.used = True
    session.commit()


# ── Rate limiting ────────────────────────────────────────────────

def _count(session: Session, key: str, window: timedelta) -> int:
    return session.scalar(select(func.count()).select_from(RateEvent)
                          .where(RateEvent.key == key, RateEvent.created_at > _now() - window)) or 0


def too_many(session: Session, key: str, limit: int, window: timedelta) -> bool:
    return RATE_LIMITS and _count(session, key, window) >= limit


def record(session: Session, key: str) -> None:
    session.add(RateEvent(key=key))
    if secrets.randbelow(50) == 0:  # occasional housekeeping
        session.execute(delete(RateEvent).where(RateEvent.created_at < _now() - timedelta(days=2)))
    session.commit()


def limit(session: Session, key: str, limit: int, window: timedelta, message: str = "Too many attempts") -> None:
    """Allow at most `limit` actions per `window` for `key`; records this one if allowed."""
    if too_many(session, key, limit, window):
        minutes = max(1, round(window.total_seconds() / 60))
        raise HTTPException(429, f"{message}. Please wait and try again (limit resets within {minutes} min)",
                            headers={"Retry-After": str(int(window.total_seconds()))})
    record(session, key)


# ── Unsubscribe links ────────────────────────────────────────────

def unsubscribe_token(user: User) -> str:
    return jwt.encode({"sub": str(user.id), "purpose": "unsubscribe"}, settings.secret_key, algorithm="HS256")


def read_unsubscribe_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return int(data["sub"]) if data.get("purpose") == "unsubscribe" else None
