# BurnoutAI — Early Burnout Risk Prediction with Explainable AI

Measures burnout with a validated questionnaire, explains **why** with exact SHAP driver
contributions ("workload added +4 points"), shows **what would help most**, and warns **early**
when someone's trend is heading toward burnout.

Two audiences:
- **Individuals** get their own risk score, the reasons behind it, and an action plan.
- **Companies / schools** get team-level insights (risk, trend, top drivers per department or class).
  Groups smaller than `MIN_GROUP_SIZE` (default 5) are hidden, so no individual can be singled out.

## Project structure

```
burnout-ai/
├── Dockerfile               Website + API in one production container
├── render.yaml              One-click Render deploy
├── backend/                 FastAPI service (API under /api, serves the built website)
│   ├── app/
│   │   ├── main.py          API routes
│   │   ├── ml/instrument.py Copenhagen Burnout Inventory items + scoring
│   │   ├── ml/predictor.py  Driver model, SHAP explanations, levers, what-if
│   │   ├── ml/forecast.py   Trend + early-warning forecast
│   │   ├── ml/content.py    Levels, driver questions, advice text
│   │   ├── insights.py      Privacy-preserving team aggregates
│   │   ├── db.py            SQLAlchemy models (SQLite local / Postgres prod)
│   │   └── schemas.py       Validated request/response models
│   ├── migrations/          Alembic database migrations (applied at start-up)
│   ├── scripts/             seed_demo, send_reminders, test_email
│   └── tests/
├── frontend/                React + Vite + Tailwind UI ("Ember" design)
│   └── src/pages/           Home, CheckIn, ReadingPage, Me (personal), OrgPulse (HR)
├── model/v2/                Current model: simulate.py, train.py, artifacts/ (model + report)
├── model/                   v1 model (used only by legacy/)
├── data/                    Training dataset (currently synthetic)
└── legacy/                  Old Flask API + single-file frontend (retired)
```

## Run it (development)

```bash
# terminal 1: API on :8000 (serves everything under /api)
cd backend
pip install -r requirements-dev.txt
python -m scripts.seed_demo          # first time: database + sample organisations
uvicorn app.main:app --reload

# terminal 2: website on :5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Tests: `cd backend && python -m pytest`. Settings live in `.env` (see `.env.example`).

## API

Full interactive docs at `http://localhost:8000/docs`.

| Area | Routes |
|---|---|
| Public | `GET /health`, `GET /model-info`, `GET /instrument?role=`, `POST /predict` (anonymous, nothing stored), `POST /what-if` |
| Accounts | `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET/PATCH /me` |
| My data | `POST/GET /me/assessments`, `GET /me/latest`, `GET /me/forecast`, `POST/DELETE /me/sharing`, `DELETE /me/membership` |
| Organisations | `GET/POST /orgs`, `GET /orgs/{id}`, `GET /orgs/{id}/insights` (admins), `GET /orgs/{id}/admin`, `POST /orgs/{id}/groups`, `POST /orgs/{id}/invites`, `DELETE /orgs/{id}/invites/{code}` |
| Invites | `GET /invites/{code}` (preview), `POST /invites/{code}/accept` (requires consent) |
| Public demo | `GET /demo/personas`, `GET /members/{id}/…` (demo people only) |

## SaaS model

- **Accounts:** email + password (scrypt-hashed), session in an http-only cookie signed with `SECRET_KEY`.
- **Roles per organisation:** `owner` (created it; invites admins), `admin` (HR / wellbeing staff: sees aggregates, manages invites and groups), `member` (takes check-ins).
- **Privacy rules enforced server-side:** organisations only ever get aggregates; groups under `MIN_GROUP_SIZE` are locked;
  only check-ins made *after* someone joined count; stopping sharing or leaving takes effect immediately; demo orgs are public and read-only.
- **Email & security:** 6-digit email verification (OTP) before anything else works; forgot-password by code
  (signs out every other session); change password; rate limits on sign-up, login, codes and resets; branded HTML +
  plain-text emails (code, welcome, invite, reminder, password changed, account deleted).
- **Privacy rights:** download all your data (JSON) and permanently delete your account from Account & privacy.
- **Not built yet:** billing (prices on `/pricing` are placeholders), SSO, DB migrations (Alembic).

## Deploy (production)

The whole product (website + API + model) runs as **one Docker service on one domain**. The API lives under
`/api`, so the login cookie is first-party and secure. Migrations run automatically at start-up.

**1. Database:** create a free PostgreSQL database on [Neon](https://neon.tech) (or any Postgres) and copy its connection string.

**2. Host:** any platform that runs a Dockerfile: Render (`render.yaml` included), Railway, Fly.io, Google Cloud Run,
or a VPS with `docker build -t burnoutai . && docker run -p 8000:8000 --env-file .env.production burnoutai`.
Give it at least 1 GB RAM (the model + SHAP need ~400 MB).

**3. Environment variables** on the host:

| Variable | Value |
|---|---|
| `ENV` | `production` |
| `DATABASE_URL` | your Postgres connection string |
| `SECRET_KEY` | 48+ random characters (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
| `COOKIE_SECURE` | `true` |
| `APP_URL` | your public address, e.g. `https://burnoutai.in` |
| `REQUIRE_EMAIL_VERIFICATION` | `false` until email works, then `true` |
| `EMAIL_BACKEND` + `SMTP_*` | `console` for now; `smtp` + your provider later (see `.env.example`) |

In production the app **refuses to start** if `SECRET_KEY`, `COOKIE_SECURE`, `DATABASE_URL` or `APP_URL` are unsafe, and tells you which.

**4. Build-time website details** (Docker build args): `VITE_COMPANY_NAME`, `VITE_CONTACT_EMAIL`, `VITE_JURISDICTION`.

**5. After the first deploy:** run once in the host's shell: `python -m scripts.seed_demo` (adds the sample company
shown to people exploring the product; safe to re-run, and it refuses `--reset` in production).

**6. Daily reminders** (optional): schedule `python -m scripts.send_reminders` hourly (Render Cron Job, Railway cron, or system cron).

**7. Before inviting real users:** set up email (until then *forgot password* can't reach anyone), have a lawyer review
`/privacy` and `/terms`, and check the site with a real phone over HTTPS.

**Changing the database later:** edit `app/db.py`, then `alembic revision --autogenerate -m "what changed"` in `backend/`;
the next deploy applies it automatically.

## How it works

1. **What — validated measurement.** The headline score is the
   [Copenhagen Burnout Inventory](https://doi.org/10.1080/02678370500297720) (public domain,
   13 items: personal + work/study-related burnout, 0–100). Levels: < 50 Low, 50–74 Moderate,
   ≥ 75 High. If the questionnaire is skipped, the model's estimate is shown and labelled as such.
2. **Why — explainable driver model.** XGBoost with monotonic constraints estimates the CBI score
   from 12 modifiable drivers based on the Job Demands–Resources model (workload, hours, after-hours work,
   meetings, sleep, days off, autonomy, support, recognition, ability to disconnect, role, remote).
   TreeSHAP splits the estimate exactly: `base_score + Σ contributions = estimated_score`. The
   gap between measured and estimated score is shown as burnout *not* explained by work factors.
   Symptoms (exhaustion, cynicism) are deliberately **not** used as predictors — v1 did, which was circular.
3. **What helps — levers & what-if.** The estimated effect of one realistic step on each driver.
4. **When — early warning.** A recency-weighted trend over check-ins projects 4 weeks ahead with an
   80% interval; a warning fires when someone below 50 is projected to cross it. SHAP contributions
   from early vs. recent check-ins show what changed.

## Model status — read before quoting accuracy

The current model (`2.0.0-prior`) is trained on a **simulation calibrated to published burnout
research** — no public dataset pairs a validated burnout score with these drivers. See
[model/v2/artifacts/report.md](model/v2/artifacts/report.md): MAE 12 CBI points, R² 0.29,
AUC 0.76 for CBI ≥ 50 on simulated test data. That shows the pipeline behaves sensibly; it is
**not** real-world accuracy. The measured score (CBI) is validated; the explanation model is not yet.

**Path to real accuracy:** run pilots where people answer the CBI + drivers weekly. Once ≥ 300
real check-ins exist (demo orgs are excluded automatically), retrain and compare:

```bash
cd model/v2
python train.py --from-db "$DATABASE_URL"
```

Other limitations: burnout pattern (Frenetic / Under-Challenged / Worn-Out) is rule-based; no
authentication yet (member endpoints must be locked down before real use); no DB migrations yet
(use `seed_demo --reset` after schema changes in development).

## Ethics

Risk assessment, not diagnosis. Individuals own their data; organisations see aggregates only;
results must never be used for performance evaluation.
