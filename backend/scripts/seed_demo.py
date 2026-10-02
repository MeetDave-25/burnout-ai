"""Seed a demo company and school with 8 weeks of weekly check-ins.

Usage (from backend/):  python -m scripts.seed_demo [--reset]

Demo orgs are flagged `is_demo`, so they are never used to retrain the model.
"""

import argparse
from datetime import datetime, timedelta, timezone

import numpy as np

from sqlalchemy import select

from app.config import settings
from app.db import Base, Group, Member, Organization, SessionLocal, engine
from app.migrate import upgrade
from app.ml import instrument
from app.ml.content import FEATURES
from app.ml.predictor import get_predictor
from app.records import new_assessment
from app.schemas import CheckIn, Drivers

WEEKS = 8
CBI_RATE = 0.7  # share of check-ins that include the full CBI questionnaire
rng = np.random.default_rng(7)

KEYS = dict(h="work_hours_per_day", late="after_hours_per_week", meet="meetings_per_day", sleep="sleep_hours",
            off="days_off_last_month", wl="workload", au="autonomy", sup="support", rec="recognition",
            dis="can_disconnect")
NOISE = dict(h=0.6, late=0.8, meet=0.8, sleep=0.4, off=1.0)  # Likert items default to 0.35

# (group, headcount, role, starting profile, weekly drift)
COMPANY = [
    ("Engineering", 14, "employee",
     dict(h=9.0, late=1.5, meet=4, sleep=7.0, off=2, wl=3.2, au=3.6, sup=3.4, rec=3.2, dis=3.2),
     dict(h=0.15, late=0.3, sleep=-0.12, wl=0.12, dis=-0.15)),           # release crunch building up
    ("Customer Support", 9, "employee",
     dict(h=8.5, late=0.5, meet=3, sleep=6.8, off=2, wl=3.4, au=2.4, sup=2.8, rec=2.6, dis=3.0),
     dict(sup=-0.08, rec=-0.08, wl=0.06)),                                # worn-out drift
    ("Product", 7, "employee",
     dict(h=8.2, late=0.5, meet=6, sleep=7.2, off=3, wl=3.0, au=3.4, sup=3.6, rec=3.2, dis=3.4), {}),
    ("Sales", 8, "employee",
     dict(h=8.0, late=0.3, meet=4, sleep=7.4, off=4, wl=2.6, au=4.0, sup=4.0, rec=4.0, dis=3.9),
     dict(wl=-0.03)),
    ("Legal", 3, "employee",
     dict(h=8.5, late=1.0, meet=3, sleep=7.0, off=3, wl=3.0, au=3.5, sup=3.5, rec=3.5, dis=3.0), {}),
]
SCHOOL = [
    ("CS — Final Year", 12, "student",
     dict(h=9.0, late=2.0, meet=4, sleep=6.6, off=2, wl=3.4, au=3.0, sup=3.0, rec=3.0, dis=2.8),
     dict(h=0.15, late=0.3, sleep=-0.1, wl=0.1, dis=-0.1)),              # exam season
    ("Design — Year 2", 8, "student",
     dict(h=7.0, late=0.5, meet=4, sleep=7.4, off=4, wl=2.6, au=3.8, sup=3.8, rec=3.6, dis=3.8), {}),
]


def sample_drivers(profile, drift, offset, week, role) -> Drivers:
    values = {}
    for k, base in profile.items():
        feat = KEYS[k]
        meta = FEATURES[feat]
        v = base + offset[k] + drift.get(k, 0) * week + rng.normal(0, NOISE.get(k, 0.35))
        v = float(np.clip(v, meta["min"], meta["max"]))
        values[feat] = round(v) if meta["step"] == 1 else round(v * 2) / 2
    return Drivers(**values, role_type=role, remote_work=bool(rng.random() < 0.35))


def sample_cbi(true_score: float) -> dict[str, int]:
    return {i: int(np.clip(round((true_score + rng.normal(0, 12)) / 25), 0, 4)) for i in instrument.ALL_IDS}


def seed_org(session, name, kind, spec, now) -> Organization:
    predictor = get_predictor()
    org = Organization(name=name, kind=kind, is_demo=True, groups=[Group(name=g[0]) for g in spec])
    session.add(org)
    session.flush()
    for group, (_, headcount, role, profile, drift) in zip(org.groups, spec):
        for _ in range(headcount):
            member = Member(org_id=org.id, group_id=group.id, role_type=role)
            session.add(member)
            session.flush()
            offset = {k: rng.normal(0, NOISE.get(k, 0.35) * 1.2) for k in profile}
            personal = rng.normal(0, 8)  # burnout not explained by work factors
            for week in range(WEEKS):
                if rng.random() < 0.1:  # ~10% of check-ins skipped
                    continue
                drivers = sample_drivers(profile, drift, offset, week, role)
                estimate, _ = predictor.estimate(drivers)
                answers = sample_cbi(estimate + personal) if rng.random() < CBI_RATE else None
                check_in = CheckIn(drivers=drivers, cbi_answers=answers)
                when = now - timedelta(weeks=WEEKS - 1 - week, hours=float(rng.uniform(1, 48)))
                session.add(new_assessment(member.id, check_in, predictor.assess(check_in), created_at=when))
    return org


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()
    if args.reset:
        if settings.is_production:
            raise SystemExit("Refusing to --reset a production database.")
        Base.metadata.drop_all(engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    upgrade()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        if session.scalar(select(Organization).where(Organization.is_demo)):
            print("Sample organisations already exist; nothing to do.")
            return
        for name, kind, spec in (("Acme Corp (demo)", "company", COMPANY),
                                 ("Northfield University (demo)", "school", SCHOOL)):
            org = seed_org(session, name, kind, spec, now)
            print(f"Seeded org {org.id}: {org.name}")
        session.commit()


if __name__ == "__main__":
    main()
