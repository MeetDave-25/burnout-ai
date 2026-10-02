"""Burnout assessment: validated measurement + explainable driver model.

* WHAT  — the headline score is the Copenhagen Burnout Inventory (CBI) score when the person
          answered it, otherwise the model's estimate from their work/study patterns.
* WHY   — an XGBoost model with monotonic constraints estimates the CBI score from modifiable
          drivers; exact TreeSHAP splits the estimate into per-driver points:
              base_score + sum(contributions) == estimated_score
* WHAT HELPS — "levers": the estimated effect of one realistic improvement per driver.
"""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from ..config import settings
from ..schemas import CheckIn, Contribution, Drivers, Explanation, Lever, ModelCard, Prediction, WhatIfResult
from . import content, instrument


class BurnoutPredictor:
    def __init__(self, model_dir: Path):
        self.model = xgb.XGBRegressor()
        self.model.load_model(model_dir / "model.json")
        self.metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
        self.features: list[str] = self.metadata["features"]
        self.roles: dict[str, int] = self.metadata["roles"]
        self.explainer = shap.TreeExplainer(self.model)
        self.base_score = float(np.asarray(self.explainer.expected_value).ravel()[0])
        self.halfwidth = self.metadata["metrics"]["interval_halfwidth"]
        # Drivers the daily check-in doesn't ask take the population's typical (median) value.
        self.typical = {f: v for f, v in self.metadata["feature_medians"].items() if f not in ("role_type", "remote_work")}
        self.version = self.metadata["version"]

    # ── core model ───────────────────────────────────────────────

    def _frame(self, rows: list[dict]) -> pd.DataFrame:
        encoded = [
            {**{f: (self.typical[f] if r.get(f) is None else r[f]) for f in self.typical},
             "role_type": self.roles[r["role_type"]], "remote_work": int(r["remote_work"])}
            for r in rows
        ]
        return pd.DataFrame(encoded)[self.features].astype(float)

    def estimate(self, drivers: Drivers) -> tuple[float, list[Contribution]]:
        X = self._frame([drivers.model_dump()])
        score = float(np.clip(self.model.predict(X)[0], 0, 100))
        impacts = self.explainer.shap_values(X)[0]
        contributions = sorted(
            (self._contribution(f, drivers, float(impacts[i])) for i, f in enumerate(self.features)),
            key=lambda c: -abs(c.impact),
        )
        return score, contributions

    def _contribution(self, feat: str, drivers: Drivers, impact: float) -> Contribution:
        meta = content.FEATURES[feat]
        raw = getattr(drivers, feat)
        if feat == "remote_work":
            value: float | str = "yes" if raw else "no"
        elif raw is None:
            value = "typical"  # not asked in the daily check-in
        else:
            value = raw
        return Contribution(feature=feat, label=meta["label"], value=value, unit=meta["unit"], impact=round(impact, 2))

    # ── public API ───────────────────────────────────────────────

    def assess(self, check_in: CheckIn) -> Prediction:
        drivers = check_in.drivers
        estimated, contributions = self.estimate(drivers)
        measured = instrument.score(check_in.cbi_answers) if check_in.cbi_answers else None
        score = measured["overall"] if measured else estimated
        level = content.level_for(score)
        pattern = detect_pattern(drivers) if level["level"] > 0 else None
        unexplained = round(measured["overall"] - estimated, 1) if measured else None
        levers = self.levers(drivers, estimated)

        return Prediction(
            score=round(score, 1),
            score_source="measured" if measured else "estimated",
            level=level["level"],
            label=level["label"],
            color=level["color"],
            measured=measured,
            burnout_pattern=pattern,
            explanation=Explanation(
                base_score=round(self.base_score, 1),
                estimated_score=round(estimated, 1),
                interval=(round(max(0, estimated - self.halfwidth), 1), round(min(100, estimated + self.halfwidth), 1)),
                contributions=contributions,
                unexplained=unexplained,
                summary=summarize(score, level["label"], measured is not None, estimated, self.halfwidth,
                                  contributions, unexplained),
            ),
            levers=levers,
            recommendations=recommend(contributions, levers, pattern, level["level"]),
            model=ModelCard(
                version=self.version,
                training_source=self.metadata["training_source"],
                mae=self.metadata["metrics"]["mae"],
                note="The measured score uses a validated questionnaire. The explanation comes from a model that "
                     "has not yet been validated on real-world outcomes.",
            ),
        )

    def levers(self, drivers: Drivers, current: float, top: int = 3) -> list[Lever]:
        base = drivers.model_dump()
        candidates = []
        for feat, meta in content.FEATURES.items():
            if meta["lever"] is None or base.get(feat) is None:  # only suggest changes to things we asked about
                continue
            new = float(np.clip(base[feat] + meta["lever"], meta["min"], meta["max"]))
            if new != base[feat]:
                candidates.append((feat, new))
        if not candidates:
            return []
        preds = self.model.predict(self._frame([{**base, f: v} for f, v in candidates]))
        levers = []
        for (feat, new), pred in zip(candidates, preds):
            delta = float(np.clip(pred, 0, 100)) - current
            if delta <= -0.5:
                meta = content.FEATURES[feat]
                levers.append(Lever(
                    feature=feat, label=meta["label"],
                    change=f"{_num(base[feat])}{meta['unit']} → {_num(new)}{meta['unit']}",
                    expected_change=round(delta, 1),
                ))
        return sorted(levers, key=lambda lv: lv.expected_change)[:top]

    def what_if(self, drivers: Drivers, changes: dict[str, float]) -> WhatIfResult:
        unknown = set(changes) - {f for f, m in content.FEATURES.items() if m["lever"] is not None}
        if unknown:
            raise ValueError(f"Cannot change: {sorted(unknown)}")
        after_drivers = Drivers(**{**drivers.model_dump(), **changes})  # re-validates ranges
        before, before_c = self.estimate(drivers)
        after, after_c = self.estimate(after_drivers)
        before_by = {c.feature: c.impact for c in before_c}
        diff = sorted(
            (c.model_copy(update={"impact": round(c.impact - before_by[c.feature], 2)}) for c in after_c),
            key=lambda c: c.impact,
        )
        return WhatIfResult(before=round(before, 1), after=round(after, 1), change=round(after - before, 1),
                            contributions_change=[c for c in diff if abs(c.impact) >= 0.5])


def _num(v: float) -> str:
    return f"{v:g}"


def detect_pattern(d: Drivers) -> str:
    """Rule-based burnout archetype from drivers (Paper 1 typology). Replace with a learned model once labelled."""
    hi = lambda v: 0.5 if v is None else (v - 1) / 4  # noqa: E731  Likert 1..5 -> 0..1; unasked = neutral
    scores = {
        "Frenetic": np.mean([np.clip((d.work_hours_per_day - 8) / 4, 0, 1), d.after_hours_per_week / 7,
                             hi(d.workload), 1 - hi(d.can_disconnect)]),
        "Under-Challenged": np.mean([1 - hi(d.workload), 1 - hi(d.autonomy), 1 - hi(d.recognition)]),
        "Worn-Out": np.mean([hi(d.workload), 1 - hi(d.support), 1 - hi(d.autonomy), 1 - hi(d.recognition)]),
    }
    return max(scores, key=scores.get)


def _fmt(c: Contribution) -> str:
    return f"{c.label.lower()} ({_num(c.value) if isinstance(c.value, float) else c.value}{c.unit}, {c.impact:+.0f})"


def summarize(score, label, measured, estimated, halfwidth, contributions, unexplained) -> str:
    if measured:
        parts = [f"Your burnout score is {score:.0f}/100 ({label}), measured with the Copenhagen Burnout Inventory.",
                 f"Your work patterns alone point to about {estimated:.0f}."]
    else:
        parts = [f"Estimated burnout score: {score:.0f}/100 ({label}), give or take {halfwidth:.0f}, based on your "
                 "work patterns. Answer the 13 CBI questions for a measured score."]
    raising = [c for c in contributions if c.impact >= 1][:3]
    lowering = [c for c in contributions if c.impact <= -1][:2]
    if raising:
        parts.append("Pushing it up: " + ", ".join(_fmt(c) for c in raising) + ".")
    if lowering:
        parts.append("Working in your favour: " + ", ".join(_fmt(c) for c in lowering) + ".")
    if unexplained is not None and unexplained >= 15:
        parts.append(f"About {unexplained:.0f} points aren't explained by the work factors we track — "
                     "something outside them (health, life events, finances) may be adding to the strain.")
    return " ".join(parts)


def recommend(contributions, levers, pattern, level) -> list[str]:
    recs = [content.PATTERNS[pattern]] if pattern else []
    lever_features = [lv.feature for lv in levers]
    raising = [c.feature for c in contributions if c.impact >= 1]
    for feat in dict.fromkeys(lever_features + raising):
        advice = content.FEATURES[feat]["advice"]
        if advice:
            recs.append(advice)
        if len(recs) >= 4:
            break
    if level >= 2:
        recs.append("Your burnout score is high. Please consider talking to a doctor, counsellor or your "
                    "employee/student assistance programme.")
    return recs or ["Keep your current routines and check in again next week."]


@lru_cache
def get_predictor() -> BurnoutPredictor:
    return BurnoutPredictor(settings.model_dir)
