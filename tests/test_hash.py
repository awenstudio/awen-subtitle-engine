"""Tests for video hash computation."""

import os
import hashlib

import pytest

from app.utils.hash import compute_video_hash


class TestComputeVideoHash:
    def test_deterministic(self, fake_video):
        """Same file should always produce the same hash."""
        h1 = compute_video_hash(str(fake_video))
        h2 = compute_video_hash(str(fake_video))
        assert h1 == h2

    def test_returns_sha256_hex(self, fake_video):
        """Hash should be a 64-char hex string (SHA-256)."""
        h = compute_video_hash(str(fake_video))
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_files_different_hash(self, tmp_dir):
        """Different file content should produce different hashes."""
        f1 = tmp_dir / "a.mp4"
        f2 = tmp_dir / "b.mp4"
        f1.write_bytes(b"\x00" * 1024)
        f2.write_bytes(b"\xff" * 1024)

        assert compute_video_hash(str(f1)) != compute_video_hash(str(f2))

    def test_same_content_same_hash(self, tmp_dir):
        """Identical files should produce identical hashes."""
        f1 = tmp_dir / "x.mp4"
        f2 = tmp_dir / "y.mp4"
        data = b"video content here"
        f1.write_bytes(data)
        f2.write_bytes(data)

        assert compute_video_hash(str(f1)) == compute_video_hash(str(f2))

    def test_same_size_same_prefix_same_hash(self, tmp_dir):
        """
        Hash = SHA-256(file_size || first_1MB).
        Two files >1MB with same size and same first 1MB → same hash,
        even if content after 1MB differs.
        """
        first_mb = os.urandom(1024 * 1024)

        f1 = tmp_dir / "big1.mp4"
        f2 = tmp_dir / "big2.mp4"
        f1.write_bytes(first_mb + b"\x00" * 100)
        f2.write_bytes(first_mb + b"\xff" * 100)

        # Same size (1MB+100), same first 1MB → same hash
        assert compute_video_hash(str(f1)) == compute_video_hash(str(f2))

    def test_same_prefix_different_size_different_hash(self, tmp_dir):
        """
        Two files with same first 1MB but different total size → different hash,
        because file size is part of the hash input.
        """
        first_mb = os.urandom(1024 * 1024)

        small = tmp_dir / "small.mp4"
        big = tmp_dir / "big.mp4"
        small.write_bytes(first_mb)            # exactly 1MB
        big.write_bytes(first_mb + b"\x00" * 256)  # 1MB + 256

        assert compute_video_hash(str(small)) != compute_video_hash(str(big))

    def test_sub_1mb_files(self, tmp_dir):
        """For files < 1MB, the entire file content + size determine the hash."""
        a = tmp_dir / "a.mp4"
        b = tmp_dir / "b.mp4"
        a.write_bytes(b"hello" * 100)
        b.write_bytes(b"world" * 100)

        assert compute_video_hash(str(a)) != compute_video_hash(str(b))

    def test_manual_hash_verification(self, tmp_dir):
        """Verify hash matches manual SHA-256 of size + first 1MB."""
        f = tmp_dir / "verify.mp4"
        data = os.urandom(2048)
        f.write_bytes(data)

        expected = hashlib.sha256()
        expected.update(str(len(data)).encode())
        expected.update(data)
        expected_hex = expected.hexdigest()

        assert compute_video_hash(str(f)) == expected_hex
