"""
BurnoutAI - Model Training Pipeline
=====================================
Trains a Random Forest classifier on the generated burnout dataset.
Based on research:
  - Paper 1: Burnout dimensions (exhaustion, cynicism, efficacy)
  - Paper 2: Ethical, privacy-first prediction using behavioral signals

Output files:
  - burnout_model.pkl     : Trained Random Forest model
  - scaler.pkl            : StandardScaler for feature normalization
  - label_encoder.pkl     : LabelEncoder for role_type
  - model_report.txt      : Full accuracy report + feature importance
"""

import os
import sys
import json
import joblib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score,
    f1_score, roc_auc_score
)
from sklearn.inspection import permutation_importance

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(BASE_DIR, '..', 'data', 'burnout_dataset.csv')
MODEL_DIR  = BASE_DIR

print("=" * 65)
print("  BurnoutAI — Model Training Pipeline")
print("  Based on Burnout Research Papers (2024)")
print("=" * 65)

# ──────────────────────────────────────────────
# 1. Load & Prepare Data
# ──────────────────────────────────────────────
print("\n[1/6] Loading dataset...")
df = pd.read_csv(DATA_PATH)
print(f"      Loaded {len(df)} rows, {len(df.columns)} columns")

# Encode role_type
le = LabelEncoder()
df['role_type_enc'] = le.fit_transform(df['role_type'])

FEATURES = [
    'avg_hours_per_day',
    'late_logins_per_week',
    'meetings_per_day',
    'leave_days_last_month',
    'exhaustion_score',
    'cynicism_score',
    'efficacy_score',
    'motivation_level',
    'support_from_manager',
    'can_disconnect',
    'role_type_enc',
    'remote_work',
]

TARGET = 'risk_level'

X = df[FEATURES].values
y = df[TARGET].values

print(f"      Features : {len(FEATURES)}")
print(f"      Classes  : {sorted(df[TARGET].unique())} -> {dict(df[TARGET].value_counts().sort_index())}")

# ──────────────────────────────────────────────
# 2. Train/Test Split
# ──────────────────────────────────────────────
print("\n[2/6] Splitting data (80% train / 20% test)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)
print(f"      Train size : {len(X_train)}")
print(f"      Test size  : {len(X_test)}")

# ──────────────────────────────────────────────
# 3. Train Multiple Models & Compare
# ──────────────────────────────────────────────
print("\n[3/6] Training models...")

models = {
    'Random Forest': RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    ),
    'Logistic Regression': LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        random_state=42
    ),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
results = {}

for name, model in models.items():
    if name == 'Logistic Regression':
        Xtr, Xte = X_train_scaled, X_test_scaled
    else:
        Xtr, Xte = X_train, X_test

    cv_scores = cross_val_score(model, Xtr, y_train, cv=cv, scoring='f1_weighted', n_jobs=-1)
    model.fit(Xtr, y_train)
    y_pred = model.predict(Xte)
    test_acc = accuracy_score(y_test, y_pred)
    test_f1  = f1_score(y_test, y_pred, average='weighted')

    results[name] = {
        'model'    : model,
        'cv_mean'  : cv_scores.mean(),
        'cv_std'   : cv_scores.std(),
        'test_acc' : test_acc,
        'test_f1'  : test_f1,
        'y_pred'   : y_pred,
        'X_test'   : Xte,
    }
    print(f"      {name:25s} | CV F1: {cv_scores.mean():.4f} ± {cv_scores.std():.4f} | Test Acc: {test_acc:.4f}")

# ──────────────────────────────────────────────
# 4. Select Best Model (by Test F1)
# ──────────────────────────────────────────────
print("\n[4/6] Selecting best model...")
best_name = max(results, key=lambda k: results[k]['test_f1'])
best      = results[best_name]
print(f"      Best model : {best_name}")
print(f"      Test Acc   : {best['test_acc']:.4f} ({best['test_acc']*100:.1f}%)")
print(f"      Test F1    : {best['test_f1']:.4f}")

best_model = best['model']
y_pred_best = best['y_pred']

# ──────────────────────────────────────────────
# 5. Feature Importance
# ──────────────────────────────────────────────
print("\n[5/6] Computing feature importance...")
if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    fi_df = pd.DataFrame({'feature': FEATURES, 'importance': importances})
    fi_df = fi_df.sort_values('importance', ascending=False)
    print("\n      Top Feature Importances:")
    for _, row in fi_df.iterrows():
        bar = '█' * int(row['importance'] * 50)
        print(f"      {row['feature']:30s} {bar} {row['importance']:.4f}")
else:
    fi_df = None
    print("      (Not available for this model type)")

# ──────────────────────────────────────────────
# 6. Save Everything
# ──────────────────────────────────────────────
print("\n[6/6] Saving model artifacts...")

joblib.dump(best_model, os.path.join(MODEL_DIR, 'burnout_model.pkl'))
joblib.dump(scaler,     os.path.join(MODEL_DIR, 'scaler.pkl'))
joblib.dump(le,         os.path.join(MODEL_DIR, 'label_encoder.pkl'))
print("      burnout_model.pkl   ✓")
print("      scaler.pkl          ✓")
print("      label_encoder.pkl   ✓")

# Save metadata JSON (for the API to load)
metadata = {
    "model_name"    : best_name,
    "test_accuracy" : round(best['test_acc'], 4),
    "test_f1"       : round(best['test_f1'], 4),
    "cv_f1_mean"    : round(best['cv_mean'], 4),
    "cv_f1_std"     : round(best['cv_std'], 4),
    "features"      : FEATURES,
    "classes"       : [0, 1, 2, 3],
    "class_labels"  : {
        "0": "Healthy",
        "1": "Moderate Risk",
        "2": "High Risk",
        "3": "Burnout Zone"
    },
    "training_samples": len(X_train),
    "test_samples"    : len(X_test),
    "feature_importance": (
        {row['feature']: round(row['importance'], 6) for _, row in fi_df.iterrows()}
        if fi_df is not None else {}
    )
}
with open(os.path.join(MODEL_DIR, 'model_metadata.json'), 'w') as f:
    json.dump(metadata, f, indent=2)
print("      model_metadata.json ✓")

# Save text report
report_path = os.path.join(MODEL_DIR, 'model_report.txt')
class_names = ['Healthy', 'Moderate Risk', 'High Risk', 'Burnout Zone']
with open(report_path, 'w') as f:
    f.write("BurnoutAI — Model Training Report\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Best Model     : {best_name}\n")
    f.write(f"Test Accuracy  : {best['test_acc']:.4f} ({best['test_acc']*100:.1f}%)\n")
    f.write(f"Test F1        : {best['test_f1']:.4f}\n")
    f.write(f"CV F1 (5-fold) : {best['cv_mean']:.4f} ± {best['cv_std']:.4f}\n\n")
    f.write("All Models Comparison:\n")
    f.write("-" * 60 + "\n")
    for name, res in results.items():
        f.write(f"  {name:25s} | CV: {res['cv_mean']:.4f} | Acc: {res['test_acc']:.4f} | F1: {res['test_f1']:.4f}\n")
    f.write("\n")
    f.write("Classification Report:\n")
    f.write("-" * 60 + "\n")
    f.write(classification_report(y_test, y_pred_best, target_names=class_names))
    f.write("\n")
    if fi_df is not None:
        f.write("Feature Importances:\n")
        f.write("-" * 60 + "\n")
        for _, row in fi_df.iterrows():
            f.write(f"  {row['feature']:30s} {row['importance']:.6f}\n")
print("      model_report.txt    ✓")

# ──────────────────────────────────────────────
# Generate Confusion Matrix Plot
# ──────────────────────────────────────────────
cm = confusion_matrix(y_test, y_pred_best)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor('#0A0F1E')

# Confusion Matrix
ax1 = axes[0]
ax1.set_facecolor('#0D1526')
sns.heatmap(cm, annot=True, fmt='d', cmap='YlOrRd',
            xticklabels=class_names, yticklabels=class_names,
            ax=ax1, linewidths=0.5, linecolor='#1E2D4E')
ax1.set_title('BurnoutAI — Confusion Matrix', color='white', fontsize=14, pad=15)
ax1.set_xlabel('Predicted', color='#A0AEC0', fontsize=11)
ax1.set_ylabel('Actual', color='#A0AEC0', fontsize=11)
ax1.tick_params(colors='#A0AEC0')

# Feature Importance
ax2 = axes[1]
ax2.set_facecolor('#0D1526')
if fi_df is not None:
    colors = ['#6366F1', '#8B5CF6', '#F59E0B', '#10B981',
              '#EF4444', '#3B82F6', '#EC4899', '#14B8A6',
              '#F97316', '#84CC16', '#06B6D4', '#A855F7']
    bars = ax2.barh(fi_df['feature'], fi_df['importance'],
                    color=colors[:len(fi_df)], alpha=0.9)
    ax2.set_title('Feature Importance', color='white', fontsize=14, pad=15)
    ax2.set_xlabel('Importance Score', color='#A0AEC0', fontsize=11)
    ax2.tick_params(colors='#A0AEC0')
    ax2.set_facecolor('#0D1526')
    for spine in ax2.spines.values():
        spine.set_color('#1E2D4E')
    ax2.invert_yaxis()

plt.tight_layout()
plot_path = os.path.join(MODEL_DIR, 'model_plots.png')
plt.savefig(plot_path, dpi=150, bbox_inches='tight', facecolor='#0A0F1E')
plt.close()
print("      model_plots.png     ✓")

print()
print("=" * 65)
print("  ✅  Training Complete!")
print(f"  Model Accuracy : {best['test_acc']*100:.1f}%")
print(f"  Model F1 Score : {best['test_f1']*100:.1f}%")
print(f"  Best Model     : {best_name}")
print("=" * 65)
print()
print("  Next step: Run  →  python ../api/app.py")
print()
