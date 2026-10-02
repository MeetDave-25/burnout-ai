"""Organisations (companies & schools): creation, groups, invites, and aggregate-only insights."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user, membership_of, optional_user, require_org_admin
from ..config import settings
from ..db import Group, Invite, Member, Membership, Organization, User, get_session
from ..email import templates
from ..email.sender import send_safely
from ..security import limit
from ..insights import org_insights
from ..schemas import (
    AcceptInvite,
    GroupAdmin,
    GroupCreate,
    InviteCreate,
    InviteEmails,
    InviteOut,
    InvitePreview,
    MeOut,
    OrgAdminOut,
    OrgCreate,
    OrgInsights,
    OrgOut,
    OrgSummary,
)
from ..services import get_org, group_in_org
from .accounts import _member, me_payload

router = APIRouter()


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/orgs", response_model=list[OrgSummary])
def list_orgs(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Your organisation (if any) followed by the sample organisations."""
    out = []
    for m in session.scalars(select(Membership).where(Membership.user_id == user.id)):
        o = m.org
        out.append(OrgSummary(id=o.id, name=o.name, kind=o.kind, is_demo=o.is_demo, role=m.role))
    for o in session.scalars(select(Organization).where(Organization.is_demo).order_by(Organization.id)):
        out.append(OrgSummary(id=o.id, name=o.name, kind=o.kind, is_demo=True))
    return out


@router.post("/orgs", response_model=OrgOut, status_code=201)
def create_org(body: OrgCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if session.scalar(select(Membership).where(Membership.user_id == user.id)):
        raise HTTPException(409, "You're already in an organisation. Leave it first to create a new one")
    org = Organization(name=body.name.strip(), kind=body.kind)
    org.groups = [Group(name=n.strip()) for n in body.groups if n.strip()]
    session.add(org)
    session.flush()
    session.add(Membership(user_id=user.id, org_id=org.id, role="owner", consent_at=datetime.now(timezone.utc)))
    session.commit()
    return org


@router.get("/orgs/{org_id}", response_model=OrgOut)
def read_org(org_id: int, user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    org = get_org(session, org_id)
    if not org.is_demo and membership_of(session, user, org.id) is None:
        raise HTTPException(404, "Organisation not found")
    return org


@router.get("/orgs/{org_id}/insights", response_model=OrgInsights)
def read_insights(org_id: int, user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    org = get_org(session, org_id)
    require_org_admin(session, user, org)
    return org_insights(session, org)


@router.get("/orgs/{org_id}/admin", response_model=OrgAdminOut)
def admin_overview(org_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    org = get_org(session, org_id)
    m = require_org_admin(session, user, org, write=True)
    counts = dict(session.execute(
        select(Member.group_id, func.count()).where(Member.org_id == org.id).group_by(Member.group_id)
    ).all())
    admins = session.scalar(select(func.count()).select_from(Membership)
                            .where(Membership.org_id == org.id, Membership.role.in_(("owner", "admin"))))
    invites = session.scalars(select(Invite).where(Invite.org_id == org.id, Invite.revoked.is_(False))
                              .order_by(Invite.created_at.desc())).all()
    return OrgAdminOut(org=OrgOut.model_validate(org), role=m.role, admins=admins,
                       groups=[GroupAdmin(id=g.id, name=g.name, members=counts.get(g.id, 0)) for g in org.groups],
                       invites=[InviteOut.model_validate(i) for i in invites])


@router.post("/orgs/{org_id}/groups", response_model=OrgOut, status_code=201)
def add_group(org_id: int, body: GroupCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    org = get_org(session, org_id)
    require_org_admin(session, user, org, write=True)
    session.add(Group(org_id=org.id, name=body.name.strip()))
    session.commit()
    session.refresh(org)
    return org


@router.post("/orgs/{org_id}/invites", response_model=InviteOut, status_code=201)
def create_invite(org_id: int, body: InviteCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    org = get_org(session, org_id)
    m = require_org_admin(session, user, org, write=True)
    if body.role == "admin" and m.role != "owner":
        raise HTTPException(403, "Only owners can invite admins")
    group_in_org(session, org, body.group_id)
    invite = Invite(code=secrets.token_urlsafe(9), org_id=org.id, role=body.role, group_id=body.group_id,
                    created_by=user.id, max_uses=body.max_uses,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_days))
    session.add(invite)
    session.commit()
    return invite


@router.post("/orgs/{org_id}/invites/email", status_code=201)
def email_invites(org_id: int, body: InviteEmails, background: BackgroundTasks,
                  user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Create one invite link and email it to each address."""
    org = get_org(session, org_id)
    m = require_org_admin(session, user, org, write=True)
    if body.role == "admin" and m.role != "owner":
        raise HTTPException(403, "Only owners can invite admins")
    group_in_org(session, org, body.group_id)
    emails = sorted({e.lower() for e in body.emails})
    for _ in emails:
        limit(session, f"invite-mail:{org.id}", 300, timedelta(days=1), "Daily invite email limit reached")
    invite = Invite(code=secrets.token_urlsafe(9), org_id=org.id, role=body.role, group_id=body.group_id,
                    created_by=user.id, max_uses=max(len(emails), 1) + 5,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=14))
    session.add(invite)
    session.commit()
    url = f"{settings.app_url}/join/{invite.code}"
    for email in emails:
        background.add_task(send_safely, email, *templates.invite(org.name, user.name, body.role, url, settings.min_group_size))
    return {"sent": len(emails), "invite": InviteOut.model_validate(invite)}


@router.delete("/orgs/{org_id}/invites/{code}", status_code=204)
def revoke_invite(org_id: int, code: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    org = get_org(session, org_id)
    require_org_admin(session, user, org, write=True)
    invite = session.scalar(select(Invite).where(Invite.code == code, Invite.org_id == org.id))
    if not invite:
        raise HTTPException(404, "Invite not found")
    invite.revoked = True
    session.commit()


def _valid_invite(session: Session, code: str) -> Invite:
    invite = session.scalar(select(Invite).where(Invite.code == code))
    if not invite or invite.revoked or _as_utc(invite.expires_at) < datetime.now(timezone.utc) or invite.uses >= invite.max_uses:
        raise HTTPException(404, "This invite link is invalid or has expired")
    return invite


@router.get("/invites/{code}", response_model=InvitePreview)
def preview_invite(code: str, session: Session = Depends(get_session)):
    invite = _valid_invite(session, code)
    org = get_org(session, invite.org_id)
    return InvitePreview(org_name=org.name, org_kind=org.kind, role=invite.role, group_id=invite.group_id,
                         groups=org.groups, min_group_size=settings.min_group_size)


@router.post("/invites/{code}/accept", response_model=MeOut)
def accept_invite(code: str, body: AcceptInvite, user: User = Depends(current_user), session: Session = Depends(get_session)):
    invite = _valid_invite(session, code)
    if not body.consent:
        raise HTTPException(422, "Please read and accept how your data is shared")
    existing = session.scalar(select(Membership).where(Membership.user_id == user.id))
    if existing and existing.org_id != invite.org_id:
        raise HTTPException(409, "You're already in another organisation. Leave it first")
    org = get_org(session, invite.org_id)
    group_id = invite.group_id or body.group_id
    if invite.role == "member" and group_id is None:
        raise HTTPException(422, "Choose your team or class")
    group_in_org(session, org, group_id)

    now = datetime.now(timezone.utc)
    if existing is None:
        session.add(Membership(user_id=user.id, org_id=org.id, role=invite.role, consent_at=now))
    if group_id is not None:
        member = _member(session, user)
        member.org_id, member.group_id, member.joined_at = org.id, group_id, now
    invite.uses += 1
    session.commit()
    return me_payload(session, user)
