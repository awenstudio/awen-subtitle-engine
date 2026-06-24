# ASE Project - Missing Pieces Added

**Date:** 2026-06-25  
**Commit:** 8757249

## Objective
Add missing pieces to the Awen Subtitle Engine project.

## Changes Made

### 1. `app/cli.py` - CLI Entry Point
- Click-based CLI with three commands:
  - `ase generate <video_path>` — Generate subtitles (ASR + translate). Supports `--lang`, `--no-translate`, `--online` flags.
  - `ase watch <directory>` — Watch directory for new videos, auto-queue subtitle jobs.
  - `ase status` — Show system config, DB stats, and dependency check.
- Entry point via `main()` function.

### 2. `app/services/online_subtitle.py` - Online Subtitle Search
- `compute_video_hash_opensubtitles()` — OpenSubtitles-specific hash (first+last 64KB, md5+uint64 sum).
- `search_subtitles()` — Search by video hash via OpenSubtitles REST API.
- `download_subtitle()` — Download a subtitle by file_id, saves as `.srt`.
- `search_and_download()` — Convenience: search + download best match.
- Requires `OPENSUBTITLES_API_KEY` env var.

### 3. `app/logging.py` - Logging Configuration
- `setup_logging()` — Configures console + file handlers under `ase` namespace.
- `get_logger()` — Get child loggers (e.g., `ase.cli`, `ase.watcher`).
- Silences noisy third-party loggers (watchdog, httpx, urllib3).

### 4. `requirements.txt` - Updated
- Added `httpx>=0.27.0` (for OpenSubtitles API calls)
- Added `click>=8.1.0` (for CLI)

### 5. Incidental Fixes
- `app/main.py`: initializes logging on import.
- `app/watcher.py`: uses logger instead of print statements.
- Structural refactoring (models, hash, audio extraction into separate files) was already in place.
