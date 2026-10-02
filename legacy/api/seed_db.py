import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env'))
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import joblib
import numpy as np

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, '..', '..', 'model')

model  = joblib.load(os.path.join(MODEL_DIR, 'burnout_model.pkl'))
scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
le     = joblib.load(os.path.join(MODEL_DIR, 'label_encoder.pkl'))

with open(os.path.join(MODEL_DIR, 'model_metadata.json')) as f:
    metadata = json.load(f)

NEON_DB_URI = os.environ.get("LEGACY_DATABASE_URL", "")

def seed():
    print("Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(NEON_DB_URI, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS prescriptions, appointments, assessments, employees, organizations CASCADE;")
    
    cur.execute("""
        CREATE TABLE organizations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            org_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE employees (
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
        CREATE TABLE assessments (
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
        CREATE TABLE prescriptions (
            id SERIAL PRIMARY KEY,
            employee_id INT REFERENCES employees(id),
            doctor_name VARCHAR(100) NOT NULL,
            diagnosis_code VARCHAR(50) NOT NULL,
            work_restriction_days INT DEFAULT 0,
            notes TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE appointments (
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

    cur.execute("INSERT INTO organizations (name, org_type) VALUES ('Acme Corp Enterprise', 'corporate') RETURNING id;")
    org_id = cur.fetchone()['id']

    employees_data = [
        ("Sarah Connor", "sarah@acme.com", "Engineering", "Engineering Lead", "👩‍💻", 1, 88, 3, "Burnout Zone", "Frenetic", 0.94, {"avg_hours_per_day": 11.5, "late_logins_per_week": 4, "meetings_per_day": 6, "leave_days_last_month": 0, "exhaustion_score": 4.5, "cynicism_score": 4.0, "efficacy_score": 2.5, "can_disconnect": 1.0, "support_from_manager": 2.0}),
        ("Marcus Vance", "marcus@acme.com", "Support", "Customer Support Lead", "🎧", 1, 82, 3, "Burnout Zone", "Worn-Out", 0.91, {"avg_hours_per_day": 10.0, "late_logins_per_week": 3, "meetings_per_day": 7, "leave_days_last_month": 1, "exhaustion_score": 4.0, "cynicism_score": 4.5, "efficacy_score": 2.0, "can_disconnect": 1.5, "support_from_manager": 1.5}),
        ("Alex Mercer", "alex@acme.com", "Engineering", "Senior Developer", "👨‍💻", 1, 74, 2, "High Risk", "Frenetic", 0.88, {"avg_hours_per_day": 9.5, "late_logins_per_week": 3, "meetings_per_day": 5, "leave_days_last_month": 2, "exhaustion_score": 3.5, "cynicism_score": 3.0, "efficacy_score": 3.5, "can_disconnect": 2.0, "support_from_manager": 3.0}),
        ("James Watson", "james@acme.com", "Sales", "Enterprise Sales Lead", "💼", 0, 68, 2, "High Risk", "Frenetic", 0.85, {"avg_hours_per_day": 9.5, "late_logins_per_week": 2, "meetings_per_day": 6, "leave_days_last_month": 2, "exhaustion_score": 3.5, "cynicism_score": 3.0, "efficacy_score": 3.5, "can_disconnect": 2.5, "support_from_manager": 3.0}),
        ("Elena Rostova", "elena@acme.com", "Product", "Lead Product Designer", "🎨", 0, 48, 1, "Moderate Risk", "Under-Challenged", 0.82, {"avg_hours_per_day": 8.0, "late_logins_per_week": 1, "meetings_per_day": 4, "leave_days_last_month": 3, "exhaustion_score": 2.5, "cynicism_score": 3.5, "efficacy_score": 3.0, "can_disconnect": 3.0, "support_from_manager": 3.5}),
        ("Priya Sharma", "priya@acme.com", "Data Science", "Data Scientist", "📊", 1, 42, 1, "Moderate Risk", "Frenetic", 0.80, {"avg_hours_per_day": 8.5, "late_logins_per_week": 1, "meetings_per_day": 3, "leave_days_last_month": 4, "exhaustion_score": 2.5, "cynicism_score": 2.5, "efficacy_score": 4.0, "can_disconnect": 3.5, "support_from_manager": 4.0}),
        ("David Kim", "david@acme.com", "Engineering", "Backend Engineer", "💻", 0, 18, 0, "Healthy", "Healthy Pattern", 0.96, {"avg_hours_per_day": 7.5, "late_logins_per_week": 0, "meetings_per_day": 2, "leave_days_last_month": 5, "exhaustion_score": 1.5, "cynicism_score": 1.5, "efficacy_score": 4.5, "can_disconnect": 4.5, "support_from_manager": 4.5}),
        ("Maya Lin", "maya@acme.com", "UX", "UX Researcher", "🔍", 1, 22, 0, "Healthy", "Healthy Pattern", 0.95, {"avg_hours_per_day": 7.5, "late_logins_per_week": 0, "meetings_per_day": 3, "leave_days_last_month": 4, "exhaustion_score": 1.5, "cynicism_score": 2.0, "efficacy_score": 4.5, "can_disconnect": 4.0, "support_from_manager": 4.5}),
    ]

    for emp in employees_data:
        cur.execute("""
            INSERT INTO employees (org_id, name, email, department, role, avatar, remote_work)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """, (org_id, emp[0], emp[1], emp[2], emp[3], emp[4], emp[5]))
        emp_id = cur.fetchone()['id']

        raw = emp[11]
        shap_contribs = [
            {"feature": "avg_hours_per_day", "label": "Working Hours/Day", "value": raw.get("avg_hours_per_day", 8), "shap_value": 0.18, "direction": "risk_increase", "magnitude": 0.18},
            {"feature": "exhaustion_score", "label": "Emotional Exhaustion", "value": raw.get("exhaustion_score", 3), "shap_value": 0.14, "direction": "risk_increase", "magnitude": 0.14},
            {"feature": "late_logins_per_week", "label": "Late Night Logins", "value": raw.get("late_logins_per_week", 1), "shap_value": 0.10, "direction": "risk_increase", "magnitude": 0.10},
            {"feature": "can_disconnect", "label": "Ability to Disconnect", "value": raw.get("can_disconnect", 3), "shap_value": -0.08, "direction": "risk_decrease", "magnitude": 0.08},
            {"feature": "support_from_manager", "label": "Manager Support", "value": raw.get("support_from_manager", 3), "shap_value": -0.06, "direction": "risk_decrease", "magnitude": 0.06},
        ]

        cur.execute("""
            INSERT INTO assessments (employee_id, risk_score, risk_level, risk_label, burnout_type, confidence, raw_inputs, shap_contributions)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (emp_id, emp[6], emp[7], emp[8], emp[9], emp[10], json.dumps(raw), json.dumps(shap_contribs)))

    conn.commit()
    print("SUCCESS: 8 Enterprise Employees seeded into Neon PostgreSQL!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    seed()
