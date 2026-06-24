"""API Routes - Awen Subtitle Engine"""

import time

from fastapi import APIRouter, HTTPException

from app.config import APP_VERSION, WHISPER_MODEL
from app.api import (
    GenerateRequest,
    GenerateResponse,
    JobResponse,
    SubtitleResponse,
    HealthResponse,
)
from app.db.database import get_db_session
from app.db.models import Video, Subtitle, Job
from app.workers.tasks import process_video
from app.utils.hash import compute_video_hash

router = APIRouter()

_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        whisper_model=WHISPER_MODEL,
        uptime=time.time() - _start_time,
    )


@router.post("/subtitle/generate", response_model=GenerateResponse)
async def generate_subtitle(req: GenerateRequest):
    import os
    from pathlib import Path

    video_path = Path(req.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {req.video_path}")

    video_hash = compute_video_hash(str(video_path))
    duration = _get_duration(str(video_path))

    with get_db_session() as db:
        # Check if video already processed with all subtitles
        existing_video = db.query(Video).filter(Video.path == str(video_path)).first()
        if existing_video:
            subs = (
                db.query(Subtitle)
                .filter(Subtitle.video_id == existing_video.id)
                .count()
            )
            if subs >= 3:
                # Already has all subtitles
                job = (
                    db.query(Job)
                    .filter(Job.video_id == existing_video.id, Job.status == "done")
                    .first()
                )
                if job:
                    return GenerateResponse(
                        job_id=job.id,
                        video_id=existing_video.id,
                        status="done",
                    )

        # Create or update video record
        if existing_video:
            video = existing_video
        else:
            video = Video(
                path=str(video_path),
                hash=video_hash,
                duration=duration,
            )
            db.add(video)
            db.flush()

        # Create job
        job = Job(video_id=video.id, status="pending", progress=0)
        db.add(job)
        db.commit()
        db.refresh(job)

        # Dispatch Celery task
        process_video.delay(job.id)

        return GenerateResponse(
            job_id=job.id,
            video_id=video.id,
            status="pending",
        )


@router.get("/job/{job_id}", response_model=JobResponse)
async def get_job(job_id: int):
    with get_db_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobResponse(
            job_id=job.id,
            video_id=job.video_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            error=job.error,
        )


@router.get("/subtitle/video/{video_id}", response_model=SubtitleResponse)
async def get_subtitles(video_id: int):
    with get_db_session() as db:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        subs = (
            db.query(Subtitle)
            .filter(Subtitle.video_id == video_id)
            .all()
        )

        subtitle_map = {}
        for sub in subs:
            subtitle_map[sub.type] = sub.file_path

        return SubtitleResponse(
            video_id=video.id,
            language=video.language or "unknown",
            subtitles={
                "original": subtitle_map.get("original"),
                "chinese": subtitle_map.get("chinese"),
                "bilingual": subtitle_map.get("bilingual"),
            },
        )


@router.get("/subtitles")
async def list_subtitles():
    """List all videos with their subtitle status."""
    with get_db_session() as db:
        videos = db.query(Video).all()
        result = []
        for v in videos:
            subs = (
                db.query(Subtitle)
                .filter(Subtitle.video_id == v.id)
                .all()
            )
            result.append({
                "video_id": v.id,
                "path": v.path,
                "language": v.language,
                "has_original": any(s.type == "original" for s in subs),
                "has_chinese": any(s.type == "chinese" for s in subs),
                "has_bilingual": any(s.type == "bilingual" for s in subs),
            })
        return result


def _get_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0
