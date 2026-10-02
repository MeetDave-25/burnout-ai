"""Runtime configuration, read from environment variables (and a local .env file)."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str) -> str:
    """Like os.getenv, but a blank value (e.g. `DATABASE_URL=` in .env) also falls back to the default."""
    return os.getenv(name) or default


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def normalize_database_url(url: str) -> str:
    """Accept every Postgres URL style providers hand out (postgres://, postgresql+psycopg://, postgresql+asyncpg://…)
    and use the installed psycopg2 driver."""
    url = url.strip().strip('"').strip("'")
    for prefix in ("postgres://", "postgresql+psycopg://", "postgresql+psycopg2://", "postgresql+asyncpg://", "postgresql+pg8000://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def _database_url() -> str:
    return normalize_database_url(_env("DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'burnout.db').as_posix()}"))


DEV_SECRET = "dev-only-insecure-secret-change-me"


@dataclass(frozen=True)
class Settings:
    # development | production. Production turns on the safety checks below and hides the API docs.
    env: str = _env("ENV", "development").lower()
    database_url: str = _database_url()
    # Run database migrations automatically at startup (fine for one server; set false if you run them separately).
    auto_migrate: bool = _env("AUTO_MIGRATE", "true").lower() == "true"
    # Built website (npm run build) served by the API, so the whole product runs as one service on one domain.
    frontend_dist: Path = Path(_env("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist")))
    model_dir: Path = Path(_env("MODEL_DIR", str(PROJECT_ROOT / "model" / "v2" / "artifacts")))
    cors_origins: list[str] = field(
        default_factory=lambda: _csv(_env("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"))
    )
    # Groups smaller than this are never shown to HR/admins, so individuals can't be singled out.
    min_group_size: int = int(_env("MIN_GROUP_SIZE", "5"))
    # Signs session cookies. Must be a long random value in production (set SECRET_KEY in .env).
    secret_key: str = _env("SECRET_KEY", DEV_SECRET)
    cookie_secure: bool = _env("COOKIE_SECURE", "false").lower() == "true"  # true behind HTTPS

    # Public URL of the web app, used in links inside emails.
    app_url: str = _env("APP_URL", "http://localhost:5173").rstrip("/")
    # Public URL of this API (for one-click unsubscribe links in emails). Defaults to <APP_URL>/api.
    api_url: str = _env("API_URL", _env("APP_URL", "http://localhost:5173").rstrip("/") + "/api").rstrip("/")

    # Require the 6-digit email code before an account can be used. Turn off only until email sending is set up.
    require_email_verification: bool = _env("REQUIRE_EMAIL_VERIFICATION", "true").lower() != "false"

    # Email. "console" saves every email to backend/outbox/ (development); "smtp" sends for real;
    # "memory" keeps them in a list (tests).
    email_backend: str = _env("EMAIL_BACKEND", "console")
    email_from: str = _env("EMAIL_FROM", "BurnoutAI <no-reply@localhost>")
    smtp_host: str = _env("SMTP_HOST", "")
    smtp_port: int = int(_env("SMTP_PORT", "587"))
    smtp_user: str = _env("SMTP_USER", "")
    smtp_password: str = _env("SMTP_PASSWORD", "")
    smtp_security: str = _env("SMTP_SECURITY", "starttls")  # starttls | ssl | none

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def problems(self) -> list[str]:
        """Settings that would be unsafe in production (empty list = good to go)."""
        issues = []
        if self.secret_key == DEV_SECRET or len(self.secret_key) < 32:
            issues.append("SECRET_KEY must be a long random value (32+ characters)")
        if not self.cookie_secure:
            issues.append("COOKIE_SECURE must be true (serve the site over HTTPS)")
        if self.database_url.startswith("sqlite") and _env("ALLOW_SQLITE", "false").lower() != "true":
            issues.append("DATABASE_URL points at SQLite; use PostgreSQL (or set ALLOW_SQLITE=true on a server with a persistent disk)")
        if self.app_url.startswith("http://localhost"):
            issues.append("APP_URL must be your public https:// address (it is used in email links)")
        return issues


settings = Settings()
