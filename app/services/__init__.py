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

    # Skip if already extracted
    if os.path.exists(output_path):
        return output_path

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",                    # No video
        "-acodec", "pcm_s16le",   # 16-bit PCM
        "-ar", "16000",           # 16kHz (optimal for Whisper)
        "-ac", "1",               # Mono
        "-y",                     # Overwrite
        output_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        return output_path
    except subprocess.TimeoutExpired:
        raise RuntimeError("Audio extraction timed out (10 min limit)")


def get_video_info(video_path: str) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-print_format", "json",
        video_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        import json
        return json.loads(result.stdout)
    except Exception:
        return {}


def cleanup_temp(video_hash: str):
    """Remove temporary audio file."""
    audio_path = TEMP_DIR / f"audio_{video_hash}.wav"
    if audio_path.exists():
        audio_path.unlink()
