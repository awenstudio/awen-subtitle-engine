"""Pydantic schemas for API requests/responses"""

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    video_path: str


class GenerateResponse(BaseModel):
    job_id: int
    video_id: int
    status: str


class JobResponse(BaseModel):
    job_id: int
    video_id: int
    status: str
    progress: int
    current_step: str | None = None
    error: str | None = None


class SubtitleResponse(BaseModel):
    video_id: int
    language: str
    subtitles: dict[str, str | None]


class HealthResponse(BaseModel):
    status: str
    version: str
    whisper_model: str
    uptime: float
