"""ASE Configuration"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media"))
SUBTITLE_ROOT = Path(os.getenv("SUBTITLE_ROOT", "/data/subtitles"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "/data/temp"))
DB_DIR = Path(os.getenv("DB_DIR", "/data/db"))

# Ensure dirs exist
SUBTITLE_ROOT.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# --- Database ---
DATABASE_URL = f"sqlite:///{DB_DIR / 'ase.db'}"

# --- Celery ---
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# --- Whisper ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# --- Translation ---
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# --- Supported ---
SUPPORTED_VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".flv", ".wmv", ".webm"}
SUPPORTED_LANGUAGES = {"ja", "en", "ko"}

# --- App ---
APP_VERSION = "0.1.0"
