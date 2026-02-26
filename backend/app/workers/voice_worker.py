"""Voice transcription worker -- consumes from the 'clinical' queue.

Handles ``voice.transcribe`` jobs: downloads audio from S3, runs
speech-to-text (Whisper API stub for MVP), and updates the
VoiceTranscription record.

Production pipeline:
  1. Download audio bytes from S3 (tenant-isolated key)
  2. Call OpenAI Whisper API (``openai.audio.transcriptions.create``)
  3. Update VoiceTranscription.text and .duration_seconds
  4. Update VoiceTranscription.status to 'completed'

For MVP: marks transcription as completed with stub text so the
parse step can proceed during development.

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

        # MVP stub: update transcription status to completed with placeholder text.
        # Production implementation will:
        #   1. Resolve tenant schema from message.tenant_id
        #   2. Download audio from S3 via storage_client.download_file(key=s3_key)
        #   3. Call Whisper: openai.audio.transcriptions.create(model="whisper-1", file=audio)
        #   4. Update transcription.text = whisper_response.text
        #   5. Update transcription.duration_seconds = audio_duration
        #   6. Update transcription.estimated_cost_usd = calculated_cost
        #   7. Update transcription.status = "completed"
        try:
            from sqlalchemy import select

            from app.core.database import AsyncSessionLocal
            from app.core.tenant import validate_schema_name
            from app.models.tenant.voice_session import VoiceTranscription

            # Extract tenant schema for search_path
            tenant_id = message.tenant_id
            schema_name = f"tn_{tenant_id}" if not tenant_id.startswith("tn_") else tenant_id

            async with AsyncSessionLocal() as db:
                # Set tenant search_path
                if validate_schema_name(schema_name):
                    from sqlalchemy import text

                    await db.execute(text(f"SET search_path TO {schema_name}, public"))

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

                # MVP: set stub text and mark completed
                transcription.status = "completed"
                transcription.text = (
                    "[MVP stub] Transcripcion de audio pendiente de integracion "
                    "con OpenAI Whisper API."
                )
                transcription.duration_seconds = 0.0

                await db.commit()

            logger.info(
                "Voice transcription completed (stub): id=%s tenant=%s",
                transcription_id[:8],
                message.tenant_id[:8],
            )

        except Exception:
            logger.exception(
                "Failed to process voice transcription: id=%s",
                transcription_id[:8],
            )
            raise


# Module-level instance for CLI entry point
voice_worker = VoiceWorker()
