"""Apply database migrations.

    python -m app.migrate            # bring the database up to date (run on every deploy)

A database created before migrations existed (by the old create_all) is detected and stamped, not recreated.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from .db import engine

BACKEND = Path(__file__).resolve().parents[1]


def _config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade() -> None:
    cfg = _config()
    tables = set(inspect(engine).get_table_names())
    if "users" in tables and "alembic_version" not in tables:
        command.stamp(cfg, "head")  # tables already exist from before migrations; record that they're current
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    upgrade()
    print("Database is up to date.")
