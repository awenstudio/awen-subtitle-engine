"""Tests for SRT subtitle generation."""

import os
from pathlib import Path

import pytest

from app.services.subtitle import (
    _format_srt_time,
    generate_srt,
    generate_bilingual_srt,
    get_subtitle_path,
)


# ──────────────────────────────────────────────────────────────
# _format_srt_time
# ──────────────────────────────────────────────────────────────

class TestFormatSrtTime:
    def test_zero(self):
        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_simple_seconds(self):
        assert _format_srt_time(1.5) == "00:00:01,500"

    def test_minutes(self):
        assert _format_srt_time(65.0) == "00:01:05,000"

    def test_hours(self):
        assert _format_srt_time(3661.123) == "01:01:01,123"

    def test_milliseconds_precision(self):
        assert _format_srt_time(0.001) == "00:00:00,001"
        assert _format_srt_time(0.999) == "00:00:00,999"

    def test_large_time(self):
        """10 hours should still format correctly."""
        assert _format_srt_time(36000.0) == "10:00:00,000"

    def test_fractional_ms_rounding(self):
        """Sub-millisecond precision should truncate, not round up."""
        result = _format_srt_time(1.9999)
        # 0.9999 * 1000 = 999.9 → int() truncates to 999
        assert result == "00:00:01,999"


# ──────────────────────────────────────────────────────────────
# generate_srt
# ──────────────────────────────────────────────────────────────

class TestGenerateSrt:
    def test_basic_srt(self, tmp_path, sample_segments):
        """Generate a valid SRT file from segments."""
        out = str(tmp_path / "output.srt")
        result = generate_srt(sample_segments, out)

        assert result == out
        assert Path(out).exists()

        content = Path(out).read_text(encoding="utf-8")
        # Check numbering
        assert content.startswith("1\n")
        assert "2\n" in content
        assert "3\n" in content
        # Check timestamps
        assert "00:00:00,000 --> 00:00:02,500" in content
        # 5.1 as float → 5.099999... so ms truncates to 099
        assert "00:00:02,500 --> 00:00:05,099" in content
        assert "00:00:05,099 --> 00:00:08,750" in content
        # Check text
        assert "Hello world" in content
        assert "This is a test" in content
        assert "Goodbye" in content

    def test_single_segment(self, tmp_path):
        """SRT with one segment."""
        segs = [{"start": 10.0, "end": 12.5, "text": "Only one"}]
        out = str(tmp_path / "single.srt")
        generate_srt(segs, out)

        content = Path(out).read_text(encoding="utf-8")
        assert "1\n00:00:10,000 --> 00:00:12,500\nOnly one" in content

    def test_empty_segments(self, tmp_path):
        """Empty segment list should produce an empty file."""
        out = str(tmp_path / "empty.srt")
        generate_srt([], out)

        content = Path(out).read_text(encoding="utf-8")
        assert content.strip() == ""

    def test_creates_parent_dirs(self, tmp_path):
        """generate_srt should create intermediate directories."""
        out = str(tmp_path / "sub" / "dir" / "deep.srt")
        segs = [{"start": 0.0, "end": 1.0, "text": "Nested"}]
        generate_srt(segs, out)
        assert Path(out).exists()

    def test_utf8_content(self, tmp_path):
        """SRT should handle Unicode text correctly."""
        segs = [{"start": 0.0, "end": 2.0, "text": "日本語テスト 🎌"}]
        out = str(tmp_path / "unicode.srt")
        generate_srt(segs, out)

        content = Path(out).read_text(encoding="utf-8")
        assert "日本語テスト 🎌" in content

    def test_srt_block_structure(self, tmp_path, sample_segments):
        """Each SRT block must be: index \\n timestamps \\n text \\n."""
        out = str(tmp_path / "struct.srt")
        generate_srt(sample_segments, out)

        content = Path(out).read_text(encoding="utf-8")
        blocks = [b.strip() for b in content.strip().split("\n\n") if b.strip()]
        assert len(blocks) == 3

        for i, block in enumerate(blocks, 1):
            lines = block.split("\n")
            assert lines[0] == str(i), f"Block {i} should start with index {i}"
            assert "-->" in lines[1], "Second line must be timestamp range"


# ──────────────────────────────────────────────────────────────
# generate_bilingual_srt
# ──────────────────────────────────────────────────────────────

class TestGenerateBilingualSrt:
    def test_bilingual_basic(self, tmp_path, sample_segments, sample_translations):
        """Bilingual SRT should stack original + translation."""
        out = str(tmp_path / "bilingual.srt")
        result = generate_bilingual_srt(sample_segments, sample_translations, out)

        assert result == out
        content = Path(out).read_text(encoding="utf-8")

        # Original text present
        assert "Hello world" in content
        assert "This is a test" in content
        # Translation present
        assert "你好世界" in content
        assert "这是一个测试" in content
        assert "再见" in content

    def test_bilingual_block_structure(self, tmp_path, sample_segments, sample_translations):
        """Each bilingual block: index \\n timestamps \\n original \\n translation."""
        out = str(tmp_path / "bi_struct.srt")
        generate_bilingual_srt(sample_segments, sample_translations, out)

        content = Path(out).read_text(encoding="utf-8")
        blocks = [b.strip() for b in content.strip().split("\n\n") if b.strip()]
        assert len(blocks) == 3

        first_block = blocks[0].split("\n")
        assert first_block[0] == "1"
        assert "-->" in first_block[1]
        assert first_block[2] == "Hello world"
        assert first_block[3] == "你好世界"

    def test_bilingual_empty(self, tmp_path):
        """Empty lists produce empty file."""
        out = str(tmp_path / "empty_bi.srt")
        generate_bilingual_srt([], [], out)
        assert Path(out).read_text(encoding="utf-8").strip() == ""

    def test_bilingual_creates_dirs(self, tmp_path):
        """Parent directories are created."""
        out = str(tmp_path / "a" / "b" / "bi.srt")
        segs = [{"start": 0, "end": 1, "text": "Hi"}]
        generate_bilingual_srt(segs, ["嗨"], out)
        assert Path(out).exists()


# ──────────────────────────────────────────────────────────────
# get_subtitle_path
# ──────────────────────────────────────────────────────────────

class TestGetSubtitlePath:
    def test_path_structure(self):
        """Path should follow: SUBTITLE_ROOT / {stem}.{lang}.{type}.srt."""
        path = get_subtitle_path("/media/myvideo.mp4", "ja", "original")
        assert path.endswith("myvideo.ja.original.srt")

    def test_different_langs(self):
        p1 = get_subtitle_path("/media/film.mkv", "en", "chinese")
        p2 = get_subtitle_path("/media/film.mkv", "ko", "bilingual")
        assert p1.endswith("film.en.chinese.srt")
        assert p2.endswith("film.ko.bilingual.srt")
