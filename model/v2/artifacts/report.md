# BurnoutAI driver model 2.0.0-prior

- Trained: 2026-10-02T03:55:23+00:00 on 12,267 rows
- Source: **simulation calibrated to published burnout research (JD-R model)**
- Target: Copenhagen Burnout Inventory score (0-100)

## Test-set performance

| Metric | XGBoost (monotonic) | Ridge baseline |
|---|---|---|
| MAE (CBI points) | 12.0 | 11.93 |
| R² | 0.292 | 0.299 |
| AUC for CBI ≥ 50 | 0.76 | – |
| 80% interval | ±19.4 pts, covers 79.8% of test cases | – |

## What these numbers mean

These scores measure how well the model recovers a **simulated** population. They show the
pipeline works and the model behaves sensibly; they are **not** evidence of real-world accuracy.
The simulation deliberately leaves ~70% of burnout variance unexplained by work factors, so
an R² near 0.3 is the expected ceiling, not a weakness.

Real accuracy comes from pilot data: once ≥300 real check-ins with CBI answers exist, run
`python train.py --from-db <DATABASE_URL>` and compare this report.

## Global feature importance (mean |SHAP|, CBI points)

- workload: 2.724
- can_disconnect: 2.671
- sleep_hours: 1.772
- support: 1.134
- after_hours_per_week: 1.063
- autonomy: 0.978
- work_hours_per_day: 0.821
- recognition: 0.694
- meetings_per_day: 0.597
- days_off_last_month: 0.272
- role_type: 0.177
- remote_work: 0.048

## Monotonic sanity checks

- work_hours_per_day: pass
- after_hours_per_week: pass
- meetings_per_day: pass
- sleep_hours: pass
- days_off_last_month: pass
- workload: pass
- autonomy: pass
- support: pass
- recognition: pass
- can_disconnect: pass

## Simulation calibration vs. research correlation bands

- workload: r = +0.436, target [0.3, 0.55] — OK
- work_hours_per_day: r = +0.386, target [0.15, 0.4] — OK
- after_hours_per_week: r = +0.361, target [0.15, 0.4] — OK
- sleep_hours: r = -0.392, target [-0.45, -0.15] — OK
- support: r = -0.296, target [-0.4, -0.15] — OK
- autonomy: r = -0.268, target [-0.35, -0.1] — OK
- recognition: r = -0.258, target [-0.35, -0.1] — OK
- can_disconnect: r = -0.446, target [-0.5, -0.25] — OK
- days_off_last_month: r = -0.242, target [-0.3, -0.05] — OK
