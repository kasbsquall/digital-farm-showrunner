"""Shared pytest fixtures.

Critical ordering: environment variables are set BEFORE any backend module is
imported, because `config.settings` (and the DB engine derived from it) are
module-level singletons evaluated at import time. Setting FORCE_MOCK guarantees
the whole suite runs offline (no Qwen/DashScope/OSS network), and pointing
DATABASE_URL at a throwaway sqlite file keeps tests hermetic — env vars take
priority over the committed .env in pydantic-settings.
"""
import os
import sys
import tempfile

# --- Environment must be configured before importing the app ---------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

os.environ["FORCE_MOCK"] = "true"      # no network: agents return their canned mocks
os.environ["MOCK_VIDEO"] = "true"      # placeholder video, no async submit/poll

_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="showrunner_test_")
os.close(_db_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")

import pytest  # noqa: E402

from database.db import Base, engine, SessionLocal  # noqa: E402
from database.models import Character, Episode  # noqa: E402

Base.metadata.create_all(bind=engine)


def _seed_characters(db):
    cast = [
        Character(name="Bruno", species="rooster", personality="fiery revolutionary",
                  visual_desc="a red clay rooster with a raised comb"),
        Character(name="Pepe", species="pig", personality="hungry optimist",
                  visual_desc="a chubby pink clay pig"),
        Character(name="Nina", species="hen", personality="deadpan news anchor",
                  visual_desc="a small brown clay hen"),
    ]
    db.add_all(cast)
    db.commit()


@pytest.fixture(autouse=True)
def _reset_db():
    """Truncate tables before every test so state never leaks between them."""
    db = SessionLocal()
    try:
        db.query(Episode).delete()
        db.query(Character).delete()
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_db(db):
    _seed_characters(db)
    return db


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    try:
        engine.dispose()
        os.remove(_db_path)
    except OSError:
        pass
