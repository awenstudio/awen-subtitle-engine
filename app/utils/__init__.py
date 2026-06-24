"""Video hash computation for caching"""

import hashlib
import os


def compute_video_hash(filepath: str) -> str:
    """
    Compute a fast hash using file size + first 1MB.
    Fast and collision-resistant enough for subtitle caching.
    """
    size = os.path.getsize(filepath)
    h = hashlib.sha256()
    h.update(str(size).encode())
    with open(filepath, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()
