"""Online subtitle search and download via OpenSubtitles API"""

import os
import struct
import hashlib
from pathlib import Path

import httpx

from app.logging import get_logger
from app.config import SUBTITLE_ROOT

logger = get_logger("services.online_subtitle")

OPENSUBTITLES_API_URL = "https://api.opensubtitles.com/api/v1"
OPENSUBTITLES_API_KEY = os.getenv("OPENSUBTITLES_API_KEY", "")


def compute_video_hash_opensubtitles(filepath: str) -> str:
    """
    Compute the OpenSubtitles hash for a video file.
    Uses the first and last 64KB of the file, as per the OpenSubtitles spec.
    Returns a hex string.
    """
    size = os.path.getsize(filepath)
    if size < 65536:
        return ""

    h = hashlib.md5()
    with open(filepath, "rb") as f:
        # First 64KB
        h.update(f.read(65536))
        # Last 64KB
        f.seek(-65536, 2)
        h.update(f.read(65536))

    # OpenSubtitles hash uses the sum of uint64 pairs
    hash_val = 0
    with open(filepath, "rb") as f:
        for chunk_start in (0, max(0, size - 65536)):
            f.seek(chunk_start)
            chunk = f.read(65536)
            # Pad to 8-byte boundary
            if len(chunk) % 8:
                chunk += b"\x00" * (8 - len(chunk) % 8)
            for i in range(0, len(chunk), 8):
                hash_val += struct.unpack("<Q", chunk[i:i+8])[0]
                hash_val &= 0xFFFFFFFFFFFFFFFF  # keep as uint64

    return f"{hash_val:016x}"


def search_subtitles(
    video_path: str,
    languages: str = "zh,en",
) -> list[dict]:
    """
    Search OpenSubtitles for matching subtitles by video hash.

    Args:
        video_path: Path to the video file.
        languages: Comma-separated language codes (e.g. "zh,en").

    Returns:
        List of subtitle info dicts with keys:
            - id: OpenSubtitles subtitle ID
            - language: language code
            - format: file format (srt, ass, etc.)
            - download_count: popularity
            - filename: original filename
    """
    if not OPENSUBTITLES_API_KEY:
        logger.warning("OPENSUBTITLES_API_KEY not set, skipping online subtitle search")
        return []

    file_hash = compute_video_hash_opensubtitles(video_path)
    if not file_hash:
        logger.warning(f"File too small for hash computation: {video_path}")
        return []

    file_size = os.path.getsize(video_path)

    headers = {
        "Api-Key": OPENSUBTITLES_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "ASE/0.1.0",
    }

    params = {
        "moviehash": file_hash,
        "languages": languages,
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{OPENSUBTITLES_API_URL}/subtitles",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            files = attrs.get("files", [])
            if not files:
                continue

            results.append({
                "id": files[0].get("file_id"),
                "language": attrs.get("language", "unknown"),
                "format": attrs.get("format", "srt"),
                "download_count": attrs.get("download_count", 0),
                "filename": files[0].get("file_name", ""),
            })

        # Sort by download count (most popular first)
        results.sort(key=lambda x: x["download_count"], reverse=True)
        logger.info(f"Found {len(results)} online subtitles for {Path(video_path).name}")
        return results

    except httpx.HTTPStatusError as e:
        logger.error(f"OpenSubtitles API error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Failed to search subtitles: {e}")
        return []


def download_subtitle(
    file_id: int,
    video_path: str,
    lang_code: str = "en",
) -> str | None:
    """
    Download a subtitle file from OpenSubtitles.

    Args:
        file_id: OpenSubtitles file ID.
        video_path: Original video path (used to derive output filename).
        lang_code: Language code for the subtitle file extension.

    Returns:
        Path to the downloaded .srt file, or None on failure.
    """
    if not OPENSUBTITLES_API_KEY:
        logger.warning("OPENSUBTITLES_API_KEY not set, cannot download")
        return None

    headers = {
        "Api-Key": OPENSUBTITLES_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "ASE/0.1.0",
    }

    try:
        # Step 1: Get download link
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{OPENSUBTITLES_API_URL}/download",
                headers=headers,
                json={"file_id": file_id},
            )
            resp.raise_for_status()
            download_info = resp.json()

        download_url = download_info.get("link")
        if not download_url:
            logger.error(f"No download link returned for file_id={file_id}")
            return None

        # Step 2: Download the subtitle file
        video_stem = Path(video_path).stem
        output_path = str(SUBTITLE_ROOT / f"{video_stem}.{lang_code}.online.srt")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with httpx.Client(timeout=60) as client:
            resp = client.get(download_url)
            resp.raise_for_status()

            # Write as UTF-8
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(resp.text)

        logger.info(f"Downloaded subtitle: {output_path}")
        return output_path

    except httpx.HTTPStatusError as e:
        logger.error(f"Download failed: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Failed to download subtitle: {e}")
        return None


def search_and_download(
    video_path: str,
    languages: str = "zh,en",
) -> str | None:
    """
    Search for subtitles and download the best match.

    Args:
        video_path: Path to the video file.
        languages: Comma-separated language codes.

    Returns:
        Path to downloaded .srt file, or None if nothing found.
    """
    results = search_subtitles(video_path, languages=languages)
    if not results:
        logger.info(f"No online subtitles found for {Path(video_path).name}")
        return None

    # Try downloading the most popular result
    best = results[0]
    lang_code = best.get("language", "en")
    file_id = best.get("id")

    if not file_id:
        return None

    return download_subtitle(file_id, video_path, lang_code=lang_code)
