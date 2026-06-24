"""Tests for API endpoints."""

from unittest.mock import patch, MagicMock
from pathlib import Path
from contextlib import contextmanager

import pytest
from sqlalchemy.orm import sessionmaker


# ──────────────────────────────────────────────────────────────
# GET /api/health
# ──────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "whisper_model" in body
        assert body["uptime"] >= 0

    def test_health_schema(self, client):
        """Response must include all HealthResponse fields."""
        resp = client.get("/api/health")
        body = resp.json()
        for field in ("status", "version", "whisper_model", "uptime"):
            assert field in body, f"Missing field: {field}"


# ──────────────────────────────────────────────────────────────
# POST /api/subtitle/generate
# ──────────────────────────────────────────────────────────────

class TestGenerateEndpoint:
    @patch("app.api.routes.compute_video_hash", return_value="fakehash123")
    @patch("app.api.routes._get_duration", return_value=90.0)
    @patch("app.api.routes.process_video")
    def test_generate_new_video(self, mock_task, mock_dur, mock_hash, client, tmp_path):
        """Submitting a new video should create a job and dispatch a Celery task."""
        video = tmp_path / "anime.mp4"
        video.write_bytes(b"\x00" * 1024)

        resp = client.post("/api/subtitle/generate", json={"video_path": str(video)})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert "job_id" in body
        assert "video_id" in body
        mock_task.delay.assert_called_once()

    def test_generate_missing_video(self, client):
        """Requesting a non-existent video path should return 404."""
        resp = client.post(
            "/api/subtitle/generate",
            json={"video_path": "/nonexistent/fake.mp4"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("app.api.routes.compute_video_hash", return_value="abc123hash")
    @patch("app.api.routes._get_duration", return_value=120.0)
    @patch("app.api.routes.process_video")
    def test_generate_already_done(self, mock_task, mock_dur, mock_hash,
                                   client, populated_db, make_db_session, tmp_path):
        """Video already in DB with 3 subtitles and done job → return done immediately."""
        # Create a real temp file so Path.exists() passes in the route
        video = tmp_path / "sample.mp4"
        video.write_bytes(b"\x00" * 1024)

        # Update the video path in the DB to point to the real temp file
        from app.db.models import Video as VideoModel
        with make_db_session() as db:
            v = db.query(VideoModel).filter(VideoModel.id == 1).first()
            v.path = str(video)
            db.commit()

        resp = client.post(
            "/api/subtitle/generate",
            json={"video_path": str(video)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "done"
        mock_task.delay.assert_not_called()


# ──────────────────────────────────────────────────────────────
# GET /api/job/{job_id}
# ──────────────────────────────────────────────────────────────

class TestJobEndpoint:
    def test_get_existing_job(self, client, populated_db):
        """Return job details for a known job."""
        resp = client.get("/api/job/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == 1
        assert body["status"] == "done"
        assert body["progress"] == 100

    def test_get_nonexistent_job(self, client):
        """Return 404 for unknown job id."""
        resp = client.get("/api/job/9999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────
# GET /api/subtitle/video/{video_id}
# ──────────────────────────────────────────────────────────────

class TestSubtitleVideoEndpoint:
    def test_get_subtitles_for_video(self, client, populated_db):
        """Return subtitle file paths for a video with all three types."""
        resp = client.get("/api/subtitle/video/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["video_id"] == 1
        assert body["language"] == "ja"
        assert body["subtitles"]["original"] is not None
        assert body["subtitles"]["chinese"] is not None
        assert body["subtitles"]["bilingual"] is not None

    def test_get_subtitles_nonexistent_video(self, client):
        """Return 404 for unknown video id."""
        resp = client.get("/api/subtitle/video/9999")
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────
# GET /api/subtitles
# ──────────────────────────────────────────────────────────────

class TestListSubtitlesEndpoint:
    def test_list_subtitles(self, client, populated_db):
        """List all videos with subtitle presence flags."""
        resp = client.get("/api/subtitles")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1

        entry = body[0]
        assert entry["video_id"] == 1
        assert entry["has_original"] is True
        assert entry["has_chinese"] is True
        assert entry["has_bilingual"] is True


# ──────────────────────────────────────────────────────────────
# Edge cases & validation
# ──────────────────────────────────────────────────────────────

class TestAPIValidation:
    def test_generate_missing_body(self, client):
        """POST without JSON body should return 422."""
        resp = client.post("/api/subtitle/generate")
        assert resp.status_code == 422
