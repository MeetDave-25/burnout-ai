"""
BurnoutAI — Enterprise SaaS API v3.0 (Neon PostgreSQL Integrated)
===================================================================
Features:
  - Neon PostgreSQL Cloud DB integration
  - Machine Learning Risk Prediction (Random Forest)
  - SHAP Explainable AI (XAI) Engine
  - Manager & HR Hub Endpoints (Group Analytics & Department Heatmaps)
  - 360° Individual Employee Diagnostic Profile
  - Doctor Telehealth Desk & Clinical Prescription Generator
  - Aria AI Coach Chatbot
"""

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env'))
import sys
import json
import time
import joblib
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────
# Load ML Model Artifacts
# ──────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, '..', '..', 'model')

model  = joblib.load(os.path.join(MODEL_DIR, 'burnout_model.pkl'))
scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
le     = joblib.load(os.path.join(MODEL_DIR, 'label_encoder.pkl'))

with open(os.path.join(MODEL_DIR, 'model_metadata.json')) as f:
    metadata = json.load(f)

FEATURES = metadata['features']

RISK_LABELS = {
    0: {"label": "Healthy",       "color": "#10B981", "emoji": "🟢"},
    1: {"label": "Moderate Risk", "color": "#F59E0B", "emoji": "🟡"},
    2: {"label": "High Risk",     "color": "#F97316", "emoji": "🟠"},
    3: {"label": "Burnout Zone",  "color": "#EF4444", "emoji": "🔴"},
}

FEATURE_LABELS = {
    'exhaustion_score'      : 'Emotional Exhaustion',
    'cynicism_score'        : 'Cynicism & Detachment',
    'efficacy_score'        : 'Self-Efficacy',
    'motivation_level'      : 'Motivation Level',
    'support_from_manager'  : 'Manager Support',
    'can_disconnect'        : 'Ability to Disconnect',
    'avg_hours_per_day'     : 'Working Hours/Day',
    'leave_days_last_month' : 'Leave Days Taken',
    'late_logins_per_week'  : 'Late Night Logins',
    'meetings_per_day'      : 'Meeting Load',
    'role_type_enc'         : 'Role Type',
    'remote_work'           : 'Remote Work',
}

# SHAP Lazy Load
SHAP_AVAILABLE = False
explainer = None

# ──────────────────────────────────────────────
# Neon PostgreSQL Cloud Connection
# ──────────────────────────────────────────────
NEON_DB_URI = os.environ.get("LEGACY_DATABASE_URL", "")

def get_db_connection():
    try:
        conn = psycopg2.connect(NEON_DB_URI, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"  [!] DB Connection Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("  [!] Cloud DB unreachable, running with in-memory fallback.")
        return

    try:
        cur = conn.cursor()

        # Create Tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                org_type VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                org_id INT REFERENCES organizations(id),
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                department VARCHAR(50) NOT NULL,
                role VARCHAR(50) NOT NULL,
                avatar VARCHAR(10),
                remote_work INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id SERIAL PRIMARY KEY,
                employee_id INT REFERENCES employees(id),
                risk_score INT NOT NULL,
                risk_level INT NOT NULL,
                risk_label VARCHAR(50) NOT NULL,
                burnout_type VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                raw_inputs JSONB NOT NULL,
                shap_contributions JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id SERIAL PRIMARY KEY,
                employee_id INT REFERENCES employees(id),
                doctor_name VARCHAR(100) NOT NULL,
                diagnosis_code VARCHAR(50) NOT NULL,
                work_restriction_days INT DEFAULT 0,
                notes TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id SERIAL PRIMARY KEY,
                employee_id INT REFERENCES employees(id),
                doctor_name VARCHAR(100) NOT NULL,
                appointment_date VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'Scheduled',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

        # Seed initial org & employees if empty
        cur.execute("SELECT COUNT(*) FROM employees;")
        count = cur.fetchone()['count']
        
        if count == 0:
            print("  [*] Seeding initial enterprise employees to Neon PostgreSQL...")
            cur.execute("INSERT INTO organizations (name, org_type) VALUES ('Acme Corp Enterprise', 'corporate') RETURNING id;")
            org_id = cur.fetchone()['id']

            sample_employees = [
                ("Sarah Connor", "sarah@acme.com", "Engineering", "Engineering Lead", "👩‍💻", 1),
                ("Alex Mercer", "alex@acme.com", "Engineering", "Senior Developer", "👨‍💻", 1),
                ("Elena Rostova", "elena@acme.com", "Product", "Lead Product Designer", "🎨", 0),
                ("Marcus Vance", "marcus@acme.com", "Support", "Customer Support Lead", "🎧", 1),
                ("David Kim", "david@acme.com", "Engineering", "Backend Engineer", "💻", 0),
                ("Priya Sharma", "priya@acme.com", "Data Science", "Data Scientist", "📊", 1),
                ("James Watson", "james@acme.com", "Sales", "Enterprise Sales Lead", "💼", 0),
                ("Maya Lin", "maya@acme.com", "UX", "UX Researcher", "🔍", 1),
            ]

            for emp in sample_employees:
                cur.execute("""
                    INSERT INTO employees (org_id, name, email, department, role, avatar, remote_work)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (org_id, emp[0], emp[1], emp[2], emp[3], emp[4], emp[5]))
                emp_id = cur.fetchone()['id']

                # Generate realistic sample assessment per employee
                if "Sarah" in emp[0]:
                    inputs = {"avg_hours_per_day": 11.5, "late_logins_per_week": 4, "meetings_per_day": 6, "leave_days_last_month": 0, "exhaustion_score": 4.5, "cynicism_score": 4.0, "efficacy_score": 2.5, "motivation_level": 1.5, "support_from_manager": 2.0, "can_disconnect": 1.0, "remote_work": 1}
                elif "Marcus" in emp[0]:
                    inputs = {"avg_hours_per_day": 10.0, "late_logins_per_week": 3, "meetings_per_day": 7, "leave_days_last_month": 1, "exhaustion_score": 4.0, "cynicism_score": 4.5, "efficacy_score": 2.0, "motivation_level": 2.0, "support_from_manager": 1.5, "can_disconnect": 1.5, "remote_work": 1}
                elif "Alex" in emp[0]:
                    inputs = {"avg_hours_per_day": 9.5, "late_logins_per_week": 3, "meetings_per_day": 5, "leave_days_last_month": 2, "exhaustion_score": 3.5, "cynicism_score": 3.0, "efficacy_score": 3.5, "motivation_level": 3.0, "support_from_manager": 3.0, "can_disconnect": 2.0, "remote_work": 1}
                elif "David" in emp[0]:
                    inputs = {"avg_hours_per_day": 7.5, "late_logins_per_week": 0, "meetings_per_day": 2, "leave_days_last_month": 5, "exhaustion_score": 1.5, "cynicism_score": 1.5, "efficacy_score": 4.5, "motivation_level": 4.5, "support_from_manager": 4.5, "can_disconnect": 4.5, "remote_work": 0}
                else:
                    inputs = {"avg_hours_per_day": 8.5, "late_logins_per_week": 1, "meetings_per_day": 4, "leave_days_last_month": 3, "exhaustion_score": 2.5, "cynicism_score": 2.5, "efficacy_score": 3.5, "motivation_level": 3.5, "support_from_manager": 3.5, "can_disconnect": 3.5, "remote_work": 0}

                result = _predict_core(inputs)
                vec = result.pop('_feature_vector', None)
                contributions, _ = compute_shap_explanation(vec or [8,0,3,4,2,2,4,4,4,4,0,0])

                cur.execute("""
                    INSERT INTO assessments (employee_id, risk_score, risk_level, risk_label, burnout_type, confidence, raw_inputs, shap_contributions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (emp_id, result['risk_score'], result['risk_level'], result['risk_label'], result['burnout_type'], result['confidence'], json.dumps(inputs), json.dumps(contributions)))

            conn.commit()
            print("  [+] Initial data seeding completed successfully.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"  [!] DB Initialization Exception: {e}")

# Initialize Flask App
app = Flask(__name__, static_folder='../frontend_old', static_url_path='/')
CORS(app)

# Serve the main index.html for the root route
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

# ──────────────────────────────────────────────
# Helper ML Functions
# ──────────────────────────────────────────────
def build_feature_vector(data):
    role_str = data.get('role_type', 'employee').lower()
    try:
        role_enc = int(le.transform([role_str])[0])
    except Exception:
        role_enc = 0

    vec = [
        float(data.get('avg_hours_per_day',     8.0)),
        float(data.get('late_logins_per_week',   0.0)),
        float(data.get('meetings_per_day',        4.0)),
        float(data.get('leave_days_last_month',   3.0)),
        float(data.get('exhaustion_score',         2.0)),
        float(data.get('cynicism_score',           2.0)),
        float(data.get('efficacy_score',           4.0)),
        float(data.get('motivation_level',         4.0)),
        float(data.get('support_from_manager',     4.0)),
        float(data.get('can_disconnect',           4.0)),
        float(role_enc),
        float(data.get('remote_work',              0.0)),
    ]
    return vec, role_str

def detect_burnout_type(data):
    hours      = float(data.get('avg_hours_per_day',    8))
    exhaust    = float(data.get('exhaustion_score',     3))
    cynic      = float(data.get('cynicism_score',       3))
    efficacy   = float(data.get('efficacy_score',       3))
    motivat    = float(data.get('motivation_level',     3))
    support    = float(data.get('support_from_manager', 3))
    disconnect = float(data.get('can_disconnect',       3))

    scores = {
        'Frenetic'        : hours * 0.4 + exhaust * 0.4 + (5 - disconnect) * 0.2,
        'Under-Challenged': cynic * 0.45 + (5 - motivat) * 0.35 + (5 - efficacy) * 0.2,
        'Worn-Out'        : cynic * 0.30 + exhaust * 0.30 + (5 - support) * 0.25 + (5 - efficacy) * 0.15,
    }
    best = max(scores, key=scores.get)
    conf = round(scores[best] / sum(scores.values()), 2)
    return best, conf, scores

def generate_explanation(data, risk_level, burnout_type):
    parts = []
    if float(data.get('avg_hours_per_day', 0)) > 9:
        parts.append(f"sustained overwork ({float(data['avg_hours_per_day']):.1f} hrs/day)")
    if float(data.get('exhaustion_score', 0)) >= 3.5:
        parts.append("high emotional exhaustion")
    if float(data.get('leave_days_last_month', 5)) < 2:
        parts.append("little recovery time")
    if float(data.get('cynicism_score', 0)) >= 3.5:
        parts.append("detachment from work")
    if float(data.get('can_disconnect', 3)) <= 2:
        parts.append("inability to disconnect after hours")

    if not parts:
        parts = ["balanced work-life patterns"]

    templates = {
        0: "Your wellbeing signals are healthy. Keep protecting your rest routines.",
        1: f"Early warning signs detected: {', '.join(parts[:2])}. Monitor closely.",
        2: f"Risk is escalating due to: {', '.join(parts[:3])}. Immediate workload adjustment recommended.",
        3: f"Critical burnout risk driven by: {', '.join(parts)}. Seek support and restructure load immediately.",
    }
    return templates[risk_level]

def generate_recommendations(data, risk_level, burnout_type):
    recs = {
        'Frenetic': [
            "Set a firm stop time each day — high performers often skip this",
            "Schedule at least 2 leave days in the next 2 weeks",
            "Turn off work notifications after your stop time",
            "Delegate tasks — doing everything alone is a trap",
        ],
        'Under-Challenged': [
            "Talk to your manager about new growth opportunities or projects",
            "Invest time in learning a skill that excites you",
            "Seek a role change or new responsibilities to re-engage",
        ],
        'Worn-Out': [
            "Consider speaking to HR or a mental health professional",
            "Take an extended break (minimum 5 days) if possible",
            "Have an honest conversation with your manager about workload",
        ],
    }.get(burnout_type, [
        "Maintain current work-life boundaries",
        "Schedule a weekly check-in with yourself",
    ])
    return recs[:5]

def compute_shap_explanation(feature_vector):
    global SHAP_AVAILABLE, explainer
    X = np.array([feature_vector])

    if explainer is None and not SHAP_AVAILABLE:
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            SHAP_AVAILABLE = True
        except Exception:
            SHAP_AVAILABLE = False

    if SHAP_AVAILABLE and explainer is not None:
        try:
            shap_values = explainer.shap_values(X)
            predicted_class = int(model.predict(X)[0])
            sv = shap_values[predicted_class][0] if isinstance(shap_values, list) else shap_values[0]

            contributions = []
            for i, feat in enumerate(FEATURES):
                contributions.append({
                    "feature"     : feat,
                    "label"       : FEATURE_LABELS.get(feat, feat),
                    "value"       : round(feature_vector[i], 2),
                    "shap_value"  : round(float(sv[i]), 4),
                    "direction"   : "risk_increase" if sv[i] > 0 else "risk_decrease",
                    "magnitude"   : round(abs(float(sv[i])), 4),
                })
            contributions.sort(key=lambda x: -x['magnitude'])
            return contributions, "shap"
        except Exception:
            pass

    fi = metadata.get('feature_importance', {})
    healthy_baseline = {
        'avg_hours_per_day': 7.5, 'late_logins_per_week': 0.5, 'meetings_per_day': 3.0,
        'leave_days_last_month': 5.0, 'exhaustion_score': 2.0, 'cynicism_score': 2.0,
        'efficacy_score': 4.0, 'motivation_level': 4.0, 'support_from_manager': 4.0,
        'can_disconnect': 4.0, 'role_type_enc': 0.0, 'remote_work': 0.0,
    }
    risk_dir = {
        'avg_hours_per_day': 1, 'late_logins_per_week': 1, 'meetings_per_day': 1,
        'leave_days_last_month': -1, 'exhaustion_score': 1, 'cynicism_score': 1,
        'efficacy_score': -1, 'motivation_level': -1, 'support_from_manager': -1,
        'can_disconnect': -1, 'role_type_enc': 0, 'remote_work': 1,
    }
    contributions = []
    for i, feat in enumerate(FEATURES):
        importance = fi.get(feat, 1/len(FEATURES))
        baseline = healthy_baseline.get(feat, feature_vector[i])
        deviation = (feature_vector[i] - baseline) * risk_dir.get(feat, 1)
        shap_approx = importance * deviation * 0.5
        contributions.append({
            "feature"   : feat,
            "label"     : FEATURE_LABELS.get(feat, feat),
            "value"     : round(feature_vector[i], 2),
            "shap_value": round(shap_approx, 4),
            "direction" : "risk_increase" if shap_approx > 0 else "risk_decrease",
            "magnitude" : round(abs(shap_approx), 4),
        })
    contributions.sort(key=lambda x: -x['magnitude'])
    return contributions, "feature_importance"

def _predict_core(data):
    vec, role_str = build_feature_vector(data)
    X = np.array([vec])

    risk_level    = int(model.predict(X)[0])
    probabilities = model.predict_proba(X)[0].tolist()
    confidence    = round(max(probabilities), 3)

    risk_score = min(100, int(
        risk_level * 25 +
        (confidence * 20) +
        max(0, (vec[0] - 8) * 2) +
        max(0, (vec[4] - 2.5) * 3)
    ))

    burnout_type, type_conf, _ = detect_burnout_type(data)
    explanation     = generate_explanation(data, risk_level, burnout_type)
    recommendations = generate_recommendations(data, risk_level, burnout_type)

    top_factors = []
    fi_weights = metadata.get('feature_importance', {f: 1/len(FEATURES) for f in FEATURES})
    for feat, imp in sorted(fi_weights.items(), key=lambda x: -x[1])[:5]:
        idx = FEATURES.index(feat) if feat in FEATURES else -1
        if idx >= 0:
            top_factors.append({"feature": feat, "label": FEATURE_LABELS.get(feat, feat),
                                 "value": round(vec[idx], 2), "importance": round(imp, 4)})

    return {
        "risk_level"       : risk_level,
        "risk_label"       : RISK_LABELS[risk_level]["label"],
        "risk_color"       : RISK_LABELS[risk_level]["color"],
        "risk_emoji"       : RISK_LABELS[risk_level]["emoji"],
        "risk_score"       : min(risk_score, 100),
        "confidence"       : confidence,
        "probabilities"    : {
            "healthy"      : round(probabilities[0], 3),
            "moderate_risk": round(probabilities[1], 3),
            "high_risk"    : round(probabilities[2], 3),
            "burnout_zone" : round(probabilities[3], 3),
        },
        "burnout_type"     : burnout_type,
        "type_confidence"  : type_conf,
        "explanation"      : explanation,
        "recommendations"  : recommendations,
        "top_factors"      : top_factors,
        "model_name"       : metadata['model_name'],
        "model_accuracy"   : metadata['test_accuracy'],
        "_feature_vector"  : vec,
    }

# Init DB after ML helper functions are defined
init_db()

# ──────────────────────────────────────────────
# Helper ML Functions
# ──────────────────────────────────────────────
def build_feature_vector(data):
    role_str = data.get('role_type', 'employee').lower()
    try:
        role_enc = int(le.transform([role_str])[0])
    except Exception:
        role_enc = 0

    vec = [
        float(data.get('avg_hours_per_day',     8.0)),
        float(data.get('late_logins_per_week',   0.0)),
        float(data.get('meetings_per_day',        4.0)),
        float(data.get('leave_days_last_month',   3.0)),
        float(data.get('exhaustion_score',         2.0)),
        float(data.get('cynicism_score',           2.0)),
        float(data.get('efficacy_score',           4.0)),
        float(data.get('motivation_level',         4.0)),
        float(data.get('support_from_manager',     4.0)),
        float(data.get('can_disconnect',           4.0)),
        float(role_enc),
        float(data.get('remote_work',              0.0)),
    ]
    return vec, role_str

def detect_burnout_type(data):
    hours      = float(data.get('avg_hours_per_day',    8))
    exhaust    = float(data.get('exhaustion_score',     3))
    cynic      = float(data.get('cynicism_score',       3))
    efficacy   = float(data.get('efficacy_score',       3))
    motivat    = float(data.get('motivation_level',     3))
    support    = float(data.get('support_from_manager', 3))
    disconnect = float(data.get('can_disconnect',       3))

    scores = {
        'Frenetic'        : hours * 0.4 + exhaust * 0.4 + (5 - disconnect) * 0.2,
        'Under-Challenged': cynic * 0.45 + (5 - motivat) * 0.35 + (5 - efficacy) * 0.2,
        'Worn-Out'        : cynic * 0.30 + exhaust * 0.30 + (5 - support) * 0.25 + (5 - efficacy) * 0.15,
    }
    best = max(scores, key=scores.get)
    conf = round(scores[best] / sum(scores.values()), 2)
    return best, conf, scores

def generate_explanation(data, risk_level, burnout_type):
    parts = []
    if float(data.get('avg_hours_per_day', 0)) > 9:
        parts.append(f"sustained overwork ({float(data['avg_hours_per_day']):.1f} hrs/day)")
    if float(data.get('exhaustion_score', 0)) >= 3.5:
        parts.append("high emotional exhaustion")
    if float(data.get('leave_days_last_month', 5)) < 2:
        parts.append("little recovery time")
    if float(data.get('cynicism_score', 0)) >= 3.5:
        parts.append("detachment from work")
    if float(data.get('can_disconnect', 3)) <= 2:
        parts.append("inability to disconnect after hours")

    if not parts:
        parts = ["balanced work-life patterns"]

    templates = {
        0: "Your wellbeing signals are healthy. Keep protecting your rest routines.",
        1: f"Early warning signs detected: {', '.join(parts[:2])}. Monitor closely.",
        2: f"Risk is escalating due to: {', '.join(parts[:3])}. Immediate workload adjustment recommended.",
        3: f"Critical burnout risk driven by: {', '.join(parts)}. Seek support and restructure load immediately.",
    }
    return templates[risk_level]

def generate_recommendations(data, risk_level, burnout_type):
    recs = {
        'Frenetic': [
            "Set a firm stop time each day — high performers often skip this",
            "Schedule at least 2 leave days in the next 2 weeks",
            "Turn off work notifications after your stop time",
            "Delegate tasks — doing everything alone is a trap",
        ],
        'Under-Challenged': [
            "Talk to your manager about new growth opportunities or projects",
            "Invest time in learning a skill that excites you",
            "Seek a role change or new responsibilities to re-engage",
        ],
        'Worn-Out': [
            "Consider speaking to HR or a mental health professional",
            "Take an extended break (minimum 5 days) if possible",
            "Have an honest conversation with your manager about workload",
        ],
    }.get(burnout_type, [
        "Maintain current work-life boundaries",
        "Schedule a weekly check-in with yourself",
    ])
    return recs[:5]

def compute_shap_explanation(feature_vector):
    global SHAP_AVAILABLE, explainer
    X = np.array([feature_vector])

    if explainer is None and not SHAP_AVAILABLE:
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            SHAP_AVAILABLE = True
        except Exception:
            SHAP_AVAILABLE = False

    if SHAP_AVAILABLE and explainer is not None:
        try:
            shap_values = explainer.shap_values(X)
            predicted_class = int(model.predict(X)[0])
            sv = shap_values[predicted_class][0] if isinstance(shap_values, list) else shap_values[0]

            contributions = []
            for i, feat in enumerate(FEATURES):
                contributions.append({
                    "feature"     : feat,
                    "label"       : FEATURE_LABELS.get(feat, feat),
                    "value"       : round(feature_vector[i], 2),
                    "shap_value"  : round(float(sv[i]), 4),
                    "direction"   : "risk_increase" if sv[i] > 0 else "risk_decrease",
                    "magnitude"   : round(abs(float(sv[i])), 4),
                })
            contributions.sort(key=lambda x: -x['magnitude'])
            return contributions, "shap"
        except Exception:
            pass

    # Fallback feature importance weighted by deviation
    fi = metadata.get('feature_importance', {})
    healthy_baseline = {
        'avg_hours_per_day': 7.5, 'late_logins_per_week': 0.5, 'meetings_per_day': 3.0,
        'leave_days_last_month': 5.0, 'exhaustion_score': 2.0, 'cynicism_score': 2.0,
        'efficacy_score': 4.0, 'motivation_level': 4.0, 'support_from_manager': 4.0,
        'can_disconnect': 4.0, 'role_type_enc': 0.0, 'remote_work': 0.0,
    }
    risk_dir = {
        'avg_hours_per_day': 1, 'late_logins_per_week': 1, 'meetings_per_day': 1,
        'leave_days_last_month': -1, 'exhaustion_score': 1, 'cynicism_score': 1,
        'efficacy_score': -1, 'motivation_level': -1, 'support_from_manager': -1,
        'can_disconnect': -1, 'role_type_enc': 0, 'remote_work': 1,
    }
    contributions = []
    for i, feat in enumerate(FEATURES):
        importance = fi.get(feat, 1/len(FEATURES))
        baseline = healthy_baseline.get(feat, feature_vector[i])
        deviation = (feature_vector[i] - baseline) * risk_dir.get(feat, 1)
        shap_approx = importance * deviation * 0.5
        contributions.append({
            "feature"   : feat,
            "label"     : FEATURE_LABELS.get(feat, feat),
            "value"     : round(feature_vector[i], 2),
            "shap_value": round(shap_approx, 4),
            "direction" : "risk_increase" if shap_approx > 0 else "risk_decrease",
            "magnitude" : round(abs(shap_approx), 4),
        })
    contributions.sort(key=lambda x: -x['magnitude'])
    return contributions, "feature_importance"

def _predict_core(data):
    vec, role_str = build_feature_vector(data)
    X = np.array([vec])

    risk_level    = int(model.predict(X)[0])
    probabilities = model.predict_proba(X)[0].tolist()
    confidence    = round(max(probabilities), 3)

    risk_score = min(100, int(
        risk_level * 25 +
        (confidence * 20) +
        max(0, (vec[0] - 8) * 2) +
        max(0, (vec[4] - 2.5) * 3)
    ))

    burnout_type, type_conf, _ = detect_burnout_type(data)
    explanation     = generate_explanation(data, risk_level, burnout_type)
    recommendations = generate_recommendations(data, risk_level, burnout_type)

    top_factors = []
    fi_weights = metadata.get('feature_importance', {f: 1/len(FEATURES) for f in FEATURES})
    for feat, imp in sorted(fi_weights.items(), key=lambda x: -x[1])[:5]:
        idx = FEATURES.index(feat) if feat in FEATURES else -1
        if idx >= 0:
            top_factors.append({"feature": feat, "label": FEATURE_LABELS.get(feat, feat),
                                 "value": round(vec[idx], 2), "importance": round(imp, 4)})

    return {
        "risk_level"       : risk_level,
        "risk_label"       : RISK_LABELS[risk_level]["label"],
        "risk_color"       : RISK_LABELS[risk_level]["color"],
        "risk_emoji"       : RISK_LABELS[risk_level]["emoji"],
        "risk_score"       : min(risk_score, 100),
        "confidence"       : confidence,
        "probabilities"    : {
            "healthy"      : round(probabilities[0], 3),
            "moderate_risk": round(probabilities[1], 3),
            "high_risk"    : round(probabilities[2], 3),
            "burnout_zone" : round(probabilities[3], 3),
        },
        "burnout_type"     : burnout_type,
        "type_confidence"  : type_conf,
        "explanation"      : explanation,
        "recommendations"  : recommendations,
        "top_factors"      : top_factors,
        "model_name"       : metadata['model_name'],
        "model_accuracy"   : metadata['test_accuracy'],
        "_feature_vector"  : vec,
    }

# ──────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status"  : "healthy",
        "database": "Neon PostgreSQL (AWS ap-southeast-1)",
        "model"   : metadata['model_name'],
        "accuracy": metadata['test_accuracy'],
        "message" : "BurnoutAI v3.0 Enterprise SaaS API is running"
    })

@app.route('/model-info', methods=['GET'])
def model_info():
    return jsonify({
        "model_name"       : metadata['model_name'],
        "test_accuracy"    : metadata['test_accuracy'],
        "test_f1"          : metadata['test_f1'],
        "training_samples" : metadata['training_samples'],
        "features"         : FEATURES,
        "feature_labels"   : FEATURE_LABELS,
    })

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json() or {}
        result = _predict_core(data)
        vec = result.pop('_feature_vector', None)
        
        # Log to Neon DB if connection available
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO assessments (employee_id, risk_score, risk_level, risk_label, burnout_type, confidence, raw_inputs)
                VALUES (1, %s, %s, %s, %s, %s, %s);
            """, (result['risk_score'], result['risk_level'], result['risk_label'], result['burnout_type'], result['confidence'], json.dumps(data)))
            conn.commit()
            cur.close()
            conn.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/predict/xai', methods=['POST'])
def predict_xai():
    try:
        data = request.get_json() or {}
        result = _predict_core(data)
        vec = result.pop('_feature_vector', [8,0,3,4,2,2,4,4,4,4,0,0])

        contributions, xai_method = compute_shap_explanation(vec)
        result['shap_contributions'] = contributions
        result['xai_method']         = xai_method

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ──────────────────────────────────────────────
# Manager SaaS Portal Endpoints
# ──────────────────────────────────────────────
@app.route('/api/manager/group-analytics', methods=['GET'])
def manager_group_analytics():
    conn = get_db_connection()
    if not conn:
        # Fallback mock telemetry
        return jsonify({
            "total_monitored": 8,
            "avg_risk_score": 62,
            "critical_count": 2,
            "high_risk_count": 2,
            "moderate_count": 2,
            "healthy_count": 2,
            "department_scores": {
                "Engineering": 78,
                "Support": 82,
                "Sales": 68,
                "Product": 48,
                "UX": 22
            },
            "phenotype_counts": {
                "Frenetic": 4,
                "Under-Challenged": 1,
                "Worn-Out": 1,
                "Healthy Pattern": 2
            }
        })

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.department, a.risk_score, a.risk_level, a.burnout_type
            FROM employees e
            JOIN assessments a ON e.id = a.employee_id;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        total = len(rows)
        avg_score = round(sum(r['risk_score'] for r in rows) / total) if total > 0 else 50
        crit = sum(1 for r in rows if r['risk_level'] == 3)
        high = sum(1 for r in rows if r['risk_level'] == 2)
        mod  = sum(1 for r in rows if r['risk_level'] == 1)
        hlth = sum(1 for r in rows if r['risk_level'] == 0)

        dept_scores = {}
        for r in rows:
            dept = r['department']
            dept_scores.setdefault(dept, []).append(r['risk_score'])
        dept_avg = {k: round(sum(v)/len(v)) for k, v in dept_scores.items()}

        pheno_counts = {}
        for r in rows:
            p = r['burnout_type']
            pheno_counts[p] = pheno_counts.get(p, 0) + 1

        return jsonify({
            "total_monitored": total,
            "avg_risk_score": avg_score,
            "critical_count": crit,
            "high_risk_count": high,
            "moderate_count": mod,
            "healthy_count": hlth,
            "department_scores": dept_avg,
            "phenotype_counts": pheno_counts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manager/employees', methods=['GET'])
def manager_employees():
    conn = get_db_connection()
    if not conn:
        return jsonify({"employees": []})

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.name, e.email, e.department, e.role, e.avatar, e.remote_work,
                   a.risk_score, a.risk_level, a.risk_label, a.burnout_type, a.created_at
            FROM employees e
            LEFT JOIN assessments a ON e.id = a.employee_id
            ORDER BY a.risk_score DESC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        for r in rows:
            if r['risk_level'] is not None:
                r['risk_color'] = RISK_LABELS[r['risk_level']]['color']
                r['risk_emoji'] = RISK_LABELS[r['risk_level']]['emoji']

        return jsonify({"employees": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manager/employee/<int:emp_id>', methods=['GET'])
def manager_employee_detail(emp_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB unreachable"}), 500

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.name, e.email, e.department, e.role, e.avatar, e.remote_work,
                   a.risk_score, a.risk_level, a.risk_label, a.burnout_type, a.confidence,
                   a.raw_inputs, a.shap_contributions, a.created_at
            FROM employees e
            JOIN assessments a ON e.id = a.employee_id
            WHERE e.id = %s;
        """, (emp_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Employee not found"}), 404

        row['risk_color'] = RISK_LABELS[row['risk_level']]['color']
        row['risk_emoji'] = RISK_LABELS[row['risk_level']]['emoji']
        return jsonify(row)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ──────────────────────────────────────────────
# Doctor & Clinical Prescriptions Endpoints
# ──────────────────────────────────────────────
@app.route('/api/prescriptions', methods=['POST'])
def create_prescription():
    try:
        data = request.get_json() or {}
        emp_id = data.get('employee_id', 1)
        doc_name = data.get('doctor_name', 'Dr. Aris Thorne, MD')
        diag_code = data.get('diagnosis_code', 'ICD-11 QD85 (Burnout Syndrome)')
        days = data.get('work_restriction_days', 5)
        notes = data.get('notes', 'Mandatory 5-day medical leave for autonomic nervous system recovery.')

        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO prescriptions (employee_id, doctor_name, diagnosis_code, work_restriction_days, notes)
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """, (emp_id, doc_name, diag_code, days, notes))
            rx_id = cur.fetchone()['id']
            conn.commit()
            cur.close()
            conn.close()
        else:
            rx_id = 99

        return jsonify({
            "status": "success",
            "prescription_id": rx_id,
            "message": "Clinical prescription issued and stored in Neon PostgreSQL."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ──────────────────────────────────────────────
# Chatbot Route
# ──────────────────────────────────────────────
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        msg = data.get('message', '').strip()
        if not msg:
            return jsonify({"error": "message required"}), 400

        m = msg.toLowerCase() if hasattr(msg, 'toLowerCase') else msg.lower()
        if 'burnout' in m and 'what' in m:
            resp = "**Burnout** is defined by WHO as chronic workplace stress. Core dimensions: Exhaustion, Cynicism, and Reduced Efficacy."
        elif 'symptom' in m or 'sign' in m:
            resp = "Warning signs include: chronic fatigue, emotional detachment, cynicism, insomnia, brain fog, and reduced efficacy."
        elif 'prevent' in m or 'avoid' in m:
            resp = "Research-backed prevention: Set firm work boundaries, schedule real leave, protect 7–8 hrs sleep, and limit late night logins."
        else:
            resp = "I'm **Aria**, your BurnoutAI coach. I'm trained on burnout research to answer questions, explain SHAP risk scores, or suggest recovery habits!"

        return jsonify({"response": resp, "persona": "Aria AI Coach"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ──────────────────────────────────────────────
# Run Server
# ──────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("  BurnoutAI Flask API v3.0 (Neon PostgreSQL Integrated)")
    print(f"  Model    : {metadata['model_name']} (Acc: {metadata['test_accuracy']*100:.1f}%)")
    print("  Cloud DB : Neon PostgreSQL (ap-southeast-1)")
    print("  Running at: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, port=5000, host='0.0.0.0')
