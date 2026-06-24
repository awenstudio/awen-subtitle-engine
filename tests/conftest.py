"""Shared test fixtures for ASE test suite."""

import os
import sys
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import Base  # noqa: E402
from app.db.models import Video, Job, Subtitle  # noqa: E402


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """In-memory SQLite engine with StaticPool for thread safety (TestClient)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Yield a SQLAlchemy session bound to the in-memory engine."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def make_db_session(db_engine):
    """Factory that returns a context-manager yielding a new session."""
    Session = sessionmaker(bind=db_engine)

    @contextmanager
    def _factory():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    return _factory


@pytest.fixture()
def mock_db_session(make_db_session):
    """Patch get_db_session everywhere it is imported so tests use the in-memory DB."""
    with patch("app.db.database.get_db_session", make_db_session), \
         patch("app.api.routes.get_db_session", make_db_session), \
         patch("app.workers.tasks.get_db_session", make_db_session), \
         patch("app.watcher.get_db_session", make_db_session):
        yield make_db_session


# ---------------------------------------------------------------------------
# Temporary directory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture()
def fake_video(tmp_dir):
    """Create a small fake video file."""
    video = tmp_dir / "test_video.mp4"
    video.write_bytes(os.urandom(2048))
    return video


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_segments():
    """Typical ASR output segments."""
    return [
        {"start": 0.0, "end": 2.5, "text": "Hello world"},
        {"start": 2.5, "end": 5.1, "text": "This is a test"},
        {"start": 5.1, "end": 8.75, "text": "Goodbye"},
    ]


@pytest.fixture()
def sample_translations():
    """Corresponding Chinese translations."""
    return ["你好世界", "这是一个测试", "再见"]


@pytest.fixture()
def populated_db(db_engine):
    """DB with one Video, Job, and three Subtitle records pre-loaded."""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    video = Video(
        path="/media/sample.mp4",
        hash="abc123hash",
        language="ja",
        duration=120.0,
    )
    session.add(video)
    session.flush()

    job = Job(video_id=video.id, status="done", progress=100, current_step="completed")
    session.add(job)
    session.flush()

    for sub_type in ("original", "chinese", "bilingual"):
        sub = Subtitle(
            video_id=video.id,
            type=sub_type,
            file_path=f"/data/subtitles/sample.ja.{sub_type}.srt",
        )
        session.add(sub)

    session.commit()
    session.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(populated_db, make_db_session):
    """FastAPI TestClient with mocked DB (populated with sample data)."""
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.db.database.get_db_session", make_db_session), \
         patch("app.api.routes.get_db_session", make_db_session), \
         patch("app.workers.tasks.get_db_session", make_db_session):
        yield TestClient(app)
