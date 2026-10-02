"""Helpers that turn predictions into stored assessments and history into forecasts."""

from datetime import datetime

from .db import Assessment
from .ml.forecast import Point
from .schemas import CheckIn, Prediction


def new_assessment(member_id: int, check_in: CheckIn, result: Prediction, created_at: datetime | None = None) -> Assessment:
    a = Assessment(
        member_id=member_id,
        inputs=check_in.drivers.model_dump(),
        cbi_answers=check_in.cbi_answers,
        measured_score=result.measured["overall"] if result.measured else None,
        estimated_score=result.explanation.estimated_score,
        score=result.score,
        score_source=result.score_source,
        level=result.level,
        burnout_pattern=result.burnout_pattern,
        contributions=[c.model_dump(include={"feature", "label", "impact"}) for c in result.explanation.contributions],
        model_version=result.model.version,
    )
    if created_at:
        a.created_at = created_at
    return a


def to_points(assessments: list[Assessment]) -> list[Point]:
    return [Point(at=a.created_at, score=a.score, contributions=a.contributions) for a in assessments]
