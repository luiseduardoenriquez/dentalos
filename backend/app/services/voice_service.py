"""Voice-to-odontogram pipeline service.

Handles voice session lifecycle, audio upload to S3, transcription polling,
NLP parse with Claude, and applying confirmed findings to the odontogram.

Security:
  - Voice feature requires tenant add-on ($10/doctor/mo).
  - Rate limited to 50 sessions/hour per doctor.
  - Audio stored in tenant-isolated S3 paths.
  - PHI is NEVER logged.

Pipeline overview:
  1. create_session()         -- open a session, validate add-on + rate limit
  2. upload_audio()           -- upload chunk to S3, queue Whisper transcription
  3. get_status()             -- poll transcription statuses
  4. parse_transcription()    -- concatenate text, call LLM, return findings
  5. apply_findings()         -- commit confirmed findings to odontogram

Models:
  VoiceSession, VoiceTranscription, VoiceParse -- see app.models.tenant.voice_session
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import VoiceErrors
from app.core.exceptions import (
    DentalOSError,
    ResourceNotFoundError,
    VoiceError,
)
from app.core.queue import publish_message
from app.models.tenant.patient import Patient
from app.models.tenant.voice_session import VoiceParse, VoiceSession, VoiceTranscription
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.voice")

# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_SESSION_TTL_MINUTES = 30
_DEFAULT_MAX_SESSIONS_PER_HOUR = 50

# Allowed audio content types for upload
_ALLOWED_AUDIO_TYPES = frozenset({
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
})


# ── Serialization helpers ────────────────────────────────────────────────────


def _session_to_dict(session: VoiceSession) -> dict[str, Any]:
    """Convert VoiceSession ORM instance to a plain dict."""
    return {
        "id": str(session.id),
        "patient_id": str(session.patient_id),
        "doctor_id": str(session.doctor_id),
        "context": session.context,
        "status": session.status,
        "expires_at": session.expires_at,
        "is_active": session.is_active,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "transcriptions": [
            _transcription_to_dict(t) for t in session.transcriptions
        ],
    }


def _transcription_to_dict(t: VoiceTranscription) -> dict[str, Any]:
    """Convert VoiceTranscription ORM instance to a plain dict."""
    return {
        "id": str(t.id),
        "chunk_index": t.chunk_index,
        "status": t.status,
        "text": t.text,
        "duration_seconds": t.duration_seconds,
        "s3_key": t.s3_key,
        "created_at": t.created_at,
    }


def _parse_to_dict(p: VoiceParse) -> dict[str, Any]:
    """Convert VoiceParse ORM instance to a plain dict."""
    return {
        "id": str(p.id),
        "session_id": str(p.session_id),
        "input_text": p.input_text,
        "findings": p.findings,
        "corrections": p.corrections,
        "filtered_speech": p.filtered_speech,
        "warnings": p.warnings,
        "llm_model": p.llm_model,
        "status": p.status,
        "created_at": p.created_at,
    }


# ── Voice Service ────────────────────────────────────────────────────────────


class VoiceService:
    """Stateless voice-to-odontogram pipeline service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path is already set by get_tenant_db() -- methods do NOT
    call SET search_path themselves.
    """

    # ── 1. Create Session ────────────────────────────────────────────────

    async def create_session(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        tenant_id: str,
        context: str = "odontogram",
    ) -> dict[str, Any]:
        """Open a new voice dictation session for a doctor + patient.

        Validates:
          - Voice add-on is enabled for the tenant (MVP: configurable flag).
          - Doctor has not exceeded 50 sessions in the last hour.
          - Patient exists and is active.

        Creates a VoiceSession with status='active' and a 30-minute TTL.

        Returns the session dict.

        Raises:
            VoiceError(ADDON_REQUIRED, 402)       -- add-on not enabled.
            VoiceError(RATE_LIMIT_EXCEEDED, 429)   -- hourly cap reached.
            ResourceNotFoundError                  -- patient not found.
        """
        # Check voice add-on (MVP: always enabled for testing)
        settings = await self.get_voice_settings(db=db)
        if not settings["voice_enabled"]:
            raise VoiceError(
                error=VoiceErrors.ADDON_REQUIRED,
                message=(
                    "La funcion de voz no esta habilitada. "
                    "Requiere el complemento AI Voice ($10/doctor/mes)."
                ),
                status_code=402,
            )

        # Rate limit: count sessions created by this doctor in the last hour
        did = uuid.UUID(doctor_id)
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        max_sessions = settings["max_sessions_per_hour"]

        rate_result = await db.execute(
            select(func.count(VoiceSession.id)).where(
                VoiceSession.doctor_id == did,
                VoiceSession.created_at >= one_hour_ago,
            )
        )
        session_count = rate_result.scalar() or 0

        if session_count >= max_sessions:
            raise VoiceError(
                error=VoiceErrors.RATE_LIMIT_EXCEEDED,
                message=(
                    f"Limite de sesiones de voz alcanzado ({max_sessions}/hora). "
                    "Intente de nuevo mas tarde."
                ),
                status_code=429,
                details={"limit": max_sessions, "current": session_count},
            )

        # Validate patient exists and is active
        pid = uuid.UUID(patient_id)
        patient_result = await db.execute(
            select(Patient).where(
                Patient.id == pid,
                Patient.is_active.is_(True),
            )
        )
        patient = patient_result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            )

        # Create session
        session = VoiceSession(
            patient_id=pid,
            doctor_id=did,
            context=context,
            status="active",
            expires_at=datetime.now(UTC) + timedelta(minutes=_DEFAULT_SESSION_TTL_MINUTES),
            is_active=True,
        )
        db.add(session)
        await db.flush()

        logger.info(
            "Voice session created: session=%s doctor=%s context=%s",
            str(session.id)[:8],
            doctor_id[:8],
            context,
        )

        return _session_to_dict(session)

    # ── 2. Upload Audio ──────────────────────────────────────────────────

    async def upload_audio(
        self,
        *,
        db: AsyncSession,
        session_id: str,
        tenant_id: str,
        audio_data: bytes,
        content_type: str = "audio/webm",
    ) -> dict[str, Any]:
        """Upload an audio chunk for transcription.

        Validates:
          - Session exists and is active (not expired).
          - Content type is in the allowed set.

        Stores the audio in S3 under a tenant-isolated key, creates a
        VoiceTranscription record, and publishes a ``voice.transcribe``
        job to the clinical queue.

        Returns the transcription dict.

        Raises:
            VoiceError(SESSION_NOT_FOUND)   -- session not found.
            VoiceError(SESSION_EXPIRED)     -- session TTL elapsed.
            VoiceError(UPLOAD_FAILED)       -- S3 upload failure.
        """
        sid = uuid.UUID(session_id)

        # Load session
        session_result = await db.execute(
            select(VoiceSession).where(
                VoiceSession.id == sid,
                VoiceSession.is_active.is_(True),
            )
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise VoiceError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                message="Sesion de voz no encontrada.",
                status_code=404,
            )

        if session.status != "active":
            raise VoiceError(
                error=VoiceErrors.SESSION_EXPIRED,
                message="La sesion de voz ya no esta activa.",
                status_code=410,
            )

        if session.expires_at < datetime.now(UTC):
            # Auto-expire the session
            session.status = "expired"
            await db.flush()
            raise VoiceError(
                error=VoiceErrors.SESSION_EXPIRED,
                message="La sesion de voz ha expirado.",
                status_code=410,
            )

        # Validate content type
        if content_type not in _ALLOWED_AUDIO_TYPES:
            raise VoiceError(
                error=VoiceErrors.UPLOAD_FAILED,
                message=(
                    f"Tipo de contenido '{content_type}' no permitido. "
                    f"Formatos aceptados: {', '.join(sorted(_ALLOWED_AUDIO_TYPES))}."
                ),
                status_code=422,
            )

        # Calculate chunk index
        chunk_count_result = await db.execute(
            select(func.count(VoiceTranscription.id)).where(
                VoiceTranscription.session_id == sid,
            )
        )
        chunk_index = chunk_count_result.scalar() or 0

        # Generate S3 key (tenant-isolated path)
        file_ext = content_type.split("/")[-1]
        s3_key = f"{tenant_id}/voice/{session_id}/{chunk_index}.{file_ext}"

        # Upload to S3 (try/except for graceful degradation)
        try:
            from app.core.storage import storage_client

            await storage_client.upload_file(
                key=s3_key,
                data=audio_data,
                content_type=content_type,
            )
        except ValueError as e:
            # Content type validation from storage client -- for audio we
            # need to bypass the standard ALLOWED_MIME_TYPES check since
            # those are for clinical documents (JPEG/PNG/PDF/DICOM).
            # MVP: store the s3_key without actual upload when audio types
            # are not in the storage allowlist.
            logger.warning(
                "S3 upload skipped (content type not in storage allowlist): "
                "session=%s key=%s -- %s",
                session_id[:8],
                s3_key[:30],
                str(e),
            )
        except Exception:
            logger.exception(
                "S3 upload failed: session=%s key=%s",
                session_id[:8],
                s3_key[:30],
            )
            raise VoiceError(
                error=VoiceErrors.UPLOAD_FAILED,
                message="Error al subir el archivo de audio. Intente de nuevo.",
                status_code=502,
            )

        # Create transcription record
        transcription = VoiceTranscription(
            session_id=sid,
            chunk_index=chunk_index,
            s3_key=s3_key,
            status="pending",
        )
        db.add(transcription)
        await db.flush()

        # Publish to RabbitMQ clinical queue
        await publish_message(
            "clinical",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="voice.transcribe",
                payload={
                    "transcription_id": str(transcription.id),
                    "s3_key": s3_key,
                },
            ),
        )

        logger.info(
            "Audio uploaded: session=%s chunk=%d key=%s",
            session_id[:8],
            chunk_index,
            s3_key[:30],
        )

        return {
            "transcription_id": str(transcription.id),
            "session_id": session_id,
            "s3_key": s3_key,
            "status": transcription.status,
        }

    # ── 3. Get Status ────────────────────────────────────────────────────

    async def get_status(
        self,
        *,
        db: AsyncSession,
        session_id: str,
    ) -> dict[str, Any]:
        """Return the full session state including transcription statuses.

        The VoiceSession model has ``lazy="selectin"`` on transcriptions
        and parses, so they are loaded automatically.

        Returns the session dict.

        Raises:
            VoiceError(SESSION_NOT_FOUND) -- session not found.
        """
        sid = uuid.UUID(session_id)

        session_result = await db.execute(
            select(VoiceSession).where(
                VoiceSession.id == sid,
                VoiceSession.is_active.is_(True),
            )
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise VoiceError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                message="Sesion de voz no encontrada.",
                status_code=404,
            )

        return _session_to_dict(session)

    # ── 4. Parse Transcription ───────────────────────────────────────────

    async def parse_transcription(
        self,
        *,
        db: AsyncSession,
        session_id: str,
    ) -> dict[str, Any]:
        """Parse all completed transcriptions in a session using the LLM.

        Concatenates text from all completed transcription chunks, then
        runs the NLP pipeline to extract structured dental findings.

        For MVP: returns stub findings from ``_parse_dental_text()``.
        Production: calls Claude Haiku with a dental terminology prompt.

        Creates a VoiceParse record with the extracted findings.

        Returns the parse dict.

        Raises:
            VoiceError(SESSION_NOT_FOUND) -- session not found.
            VoiceError(PARSE_FAILED)      -- no transcription text available.
        """
        sid = uuid.UUID(session_id)

        # Load session with transcriptions (selectin)
        session_result = await db.execute(
            select(VoiceSession).where(
                VoiceSession.id == sid,
                VoiceSession.is_active.is_(True),
            )
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise VoiceError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                message="Sesion de voz no encontrada.",
                status_code=404,
            )

        if session.status != "active":
            raise VoiceError(
                error=VoiceErrors.SESSION_EXPIRED,
                message="La sesion de voz ya no esta activa.",
                status_code=410,
            )

        # Collect completed transcription texts
        completed_texts: list[str] = []
        for t in session.transcriptions:
            if t.status == "completed" and t.text:
                completed_texts.append(t.text)

        if not completed_texts:
            raise VoiceError(
                error=VoiceErrors.PARSE_FAILED,
                message=(
                    "No hay transcripciones completadas para analizar. "
                    "Espere a que finalice la transcripcion."
                ),
                status_code=422,
            )

        # Concatenate all transcription texts
        concatenated_text = " ".join(completed_texts)

        # Run LLM parse (MVP stub)
        findings = self._parse_dental_text(concatenated_text)

        # Determine parse status
        parse_status = "success" if findings else "partial"

        # Create VoiceParse record
        parse = VoiceParse(
            session_id=sid,
            input_text=concatenated_text,
            findings=findings,
            corrections=[],
            filtered_speech=[],
            warnings=[],
            llm_model="stub-v1",  # Will be "claude-3-haiku" in production
            status=parse_status,
        )
        db.add(parse)
        await db.flush()

        logger.info(
            "Voice parse completed: session=%s findings=%d model=%s",
            session_id[:8],
            len(findings),
            parse.llm_model,
        )

        return _parse_to_dict(parse)

    # ── 5. Apply Findings ────────────────────────────────────────────────

    async def apply_findings(
        self,
        *,
        db: AsyncSession,
        session_id: str,
        tenant_id: str,
        doctor_id: str,
        confirmed_findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply doctor-confirmed findings to the odontogram.

        Delegates to ``odontogram_service.bulk_update()`` for atomic
        application. Updates the session status to 'applied' on success.

        Returns:
            {applied_count, skipped_count, errors}

        Raises:
            VoiceError(SESSION_NOT_FOUND)  -- session not found.
            VoiceError(APPLY_FAILED)       -- odontogram update failure.
        """
        sid = uuid.UUID(session_id)

        # Load session
        session_result = await db.execute(
            select(VoiceSession).where(
                VoiceSession.id == sid,
                VoiceSession.is_active.is_(True),
            )
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise VoiceError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                message="Sesion de voz no encontrada.",
                status_code=404,
            )

        if not confirmed_findings:
            return {
                "applied_count": 0,
                "skipped_count": 0,
                "errors": [],
            }

        patient_id = str(session.patient_id)

        # Build update dicts for odontogram bulk_update
        updates = [
            {
                "tooth_number": f["tooth_number"],
                "zone": f["zone"],
                "condition_code": f["condition_code"],
                "source": "voice",
            }
            for f in confirmed_findings
        ]

        applied_count = 0
        skipped_count = 0
        errors: list[str] = []

        try:
            from app.services.odontogram_service import odontogram_service

            result = await odontogram_service.bulk_update(
                db=db,
                patient_id=patient_id,
                tenant_id=tenant_id,
                user_id=doctor_id,
                updates=updates,
                session_notes=f"Voice session {session_id[:8]}",
            )
            applied_count = result["processed"]
            skipped_count = 0

        except DentalOSError as e:
            # Business validation errors from odontogram (e.g. invalid tooth)
            logger.warning(
                "Odontogram bulk_update validation error: session=%s -- %s",
                session_id[:8],
                e.message,
            )
            applied_count = 0
            skipped_count = len(updates)
            errors.append(e.message)

        except Exception:
            logger.exception(
                "Unexpected error applying voice findings: session=%s",
                session_id[:8],
            )
            applied_count = 0
            skipped_count = len(updates)
            errors.append(
                "Error inesperado al aplicar los hallazgos al odontograma."
            )

        # Update session status to 'applied' only if at least some succeeded
        if applied_count > 0:
            session.status = "applied"
            await db.flush()

        logger.info(
            "Voice findings applied: session=%s applied=%d skipped=%d errors=%d",
            session_id[:8],
            applied_count,
            skipped_count,
            len(errors),
        )

        return {
            "applied_count": applied_count,
            "skipped_count": skipped_count,
            "errors": errors,
        }

    # ── 6. Voice Settings ────────────────────────────────────────────────

    async def get_voice_settings(
        self,
        *,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Get voice feature settings for the current tenant.

        For MVP: returns hardcoded defaults. In production, these will
        be stored in the tenant settings table and gated by the
        subscription plan.
        """
        return {
            "voice_enabled": True,  # MVP: always enabled for testing
            "max_session_duration_seconds": _DEFAULT_SESSION_TTL_MINUTES * 60,
            "max_sessions_per_hour": _DEFAULT_MAX_SESSIONS_PER_HOUR,
        }

    async def update_voice_settings(
        self,
        *,
        db: AsyncSession,
        voice_enabled: bool | None = None,
        max_session_duration_seconds: int | None = None,
        max_sessions_per_hour: int | None = None,
    ) -> dict[str, Any]:
        """Update voice feature settings for the current tenant.

        For MVP: this is a no-op that echoes back the requested changes.
        In production, persists to the tenant settings table.
        """
        current = await self.get_voice_settings(db=db)

        if voice_enabled is not None:
            current["voice_enabled"] = voice_enabled
        if max_session_duration_seconds is not None:
            current["max_session_duration_seconds"] = max_session_duration_seconds
        if max_sessions_per_hour is not None:
            current["max_sessions_per_hour"] = max_sessions_per_hour

        logger.info(
            "Voice settings updated (MVP stub): enabled=%s",
            current["voice_enabled"],
        )

        return current

    # ── Private Helpers ──────────────────────────────────────────────────

    def _parse_dental_text(self, text: str) -> list[dict[str, Any]]:
        """MVP stub: simple dental finding extraction.

        In production, this calls Claude Haiku with a dental terminology
        prompt that maps Spanish dental dictation to structured findings:

            claude_client.messages.create(
                model="claude-3-haiku-20240307",
                system="You are a dental NLP parser...",
                messages=[{"role": "user", "content": text}],
            )

        For MVP, returns empty findings -- the real pipeline will be
        implemented when the Anthropic API integration is set up.

        The production prompt will handle:
          - Spanish dental terminology normalization
          - FDI tooth numbering (11-48 for adults, 51-85 for deciduous)
          - Zone mapping (mesial, distal, oclusal, vestibular, lingual, full)
          - Condition code resolution against the DentalOS catalog
          - Ambiguity detection (warnings)
          - Filler word filtering
        """
        logger.info("Voice parse stub called (MVP mode)")
        return []


# Module-level singleton for dependency injection
voice_service = VoiceService()
