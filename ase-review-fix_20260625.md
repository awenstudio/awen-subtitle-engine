# ASE Code Review & Fix — 2026-06-25

## Objective
Make the Awen Subtitle Engine (ASE) project importable and functionally correct end-to-end.

## Issues Found & Fixed

### 1. config.py — Docker paths fail on local Mac (CRITICAL)
**Problem:** Default paths `/data/subtitles`, `/data/temp`, `/data/db` assume Docker. On local macOS, `Path.mkdir()` fails with `OSError: Read-only file system: '/data'` at import time — the app can't even load.

**Fix:** Changed defaults to project-relative paths (`./data/subtitles`, `./data/temp`, `./data/db`). Docker deployments override via env vars in `docker-compose.yml`, so no Docker behavior changes.

### 2. routes.py — Route checks file existence before DB cache (BUG)
**Problem:** `generate_subtitle()` called `video_path.exists()` first, returning 404 for videos already processed and removed. The "already done" DB check was unreachable when the original file was gone.

**Fix:** Restructured to check DB for existing complete results first, then validate file existence only for new submissions.

### 3. routes.py — Empty video_path crashes with IsADirectoryError (BUG)
**Problem:** `Path("").exists()` returns `True` (resolves to `.`), so empty string passed the existence check. Then `compute_video_hash("")` tried to hash the current directory, crashing.

**Fix:** Added explicit empty-string validation returning HTTP 422.

## Verification
- `python -c "from app.main import app; print('OK')"` → **OK**
- `pytest tests/` → **49 passed, 0 failed** (6 deprecation warnings)
- All imports resolve correctly, no circular dependencies

## Files Modified
- `app/config.py` — project-relative default paths
- `app/api/routes.py` — restructured generate endpoint logic

## Commit
`b0f1319` — "fix: resolve import errors and route logic issues"
