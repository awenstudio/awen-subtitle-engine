"""Audio extraction from video using FFmpeg"""

import subprocess
import os
from pathlib import Path

from app.config import TEMP_DIR


def extract_audio(video_path: str, video_hash: str) -> str:
    """
    Extract audio from video file as WAV (16kHz mono, Whisper-optimized).
    Returns path to extracted audio file.
    """
    output_path = str(TEMP_DIR / f"audio_{video_hash}.wav")

    if os.path.exists(output_path):
        return output_path

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    return output_path


def cleanup_temp(video_hash: str):
    """Remove temporary audio file."""
    audio_path = TEMP_DIR / f"audio_{video_hash}.wav"
    if audio_path.exists():
        audio_path.unlink()
