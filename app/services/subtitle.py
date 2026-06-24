"""SRT subtitle file generation"""

from pathlib import Path

from app.config import SUBTITLE_ROOT


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(segments: list[dict], output_path: str) -> str:
    """
    Generate SRT file from segments.
    segments: [{"start": float, "end": float, "text": str}]
    Returns the output path.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        text = seg["text"]
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def generate_bilingual_srt(
    original_segments: list[dict],
    translated_texts: list[str],
    output_path: str,
) -> str:
    """
    Generate bilingual SRT with original + translation stacked.
    Original on top, translation below, blank line separator.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, (seg, zh_text) in enumerate(zip(original_segments, translated_texts), 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        original_text = seg["text"]
        lines.append(f"{i}\n{start} --> {end}\n{original_text}\n{zh_text}\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def get_subtitle_path(video_path: str, lang_code: str, sub_type: str) -> str:
    """
    Get the output path for a subtitle file.
    Example: /data/subtitles/movie.jp.srt
    """
    video_name = Path(video_path).stem
    filename = f"{video_name}.{lang_code}.{sub_type}.srt"
    return str(SUBTITLE_ROOT / filename)
