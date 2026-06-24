"""Speech-to-Text using faster-whisper"""

from faster_whisper import WhisperModel

from app.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

# Lazy-loaded model (loaded once per worker process)
_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _model


def detect_language(audio_path: str) -> str:
    """Detect the spoken language in audio. Returns ISO 639-1 code."""
    model = _get_model()
    segments, info = model.transcribe(audio_path, beam_size=1, language=None)
    # Consume generator to get detected language
    for _ in segments:
        pass
    return info.language


def transcribe(audio_path: str, language: str | None = None) -> list[dict]:
    """
    Transcribe audio to text segments.
    Returns list of {"start": float, "end": float, "text": str}.
    """
    model = _get_model()
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=language,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
    )

    results = []
    for seg in segments:
        results.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
        })

    return results
