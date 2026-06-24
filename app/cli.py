"""CLI entry point for Awen Subtitle Engine"""

import sys
from pathlib import Path

import click

from app.logging import setup_logging, get_logger

logger = get_logger("cli")


@click.group()
@click.option("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)")
@click.pass_context
def cli(ctx: click.Context, log_level: str):
    """Awen Subtitle Engine - AI-powered subtitle generation."""
    setup_logging(level=log_level)
    ctx.ensure_object(dict)


@cli.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--lang", default=None, help="Force source language (ja, en, ko). Auto-detects if omitted.")
@click.option("--no-translate", is_flag=True, help="Skip translation, only generate original subtitle.")
@click.option("--online", is_flag=True, help="Search OpenSubtitles first, fall back to ASR if not found.")
def generate(video_path: str, lang: str | None, no_translate: bool, online: bool):
    """Generate subtitles for a single video file."""
    from app.services.audio import extract_audio, cleanup_temp, get_video_info
    from app.services.asr import detect_language, transcribe
    from app.services.translator import translate_batch
    from app.services.subtitle import generate_srt, generate_bilingual_srt, get_subtitle_path
    from app.services.online_subtitle import search_and_download
    from app.utils.hash import compute_video_hash

    video_path = str(Path(video_path).resolve())
    logger.info(f"Processing: {video_path}")

    video_hash = compute_video_hash(video_path)

    # Try online subtitle search first
    if online:
        click.echo("🔍 Searching OpenSubtitles...")
        result = search_and_download(video_path)
        if result:
            click.echo(f"✅ Online subtitle found: {result}")
            return
        click.echo("⚠️  No online match found, falling back to ASR...")

    # Step 1: Extract audio
    click.echo("🎵 Extracting audio...")
    audio_path = extract_audio(video_path, video_hash)

    # Step 2: Detect or use specified language
    if lang:
        language = lang
        click.echo(f"🌐 Using specified language: {language}")
    else:
        click.echo("🌐 Detecting language...")
        language = detect_language(audio_path)
        click.echo(f"🌐 Detected: {language}")

    # Step 3: Transcribe
    click.echo("📝 Transcribing...")
    segments = transcribe(audio_path, language=language)

    if not segments:
        click.echo("❌ No speech detected in audio")
        cleanup_temp(video_hash)
        sys.exit(1)

    click.echo(f"📝 Got {len(segments)} segments")

    # Step 4: Generate original subtitle
    lang_code = language[:2]
    original_path = get_subtitle_path(video_path, lang_code, "original")
    generate_srt(segments, original_path)
    click.echo(f"📄 Original subtitle: {original_path}")

    if no_translate:
        cleanup_temp(video_hash)
        click.echo("✅ Done (translation skipped)")
        return

    # Step 5: Translate
    click.echo("🔤 Translating to Chinese...")
    texts = [seg["text"] for seg in segments]
    translated = translate_batch(texts, source_lang=language)

    # Step 6: Generate Chinese subtitle
    chinese_path = get_subtitle_path(video_path, lang_code, "chinese")
    chinese_segments = [
        {"start": seg["start"], "end": seg["end"], "text": zh}
        for seg, zh in zip(segments, translated)
    ]
    generate_srt(chinese_segments, chinese_path)
    click.echo(f"📄 Chinese subtitle: {chinese_path}")

    # Step 7: Generate bilingual subtitle
    bilingual_path = get_subtitle_path(video_path, lang_code, "bilingual")
    generate_bilingual_srt(segments, translated, bilingual_path)
    click.echo(f"📄 Bilingual subtitle: {bilingual_path}")

    # Cleanup
    cleanup_temp(video_hash)
    click.echo("✅ Done!")


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
def watch(directory: str):
    """Watch a directory for new video files and auto-generate subtitles."""
    from app.watcher import start_watcher

    directory = str(Path(directory).resolve())
    click.echo(f"👁️  Watching directory: {directory}")
    click.echo("   Press Ctrl+C to stop")
    try:
        start_watcher(directory)
    except KeyboardInterrupt:
        click.echo("\n🛑 Stopped watching")


@cli.command()
def status():
    """Show system status and configuration."""
    from app.config import (
        APP_VERSION, MEDIA_ROOT, SUBTITLE_ROOT, TEMP_DIR,
        WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
        TRANSLATION_PROVIDER, SUPPORTED_VIDEO_EXTENSIONS,
    )
    from app.db.database import get_db_session
    from app.db.models import Video, Job

    click.echo(f"🎬 Awen Subtitle Engine v{APP_VERSION}")
    click.echo(f"{'='*40}")
    click.echo(f"Whisper model:   {WHISPER_MODEL} ({WHISPER_DEVICE}, {WHISPER_COMPUTE_TYPE})")
    click.echo(f"Translator:      {TRANSLATION_PROVIDER}")
    click.echo(f"Media root:      {MEDIA_ROOT}")
    click.echo(f"Subtitle root:   {SUBTITLE_ROOT}")
    click.echo(f"Temp dir:        {TEMP_DIR}")
    click.echo(f"Video formats:   {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}")
    click.echo()

    # Database stats
    try:
        with get_db_session() as db:
            video_count = db.query(Video).count()
            job_count = db.query(Job).count()
            done_count = db.query(Job).filter(Job.status == "done").count()
            failed_count = db.query(Job).filter(Job.status == "failed").count()
            pending_count = db.query(Job).filter(Job.status == "pending").count()

        click.echo(f"📊 Database:")
        click.echo(f"   Videos:        {video_count}")
        click.echo(f"   Jobs total:    {job_count}")
        click.echo(f"   Completed:     {done_count}")
        click.echo(f"   Failed:        {failed_count}")
        click.echo(f"   Pending:       {pending_count}")
    except Exception as e:
        click.echo(f"⚠️  Database not available: {e}")

    # Check dependencies
    click.echo()
    click.echo("🔧 Dependencies:")
    import shutil
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        click.echo(f"   {tool}: {'✅ ' + path if path else '❌ not found'}")

    try:
        import faster_whisper
        click.echo(f"   faster-whisper: ✅")
    except ImportError:
        click.echo(f"   faster-whisper: ❌ not installed")


def main():
    """Entry point for `ase` CLI."""
    cli()


if __name__ == "__main__":
    main()
