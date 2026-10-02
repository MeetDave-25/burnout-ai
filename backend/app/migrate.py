"""Apply database migrations.

    python -m app.migrate            # bring the database up to date (run on every deploy)

Safety: a database is only "adopted" (stamped as current) if its existing tables really match BurnoutAI's
schema. If it holds tables from another application, start-up stops with a clear message instead of
running against a broken schema.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from .db import Base, engine

BACKEND = Path(__file__).resolve().parents[1]


class SchemaMismatch(RuntimeError):
    pass


def _config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.attributes["configure_logger"] = False
    return cfg


def schema_problems() -> list[str]:
    """Differences between the live database and the models: missing tables or columns."""
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    problems = []
    for name, table in Base.metadata.tables.items():
        if name not in existing:
            problems.append(f"table '{name}' is missing")
            continue
        have = {c["name"] for c in insp.get_columns(name)}
        missing = [c.name for c in table.columns if c.name not in have]
        if missing:
            problems.append(f"table '{name}' has different columns (missing {', '.join(missing)})")
    return problems


def _fail(problems: list[str]) -> None:
    raise SchemaMismatch(
        "The database in DATABASE_URL contains tables that don't match BurnoutAI "
        "(probably left over from another app):\n  - " + "\n  - ".join(problems)
        + "\nPoint DATABASE_URL at a new, empty database (or clear this one), then start again."
    )


def upgrade() -> None:
    cfg = _config()
    tables = set(inspect(engine).get_table_names())
    ours = set(Base.metadata.tables)
    if "alembic_version" not in tables and tables & ours:
        # Tables exist but were never migrated: adopt them only if they really are ours.
        if problems := schema_problems():
            _fail(problems)
        command.stamp(cfg, "head")
    command.upgrade(cfg, "head")
    if problems := schema_problems():
        _fail(problems)


if __name__ == "__main__":
    upgrade()
    print("Database is up to date.")
