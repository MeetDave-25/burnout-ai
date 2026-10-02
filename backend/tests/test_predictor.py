import pytest

from app.ml import instrument
from app.ml.predictor import get_predictor
from app.schemas import CheckIn, Drivers

HEALTHY = Drivers(
    work_hours_per_day=7.5, after_hours_per_week=0, meetings_per_day=2, sleep_hours=8, days_off_last_month=4,
    workload=2, autonomy=4, support=5, recognition=4, can_disconnect=5,
)
OVERWORKED = Drivers(
    work_hours_per_day=11.5, after_hours_per_week=5, meetings_per_day=7, sleep_hours=5, days_off_last_month=0,
    workload=5, autonomy=2, support=2, recognition=2, can_disconnect=1, remote_work=True,
)
ALL_OFTEN = {i: 3 for i in instrument.ALL_IDS}  # CBI = 75


@pytest.mark.parametrize("drivers", [HEALTHY, OVERWORKED])
def test_shap_contributions_add_up_to_estimate(drivers):
    p = get_predictor().assess(CheckIn(drivers=drivers))
    e = p.explanation
    assert e.base_score + sum(c.impact for c in e.contributions) == pytest.approx(e.estimated_score, abs=0.5)
    assert e.interval[0] <= e.estimated_score <= e.interval[1]


def test_estimated_risk_ordering_and_reasons():
    pred = get_predictor()
    healthy, burnt = pred.assess(CheckIn(drivers=HEALTHY)), pred.assess(CheckIn(drivers=OVERWORKED))
    assert healthy.score_source == "estimated" and healthy.level == 0 and healthy.burnout_pattern is None
    assert burnt.score > healthy.score + 30
    assert burnt.burnout_pattern == "Frenetic"
    assert burnt.explanation.contributions[0].impact > 0
    assert burnt.levers and all(lv.expected_change < 0 for lv in burnt.levers)
    assert healthy.levers == [] or all(lv.expected_change < 0 for lv in healthy.levers)


def test_measured_score_is_headline_and_gap_reported():
    p = get_predictor().assess(CheckIn(drivers=HEALTHY, cbi_answers=ALL_OFTEN))
    assert p.score_source == "measured" and p.score == 75 and p.label == "High"
    assert p.explanation.unexplained == pytest.approx(75 - p.explanation.estimated_score, abs=0.11)
    assert "aren't explained" in p.explanation.summary
    assert any("doctor" in r for r in p.recommendations)


@pytest.mark.parametrize("feature,worse", [
    ("sleep_hours", 4), ("work_hours_per_day", 13), ("support", 1), ("can_disconnect", 1), ("workload", 5),
])
def test_monotonic_worse_input_never_lowers_estimate(feature, worse):
    pred = get_predictor()
    base, _ = pred.estimate(HEALTHY)
    worse_score, _ = pred.estimate(HEALTHY.model_copy(update={feature: worse}))
    assert worse_score >= base


def test_what_if():
    pred = get_predictor()
    r = pred.what_if(OVERWORKED, {"sleep_hours": 7.5, "after_hours_per_week": 1})
    assert r.after < r.before and r.change == pytest.approx(r.after - r.before, abs=0.11)
    assert {c.feature for c in r.contributions_change} >= {"sleep_hours", "after_hours_per_week"}
    with pytest.raises(ValueError):
        pred.what_if(OVERWORKED, {"role_type": 1})
