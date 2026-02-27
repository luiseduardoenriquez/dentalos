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
import uuid as uuid_mod

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
        """Process a single voice transcription job."""
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

        # H5: Reject if s3_key is missing
        if not s3_key:
            logger.warning(
                "voice.transcribe missing s3_key: message_id=%s transcription_id=%s",
                message.message_id,
                str(transcription_id)[:8],
            )
            return

        logger.info(
            "Processing voice transcription: id=%s s3_key=%s tenant=%s",
            str(transcription_id)[:8],
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

            # H6: Validate schema name before proceeding
            if not validate_schema_name(schema_name):
                logger.error(
                    "Invalid schema name '%s' for tenant '%s' — skipping transcription",
                    schema_name,
                    tenant_id,
                )
                return

            # Download audio from S3 and transcribe
            audio_bytes = await storage_client.download_file(key=s3_key)
            text = await transcribe_audio(audio_bytes)

            # M3: Convert transcription_id to UUID for proper comparison
            tid = uuid_mod.UUID(transcription_id)

            async with AsyncSessionLocal() as db:
                # Set tenant search_path
                from sqlalchemy import text as sa_text

                await db.execute(sa_text(f"SET search_path TO {schema_name}, public"))

                result = await db.execute(
                    select(VoiceTranscription).where(
                        VoiceTranscription.id == tid
                    )
                )
                transcription = result.scalar_one_or_none()

                if transcription is None:
                    logger.warning(
                        "Transcription not found: id=%s",
                        str(transcription_id)[:8],
                    )
                    return

                transcription.status = "completed"
                transcription.text = text
                # H8: Don't estimate duration from compressed bytes — set None
                transcription.duration_seconds = None

                await db.commit()

            logger.info(
                "Voice transcription completed: id=%s tenant=%s",
                str(transcription_id)[:8],
                message.tenant_id[:8],
            )

        except Exception:
            logger.exception(
                "Failed to process voice transcription: id=%s",
                str(transcription_id)[:8],
            )
            # C3: Mark transcription as failed before re-raising
            await self._mark_transcription_failed(message, transcription_id)
            raise

    async def _mark_transcription_failed(
        self, message: QueueMessage, transcription_id: str
    ) -> None:
        """Best-effort update of transcription status to 'failed'."""
        try:
            from sqlalchemy import select

            from app.core.database import AsyncSessionLocal
            from app.core.tenant import validate_schema_name
            from app.models.tenant.voice_session import VoiceTranscription

            tenant_id = message.tenant_id
            schema_name = f"tn_{tenant_id}" if not tenant_id.startswith("tn_") else tenant_id

            if not validate_schema_name(schema_name):
                return

            tid = uuid_mod.UUID(transcription_id)

            async with AsyncSessionLocal() as db:
                from sqlalchemy import text as sa_text

                await db.execute(sa_text(f"SET search_path TO {schema_name}, public"))

                result = await db.execute(
                    select(VoiceTranscription).where(VoiceTranscription.id == tid)
                )
                transcription = result.scalar_one_or_none()
                if transcription is not None:
                    transcription.status = "failed"
                    await db.commit()

                logger.info(
                    "Marked transcription as failed: id=%s",
                    str(transcription_id)[:8],
                )
        except Exception:
            logger.exception(
                "Could not mark transcription as failed: id=%s",
                str(transcription_id)[:8],
            )


# Module-level instance for CLI entry point
voice_worker = VoiceWorker()
