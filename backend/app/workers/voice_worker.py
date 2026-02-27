"""Voice transcription worker -- consumes from the 'clinical' queue.

Handles ``voice.transcribe`` jobs: downloads audio from S3, runs
speech-to-text via the configured provider (local faster-whisper or
OpenAI Whisper API), and updates the VoiceTranscription record.

Pipeline:
  1. Download audio bytes from S3 (tenant-isolated key)
  2. Transcribe via ``voice_stt.transcribe_audio()``
  3. Update VoiceTranscription.text and .duration_seconds
  4. Update VoiceTranscription.status to 'completed'

Security:
  - PHI (transcription text) is NEVER logged.
  - Audio files are tenant-isolated in S3.
  - Worker sets search_path per tenant before DB operations.
"""

import logging

from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.voice")


class VoiceWorker(BaseWorker):
    """Processes ``voice.transcribe`` jobs from the clinical queue.

    Sits alongside other clinical queue consumers (PDF generation,
    RIPS, odontogram snapshots). Only handles ``voice.transcribe``
    job types and skips all others.

    Uses ``prefetch_count=2`` to limit concurrent audio processing
    (Whisper API has latency; we do not want to hold too many
    connections open).
    """

    queue_name = "clinical"
    prefetch_count = 2

    async def process(self, message: QueueMessage) -> None:
        """Process a single voice transcription job.

        For MVP: marks transcription as completed with stub text.
        Production: downloads audio from S3, calls Whisper API.
        """
        if message.job_type != "voice.transcribe":
            return  # Not our job type -- skip

        transcription_id = message.payload.get("transcription_id")
        s3_key = message.payload.get("s3_key")

        if not transcription_id:
            logger.warning(
                "voice.transcribe missing transcription_id: message_id=%s",
                message.message_id,
            )
            return

        logger.info(
            "Processing voice transcription: id=%s s3_key=%s tenant=%s",
            transcription_id[:8] if transcription_id else "?",
            s3_key[:20] if s3_key else "?",
            message.tenant_id[:8] if message.tenant_id else "?",
        )

        try:
            from sqlalchemy import select

            from app.core.database import AsyncSessionLocal
            from app.core.storage import storage_client
            from app.core.tenant import validate_schema_name
            from app.models.tenant.voice_session import VoiceTranscription
            from app.services.voice_stt import transcribe_audio

            # Extract tenant schema for search_path
            tenant_id = message.tenant_id
            schema_name = f"tn_{tenant_id}" if not tenant_id.startswith("tn_") else tenant_id

            # Download audio from S3 and transcribe
            audio_bytes = await storage_client.download_file(key=s3_key)
            text = await transcribe_audio(audio_bytes)

            async with AsyncSessionLocal() as db:
                # Set tenant search_path
                if validate_schema_name(schema_name):
                    from sqlalchemy import text as sa_text

                    await db.execute(sa_text(f"SET search_path TO {schema_name}, public"))

                result = await db.execute(
                    select(VoiceTranscription).where(
                        VoiceTranscription.id == transcription_id
                    )
                )
                transcription = result.scalar_one_or_none()

                if transcription is None:
                    logger.warning(
                        "Transcription not found: id=%s",
                        transcription_id[:8],
                    )
                    return

                transcription.status = "completed"
                transcription.text = text
                transcription.duration_seconds = len(audio_bytes) / 32000.0  # rough estimate

                await db.commit()

            logger.info(
                "Voice transcription completed: id=%s tenant=%s chars=%d",
                transcription_id[:8],
                message.tenant_id[:8],
                len(text),
            )

        except Exception:
            logger.exception(
                "Failed to process voice transcription: id=%s",
                transcription_id[:8],
            )
            raise


# Module-level instance for CLI entry point
voice_worker = VoiceWorker()
