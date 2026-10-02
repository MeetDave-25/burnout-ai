from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import db
from app.email import sender
from app.main import api as app
from app.ml.predictor import get_predictor
from app.records import new_assessment
from app.schemas import CheckIn
from tests.test_predictor import ALL_OFTEN, HEALTHY, OVERWORKED


def client() -> TestClient:
    return TestClient(app)  # each instance keeps its own session cookie


def last_code(email: str) -> str:
    """The most recent 6-digit code emailed to `email` (subject starts with it)."""
    msg = [m for m in sender.SENT if m["to"] == email.lower()][-1]
    return msg["subject"][:6]


def signup(email: str, name: str = "Test", role_type: str = "employee", verify: bool = True) -> TestClient:
    c = client()
    r = c.post("/auth/signup", json={"email": email, "password": "correct horse", "name": name, "role_type": role_type})
    assert r.status_code == 201, r.text
    if verify:
        assert c.post("/auth/verify", json={"code": last_code(email)}).status_code == 200
    return c


def _seed_history(member_id: int, drivers_by_week, end: datetime | None = None):
    """Insert backdated weekly check-ins directly (the API always stamps 'now')."""
    pred = get_predictor()
    end = end or datetime.now(timezone.utc)
    with db.SessionLocal() as s:
        for week, drivers in enumerate(drivers_by_week):
            ci = CheckIn(drivers=drivers)
            when = end - timedelta(weeks=len(drivers_by_week) - 1 - week, hours=1)
            s.add(new_assessment(member_id, ci, pred.assess(ci), created_at=when))
        s.commit()


def _worsening_weeks(n=8):
    return [HEALTHY.model_copy(update={"sleep_hours": 8 - 0.4 * w, "after_hours_per_week": min(7, w),
                                       "workload": min(5, 2 + w * 0.4), "can_disconnect": max(1, 5 - w * 0.5)})
            for w in range(n)]


def _demo_org(groups: dict[str, int]) -> tuple[int, dict[str, list[int]]]:
    """A public demo organisation with account-less members, like the seed script makes."""
    with db.SessionLocal() as s:
        org = db.Organization(name="Demo Co", kind="company", is_demo=True,
                              groups=[db.Group(name=n) for n in groups])
        s.add(org)
        s.flush()
        ids = {}
        for g in org.groups:
            ids[g.name] = []
            for _ in range(groups[g.name]):
                m = db.Member(org_id=org.id, group_id=g.id, role_type="employee")
                s.add(m)
                s.flush()
                ids[g.name].append(m.id)
        s.commit()
        return org.id, ids


# ── Public ───────────────────────────────────────────────────────

DAILY = {"sleep_hours": 5.5, "work_hours_per_day": 11, "after_hours_per_week": 3.5,
         "workload": 5, "can_disconnect": 2, "support": 2}
WEEKLY_OFTEN = {f"p{i}": 3 for i in range(1, 7)}


def test_everything_needs_login():
    anon = client()
    assert anon.get("/instrument").status_code == 401
    assert anon.post("/predict", json={"drivers": OVERWORKED.model_dump()}).status_code == 401
    assert anon.post("/what-if", json={"drivers": OVERWORKED.model_dump(), "changes": {}}).status_code == 401
    assert anon.get("/demo/personas").status_code == 401
    assert anon.get("/orgs").status_code == 401
    assert anon.get("/health").status_code == 200


def test_instrument_is_short_and_worded_for_the_person():
    c = signup("stu@example.com", role_type="student")
    body = c.get("/instrument").json()
    assert len(body["questions"]) == 6 and len(body["weekly"]) == 6 and body["weekly_due"] is True
    hours = next(q for q in body["questions"] if q["id"] == "work_hours_per_day")
    assert "study" in hours["text"] and all(len(q["options"]) == 5 for q in body["questions"])


def test_predict_and_what_if_with_daily_answers_only():
    c = signup("p@example.com")
    r = c.post("/predict", json={"drivers": DAILY, "cbi_answers": WEEKLY_OFTEN}).json()
    assert r["score_source"] == "measured" and r["measured"] == {"personal": 75.0, "work": None, "overall": 75.0}
    values = {x["feature"]: x["value"] for x in r["explanation"]["contributions"]}
    assert values["autonomy"] == "typical" and values["meetings_per_day"] == "typical"
    assert all(lv["feature"] in DAILY for lv in r["levers"])  # only suggest changes to things we asked
    assert c.post("/predict", json={"drivers": DAILY | {"workload": 9}}).status_code == 422
    assert c.post("/what-if", json={"drivers": DAILY, "changes": {"sleep_hours": 8}}).json()["change"] < 0


# ── Accounts ─────────────────────────────────────────────────────

def test_signup_login_logout_and_me():
    c = signup("Ada@Example.com", "Ada", "student")
    me = c.get("/me").json()
    assert me["user"]["email"] == "ada@example.com" and me["role_type"] == "student" and me["membership"] is None
    assert client().post("/auth/signup", json={"email": "ada@example.com", "password": "another one", "name": "X"}).status_code == 409
    assert client().post("/auth/signup", json={"email": "short@example.com", "password": "short", "name": "X"}).status_code == 422

    fresh = client()
    assert fresh.get("/me").status_code == 401
    assert fresh.post("/auth/login", json={"email": "ada@example.com", "password": "wrong password"}).status_code == 401
    assert fresh.post("/auth/login", json={"email": "ADA@example.com", "password": "correct horse"}).status_code == 200
    assert fresh.get("/me").status_code == 200
    fresh.post("/auth/logout")
    assert fresh.get("/me").status_code == 401


def test_my_check_ins_history_latest_forecast():
    c = signup("me@example.com")
    assert c.get("/me/latest").status_code == 404
    assert c.get("/me").json()["today"] == {"done": False, "weekly_due": True, "next_at": None}
    r = c.post("/me/assessments", json={"drivers": OVERWORKED.model_dump(), "cbi_answers": ALL_OFTEN})
    assert r.status_code == 201
    assert c.get("/me/assessments").json()[0]["measured_score"] == 75
    assert c.get("/me/latest").json()["prediction"]["score"] == 75
    assert c.get("/me/forecast").json()["status"] == "insufficient_data"
    me = c.get("/me").json()
    assert me["check_ins"] == 1 and me["today"]["done"] is True and me["today"]["next_at"]
    assert client().post("/me/assessments", json={"drivers": HEALTHY.model_dump()}).status_code == 401


def test_one_check_in_per_day_in_the_users_timezone():
    c = client()
    c.post("/auth/signup", json={"email": "tz@example.com", "password": "correct horse", "name": "T", "timezone": "Asia/Kolkata"})
    c.post("/auth/verify", json={"code": last_code("tz@example.com")})
    me = c.get("/me").json()
    assert me["timezone"] == "Asia/Kolkata"
    assert c.post("/me/assessments", json={"drivers": DAILY}).status_code == 201
    assert c.post("/me/assessments", json={"drivers": DAILY}).status_code == 409
    # Yesterday's check-in doesn't block today; the weekly measure stays due until it's answered.
    with db.SessionLocal() as s:
        for a in s.query(db.Assessment).filter_by(member_id=me["member_id"]):
            a.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        s.commit()
    today = c.get("/me").json()["today"]
    assert today["done"] is False and today["weekly_due"] is True
    assert c.post("/me/assessments", json={"drivers": DAILY, "cbi_answers": WEEKLY_OFTEN}).status_code == 201
    assert c.get("/instrument").json()["weekly_due"] is False


def test_bad_timezone_falls_back_to_utc():
    c = client()
    c.post("/auth/signup", json={"email": "bad@example.com", "password": "correct horse", "name": "B", "timezone": "Mars/Base"})
    assert c.get("/me").json()["timezone"] == "UTC"


# ── Organisations ────────────────────────────────────────────────

def test_org_invite_consent_and_admin_only_insights():
    owner = signup("hr@acme.com", "HR")
    org = owner.post("/orgs", json={"name": "Acme", "groups": ["Eng", "Ops"]}).json()
    eng = org["groups"][0]["id"]
    assert owner.get("/me").json()["membership"]["role"] == "owner"
    assert owner.post("/orgs", json={"name": "Second"}).status_code == 409

    invite = owner.post(f"/orgs/{org['id']}/invites", json={"group_id": eng}).json()
    preview = client().get(f"/invites/{invite['code']}").json()
    assert preview["org_name"] == "Acme" and preview["min_group_size"] == 5

    worker = signup("dev@acme.com", "Dev")
    assert worker.post(f"/invites/{invite['code']}/accept", json={"consent": False}).status_code == 422
    me = worker.post(f"/invites/{invite['code']}/accept", json={"consent": True}).json()
    assert me["membership"]["role"] == "member" and me["membership"]["group_name"] == "Eng"
    assert me["membership"]["sharing_since"] is not None

    # Members, strangers and anonymous visitors can't see insights; the owner can.
    assert worker.get(f"/orgs/{org['id']}/insights").status_code == 403
    assert signup("stranger@x.com").get(f"/orgs/{org['id']}/insights").status_code == 403
    assert client().get(f"/orgs/{org['id']}/insights").status_code == 403
    assert client().get(f"/orgs/{org['id']}").status_code == 404
    assert owner.get(f"/orgs/{org['id']}/insights").status_code == 200

    admin = owner.get(f"/orgs/{org['id']}/admin").json()
    assert {g["name"]: g["members"] for g in admin["groups"]} == {"Eng": 1, "Ops": 0}
    assert worker.get(f"/orgs/{org['id']}/admin").status_code == 403

    # Revoked invites stop working.
    owner.delete(f"/orgs/{org['id']}/invites/{invite['code']}")
    assert client().get(f"/invites/{invite['code']}").status_code == 404


def test_only_check_ins_after_joining_are_shared():
    owner = signup("lead@co.com")
    org = owner.post("/orgs", json={"name": "Co", "groups": ["Team"]}).json()
    team = org["groups"][0]["id"]
    code = owner.post(f"/orgs/{org['id']}/invites", json={"group_id": team}).json()["code"]

    members = []
    for i in range(6):
        w = signup(f"w{i}@co.com")
        mid = w.get("/me").json()["member_id"]
        _seed_history(mid, _worsening_weeks(4), end=datetime.now(timezone.utc) - timedelta(days=1))  # private, before joining
        w.post(f"/invites/{code}/accept", json={"consent": True})
        members.append(w)

    ins = owner.get(f"/orgs/{org['id']}/insights").json()
    assert ins["respondents"] == 0  # nothing from before they joined leaks to the organisation

    for w in members:
        w.post("/me/assessments", json={"drivers": OVERWORKED.model_dump()})
    ins = owner.get(f"/orgs/{org['id']}/insights").json()
    assert ins["respondents"] == 6 and ins["groups"][0]["suppressed"] is False

    # Stopping sharing or leaving removes you from aggregates immediately.
    members[0].delete("/me/sharing")
    members[1].delete("/me/membership")
    assert owner.get(f"/orgs/{org['id']}/insights").json()["groups"][0]["suppressed"] is True


def test_owner_rules():
    owner = signup("own@co.com")
    org = owner.post("/orgs", json={"name": "Co", "groups": ["A"]}).json()
    assert owner.delete("/me/membership").status_code == 409  # sole owner can't leave
    admin_code = owner.post(f"/orgs/{org['id']}/invites", json={"role": "admin"}).json()["code"]
    hr = signup("hr@co.com")
    assert hr.post(f"/invites/{admin_code}/accept", json={"consent": True}).json()["membership"]["role"] == "admin"
    assert hr.get(f"/orgs/{org['id']}/insights").status_code == 200
    assert hr.post(f"/orgs/{org['id']}/invites", json={"role": "admin"}).status_code == 403  # only owners invite admins
    assert hr.post(f"/orgs/{org['id']}/groups", json={"name": "B"}).status_code == 201
    member_code = owner.post(f"/orgs/{org['id']}/invites", json={}).json()["code"]
    assert signup("m@co.com").post(f"/invites/{member_code}/accept", json={"consent": True}).status_code == 422  # must pick a group
    # admins can opt in to take part themselves
    group_a = org["groups"][0]["id"]
    assert hr.post(f"/me/sharing?group_id={group_a}").json()["membership"]["group_name"] == "A"


# ── Demo (public, read-only) ─────────────────────────────────────

def test_demo_org_is_public_read_only_with_suppression():
    org_id, ids = _demo_org({"Big": 6, "Small": 2})
    for mid in ids["Big"]:
        _seed_history(mid, _worsening_weeks())
    for mid in ids["Small"]:
        _seed_history(mid, [HEALTHY] * 8)

    assert client().get(f"/orgs/{org_id}/insights").status_code == 401  # sample data is for signed-in users
    viewer = signup("viewer@example.com")
    ins = viewer.get(f"/orgs/{org_id}/insights").json()
    big, small = ins["groups"]
    assert big["suppressed"] is False and big["rising_count"] == 6 and big["what_changed"][0]["change"] > 0
    assert small["suppressed"] is True and small["avg_score"] is None and small["rising_count"] is None

    assert [o["name"] for o in viewer.get("/orgs").json()] == ["Demo Co"]
    assert viewer.get(f"/members/{ids['Big'][0]}/forecast").json()["status"] == "rising"
    assert viewer.get(f"/members/{ids['Big'][0]}/latest").status_code == 200
    assert client().get(f"/members/{ids['Big'][0]}/latest").status_code == 401
    personas = viewer.get("/demo/personas").json()
    assert personas and all(p["member_id"] in sum(ids.values(), []) for p in personas)

    hacker = signup("h@x.com")
    assert hacker.post(f"/orgs/{org_id}/invites", json={}).status_code == 403
    assert hacker.post(f"/orgs/{org_id}/groups", json={"name": "X"}).status_code == 403


def test_real_members_are_not_reachable_through_demo_routes():
    c = signup("private@x.com")
    mid = c.get("/me").json()["member_id"]
    c.post("/me/assessments", json={"drivers": HEALTHY.model_dump()})
    other = signup("nosy@example.com")
    assert other.get(f"/members/{mid}/assessments").status_code == 404
    assert other.get(f"/members/{mid}/latest").status_code == 404
    assert other.post("/assessments", json={"member_id": mid, "drivers": HEALTHY.model_dump()}).status_code == 404
