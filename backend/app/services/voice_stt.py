"""Speech-to-text provider for the voice pipeline.

Dispatches to either a local faster-whisper model or the OpenAI Whisper API
based on ``settings.voice_stt_provider``.

Local mode:
  - Uses faster-whisper with a singleton model (lazy-loaded, stays in memory).
  - Runs inference in a thread executor to avoid blocking the async loop.
  - Requires ``ffmpeg`` installed on the host for audio decoding.

OpenAI mode:
  - Calls ``openai.AsyncOpenAI.audio.transcriptions.create(model="whisper-1")``.
  - Requires ``OPENAI_API_KEY`` set in environment/config.
"""

import asyncio
import io
import logging
import threading
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = logging.getLogger("dentalos.voice.stt")

# ── Singleton faster-whisper model ────────────────────────────────────────

_whisper_model: "WhisperModel | None" = None
_whisper_lock = threading.Lock()


def _get_whisper_model() -> "WhisperModel":
    """Lazy-load the faster-whisper model (thread-safe singleton)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    with _whisper_lock:
        if _whisper_model is not None:
            return _whisper_model

        from faster_whisper import WhisperModel

        logger.info(
            "Loading faster-whisper model: size=%s compute_type=int8",
            settings.whisper_model_size,
        )
        _whisper_model = WhisperModel(
            settings.whisper_model_size,
            device="cpu",
            compute_type="int8",
        )
        logger.info("faster-whisper model loaded successfully")
        return _whisper_model


def _transcribe_sync(audio_bytes: bytes) -> str:
    """Run faster-whisper transcription (blocking, meant for thread executor)."""
    model = _get_whisper_model()
    audio_stream = io.BytesIO(audio_bytes)

    segments, _info = model.transcribe(
        audio_stream,
        language="es",
        vad_filter=True,
    )

    return " ".join(segment.text.strip() for segment in segments)


# ── Public API ────────────────────────────────────────────────────────────


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio bytes to Spanish text.

    Dispatches based on ``settings.voice_stt_provider``:
      - ``"local"``: faster-whisper (in-process, CPU)
      - ``"openai"``: OpenAI Whisper API

    Returns the transcribed text (may be empty if audio has no speech).
    """
    provider = settings.voice_stt_provider

    if provider == "local":
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, _transcribe_sync, audio_bytes)
        logger.info("Local STT completed: %d chars", len(text))
        return text

    if provider == "openai":
        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"

        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="es",
            response_format="text",
        )
        text = str(transcription).strip()
        logger.info("OpenAI STT completed: %d chars", len(text))
        return text

    raise ValueError(f"Unknown STT provider: {provider!r}. Use 'local' or 'openai'.")
