"""Database models and session handling (SQLite locally, PostgreSQL in production)."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")  # IANA name, for "one check-in per day"
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # bump to sign out every session
    reminders: Mapped[bool] = mapped_column(Boolean, default=True)  # daily check-in reminder email
    last_reminded_on: Mapped[str | None] = mapped_column(String(10), nullable=True)  # local date, YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OtpCode(Base):
    """A 6-digit one-time code for email verification or password reset. Only a hash is stored."""

    __tablename__ = "otp_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(10))  # verify | reset
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RateEvent(Base):
    """One row per rate-limited action (login attempt, code request…), counted within a time window."""

    __tablename__ = "rate_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # company | school
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)  # public demo; excluded from model retraining
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    groups: Mapped[list["Group"]] = relationship(back_populates="org", order_by="Group.id")


class Group(Base):
    """A department, team or class."""

    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    org: Mapped[Organization] = relationship(back_populates="groups")


class Membership(Base):
    """A user's role in an organisation: owner / admin (HR, see team aggregates) / member (takes check-ins)."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "org_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    org: Mapped[Organization] = relationship()


class Member(Base):
    """The subject of check-ins. Pseudonymous: no name or email here.

    Every user has exactly one Member. `org_id`/`group_id` are set while they share with an organisation,
    and only check-ins made after `joined_at` ever count toward that organisation's aggregates.
    Demo members have no user.
    """

    __tablename__ = "members"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), index=True, nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role_type: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # member | admin
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int] = mapped_column(Integer, default=500)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    inputs: Mapped[dict] = mapped_column(JSON)  # Drivers
    cbi_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    measured_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # CBI overall, if answered
    estimated_score: Mapped[float] = mapped_column(Float)  # driver-model estimate
    score: Mapped[float] = mapped_column(Float)  # headline: measured if available, else estimated
    score_source: Mapped[str] = mapped_column(String(10))
    level: Mapped[int] = mapped_column(Integer)
    burnout_pattern: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contributions: Mapped[list] = mapped_column(JSON)  # [{feature, label, impact}, ...]
    model_version: Mapped[str] = mapped_column(String(40))


def get_session():
    with SessionLocal() as session:
        yield session
