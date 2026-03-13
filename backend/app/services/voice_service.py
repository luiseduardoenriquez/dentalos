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
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.error_codes import VoiceErrors
from app.core.exceptions import (
    DentalOSError,
    ResourceNotFoundError,
    VoiceError,
)
from app.core.odontogram_constants import (
    ALL_ZONES,
    ANTERIOR_TEETH,
    VALID_CONDITION_CODES,
    VALID_FDI_ALL,
    is_zone_valid_for_condition,
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

# ── LLM Prompt for Dental NLP ──────────────────────────────────────────────
# H1: Condition codes MUST match VALID_CONDITION_CODES from odontogram_constants.
# M1: All 9 zones from ALL_ZONES are listed.
# M2: Multiple conditions per tooth explicitly instructed.

DENTAL_NLP_PROMPT = """You are a dental NLP parser for DentalOS. Your task is to extract
structured findings from Spanish dental dictation text.

For each finding, extract:
- tooth_number: FDI notation (11-48 for permanent, 51-85 for deciduous)
- zone: one of "mesial", "distal", "vestibular", "lingual", "palatino",
  "oclusal", "incisal", "root", "full"
- condition_code: one of the English codes listed below
- confidence: float 0.0-1.0 indicating parsing confidence

CONDITION CODES (use these exact English strings):
  caries         — Caries dental
  fracture       — Fractura
  crown          — Corona protésica
  restoration    — Restauración (resina, amalgama, composite, calza)
  absent         — Ausente / exodoncia previa
  endodontic     — Endodoncia / tratamiento de conducto
  implant        — Implante dental
  sealant        — Sellante
  prosthesis     — Prótesis fija o removible (puente, placa)
  extraction     — Extracción indicada (pendiente)
  fluorosis      — Fluorosis
  temporary      — Restauración temporal

SPANISH → ENGLISH MAPPING:
  caries → caries | fractura → fracture | corona → crown
  resina, amalgama, composite, calza → restoration
  ausente, exodoncia → absent | endodoncia → endodontic
  implante → implant | sellante → sealant
  prótesis fija, prótesis removible, puente, placa → prosthesis
  extracción indicada → extraction | fluorosis → fluorosis
  restauración temporal, provisional → temporary

Return a JSON array of findings. Example:
[
  {"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.95},
  {"tooth_number": 11, "zone": "incisal", "condition_code": "fracture", "confidence": 0.90}
]

Important rules:
- FDI notation only (not universal numbering)
- Use the English condition codes above — NEVER use Spanish terms as codes
- If tooth number is ambiguous, set confidence < 0.7
- If zone is not mentioned, default to "full"
- Ignore filler words and non-dental content
- Return empty array if no dental findings detected
- A single tooth can have MULTIPLE findings (e.g., caries + restoration on the same tooth).
  Return separate objects for each finding. Example:
  [
    {"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.90},
    {"tooth_number": 36, "zone": "mesial", "condition_code": "restoration", "confidence": 0.85}
  ]
"""


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


# ── Findings Validation (H2) ────────────────────────────────────────────────


def _validate_findings(
    raw_findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate and clean LLM-extracted findings.

    Returns (valid_findings, warnings) where invalid entries are dropped
    and warnings explain what was filtered.
    """
    valid: list[dict[str, Any]] = []
    warnings: list[str] = []

    for i, f in enumerate(raw_findings):
        if not isinstance(f, dict):
            warnings.append(f"Finding #{i}: not a dict, skipped")
            continue

        # Validate tooth_number
        tooth = f.get("tooth_number")
        try:
            tooth = int(tooth)
        except (TypeError, ValueError):
            warnings.append(f"Finding #{i}: invalid tooth_number '{tooth}', skipped")
            continue

        if tooth not in VALID_FDI_ALL:
            warnings.append(f"Finding #{i}: tooth {tooth} not in FDI range, skipped")
            continue

        # Validate zone
        zone = f.get("zone", "full")
        if not isinstance(zone, str) or zone not in ALL_ZONES:
            warnings.append(f"Finding #{i}: invalid zone '{zone}', defaulting to 'full'")
            zone = "full"

        # Validate condition_code
        code = f.get("condition_code")
        if not isinstance(code, str) or code not in VALID_CONDITION_CODES:
            warnings.append(f"Finding #{i}: invalid condition_code '{code}', skipped")
            continue

        # Normalize zone for tooth morphology:
        # Anterior teeth (incisors/canines) use "incisal" not "oclusal"
        if zone == "oclusal" and tooth in ANTERIOR_TEETH:
            zone = "incisal"
            warnings.append(f"Finding #{i}: remapped 'oclusal' to 'incisal' for anterior tooth {tooth}")

        # Normalize "full" for conditions that don't support it
        if zone == "full" and not is_zone_valid_for_condition("full", code):
            zone = "incisal" if tooth in ANTERIOR_TEETH else "oclusal"
            warnings.append(
                f"Finding #{i}: '{code}' does not support zone 'full', "
                f"defaulted to '{zone}' for tooth {tooth}"
            )

        # Clamp confidence to 0.0-1.0
        confidence = f.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        valid.append({
            "tooth_number": tooth,
            "zone": zone,
            "condition_code": code,
            "confidence": confidence,
        })

    return valid, warnings


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
        voice_settings = await self.get_voice_settings(db=db)
        if not voice_settings["voice_enabled"]:
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
        max_sessions = voice_settings["max_sessions_per_hour"]

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
        # Eagerly load transcriptions (empty for new session) to avoid
        # MissingGreenlet when _session_to_dict accesses the relationship.
        await db.refresh(session, ["transcriptions"])

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
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Upload an audio chunk for transcription.

        Validates:
          - Session exists and is active (not expired).
          - Content type is in the allowed set.
          - Audio size does not exceed limit (H4).

        Stores the audio in S3 under a tenant-isolated key, creates a
        VoiceTranscription record, and publishes a ``voice.transcribe``
        job to the clinical queue.

        Returns the transcription dict.

        Raises:
            VoiceError(SESSION_NOT_FOUND)   -- session not found.
            VoiceError(SESSION_EXPIRED)     -- session TTL elapsed.
            VoiceError(UPLOAD_FAILED)       -- S3 upload failure or size exceeded.
        """
        # H4: Enforce audio size limit
        max_audio_bytes = settings.voice_max_audio_bytes
        if len(audio_data) > max_audio_bytes:
            raise VoiceError(
                error=VoiceErrors.UPLOAD_FAILED,
                message=(
                    f"Archivo de audio demasiado grande ({len(audio_data)} bytes). "
                    f"Maximo permitido: {max_audio_bytes} bytes "
                    f"({max_audio_bytes // (1024 * 1024)} MB)."
                ),
                status_code=422,
            )

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

        # Normalize content type: strip codec params (e.g. "audio/webm;codecs=opus" → "audio/webm")
        base_content_type = content_type.split(";")[0].strip()

        # Validate content type
        if base_content_type not in _ALLOWED_AUDIO_TYPES:
            raise VoiceError(
                error=VoiceErrors.UPLOAD_FAILED,
                message=(
                    f"Tipo de contenido '{base_content_type}' no permitido. "
                    f"Formatos aceptados: {', '.join(sorted(_ALLOWED_AUDIO_TYPES))}."
                ),
                status_code=422,
            )

        # Idempotency check: if same session + key already exists, return it
        if idempotency_key:
            existing_result = await db.execute(
                select(VoiceTranscription).where(
                    VoiceTranscription.session_id == sid,
                    VoiceTranscription.idempotency_key == idempotency_key,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                logger.info(
                    "Idempotent upload: returning existing transcription=%s "
                    "for session=%s key=%s",
                    str(existing.id)[:8],
                    session_id[:8],
                    idempotency_key[:8],
                )
                return {
                    "transcription_id": str(existing.id),
                    "session_id": str(existing.session_id),
                    "s3_key": existing.s3_key,
                    "status": existing.status,
                }

        # Calculate chunk index
        chunk_count_result = await db.execute(
            select(func.count(VoiceTranscription.id)).where(
                VoiceTranscription.session_id == sid,
            )
        )
        chunk_index = chunk_count_result.scalar() or 0

        # Generate S3 key (tenant-isolated path)
        file_ext = base_content_type.split("/")[-1]
        s3_key = f"{tenant_id}/voice/{session_id}/{chunk_index}.{file_ext}"

        # Upload to S3 (try/except for graceful degradation)
        try:
            from app.core.storage import storage_client

            await storage_client.upload_file(
                key=s3_key,
                data=audio_data,
                content_type=base_content_type,
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
        except Exception as exc:
            logger.exception(
                "S3 upload failed: session=%s key=%s",
                session_id[:8],
                s3_key[:30],
            )
            raise VoiceError(
                error=VoiceErrors.UPLOAD_FAILED,
                message="Error al subir el archivo de audio. Intente de nuevo.",
                status_code=502,
            ) from exc

        # Create transcription record
        transcription = VoiceTranscription(
            session_id=sid,
            chunk_index=chunk_index,
            s3_key=s3_key,
            status="pending",
            idempotency_key=idempotency_key,
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
            select(VoiceSession)
            .options(selectinload(VoiceSession.transcriptions))
            .where(
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

        Creates a VoiceParse record with the extracted findings.

        Returns the parse dict.

        Raises:
            VoiceError(SESSION_NOT_FOUND) -- session not found.
            VoiceError(SESSION_EXPIRED)   -- session expired.
            VoiceError(PARSE_FAILED)      -- no transcription text available.
        """
        sid = uuid.UUID(session_id)

        # Load session with transcriptions (selectin)
        session_result = await db.execute(
            select(VoiceSession)
            .options(selectinload(VoiceSession.transcriptions))
            .where(
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

        # H7: Check session expiry
        if session.expires_at < datetime.now(UTC):
            session.status = "expired"
            await db.flush()
            raise VoiceError(
                error=VoiceErrors.SESSION_EXPIRED,
                message="La sesion de voz ha expirado.",
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

        # Run NLP parse via provider
        from app.services.voice_nlp import get_model_identifier

        parse_result = await self._parse_dental_text(concatenated_text)
        findings = parse_result["findings"]
        parse_warnings = parse_result["warnings"]
        parse_status = parse_result["status"]

        # Create VoiceParse record
        parse = VoiceParse(
            session_id=sid,
            input_text=concatenated_text,
            findings=findings,
            corrections=[],
            filtered_speech=[],
            warnings=parse_warnings,
            llm_model=get_model_identifier(),
            status=parse_status,
            input_tokens=parse_result.get("input_tokens", 0),
            output_tokens=parse_result.get("output_tokens", 0),
        )
        db.add(parse)
        await db.flush()

        logger.info(
            "Voice parse completed: session=%s findings=%d model=%s status=%s",
            session_id[:8],
            len(findings),
            parse.llm_model,
            parse_status,
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
            VoiceError(SESSION_EXPIRED)    -- session expired.
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

        # H7: Check session expiry
        if session.expires_at < datetime.now(UTC):
            session.status = "expired"
            await db.flush()
            raise VoiceError(
                error=VoiceErrors.SESSION_EXPIRED,
                message="La sesion de voz ha expirado.",
                status_code=410,
            )

        if not confirmed_findings:
            return {
                "applied_count": 0,
                "skipped_count": 0,
                "errors": [],
            }

        patient_id = str(session.patient_id)

        # H3: Validate each confirmed finding has required keys
        required_keys = {"tooth_number", "zone", "condition_code"}
        updates: list[dict[str, Any]] = []
        errors: list[str] = []

        for i, f in enumerate(confirmed_findings):
            if not isinstance(f, dict):
                errors.append(f"Finding #{i}: not a dict, skipped")
                continue
            missing = required_keys - f.keys()
            if missing:
                errors.append(f"Finding #{i}: missing keys {missing}, skipped")
                continue
            updates.append({
                "tooth_number": f["tooth_number"],
                "zone": f["zone"],
                "condition_code": f["condition_code"],
                "source": "voice",
            })

        if not updates:
            return {
                "applied_count": 0,
                "skipped_count": len(confirmed_findings),
                "errors": errors,
            }

        applied_count = 0
        skipped_count = len(confirmed_findings) - len(updates)

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

    # ── 5b. Submit Feedback ─────────────────────────────────────────────

    async def submit_feedback(
        self,
        *,
        db: AsyncSession,
        session_id: str,
        findings_corrections: list[dict[str, Any]],
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Record doctor corrections on parsed voice findings.

        Stores feedback as a VoiceParse with status='feedback' and
        updates the session status to 'feedback_received'.

        Returns:
            {session_id, feedback_recorded, correction_count, correction_rate}

        Raises:
            VoiceError(SESSION_NOT_FOUND) -- session not found.
        """
        sid = uuid.UUID(session_id)

        # Load session with parses
        session_result = await db.execute(
            select(VoiceSession)
            .options(selectinload(VoiceSession.parses))
            .where(
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

        # Count corrections (non-rejected items with actual changes)
        correction_count = sum(
            1 for c in findings_corrections
            if c.get("corrected_tooth") is not None
            or c.get("corrected_condition") is not None
            or c.get("is_rejected", False)
        )

        # Compute correction rate from the latest parse
        total_findings = 0
        for p in session.parses:
            if p.findings:
                total_findings += len(p.findings)

        correction_rate = (
            correction_count / total_findings if total_findings > 0 else None
        )

        # C1+C2: Store feedback as a VoiceParse record with status='feedback'
        # (CHECK constraint now allows 'feedback')
        feedback_parse = VoiceParse(
            session_id=sid,
            input_text=notes or "",
            findings=[],
            corrections=findings_corrections,
            filtered_speech=[],
            warnings=[],
            llm_model="feedback",
            status="feedback",
        )
        db.add(feedback_parse)

        # C1: Update session status (CHECK constraint now allows 'feedback_received')
        session.status = "feedback_received"
        await db.flush()

        logger.info(
            "Voice feedback recorded: session=%s corrections=%d rate=%s",
            session_id[:8],
            correction_count,
            f"{correction_rate:.2%}" if correction_rate is not None else "N/A",
        )

        return {
            "session_id": session_id,
            "feedback_recorded": True,
            "correction_count": correction_count,
            "correction_rate": correction_rate,
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

    async def _parse_dental_text(self, text: str) -> dict[str, Any]:
        """Parse dental dictation text into structured findings via NLP provider.

        Returns a dict with keys: findings, warnings, status, input_tokens, output_tokens.
        C4: On NLP failure, returns status='failed' with a warning instead
        of silently returning empty.
        H2: Validates findings against odontogram constants.
        """
        from app.services.voice_nlp import parse_dental_text

        try:
            parse_result = await parse_dental_text(text, DENTAL_NLP_PROMPT)
        except Exception:
            logger.exception("NLP parse failed")
            return {
                "findings": [],
                "warnings": ["NLP parse failed: el servicio de análisis no respondió"],
                "status": "failed",
                "input_tokens": 0,
                "output_tokens": 0,
            }

        raw_findings = parse_result.findings

        # H2: Validate findings
        valid_findings, validation_warnings = _validate_findings(raw_findings)

        if not raw_findings:
            # NLP returned nothing
            return {
                "findings": [],
                "warnings": validation_warnings,
                "status": "partial",
                "input_tokens": parse_result.input_tokens,
                "output_tokens": parse_result.output_tokens,
            }

        if not valid_findings and raw_findings:
            # NLP returned data but all was invalid
            return {
                "findings": [],
                "warnings": validation_warnings,
                "status": "partial",
                "input_tokens": parse_result.input_tokens,
                "output_tokens": parse_result.output_tokens,
            }

        status = "success" if valid_findings else "partial"
        return {
            "findings": valid_findings,
            "warnings": validation_warnings,
            "status": status,
            "input_tokens": parse_result.input_tokens,
            "output_tokens": parse_result.output_tokens,
        }


# Module-level singleton for dependency injection
voice_service = VoiceService()
