"""Request / response models for the public API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .ml import instrument

RoleType = Literal["employee", "student", "general"]
Likert = Field(ge=1, le=5)


class Drivers(BaseModel):
    """Work/study patterns the model uses to explain burnout.

    The daily check-in asks six of them; the other four are optional and default to typical values.
    """

    work_hours_per_day: float = Field(ge=0, le=24)
    after_hours_per_week: float = Field(ge=0, le=7)
    sleep_hours: float = Field(ge=0, le=14)
    workload: float = Likert
    support: float = Likert
    can_disconnect: float = Likert
    meetings_per_day: float | None = Field(None, ge=0, le=20, description="Meetings, or lectures/classes for students")
    days_off_last_month: float | None = Field(None, ge=0, le=31)
    autonomy: float | None = Field(None, ge=1, le=5)
    recognition: float | None = Field(None, ge=1, le=5)
    role_type: RoleType = "employee"
    remote_work: bool = False


class CheckIn(BaseModel):
    drivers: Drivers
    cbi_answers: dict[str, int] | None = Field(
        default=None, description="Copenhagen Burnout Inventory answers, item id -> 0..4 (see GET /instrument)"
    )

    @field_validator("cbi_answers")
    @classmethod
    def _valid_cbi(cls, v):
        if v is not None:
            instrument.score(v)  # raises ValueError on unknown items / out-of-range values
        return v


class Contribution(BaseModel):
    feature: str
    label: str
    value: float | str
    unit: str
    impact: float = Field(description="Burnout points this factor added (+) or removed (-) vs. the average person")


class Lever(BaseModel):
    feature: str
    label: str
    change: str
    expected_change: float = Field(description="Estimated change in burnout score (negative = better)")


class Explanation(BaseModel):
    method: Literal["shap_tree"] = "shap_tree"
    base_score: float = Field(description="Model's average burnout score across the population")
    estimated_score: float
    interval: tuple[float, float] = Field(description="80% prediction interval for the estimate")
    contributions: list[Contribution]
    unexplained: float | None = Field(
        None, description="Measured minus estimated score: burnout not explained by the work factors collected"
    )
    summary: str


class ModelCard(BaseModel):
    version: str
    training_source: str
    mae: float
    note: str


class Prediction(BaseModel):
    score: float = Field(ge=0, le=100, description="Headline burnout score (CBI scale, 0–100)")
    score_source: Literal["measured", "estimated"]
    level: int
    label: str
    color: str
    measured: dict[str, float | None] | None = Field(None, description="CBI scale scores when answers were given")
    burnout_pattern: str | None
    explanation: Explanation
    levers: list[Lever]
    recommendations: list[str]
    model: ModelCard


class WhatIfRequest(BaseModel):
    drivers: Drivers
    changes: dict[str, float] = Field(description="Driver name -> new value")


class WhatIfResult(BaseModel):
    before: float
    after: float
    change: float
    contributions_change: list[Contribution]


# ── Forecast ─────────────────────────────────────────────────────

class DriverChange(BaseModel):
    feature: str
    label: str
    change: float = Field(description="Change in this factor's burnout contribution, early vs. recent check-ins")


class Forecast(BaseModel):
    status: Literal["insufficient_data", "improving", "stable", "rising"]
    check_ins: int
    current: float | None = None
    slope_per_week: float | None = None
    horizon_weeks: int = 4
    projected: float | None = None
    projected_interval: tuple[float, float] | None = None
    weeks_to_threshold: float | None = Field(None, description="Weeks until the score is expected to reach 50, if rising")
    early_warning: bool = False
    what_changed: list[DriverChange] = []
    summary: str


# ── Organisations ────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["company", "school"] = "company"
    groups: list[str] = Field(default_factory=list, description="Departments, teams or classes")


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    kind: str
    groups: list[GroupOut]


class OrgSummary(BaseModel):
    id: int
    name: str
    kind: str
    is_demo: bool
    role: str | None = Field(None, description="Your role here; null for public demo organisations")


class AssessmentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    score: float
    score_source: str
    measured_score: float | None
    estimated_score: float
    level: int
    burnout_pattern: str | None


class AssessmentCreate(CheckIn):
    member_id: int


# ── Accounts & SaaS ──────────────────────────────────────────────

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(min_length=1, max_length=120)
    role_type: RoleType = "employee"
    timezone: str | None = Field(None, max_length=64, description="IANA timezone from the browser, e.g. Asia/Kolkata")


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    timezone: str | None = Field(None, max_length=64)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    email_verified: bool
    reminders: bool


Password = Field(min_length=8, max_length=200)
Code = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyIn(BaseModel):
    code: str = Code


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    email: EmailStr
    code: str = Code
    password: str = Password


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Password


class DeleteAccount(BaseModel):
    password: str


class ProfileUpdate(BaseModel):
    role_type: RoleType | None = None
    reminders: bool | None = None


class InviteEmails(BaseModel):
    emails: list[EmailStr] = Field(min_length=1, max_length=50)
    role: Literal["member", "admin"] = "member"
    group_id: int | None = None


class MembershipOut(BaseModel):
    org_id: int
    org_name: str
    org_kind: str
    role: str
    group_id: int | None
    group_name: str | None
    sharing_since: datetime | None


class TodayOut(BaseModel):
    done: bool = Field(description="Already checked in today (in the user's timezone)")
    weekly_due: bool = Field(description="Today's check-in includes the weekly burnout measure")
    next_at: datetime | None = Field(None, description="When the next check-in opens, if done today")


class MeOut(BaseModel):
    user: UserOut
    member_id: int
    role_type: str
    check_ins: int
    timezone: str
    today: TodayOut
    membership: MembershipOut | None


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class InviteCreate(BaseModel):
    role: Literal["member", "admin"] = "member"
    group_id: int | None = None
    expires_days: int = Field(14, ge=1, le=90)
    max_uses: int = Field(500, ge=1, le=10000)


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    role: str
    group_id: int | None
    expires_at: datetime
    uses: int
    max_uses: int
    revoked: bool


class InvitePreview(BaseModel):
    org_name: str
    org_kind: str
    role: str
    group_id: int | None
    groups: list[GroupOut]
    min_group_size: int


class AcceptInvite(BaseModel):
    consent: bool = Field(description="Must be true: the user agreed to share check-ins as team-level aggregates")
    group_id: int | None = None


class GroupAdmin(BaseModel):
    id: int
    name: str
    members: int


class OrgAdminOut(BaseModel):
    org: OrgOut
    role: str
    groups: list[GroupAdmin]
    admins: int
    invites: list[InviteOut]


# ── HR insights (aggregate-only) ─────────────────────────────────

class Driver(BaseModel):
    feature: str
    label: str
    avg_impact: float


class GroupInsight(BaseModel):
    group_id: int
    group_name: str
    member_count: int
    suppressed: bool = Field(description="True when too few people answered to show data safely")
    avg_score: float | None = None
    level_distribution: dict[str, int] | None = None
    pattern_distribution: dict[str, int] | None = None
    top_drivers: list[Driver] | None = None
    what_changed: list[DriverChange] | None = None
    rising_count: int | None = Field(None, description="Members whose trend is rising")
    early_warning_count: int | None = Field(None, description="Members below 50 now but projected to cross it")
    weekly_trend: list[dict] | None = None


class OrgInsights(BaseModel):
    org_id: int
    org_name: str
    min_group_size: int
    respondents: int
    avg_score: float | None
    level_distribution: dict[str, int]
    top_drivers: list[Driver]
    rising_count: int | None
    early_warning_count: int | None
    groups: list[GroupInsight]
