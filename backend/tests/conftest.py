import os
import sys
from pathlib import Path

# Use a throwaway in-memory database for tests; must be set before the app is imported.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["MIN_GROUP_SIZE"] = "5"
os.environ["EMAIL_BACKEND"] = "memory"  # capture emails (and their codes) instead of sending
os.environ["RATE_LIMITS"] = "off"  # individual tests switch them on
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "true"  # test the full flow whatever .env says
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy.pool import StaticPool

from app import db
from app.email import sender


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    sender.SENT.clear()
    engine = db.create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(db, "engine", engine)
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(engine)
    yield
    engine.dispose()
