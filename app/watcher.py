"""Directory watcher for automatic subtitle generation"""

import os
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.config import SUPPORTED_VIDEO_EXTENSIONS
from app.db.database import get_db_session
from app.db.models import Video, Job
from app.utils.hash import compute_video_hash
from app.workers.tasks import process_video


class VideoHandler(FileSystemEventHandler):
    """Watch for new video files and auto-create subtitle jobs."""

    def __init__(self, media_root: str):
        self.media_root = media_root

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        if filepath.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            return

        # Wait for file to be fully written
        time.sleep(2)

        self._process_video(str(filepath))

    def _process_video(self, video_path: str):
        """Check if video needs processing and create job."""
        try:
            video_hash = compute_video_hash(video_path)

            with get_db_session() as db:
                # Skip if already exists
                existing = db.query(Video).filter(Video.path == video_path).first()
                if existing:
                    return

                video = Video(path=video_path, hash=video_hash)
                db.add(video)
                db.flush()

                job = Job(video_id=video.id, status="pending", progress=0)
                db.add(job)
                db.commit()

                process_video.delay(job.id)
                print(f"[Watcher] Queued: {video_path}")

        except Exception as e:
            print(f"[Watcher] Error processing {video_path}: {e}")


def start_watcher(media_root: str):
    """Start the directory watcher."""
    handler = VideoHandler(media_root)
    observer = Observer()
    observer.schedule(handler, media_root, recursive=True)
    observer.start()
    print(f"[Watcher] Watching: {media_root}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
