"""Accounts (sign up → email code → verified), passwords, the signed-in person's own data (/me), and privacy rights."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..auth import (
    clear_session, current_user, hash_password, is_verified, set_session, signed_in_user, verification_required,
    verify_password,
)
from ..db import Assessment, Group, Invite, Member, Membership, Organization, OtpCode, User, get_session
from ..email import templates
from ..email.sender import send_safely
from ..ml.predictor import get_predictor
from ..records import new_assessment
from ..schemas import (
    AssessmentRecord,
    CheckIn,
    DeleteAccount,
    ForgotIn,
    Forecast,
    LoginIn,
    MembershipOut,
    MeOut,
    PasswordChange,
    Prediction,
    ProfileUpdate,
    ResetIn,
    SignupIn,
    UserOut,
    VerifyIn,
)
from ..security import check_code, issue_code, limit, read_unsubscribe_token, record, too_many
from ..services import group_in_org, history, latest_payload, member_forecast, safe_zone, today_status, user_member

router = APIRouter()
_member = user_member

QUARTER = timedelta(minutes=15)
HOUR = timedelta(hours=1)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _email(background: BackgroundTasks, to: str, message: tuple[str, str, str]) -> None:
    background.add_task(send_safely, to, *message)


def me_payload(session: Session, user: User) -> MeOut:
    member = _member(session, user)
    m = session.scalar(select(Membership).where(Membership.user_id == user.id))
    membership = None
    if m:
        org = session.get(Organization, m.org_id)
        sharing = member.org_id == m.org_id
        group = session.get(Group, member.group_id) if sharing and member.group_id else None
        membership = MembershipOut(org_id=org.id, org_name=org.name, org_kind=org.kind, role=m.role,
                                   group_id=group.id if group else None, group_name=group.name if group else None,
                                   sharing_since=member.joined_at if sharing else None)
    count = session.scalar(select(func.count()).select_from(Assessment).where(Assessment.member_id == member.id))
    return MeOut(
        user=UserOut(id=user.id, email=user.email, name=user.name,
                     email_verified=is_verified(user), reminders=user.reminders),
        member_id=member.id, role_type=member.role_type, check_ins=count,
        timezone=user.timezone, today=today_status(session, user, member), membership=membership,
    )


# ── Sign up & verify ─────────────────────────────────────────────

@router.post("/auth/signup", response_model=MeOut, status_code=201)
def signup(body: SignupIn, request: Request, response: Response, background: BackgroundTasks,
           session: Session = Depends(get_session)):
    limit(session, f"signup-ip:{_ip(request)}", 10, HOUR, "Too many sign-ups from this network")
    email = body.email.lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists. Log in instead")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password),
                timezone=safe_zone(body.timezone))
    session.add(user)
    session.flush()
    session.add(Member(user_id=user.id, role_type=body.role_type))
    session.commit()
    if verification_required():
        _email(background, user.email, templates.verify_code(user.name, issue_code(session, user, "verify")))
    else:  # verification switched off: the account works straight away
        _email(background, user.email, templates.welcome(user.name))
    set_session(response, user)
    return me_payload(session, user)


@router.post("/auth/verify", response_model=MeOut)
def verify_email(body: VerifyIn, background: BackgroundTasks, user: User = Depends(signed_in_user),
                 session: Session = Depends(get_session)):
    if user.email_verified_at is None:
        check_code(session, user, "verify", body.code)
        user.email_verified_at = datetime.now(timezone.utc)
        session.commit()
        _email(background, user.email, templates.welcome(user.name))
    return me_payload(session, user)


@router.post("/auth/verify/resend", status_code=204)
def resend_code(background: BackgroundTasks, user: User = Depends(signed_in_user), session: Session = Depends(get_session)):
    if user.email_verified_at is not None:
        return
    limit(session, f"code-burst:{user.id}", 1, timedelta(seconds=45), "Please wait a moment before asking again")
    limit(session, f"code-hour:{user.id}", 6, HOUR, "Too many codes requested")
    _email(background, user.email, templates.verify_code(user.name, issue_code(session, user, "verify")))


# ── Log in / out ─────────────────────────────────────────────────

@router.post("/auth/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, session: Session = Depends(get_session)):
    email = body.email.lower()
    keys = (f"login-fail:{email}", f"login-fail-ip:{_ip(request)}")
    if too_many(session, keys[0], 8, QUARTER) or too_many(session, keys[1], 30, QUARTER):
        raise HTTPException(429, "Too many failed attempts. Wait 15 minutes or reset your password",
                            headers={"Retry-After": "900"})
    user = session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(body.password, user.password_hash):
        for k in keys:
            record(session, k)
        raise HTTPException(401, "Wrong email or password")
    if body.timezone:
        user.timezone = safe_zone(body.timezone)
        session.commit()
    set_session(response, user)
    return me_payload(session, user)


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    clear_session(response)


# ── Forgot / reset password ──────────────────────────────────────

@router.post("/auth/forgot", status_code=204)
def forgot_password(body: ForgotIn, request: Request, background: BackgroundTasks, session: Session = Depends(get_session)):
    """Always answers the same way, so it can't be used to discover who has an account."""
    email = body.email.lower()
    limit(session, f"forgot-ip:{_ip(request)}", 10, HOUR, "Too many reset requests")
    if too_many(session, f"forgot:{email}", 3, QUARTER):
        return
    record(session, f"forgot:{email}")
    user = session.scalar(select(User).where(User.email == email))
    if user:
        _email(background, user.email, templates.reset_code(user.name, issue_code(session, user, "reset")))


@router.post("/auth/reset", response_model=MeOut)
def reset_password(body: ResetIn, response: Response, background: BackgroundTasks, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        raise HTTPException(400, "This code has expired. Request a new one")
    check_code(session, user, "reset", body.code)
    user.password_hash = hash_password(body.password)
    user.token_version += 1  # sign out every other session
    user.email_verified_at = user.email_verified_at or datetime.now(timezone.utc)  # they proved they own the inbox
    session.commit()
    _email(background, user.email, templates.password_changed(user.name))
    set_session(response, user)
    return me_payload(session, user)


@router.post("/me/password", response_model=MeOut)
def change_password(body: PasswordChange, response: Response, background: BackgroundTasks,
                    user: User = Depends(current_user), session: Session = Depends(get_session)):
    limit(session, f"pw-change:{user.id}", 10, HOUR)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Your current password isn’t right")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    session.commit()
    _email(background, user.email, templates.password_changed(user.name))
    set_session(response, user)  # keep this device signed in
    return me_payload(session, user)


# ── Me ───────────────────────────────────────────────────────────

@router.get("/me", response_model=MeOut)
def me(user: User = Depends(signed_in_user), session: Session = Depends(get_session)):
    return me_payload(session, user)


@router.patch("/me", response_model=MeOut)
def update_me(body: ProfileUpdate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if body.role_type is not None:
        _member(session, user).role_type = body.role_type
    if body.reminders is not None:
        user.reminders = body.reminders
    session.commit()
    return me_payload(session, user)


@router.post("/me/assessments", response_model=Prediction, status_code=201)
def submit(body: CheckIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Today's check-in. One per day, so each reading reflects a day rather than a mood swing."""
    member = _member(session, user)
    if today_status(session, user, member).done:
        raise HTTPException(409, "You've already checked in today. Come back tomorrow")
    body = body.model_copy(update={"drivers": body.drivers.model_copy(update={"role_type": member.role_type})})
    result = get_predictor().assess(body)
    session.add(new_assessment(member.id, body, result))
    session.commit()
    return result


@router.get("/me/assessments", response_model=list[AssessmentRecord])
def my_history(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return history(session, _member(session, user).id)


@router.get("/me/latest")
def my_latest(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return latest_payload(session, _member(session, user))


@router.get("/me/forecast", response_model=Forecast)
def my_forecast(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return member_forecast(session, _member(session, user))


# ── Sharing with an organisation ─────────────────────────────────

@router.post("/me/sharing", response_model=MeOut)
def start_sharing(group_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Admins/owners can also take part: start sharing check-ins with their organisation's group."""
    m = session.scalar(select(Membership).where(Membership.user_id == user.id))
    if not m:
        raise HTTPException(409, "You're not in an organisation")
    group_in_org(session, session.get(Organization, m.org_id), group_id)
    member = _member(session, user)
    member.org_id, member.group_id, member.joined_at = m.org_id, group_id, datetime.now(timezone.utc)
    m.consent_at = m.consent_at or datetime.now(timezone.utc)
    session.commit()
    return me_payload(session, user)


@router.delete("/me/sharing", response_model=MeOut)
def stop_sharing(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Stop contributing to team aggregates. Your own history stays yours."""
    member = _member(session, user)
    member.org_id = member.group_id = member.joined_at = None
    session.commit()
    return me_payload(session, user)


def _sole_owner(session: Session, m: Membership) -> bool:
    owners = session.scalar(select(func.count()).select_from(Membership)
                            .where(Membership.org_id == m.org_id, Membership.role == "owner"))
    return m.role == "owner" and owners <= 1


@router.delete("/me/membership", response_model=MeOut)
def leave_org(user: User = Depends(current_user), session: Session = Depends(get_session)):
    m = session.scalar(select(Membership).where(Membership.user_id == user.id))
    if not m:
        raise HTTPException(409, "You're not in an organisation")
    if _sole_owner(session, m):
        raise HTTPException(409, "You're the only owner. Make someone else an owner before leaving")
    member = _member(session, user)
    if member.org_id == m.org_id:
        member.org_id = member.group_id = member.joined_at = None
    session.delete(m)
    session.commit()
    return me_payload(session, user)


# ── Privacy rights: export & delete ──────────────────────────────

@router.get("/me/export")
def export_my_data(user: User = Depends(signed_in_user), session: Session = Depends(get_session)):
    """Everything we hold about you, as JSON (right of access / portability)."""
    member = _member(session, user)
    m = session.scalar(select(Membership).where(Membership.user_id == user.id))
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {"email": user.email, "name": user.name, "timezone": user.timezone,
                    "created_at": user.created_at.isoformat(), "email_verified": user.email_verified_at is not None,
                    "reminders": user.reminders},
        "profile": {"role_type": member.role_type},
        "organisation": None if not m else {"name": m.org.name, "role": m.role,
                                            "sharing_since": member.joined_at.isoformat() if member.joined_at else None},
        "check_ins": [{
            "at": a.created_at.isoformat(), "answers": a.inputs, "weekly_answers": a.cbi_answers,
            "score": a.score, "score_source": a.score_source, "measured_score": a.measured_score,
            "estimated_score": a.estimated_score, "level": a.level, "pattern": a.burnout_pattern,
            "explanation": a.contributions, "model_version": a.model_version,
        } for a in history(session, member.id)],
    }
    return Response(content=json.dumps(data, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="burnoutai-my-data.json"'})


@router.delete("/me", status_code=204)
def delete_account(body: DeleteAccount, response: Response, background: BackgroundTasks,
                   user: User = Depends(signed_in_user), session: Session = Depends(get_session)):
    """Permanently delete the account and every check-in (right to erasure)."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(400, "That password isn’t right")
    member = _member(session, user)
    m = session.scalar(select(Membership).where(Membership.user_id == user.id))
    if m and _sole_owner(session, m):
        # An organisation can't exist without an owner, so it closes. Members keep their own accounts and history.
        org_id = m.org_id
        for other in session.scalars(select(Member).where(Member.org_id == org_id)):
            other.org_id = other.group_id = other.joined_at = None
        session.execute(delete(Invite).where(Invite.org_id == org_id))
        session.execute(delete(Membership).where(Membership.org_id == org_id))
        session.execute(delete(Group).where(Group.org_id == org_id))
        session.execute(delete(Organization).where(Organization.id == org_id))
    elif m:
        session.delete(m)
    session.execute(delete(Assessment).where(Assessment.member_id == member.id))
    session.execute(delete(OtpCode).where(OtpCode.user_id == user.id))
    session.delete(member)
    email, name = user.email, user.name
    session.delete(user)
    session.commit()
    _email(background, email, templates.account_deleted(name))
    clear_session(response)


# ── One-click unsubscribe (from reminder emails) ─────────────────

@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(token: str, session: Session = Depends(get_session)):
    user_id = read_unsubscribe_token(token)
    user = session.get(User, user_id) if user_id else None
    if user:
        user.reminders = False
        session.commit()
    msg = "Reminders turned off." if user else "This link is no longer valid."
    return f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1"><title>BurnoutAI</title>
<body style="margin:0;display:grid;place-items:center;min-height:100vh;background:#ece9e2;font-family:Arial,sans-serif">
<div style="border:2px solid #0b0b0b;background:#f4f2ec;padding:32px;max-width:420px">
<div style="height:8px;background:#ff4a00;margin:-32px -32px 24px"></div>
<h1 style="margin:0 0 8px;text-transform:uppercase">{msg}</h1>
<p>You can turn them back on any time in Account &amp; privacy.</p></div></body>"""
