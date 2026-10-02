from datetime import datetime, timedelta, timezone

import pytest

from app.ml import instrument
from app.ml.forecast import Point, forecast

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_cbi_scoring():
    assert instrument.score({i: 0 for i in instrument.ALL_IDS}) == {"personal": 0, "work": 0, "overall": 0}
    mixed = {i: 4 for i in instrument.PERSONAL_IDS} | {i: 2 for i in instrument.WORK_IDS}
    assert instrument.score(mixed) == {"personal": 100, "work": 50, "overall": 75}
    # the weekly measure (Personal scale alone) scores on its own
    assert instrument.score({i: 2 for i in instrument.PERSONAL_IDS}) == {"personal": 50, "work": None, "overall": 50}
    # fewer than half of the Personal scale answered -> no score
    assert instrument.score({"p1": 3, "p2": 3, "w1": 3}) is None
    with pytest.raises(ValueError):
        instrument.score({"p1": 7})
    with pytest.raises(ValueError):
        instrument.score({"zz": 1})


def test_reversed_item_option_values():
    q = instrument.questionnaire("student")
    w7 = next(i for s in q["scales"] for i in s["items"] if i["id"] == "w7")
    always = next(o for o in w7["options"] if o["label"] == "Always")
    assert always["value"] == 0  # always having energy = least burnout
    assert "studies" in q["scales"][1]["items"][0]["text"]


def _points(scores, contributions=None):
    n = len(scores)
    return [Point(at=NOW - timedelta(weeks=n - 1 - i), score=s,
                  contributions=(contributions or (lambda i: []))(i)) for i, s in enumerate(scores)]


def test_forecast_needs_history():
    f = forecast(_points([40, 42]))
    assert f.status == "insufficient_data" and f.current == 42


def test_rising_trend_triggers_early_warning_with_reasons():
    sleep = lambda i: [{"feature": "sleep_hours", "impact": i * 1.5}, {"feature": "support", "impact": -1}]  # noqa: E731
    f = forecast(_points([28, 31, 34, 37, 40, 43], sleep))
    assert f.status == "rising" and f.slope_per_week == pytest.approx(3, abs=0.1)
    assert f.early_warning and f.weeks_to_threshold == pytest.approx(2.3, abs=0.3)
    assert f.projected_interval[0] <= f.projected <= f.projected_interval[1]
    assert f.what_changed[0].feature == "sleep_hours" and f.what_changed[0].change > 0
    assert "early warning" in f.summary


def test_stable_and_improving():
    assert forecast(_points([50, 51, 49, 50, 50])).status == "stable"
    improving = forecast(_points([70, 66, 62, 58]))
    assert improving.status == "improving" and not improving.early_warning
