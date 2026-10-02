"""Model endpoints (signed-in users only) and the open health/model-info routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import Group, Member, Organization, User, get_session
from ..ml import content, instrument
from ..ml.forecast import forecast
from ..ml.predictor import get_predictor
from ..records import new_assessment, to_points
from ..schemas import AssessmentCreate, AssessmentRecord, CheckIn, Forecast, Prediction, WhatIfRequest, WhatIfResult
from ..services import history, latest_payload, member_forecast, today_status, user_member

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "model_version": get_predictor().version}


@router.get("/model-info")
def model_info():
    m = get_predictor().metadata
    return {k: m[k] for k in ("version", "trained_at", "target", "training_source", "training_rows",
                              "features", "metrics", "global_importance", "base_score")}


@router.get("/instrument")
def get_instrument(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Today's check-in: 6 daily questions, plus the 6-item weekly burnout measure when it's due."""
    member = user_member(session, user)
    student = member.role_type == "student"
    questions = [
        {"id": f, "text": q.get("student_text", q["text"]) if student else q["text"], "options": q["options"]}
        for f, q in content.DAILY.items()
    ]
    sliders = [
        {"id": f, "label": content.FEATURES[f]["label"], "unit": content.FEATURES[f]["unit"].strip(),
         "min": content.FEATURES[f]["min"], "max": content.FEATURES[f]["max"], "step": content.FEATURES[f]["step"]}
        for f in content.DAILY
    ]
    return {
        "questions": questions,
        "weekly": instrument.weekly_items(),
        "weekly_due": today_status(session, user, member).weekly_due,
        "sliders": sliders,
        "levels": content.LEVELS,
        "citation": "Weekly measure: Copenhagen Burnout Inventory, Personal burnout scale (Kristensen et al., 2005).",
    }


@router.post("/predict", response_model=Prediction)
def predict(check_in: CheckIn, _: User = Depends(current_user)):
    """Preview a reading without saving it (used for the live estimate while answering)."""
    return get_predictor().assess(check_in)


@router.post("/what-if", response_model=WhatIfResult)
def what_if(body: WhatIfRequest, _: User = Depends(current_user)):
    """Estimate how the burnout score would change if some drivers changed."""
    try:
        return get_predictor().what_if(body.drivers, body.changes)
    except ValueError as e:
        raise HTTPException(422, str(e))


# ── Demo people (sample data, signed-in users only) ──────────────

def _demo_member(session: Session, member_id: int) -> Member:
    member = session.get(Member, member_id)
    org = session.get(Organization, member.org_id) if member and member.org_id else None
    if not member or member.user_id is not None or not org or not org.is_demo:
        raise HTTPException(404, "Demo member not found")
    return member


@router.get("/demo/personas")
def demo_personas(_: User = Depends(current_user), session: Session = Depends(get_session)):
    """A few contrasting members from demo orgs."""
    rows = session.execute(
        select(Member, Group.name, Organization.kind)
        .join(Group, Group.id == Member.group_id)
        .join(Organization, Organization.id == Member.org_id)
        .where(Organization.is_demo, Member.user_id.is_(None))
        .order_by(Member.id)
    ).all()
    candidates = []
    for member, group_name, kind in rows:
        hist = history(session, member.id)
        if len(hist) < 3:
            continue
        f = forecast(to_points(hist))
        candidates.append({"member_id": member.id, "group": group_name, "org_kind": kind,
                           "role_type": member.role_type, "score": hist[-1].score,
                           "status": f.status, "early_warning": f.early_warning})

    picks: list[dict] = []

    def pick(title, pred, key):
        pool = [c for c in candidates if pred(c) and c not in picks]
        if pool:
            picks.append({**max(pool, key=key), "title": title})

    pick("Heading for burnout", lambda c: c["early_warning"], lambda c: c["score"])
    pick("Running hot", lambda c: c["org_kind"] == "company", lambda c: c["score"])
    pick("Student in exam season", lambda c: c["role_type"] == "student" and c["status"] == "rising", lambda c: c["score"])
    pick("Doing well", lambda c: True, lambda c: -c["score"])
    return picks


@router.get("/members/{member_id}/assessments", response_model=list[AssessmentRecord])
def demo_history(member_id: int, _: User = Depends(current_user), session: Session = Depends(get_session)):
    return history(session, _demo_member(session, member_id).id)


@router.get("/members/{member_id}/latest")
def demo_latest(member_id: int, _: User = Depends(current_user), session: Session = Depends(get_session)):
    return latest_payload(session, _demo_member(session, member_id))


@router.get("/members/{member_id}/forecast", response_model=Forecast)
def demo_forecast(member_id: int, _: User = Depends(current_user), session: Session = Depends(get_session)):
    return member_forecast(session, _demo_member(session, member_id))


@router.post("/assessments", response_model=Prediction, status_code=201)
def demo_submit(body: AssessmentCreate, _: User = Depends(current_user), session: Session = Depends(get_session)):
    member = _demo_member(session, body.member_id)
    result = get_predictor().assess(body)
    session.add(new_assessment(member.id, body, result))
    session.commit()
    return result
