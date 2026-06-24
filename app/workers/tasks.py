"""Celery task for processing video subtitles"""

import traceback

from app.workers import celery_app
from app.db.database import get_db_session
from app.db.models import Video, Job, Subtitle
from app.services.audio import extract_audio, cleanup_temp
from app.services.asr import detect_language, transcribe
from app.services.translator import translate_batch
from app.services.subtitle import (
    generate_srt,
    generate_bilingual_srt,
    get_subtitle_path,
)


def _update_job(job_id: int, status: str, progress: int = 0, step: str = "", error: str = ""):
    """Update job status in database."""
    with get_db_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            job.progress = progress
            job.current_step = step
            job.error = error
            db.commit()


def _add_subtitle(video_id: int, sub_type: str, file_path: str):
    """Add subtitle record to database."""
    with get_db_session() as db:
        sub = Subtitle(video_id=video_id, type=sub_type, file_path=file_path)
        db.add(sub)
        db.commit()


@celery_app.task(bind=True, name="process_video")
def process_video(self, job_id: int):
    """
    Main pipeline: extract audio → transcribe → translate → generate SRT.
    """
    try:
        # Get video info
        with get_db_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return
            video = db.query(Video).filter(Video.id == job.video_id).first()
            if not video:
                return

        video_path = video.path
        video_hash = video.hash

        # Step 1: Extract audio
        _update_job(job_id, "processing", 10, "extracting_audio")
        audio_path = extract_audio(video_path, video_hash)

        # Step 2: Detect language
        _update_job(job_id, "processing", 20, "detecting_language")
        language = detect_language(audio_path)

        # Update video language
        with get_db_session() as db:
            video = db.query(Video).filter(Video.id == job.video_id).first()
            video.language = language
            db.commit()

        # Step 3: Transcribe
        _update_job(job_id, "processing", 30, "transcribing")
        segments = transcribe(audio_path, language=language)

        if not segments:
            _update_job(job_id, "failed", error="No speech detected in audio")
            return

        # Step 4: Generate original subtitle
        _update_job(job_id, "processing", 50, "generating_original_subtitle")
        lang_code = language[:2]  # ja, en, ko
        original_path = get_subtitle_path(video_path, lang_code, "original")
        generate_srt(segments, original_path)
        _add_subtitle(job.id, "original", original_path)

        # Step 5: Batch translate
        _update_job(job_id, "processing", 60, "translating")
        texts_to_translate = [seg["text"] for seg in segments]
        translated = translate_batch(texts_to_translate, source_lang=language)

        # Step 6: Generate Chinese subtitle
        _update_job(job_id, "processing", 80, "generating_chinese_subtitle")
        chinese_path = get_subtitle_path(video_path, lang_code, "chinese")
        chinese_segments = [
            {"start": seg["start"], "end": seg["end"], "text": zh}
            for seg, zh in zip(segments, translated)
        ]
        generate_srt(chinese_segments, chinese_path)
        _add_subtitle(job.id, "chinese", chinese_path)

        # Step 7: Generate bilingual subtitle
        _update_job(job_id, "processing", 90, "generating_bilingual_subtitle")
        bilingual_path = get_subtitle_path(video_path, lang_code, "bilingual")
        generate_bilingual_srt(segments, translated, bilingual_path)
        _add_subtitle(job.id, "bilingual", bilingual_path)

        # Step 8: Cleanup and done
        cleanup_temp(video_hash)
        _update_job(job_id, "done", 100, "completed")

    except Exception as e:
        _update_job(job_id, "failed", error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
