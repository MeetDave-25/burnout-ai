"""Train the v2 burnout driver model.

    python train.py                       # prior model from the calibrated simulation
    python train.py --from-db URL         # retrain on real check-ins (needs CBI answers)

Target: Copenhagen Burnout Inventory score (0–100).
Model:  XGBoost regressor with monotonic constraints, so an explanation can never say
        "sleeping less lowered your risk". Explained with exact TreeSHAP.
Output: artifacts/model.json, artifacts/metadata.json, artifacts/report.md
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split

from simulate import FEATURES, MONOTONE, ROLES, calibration_check, simulate

OUT = Path(__file__).parent / "artifacts"
HIGH_BURNOUT = 50  # CBI cut-off commonly used for high burnout
PI_COVERAGE = 0.8
PARAMS = dict(n_estimators=1000, learning_rate=0.03, max_depth=4, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=20, early_stopping_rounds=50, random_state=42)


def load_real(url: str, min_rows: int) -> pd.DataFrame:
    """Real check-ins that include CBI answers, excluding demo organisations."""
    from sqlalchemy import create_engine, text

    query = text("""
        SELECT a.inputs, a.measured_score FROM assessments a
        JOIN members m ON m.id = a.member_id
        JOIN organizations o ON o.id = m.org_id
        WHERE a.measured_score IS NOT NULL AND NOT o.is_demo
    """)
    with create_engine(url).connect() as conn:
        rows = conn.execute(query).all()
    if len(rows) < min_rows:
        raise SystemExit(f"Only {len(rows)} real check-ins with CBI answers; need at least {min_rows}.")
    records = []
    for inputs, score in rows:
        inputs = json.loads(inputs) if isinstance(inputs, str) else inputs
        rec = {f: inputs[f] for f in FEATURES}
        rec["role_type"] = ROLES[rec["role_type"]]
        rec["remote_work"] = int(rec["remote_work"])
        rec["cbi_score"] = score
        records.append(rec)
    return pd.DataFrame(records)


def check_monotonic(model: xgb.XGBRegressor, X: pd.DataFrame) -> dict[str, bool]:
    sample = X.sample(200, random_state=0)
    result = {}
    for feat, sign in MONOTONE.items():
        if sign == 0:
            continue
        grid = np.linspace(X[feat].min(), X[feat].max(), 15)
        preds = []
        for v in grid:
            probe = sample.copy()
            probe[feat] = v
            preds.append(model.predict(probe))
        diffs = np.diff(np.array(preds), axis=0) * sign
        result[feat] = bool((diffs >= -1e-4).all())
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-db", help="SQLAlchemy URL of the app database")
    ap.add_argument("--min-rows", type=int, default=300)
    args = ap.parse_args()

    if args.from_db:
        df, source = load_real(args.from_db, args.min_rows), "real check-ins"
        calibration = None
    else:
        df, source = simulate(), "simulation calibrated to published burnout research (JD-R model)"
        calibration = calibration_check(df)

    X, y = df[FEATURES], df["cbi_score"]
    X_tmp, X_test, y_tmp, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    X_tmp, X_cal, y_tmp, y_cal = train_test_split(X_tmp, y_tmp, test_size=0.18, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_tmp, y_tmp, test_size=0.12, random_state=42)

    model = xgb.XGBRegressor(monotone_constraints=tuple(MONOTONE[f] for f in FEATURES), **PARAMS)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    # Split-conformal prediction interval: holds ~80% coverage without distribution assumptions.
    cal_resid = np.abs(y_cal - model.predict(X_cal))
    k = int(np.ceil((len(cal_resid) + 1) * PI_COVERAGE))
    halfwidth = float(np.sort(cal_resid)[min(k, len(cal_resid)) - 1])

    pred = model.predict(X_test)
    baseline = Ridge().fit(X_train, y_train).predict(X_test)
    coverage = float(np.mean(np.abs(y_test - pred) <= halfwidth))
    high = (y_test >= HIGH_BURNOUT).astype(int)

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_test.iloc[:2000])
    importance = dict(sorted(
        {f: round(float(v), 3) for f, v in zip(FEATURES, np.abs(sv).mean(0))}.items(), key=lambda kv: -kv[1]
    ))

    metrics = {
        "test_rows": len(X_test),
        "mae": round(float(mean_absolute_error(y_test, pred)), 2),
        "r2": round(float(r2_score(y_test, pred)), 3),
        "baseline_ridge_mae": round(float(mean_absolute_error(y_test, baseline)), 2),
        "baseline_ridge_r2": round(float(r2_score(y_test, baseline)), 3),
        "high_burnout_auc": round(float(roc_auc_score(high, pred)), 3),
        "interval_halfwidth": round(halfwidth, 1),
        "interval_coverage_target": PI_COVERAGE,
        "interval_coverage_test": round(coverage, 3),
    }
    monotonic = check_monotonic(model, X_test)
    assert all(monotonic.values()), f"Monotonic constraint violated: {monotonic}"

    OUT.mkdir(exist_ok=True)
    model.save_model(OUT / "model.json")
    version = f"2.0.0-{'real' if args.from_db else 'prior'}"
    metadata = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": "Copenhagen Burnout Inventory score (0-100)",
        "training_source": source,
        "training_rows": len(X_train),
        "features": FEATURES,
        "monotone": MONOTONE,
        "roles": ROLES,
        "base_score": round(float(np.asarray(explainer.expected_value).ravel()[0]), 2),
        "feature_medians": {f: float(X[f].median()) for f in FEATURES},
        "metrics": metrics,
        "global_importance": importance,
        "simulation_calibration": calibration,
        "monotonic_check": monotonic,
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(render_report(metadata), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


def render_report(m: dict) -> str:
    mt = m["metrics"]
    lines = [
        f"# BurnoutAI driver model {m['version']}",
        "",
        f"- Trained: {m['trained_at']} on {m['training_rows']:,} rows",
        f"- Source: **{m['training_source']}**",
        f"- Target: {m['target']}",
        "",
        "## Test-set performance",
        "",
        "| Metric | XGBoost (monotonic) | Ridge baseline |",
        "|---|---|---|",
        f"| MAE (CBI points) | {mt['mae']} | {mt['baseline_ridge_mae']} |",
        f"| R² | {mt['r2']} | {mt['baseline_ridge_r2']} |",
        f"| AUC for CBI ≥ {HIGH_BURNOUT} | {mt['high_burnout_auc']} | – |",
        f"| {int(mt['interval_coverage_target'] * 100)}% interval | ±{mt['interval_halfwidth']} pts, "
        f"covers {mt['interval_coverage_test'] * 100:.1f}% of test cases | – |",
        "",
        "## What these numbers mean",
        "",
    ]
    if "prior" in m["version"]:
        lines += [
            "These scores measure how well the model recovers a **simulated** population. They show the",
            "pipeline works and the model behaves sensibly; they are **not** evidence of real-world accuracy.",
            "The simulation deliberately leaves ~70% of burnout variance unexplained by work factors, so",
            "an R² near 0.3 is the expected ceiling, not a weakness.",
            "",
            "Real accuracy comes from pilot data: once ≥300 real check-ins with CBI answers exist, run",
            "`python train.py --from-db <DATABASE_URL>` and compare this report.",
            "",
        ]
    lines += ["## Global feature importance (mean |SHAP|, CBI points)", ""]
    lines += [f"- {f}: {v}" for f, v in m["global_importance"].items()]
    lines += ["", "## Monotonic sanity checks", ""]
    lines += [f"- {f}: {'pass' if ok else 'FAIL'}" for f, ok in m["monotonic_check"].items()]
    if m["simulation_calibration"]:
        lines += ["", "## Simulation calibration vs. research correlation bands", ""]
        lines += [f"- {f}: r = {c['r']:+.3f}, target {c['target']} — {'OK' if c['ok'] else 'OUT'}"
                  for f, c in m["simulation_calibration"].items()]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
