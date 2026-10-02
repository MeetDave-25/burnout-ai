from datetime import datetime, timedelta, timezone

from app import db, security
from app.email import sender
from tests.test_api import DAILY, client, last_code, signup

PW = "correct horse"


def emails_to(addr: str) -> list[dict]:
    return [m for m in sender.SENT if m["to"] == addr]


# ── Email verification ───────────────────────────────────────────

def test_signup_emails_a_code_and_app_is_locked_until_verified():
    c = client()
    me = c.post("/auth/signup", json={"email": "new@example.com", "password": PW, "name": "Nia"}).json()
    assert me["user"]["email_verified"] is False
    mail = emails_to("new@example.com")[-1]
    assert "verification code" in mail["subject"] and mail["subject"][:6] in mail["html"].replace(" ", "")
    assert "<table" in mail["html"] and mail["text"]  # branded HTML + plain-text part

    assert c.get("/me").status_code == 200  # can see who they are…
    assert c.get("/instrument").status_code == 403  # …but nothing else
    assert c.post("/me/assessments", json={"drivers": DAILY}).status_code == 403

    wrong = "000000" if last_code("new@example.com") != "000000" else "111111"
    r = c.post("/auth/verify", json={"code": wrong})
    assert r.status_code == 400 and "attempts left" in r.json()["detail"]
    assert c.post("/auth/verify", json={"code": "12ab"}).status_code == 422
    me = c.post("/auth/verify", json={"code": last_code("new@example.com")}).json()
    assert me["user"]["email_verified"] is True
    assert "Welcome" in emails_to("new@example.com")[-1]["subject"]
    assert c.get("/instrument").status_code == 200


def test_verification_can_be_switched_off(monkeypatch):
    from app import auth
    from app.routers import accounts

    monkeypatch.setattr(auth, "verification_required", lambda: False)
    monkeypatch.setattr(accounts, "verification_required", lambda: False)
    c = client()
    me = c.post("/auth/signup", json={"email": "quick@example.com", "password": PW, "name": "Q"}).json()
    assert me["user"]["email_verified"] is True
    assert "Welcome" in emails_to("quick@example.com")[-1]["subject"]  # no code email
    assert c.get("/instrument").status_code == 200


def test_codes_lock_after_five_wrong_tries_and_resend_replaces_them():
    c = client()
    c.post("/auth/signup", json={"email": "x@example.com", "password": PW, "name": "X"})
    first = last_code("x@example.com")
    wrong = "999999" if first != "999999" else "888888"
    for _ in range(5):
        assert c.post("/auth/verify", json={"code": wrong}).status_code == 400
    assert c.post("/auth/verify", json={"code": first}).status_code == 429  # locked, even with the right code
    assert c.post("/auth/verify/resend").status_code == 204
    second = last_code("x@example.com")
    assert c.post("/auth/verify", json={"code": second}).status_code == 200


def test_expired_codes_are_rejected():
    c = client()
    c.post("/auth/signup", json={"email": "old@example.com", "password": PW, "name": "O"})
    with db.SessionLocal() as s:
        for otp in s.query(db.OtpCode):
            otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.commit()
    r = c.post("/auth/verify", json={"code": last_code("old@example.com")})
    assert r.status_code == 400 and "expired" in r.json()["detail"]


# ── Password reset & change ──────────────────────────────────────

def test_forgot_password_never_reveals_accounts_and_resets_with_code():
    owner = signup("forgot@example.com")
    sender.SENT.clear()
    anon = client()
    assert anon.post("/auth/forgot", json={"email": "nobody@example.com"}).status_code == 204
    assert sender.SENT == []  # same answer, no email, for unknown addresses
    assert anon.post("/auth/forgot", json={"email": "Forgot@Example.com"}).status_code == 204
    code = last_code("forgot@example.com")
    assert "reset" in emails_to("forgot@example.com")[-1]["subject"]

    r = anon.post("/auth/reset", json={"email": "forgot@example.com", "code": code, "password": "brand new password"})
    assert r.status_code == 200 and anon.get("/me").status_code == 200
    assert "password was changed" in emails_to("forgot@example.com")[-1]["subject"]
    # the old session is signed out, the old password is dead, the code can't be reused
    assert owner.get("/me").status_code == 401
    assert client().post("/auth/login", json={"email": "forgot@example.com", "password": PW}).status_code == 401
    assert client().post("/auth/login", json={"email": "forgot@example.com", "password": "brand new password"}).status_code == 200
    assert client().post("/auth/reset", json={"email": "forgot@example.com", "code": code, "password": "x" * 9}).status_code == 400


def test_change_password_keeps_this_device_signs_out_others():
    a = signup("pw@example.com")
    other = client()
    other.post("/auth/login", json={"email": "pw@example.com", "password": PW})
    assert a.post("/me/password", json={"current_password": "nope nope", "new_password": "longer password"}).status_code == 400
    assert a.post("/me/password", json={"current_password": PW, "new_password": "longer password"}).status_code == 200
    assert a.get("/me").status_code == 200
    assert other.get("/me").status_code == 401


# ── Rate limits ──────────────────────────────────────────────────

def test_rate_limits(monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMITS", True)
    signup("rl@example.com")
    c = client()
    for _ in range(8):
        assert c.post("/auth/login", json={"email": "rl@example.com", "password": "wrong wrong"}).status_code == 401
    r = c.post("/auth/login", json={"email": "rl@example.com", "password": PW})
    assert r.status_code == 429 and r.headers["retry-after"] == "900"  # even the right password, for a while

    u = client()
    u.post("/auth/signup", json={"email": "rs@example.com", "password": PW, "name": "R"})
    assert u.post("/auth/verify/resend").status_code == 204
    assert u.post("/auth/verify/resend").status_code == 429  # one per 45 seconds

    sender.SENT.clear()
    f = client()
    for _ in range(5):
        assert f.post("/auth/forgot", json={"email": "rl@example.com"}).status_code == 204
    assert len(emails_to("rl@example.com")) == 3  # quietly capped at 3 per 15 minutes


# ── Profile, reminders, privacy rights ───────────────────────────

def test_reminders_and_one_click_unsubscribe():
    from scripts.send_reminders import run

    c = signup("rem@example.com")
    sender.SENT.clear()
    noon_utc = datetime.now(timezone.utc).replace(hour=12, minute=0)
    assert run(noon_utc) == 1 and run(noon_utc) == 0  # once per day
    mail = emails_to("rem@example.com")[-1]
    token_url = mail["text"].split("Turn off reminders: ")[1].strip()
    path = token_url.split("/api", 1)[1]  # links point at <APP_URL>/api/unsubscribe
    assert "Reminders turned off" in client().get(path).text
    assert c.get("/me").json()["user"]["reminders"] is False
    assert c.patch("/me", json={"reminders": True}).json()["user"]["reminders"] is True

    c.post("/me/assessments", json={"drivers": DAILY})
    with db.SessionLocal() as s:
        s.query(db.User).update({"last_reminded_on": None})
        s.commit()
    assert run(noon_utc) == 0  # already checked in today: no nagging


def test_export_and_delete_account():
    c = signup("gone@example.com")
    c.post("/me/assessments", json={"drivers": DAILY})
    export = c.get("/me/export")
    assert export.headers["content-disposition"].startswith("attachment")
    data = export.json()
    assert data["account"]["email"] == "gone@example.com" and len(data["check_ins"]) == 1

    assert c.request("DELETE", "/me", json={"password": "wrong wrong"}).status_code == 400
    assert c.request("DELETE", "/me", json={"password": PW}).status_code == 204
    assert c.get("/me").status_code == 401
    assert "deleted" in emails_to("gone@example.com")[-1]["subject"]
    assert client().post("/auth/login", json={"email": "gone@example.com", "password": PW}).status_code == 401
    with db.SessionLocal() as s:
        assert s.query(db.Assessment).count() == 0 and s.query(db.User).count() == 0


def test_deleting_sole_owner_closes_org_but_members_keep_their_data():
    owner = signup("boss@example.com")
    org = owner.post("/orgs", json={"name": "Shortlived", "groups": ["A"]}).json()
    code = owner.post(f"/orgs/{org['id']}/invites", json={"group_id": org["groups"][0]["id"]}).json()["code"]
    worker = signup("worker@example.com")
    worker.post(f"/invites/{code}/accept", json={"consent": True})
    worker.post("/me/assessments", json={"drivers": DAILY})

    assert owner.request("DELETE", "/me", json={"password": PW}).status_code == 204
    me = worker.get("/me").json()
    assert me["membership"] is None and me["check_ins"] == 1


# ── Invites by email ─────────────────────────────────────────────

def test_invite_by_email():
    owner = signup("hr@example.com", "Hana HR")
    org = owner.post("/orgs", json={"name": "Mailco", "groups": ["Ops"]}).json()
    r = owner.post(f"/orgs/{org['id']}/invites/email",
                   json={"emails": ["a@example.com", "B@example.com", "a@example.com"], "group_id": org["groups"][0]["id"]})
    assert r.status_code == 201 and r.json()["sent"] == 2
    mail = emails_to("b@example.com")[-1]
    assert "Hana HR invited you to Mailco" in mail["subject"] and f"/join/{r.json()['invite']['code']}" in mail["text"]
    assert owner.post(f"/orgs/{org['id']}/invites/email", json={"emails": ["not-an-email"]}).status_code == 422
    assert signup("member@example.com").post(f"/orgs/{org['id']}/invites/email", json={"emails": ["c@example.com"]}).status_code == 403
