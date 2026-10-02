# BurnoutAI: website + API in one container.
#   docker build -t burnoutai .
#   docker run -p 8000:8000 --env-file .env.production burnoutai

# ── 1. Build the website ──────────────────────────────────────────
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Shown in the footer and legal pages (baked in at build time).
ARG VITE_COMPANY_NAME=BurnoutAI
ARG VITE_CONTACT_EMAIL=
ARG VITE_JURISDICTION=India
ENV VITE_COMPANY_NAME=$VITE_COMPANY_NAME VITE_CONTACT_EMAIL=$VITE_CONTACT_EMAIL VITE_JURISDICTION=$VITE_JURISDICTION
RUN npm run build

# ── 2. API + model, serving the built website ─────────────────────
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    ENV=production FRONTEND_DIST=/app/frontend/dist
# libgomp1: OpenMP runtime needed by XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY backend/app backend/app
COPY backend/migrations backend/migrations
COPY backend/scripts backend/scripts
COPY backend/alembic.ini backend/alembic.ini
COPY model/v2/artifacts model/v2/artifacts
COPY --from=web /web/dist frontend/dist
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/api/health')"
# Migrations run at startup (AUTO_MIGRATE=true). Proxy headers so rate limits see the visitor's real IP.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
