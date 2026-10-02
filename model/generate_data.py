"""
BurnoutAI - Synthetic Dataset Generator
========================================
Generates a realistic burnout dataset based on:
  - Paper 1 (BURNOUT_RESERCH.pdf): Burnout types, prevalence, and dimensions
  - Paper 2 (burnout_2.pdf): Predictive features and risk scoring logic

Burnout Types (from Paper 1):
  - Frenetic   : Overworking, perfectionism, high achievement → silent collapse
  - Under-Challenged : Boredom, lack of growth, emotional withdrawal
  - Worn-Out   : Learned helplessness, chronic undervaluation, poor management

Risk Levels (from Paper 2, Section 8):
  - 0 : Healthy
  - 1 : Moderate Risk
  - 2 : High Risk
  - 3 : Burnout Zone
"""

import numpy as np
import pandas as pd
import os

np.random.seed(42)
N = 6000  # Total samples

# ──────────────────────────────────────────────
# Helper: clamp values to a range
# ──────────────────────────────────────────────
def clamp(arr, lo, hi):
    return np.clip(arr, lo, hi)


# ──────────────────────────────────────────────
# Generate profiles per burnout archetype
# ──────────────────────────────────────────────

def gen_healthy(n):
    """Profile: Balanced workload, recovery, high motivation."""
    d = {}
    d['avg_hours_per_day']      = clamp(np.random.normal(7.5, 0.8, n), 4, 9)
    d['late_logins_per_week']   = clamp(np.random.poisson(0.3, n), 0, 2).astype(float)
    d['meetings_per_day']       = clamp(np.random.normal(3, 1, n), 0, 6)
    d['leave_days_last_month']  = clamp(np.random.normal(5, 2, n), 1, 20)
    d['exhaustion_score']       = clamp(np.random.normal(1.8, 0.5, n), 1, 5)
    d['cynicism_score']         = clamp(np.random.normal(1.5, 0.5, n), 1, 5)
    d['efficacy_score']         = clamp(np.random.normal(4.2, 0.5, n), 1, 5)
    d['motivation_level']       = clamp(np.random.normal(4.3, 0.5, n), 1, 5)
    d['support_from_manager']   = clamp(np.random.normal(4.1, 0.6, n), 1, 5)
    d['can_disconnect']         = clamp(np.random.normal(4.2, 0.5, n), 1, 5)
    d['burnout_type']           = 'none'
    d['risk_level']             = 0
    return d


def gen_moderate_risk(n):
    """Profile: Slightly elevated stress, manageable but trending upward."""
    d = {}
    d['avg_hours_per_day']      = clamp(np.random.normal(9.2, 0.8, n), 7, 11)
    d['late_logins_per_week']   = clamp(np.random.poisson(1.5, n), 0, 4).astype(float)
    d['meetings_per_day']       = clamp(np.random.normal(5, 1.2, n), 2, 8)
    d['leave_days_last_month']  = clamp(np.random.normal(2.5, 1.5, n), 0, 8)
    d['exhaustion_score']       = clamp(np.random.normal(2.8, 0.6, n), 1.5, 4)
    d['cynicism_score']         = clamp(np.random.normal(2.5, 0.6, n), 1, 4)
    d['efficacy_score']         = clamp(np.random.normal(3.2, 0.6, n), 1.5, 5)
    d['motivation_level']       = clamp(np.random.normal(3.1, 0.6, n), 1.5, 5)
    d['support_from_manager']   = clamp(np.random.normal(3.0, 0.7, n), 1, 5)
    d['can_disconnect']         = clamp(np.random.normal(3.0, 0.7, n), 1, 5)
    d['burnout_type']           = 'none'
    d['risk_level']             = 1
    return d


def gen_frenetic(n):
    """Paper 1 Frenetic Type: Overworking high performers → silent collapse."""
    d = {}
    d['avg_hours_per_day']      = clamp(np.random.normal(12.5, 1.2, n), 10, 16)
    d['late_logins_per_week']   = clamp(np.random.poisson(4.5, n), 2, 7).astype(float)
    d['meetings_per_day']       = clamp(np.random.normal(8, 1.5, n), 5, 14)
    d['leave_days_last_month']  = clamp(np.random.normal(0.5, 0.5, n), 0, 2)
    d['exhaustion_score']       = clamp(np.random.normal(4.5, 0.4, n), 3.5, 5)
    d['cynicism_score']         = clamp(np.random.normal(3.0, 0.7, n), 1.5, 5)  # may still care
    d['efficacy_score']         = clamp(np.random.normal(2.5, 0.7, n), 1, 4)    # declining
    d['motivation_level']       = clamp(np.random.normal(2.2, 0.6, n), 1, 3.5)  # driven but crashing
    d['support_from_manager']   = clamp(np.random.normal(2.5, 0.8, n), 1, 4)
    d['can_disconnect']         = clamp(np.random.normal(1.5, 0.5, n), 1, 3)    # can never stop
    d['burnout_type']           = 'frenetic'
    d['risk_level']             = np.where(np.random.rand(n) > 0.3, 3, 2)
    return d


def gen_under_challenged(n):
    """Paper 1 Under-Challenged Type: Boredom, disengagement, quiet quitting."""
    d = {}
    d['avg_hours_per_day']      = clamp(np.random.normal(8.0, 1.0, n), 5, 10)
    d['late_logins_per_week']   = clamp(np.random.poisson(0.5, n), 0, 2).astype(float)
    d['meetings_per_day']       = clamp(np.random.normal(2.5, 1, n), 0, 5)
    d['leave_days_last_month']  = clamp(np.random.normal(3, 2, n), 0, 10)
    d['exhaustion_score']       = clamp(np.random.normal(2.5, 0.7, n), 1, 4)
    d['cynicism_score']         = clamp(np.random.normal(4.2, 0.5, n), 2.5, 5)  # very high cynicism
    d['efficacy_score']         = clamp(np.random.normal(2.2, 0.6, n), 1, 3.5)  # low efficacy
    d['motivation_level']       = clamp(np.random.normal(1.6, 0.5, n), 1, 3)    # very low motivation
    d['support_from_manager']   = clamp(np.random.normal(2.0, 0.8, n), 1, 4)
    d['can_disconnect']         = clamp(np.random.normal(3.5, 0.7, n), 1.5, 5)
    d['burnout_type']           = 'under_challenged'
    d['risk_level']             = np.where(np.random.rand(n) > 0.4, 2, 1)
    return d


def gen_worn_out(n):
    """Paper 1 Worn-Out Type: Learned helplessness, most dangerous, hardest recovery."""
    d = {}
    d['avg_hours_per_day']      = clamp(np.random.normal(10.5, 1.5, n), 7, 14)
    d['late_logins_per_week']   = clamp(np.random.poisson(2.5, n), 0, 5).astype(float)
    d['meetings_per_day']       = clamp(np.random.normal(5.5, 2, n), 2, 12)
    d['leave_days_last_month']  = clamp(np.random.normal(1.0, 1.0, n), 0, 5)
    d['exhaustion_score']       = clamp(np.random.normal(4.3, 0.5, n), 3, 5)
    d['cynicism_score']         = clamp(np.random.normal(4.5, 0.4, n), 3.5, 5)  # highest cynicism
    d['efficacy_score']         = clamp(np.random.normal(1.8, 0.5, n), 1, 3)    # worst efficacy
    d['motivation_level']       = clamp(np.random.normal(1.4, 0.4, n), 1, 2.5)  # nearly gone
    d['support_from_manager']   = clamp(np.random.normal(1.5, 0.5, n), 1, 3)    # no support
    d['can_disconnect']         = clamp(np.random.normal(2.0, 0.7, n), 1, 3.5)
    d['burnout_type']           = 'worn_out'
    d['risk_level']             = np.where(np.random.rand(n) > 0.2, 3, 2)
    return d


# ──────────────────────────────────────────────
# Combine all profiles
# ──────────────────────────────────────────────
portions = {
    'healthy':           int(N * 0.25),
    'moderate':          int(N * 0.20),
    'frenetic':          int(N * 0.20),
    'under_challenged':  int(N * 0.17),
    'worn_out':          int(N * 0.18),
}

generators = {
    'healthy':          gen_healthy,
    'moderate':         gen_moderate_risk,
    'frenetic':         gen_frenetic,
    'under_challenged': gen_under_challenged,
    'worn_out':         gen_worn_out,
}

frames = []
for key, count in portions.items():
    profile_data = generators[key](count)
    frames.append(pd.DataFrame(profile_data))

df = pd.concat(frames, ignore_index=True)

# ──────────────────────────────────────────────
# Add categorical features
# ──────────────────────────────────────────────
roles = np.random.choice(
    ['employee', 'student', 'general'],
    size=len(df),
    p=[0.50, 0.30, 0.20]
)
df['role_type'] = roles

# Students: adjust some features to be more student-relevant
student_mask = df['role_type'] == 'student'
df.loc[student_mask, 'meetings_per_day'] = clamp(
    df.loc[student_mask, 'meetings_per_day'] * 0.6, 0, 8
)

df['remote_work'] = np.random.choice([0, 1], size=len(df), p=[0.45, 0.55])

# Remote workers: Paper 1 says +2.5 hrs/day but harder to disconnect
remote_mask = df['remote_work'] == 1
df.loc[remote_mask, 'avg_hours_per_day'] = clamp(
    df.loc[remote_mask, 'avg_hours_per_day'] + np.random.uniform(0, 2.5, remote_mask.sum()),
    4, 16
)
df.loc[remote_mask, 'can_disconnect'] = clamp(
    df.loc[remote_mask, 'can_disconnect'] - np.random.uniform(0, 0.8, remote_mask.sum()),
    1, 5
)

# ──────────────────────────────────────────────
# Round & ensure types
# ──────────────────────────────────────────────
float_cols = ['avg_hours_per_day', 'exhaustion_score', 'cynicism_score',
              'efficacy_score', 'motivation_level', 'support_from_manager', 'can_disconnect']
int_cols   = ['late_logins_per_week', 'meetings_per_day', 'leave_days_last_month', 'remote_work']

for c in float_cols:
    df[c] = df[c].round(2)
for c in int_cols:
    df[c] = df[c].round(0).astype(int)

df['risk_level'] = df['risk_level'].astype(int)

# Shuffle
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# ──────────────────────────────────────────────
# Save
# ──────────────────────────────────────────────
os.makedirs('../data', exist_ok=True)
output_path = '../data/burnout_dataset.csv'
df.to_csv(output_path, index=False)

print("=" * 60)
print("  BurnoutAI Dataset Generated Successfully")
print("=" * 60)
print(f"  Total samples : {len(df)}")
print(f"  Output file   : {output_path}")
print()
print("  Risk Level Distribution:")
print(df['risk_level'].value_counts().sort_index().rename({
    0: '0 - Healthy',
    1: '1 - Moderate Risk',
    2: '2 - High Risk',
    3: '3 - Burnout Zone'
}))
print()
print("  Burnout Type Distribution:")
print(df['burnout_type'].value_counts())
print()
print("  Role Distribution:")
print(df['role_type'].value_counts())
print("=" * 60)
