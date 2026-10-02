"""Accounts: password hashing, session tokens in an httpOnly cookie, and access-control dependencies."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import Membership, Organization, User, get_session

COOKIE = "bai_session"
SESSION_DAYS = 30
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **_SCRYPT)
    return hmac.compare_digest(check.hex(), digest)


def set_session(response: Response, user: User) -> None:
    exp = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    token = jwt.encode({"sub": str(user.id), "ver": user.token_version, "exp": exp}, settings.secret_key, algorithm="HS256")
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                        samesite="lax", secure=settings.cookie_secure, path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def any_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    """The signed-in user, verified or not. Sessions die when the password changes (token_version)."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    user = session.get(User, int(payload["sub"]))
    if user is None or payload.get("ver", 0) != user.token_version:
        return None
    return user


def signed_in_user(user: User | None = Depends(any_user)) -> User:
    """Signed in, email not necessarily verified yet (verification, /me, account deletion)."""
    if user is None:
        raise HTTPException(401, "Please log in")
    return user


def optional_user(user: User | None = Depends(any_user)) -> User | None:
    return user if user is not None and is_verified(user) else None


def verification_required() -> bool:
    return settings.require_email_verification


def is_verified(user: User) -> bool:
    """Verified email, or verification switched off (REQUIRE_EMAIL_VERIFICATION=false)."""
    return user.email_verified_at is not None or not verification_required()


def current_user(user: User = Depends(signed_in_user)) -> User:
    """Signed in with a verified email: required for everything in the app."""
    if not is_verified(user):
        raise HTTPException(403, "Please verify your email first")
    return user


def membership_of(session: Session, user: User | None, org_id: int) -> Membership | None:
    if user is None:
        return None
    return session.scalar(select(Membership).where(Membership.user_id == user.id, Membership.org_id == org_id))


def require_org_admin(session: Session, user: User | None, org: Organization, *, write: bool = False) -> Membership | None:
    """Admins and owners only. Demo organisations are public to read and closed to writes."""
    if org.is_demo:
        if user is None:
            raise HTTPException(401, "Please log in")
        if write:
            raise HTTPException(403, "Demo organisations are read-only")
        return None
    m = membership_of(session, user, org.id)
    if m is None or m.role not in ("owner", "admin"):
        raise HTTPException(403, "Only organisation admins can do this")
    return m
