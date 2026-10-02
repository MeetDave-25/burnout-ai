"""Research-calibrated simulation used to train the *prior* driver model.

Why simulate at all?  No public dataset pairs a validated burnout measure with the
work/study drivers this product collects. Until real check-ins accumulate (see
`train.py --from-db`), we train on a structural simulation built on the
Job Demands–Resources (JD-R) model of burnout:

  * demands (workload, hours, after-hours work, meetings) raise burnout
  * resources (support, autonomy, recognition, sleep, time off, detachment) lower it
  * high demands hurt more when resources are low (buffering interaction)
  * short sleep (<6h) and very long days (>10h) have non-linear effects

The outcome is on the Copenhagen Burnout Inventory (CBI) 0–100 scale. Driver
effects are set so the simulated driver–burnout correlations land inside
approximate bands reported in meta-analytic burnout research; `calibration_check`
verifies this. Most of the variance (~70%) is left unexplained on purpose: work
factors do not explain everything about a person's burnout, and a model claiming
otherwise would be overfitting.
"""

import numpy as np
import pandas as pd

FEATURES = [
    "work_hours_per_day",      # incl. study + class time for students
    "after_hours_per_week",    # evenings/nights per week spent working
    "meetings_per_day",        # meetings, or lectures/classes for students
    "sleep_hours",
    "days_off_last_month",
    "workload",                # 1–5: "I have too much to do"
    "autonomy",                # 1–5: control over how/when I work
    "support",                 # 1–5: manager / mentor / teacher support
    "recognition",             # 1–5: effort is noticed and valued
    "can_disconnect",          # 1–5: able to switch off after work
    "role_type",               # 0 employee, 1 student, 2 general
    "remote_work",             # 0/1
]

# +1: more of this can only raise predicted burnout; -1: can only lower it; 0: free.
MONOTONE = {
    "work_hours_per_day": 1, "after_hours_per_week": 1, "meetings_per_day": 1,
    "sleep_hours": -1, "days_off_last_month": -1, "workload": 1, "autonomy": -1,
    "support": -1, "recognition": -1, "can_disconnect": -1, "role_type": 0, "remote_work": 0,
}

ROLES = {"employee": 0, "student": 1, "general": 2}

# Approximate correlation bands with burnout (exhaustion-dominant) from meta-analytic literature
# (e.g. JD-R research; Alarcon 2011 on demands/resources; Wendsche & Lohmann-Haislah 2017 on detachment).
TARGET_CORRELATIONS = {
    "workload": (0.30, 0.55),
    "work_hours_per_day": (0.15, 0.40),
    "after_hours_per_week": (0.15, 0.40),
    "sleep_hours": (-0.45, -0.15),
    "support": (-0.40, -0.15),
    "autonomy": (-0.35, -0.10),
    "recognition": (-0.35, -0.10),
    "can_disconnect": (-0.50, -0.25),
    "days_off_last_month": (-0.30, -0.05),
}


def _z(x: np.ndarray) -> np.ndarray:
    return (x - x.mean()) / x.std()


def _likert(center: np.ndarray, rng, sd: float = 0.6) -> np.ndarray:
    return np.clip(np.round((center + rng.normal(0, sd, len(center))) * 2) / 2, 1, 5)


def simulate(n: int = 20000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    role = rng.choice([0, 1, 2], size=n, p=[0.5, 0.35, 0.15])
    student = role == 1

    # Latent job demands (D) and resources (R), mildly negatively correlated.
    D = rng.normal(0, 1, n)
    R = -0.2 * D + np.sqrt(1 - 0.04) * rng.normal(0, 1, n)

    df = pd.DataFrame({"role_type": role})
    df["work_hours_per_day"] = np.clip(np.where(student, 7.5, 8.4) + 1.3 * D + rng.normal(0, 0.8, n), 3, 16).round(1)
    df["after_hours_per_week"] = np.clip(rng.poisson(np.exp(0.2 + 0.55 * D - 0.2 * R + 0.3 * student)), 0, 7)
    df["meetings_per_day"] = np.clip(np.where(student, 4.0, 3.2) + 0.9 * D + rng.normal(0, 1.2, n), 0, 10).round()
    df["sleep_hours"] = np.clip(np.where(student, 6.8, 7.1) - 0.4 * D + 0.3 * R + rng.normal(0, 0.7, n), 3.5, 10).round(1)
    df["days_off_last_month"] = np.clip(2.2 + 0.6 * R - 0.4 * D + rng.normal(0, 1.5, n), 0, 15).round()
    df["workload"] = _likert(3.0 + 0.8 * D, rng, 0.5)
    df["autonomy"] = _likert(3.2 + 0.6 * R - 0.2 * student, rng)
    df["support"] = _likert(3.4 + 0.7 * R, rng)
    df["recognition"] = _likert(3.2 + 0.6 * R, rng)
    df["can_disconnect"] = _likert(3.2 - 0.6 * D + 0.4 * R, rng)
    df["remote_work"] = (rng.random(n) < np.where(student, 0.15, 0.35)).astype(int)

    z = {f: _z(df[f].to_numpy(float)) for f in FEATURES if f not in ("role_type", "remote_work")}
    burnout = (
        0.30 * z["workload"] + 0.14 * z["work_hours_per_day"] + 0.12 * z["after_hours_per_week"]
        + 0.06 * z["meetings_per_day"] - 0.18 * z["sleep_hours"] - 0.05 * z["days_off_last_month"]
        - 0.10 * z["autonomy"] - 0.15 * z["support"] - 0.10 * z["recognition"] - 0.20 * z["can_disconnect"]
        + 0.25 * np.clip(6 - df["sleep_hours"], 0, None)          # short-sleep penalty
        + 0.12 * np.clip(df["work_hours_per_day"] - 10, 0, None)  # very-long-day penalty
        + 0.10 * np.clip(z["workload"], 0, None) * np.clip(-z["support"], 0, None)  # JD-R buffering
        + 0.15 * student
    ).to_numpy()
    burnout = burnout + rng.normal(0, burnout.std() * 1.5, n)  # work factors explain ~30% of variance

    df["cbi_score"] = np.clip(43 + 18 * _z(burnout), 0, 100).round(1)
    return df[FEATURES + ["cbi_score"]]


def calibration_check(df: pd.DataFrame) -> dict[str, dict]:
    out = {}
    for feat, (lo, hi) in TARGET_CORRELATIONS.items():
        r = float(np.corrcoef(df[feat], df["cbi_score"])[0, 1])
        out[feat] = {"r": round(r, 3), "target": [lo, hi], "ok": lo <= r <= hi}
    return out


if __name__ == "__main__":
    data = simulate()
    for feat, res in calibration_check(data).items():
        print(f"{feat:24s} r={res['r']:+.3f}  target {res['target']}  {'OK' if res['ok'] else 'OUT OF BAND'}")
    print(data.describe().T[["mean", "std", "min", "max"]])
