"""Voice clinical notes service (AI-03).

Structures voice transcriptions into SOAP notes using Claude. Takes
transcription text from a VoiceSession with context='evolution', publishes
a structuring job to the clinical queue, and saves the result as a
ClinicalRecord evolution note when the doctor approves.

Security invariants:
  - PHI is NEVER logged (patient names, document numbers, phone, email).
  - Voice feature requires tenant add-on ($10/doctor/mo).
  - All Spanish (es-419) output for clinical staff.

Pipeline overview:
  1. structure_note()          -- validate session, create VoiceClinicalNote, publish job
  2. complete_structuring()    -- worker callback: save Claude results
  3. fail_structuring()        -- worker callback: record error
  4. get_note()                -- retrieve a structured note
  5. save_as_evolution()       -- save SOAP note as ClinicalRecord evolution_note
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.error_codes import VoiceErrors
from app.core.exceptions import (
    DentalOSError,
    ResourceNotFoundError,
    VoiceError,
)
from app.core.queue import publish_message
from app.models.tenant.ai_usage_log import AIUsageLog
from app.models.tenant.clinical_record import ClinicalRecord
from app.models.tenant.voice_clinical_note import VoiceClinicalNote
from app.models.tenant.voice_session import VoiceSession, VoiceTranscription
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.ai.voice_notes")

# ── Constants ────────────────────────────────────────────────────────────────

# Use Sonnet for SOAP structuring (quality over speed for clinical notes)
_MODEL = settings.anthropic_model_treatment

# ── SOAP structuring system prompt ───────────────────────────────────────────

_SYSTEM_PROMPT = """\
Eres un asistente clinico dental experto que trabaja en una clinica dental en \
Colombia. Se te proporciona la transcripcion de una dictacion de voz de un \
odontologo durante una consulta de evolucion con un paciente.

Tu tarea es estructurar esta dictacion en una nota clinica SOAP \
(Subjective, Objective, Assessment, Plan) en espanol (es-419).

REGLAS:
1. Todo el texto generado debe estar en espanol (es-419).
2. Se conciso y clinicamente preciso.
3. Extrae numeros de dientes en notacion FDI (11-48) cuando se mencionen.
4. Extrae codigos CIE-10 cuando se mencionen diagnosticos reconocibles.
5. Extrae codigos CUPS cuando se mencionen procedimientos reconocibles.
6. Si la dictacion es ambigua, usa el campo "warnings" para senalar dudas.
7. Filtra expresiones no clinicas (muletillas, conversaciones laterales) y \
reportalas en "filtered_speech".
8. No inventes informacion que no este en la dictacion.
9. Numeros de dientes FDI validos: cuadrante (1-4) + diente (1-8), \
ej: 11, 16, 21, 24, 31, 36, 41, 48. Para dientes deciduos: cuadrante \
(5-8) + diente (1-5).

Devuelve UNICAMENTE un objeto JSON con esta estructura exacta:

{
  "subjective": {
    "chief_complaint": "<motivo de consulta principal>",
    "history_present_illness": "<historia de la enfermedad actual>",
    "patient_reported_symptoms": ["<sintoma1>", "<sintoma2>"]
  },
  "objective": {
    "clinical_findings": "<hallazgos clinicos del examen>",
    "vital_signs": "<signos vitales si se mencionan, null si no>",
    "intraoral_exam": "<examen intraoral>",
    "extraoral_exam": "<examen extraoral si se menciona, null si no>"
  },
  "assessment": {
    "diagnoses": [
      {
        "description": "<descripcion del diagnostico>",
        "cie10_code": "<codigo CIE-10 si es identificable, null si no>",
        "severity": "<mild|moderate|severe>",
        "tooth_numbers": [<numeros FDI involucrados>]
      }
    ],
    "clinical_impression": "<impresion clinica general>"
  },
  "plan": {
    "procedures_performed": [
      {
        "description": "<procedimiento realizado>",
        "cups_code": "<codigo CUPS si es identificable, null si no>",
        "tooth_numbers": [<numeros FDI involucrados>]
      }
    ],
    "procedures_planned": [
      {
        "description": "<procedimiento planeado>",
        "cups_code": "<codigo CUPS si es identificable, null si no>",
        "tooth_numbers": [<numeros FDI involucrados>]
      }
    ],
    "prescriptions": "<medicamentos prescritos si se mencionan>",
    "follow_up": "<indicaciones de seguimiento>",
    "patient_instructions": "<instrucciones al paciente>"
  },
  "extracted_codes": {
    "teeth": [<lista unica de numeros FDI mencionados>],
    "cie10": [
      {"code": "<codigo>", "description": "<descripcion>"}
    ],
    "cups": [
      {"code": "<codigo>", "description": "<descripcion>"}
    ]
  },
  "warnings": ["<frases ambiguas o que requieren revision>"],
  "filtered_speech": ["<expresiones no clinicas filtradas>"]
}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────


def _note_to_dict(note: VoiceClinicalNote) -> dict[str, Any]:
    """Convert a VoiceClinicalNote to a serialisable dict.

    Does NOT include input_text (may contain PHI in transcription).
    """
    return {
        "id": str(note.id),
        "session_id": str(note.session_id),
        "patient_id": str(note.patient_id),
        "doctor_id": str(note.doctor_id),
        "status": note.status,
        "structured_note": note.structured_note,
        "linked_teeth": note.linked_teeth,
        "linked_cie10_codes": note.linked_cie10_codes,
        "linked_cups_codes": note.linked_cups_codes,
        "template_id": str(note.template_id) if note.template_id else None,
        "template_mapping": note.template_mapping,
        "model_used": note.model_used,
        "input_tokens": note.input_tokens,
        "output_tokens": note.output_tokens,
        "error_message": note.error_message,
        "reviewed_at": note.reviewed_at.isoformat() if note.reviewed_at else None,
        "clinical_record_id": (
            str(note.clinical_record_id) if note.clinical_record_id else None
        ),
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


# ── Service class ────────────────────────────────────────────────────────────


class VoiceClinicalNotesService:
    """Structures voice transcriptions into SOAP clinical notes using Claude.

    Follows the same queue-based async pattern as voice_service.py:
    1. API call creates the record and publishes a job.
    2. Worker calls Claude and invokes complete/fail callbacks.
    3. Doctor reviews and saves as a ClinicalRecord.
    """

    # ── 1. Structure Note ────────────────────────────────────────────────

    async def structure_note(
        self,
        *,
        db: AsyncSession,
        session_id: str,
        patient_id: str,
        doctor_id: str,
        template_id: str | None = None,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Initiate SOAP structuring of a voice session's transcriptions.

        Validates the voice session exists with context='evolution' and
        has completed transcriptions, assembles all text chunks, creates
        a VoiceClinicalNote row (status=processing), and publishes a
        ``voice_notes.structure`` job to the clinical queue.

        Args:
            db: Tenant-scoped async DB session.
            session_id: UUID string of the voice session.
            patient_id: UUID string of the patient.
            doctor_id: UUID string of the requesting doctor.
            template_id: Optional UUID string of an evolution template.
            tenant_id: Tenant identifier for queue message.

        Returns:
            dict representation of the created VoiceClinicalNote.

        Raises:
            VoiceError(SESSION_NOT_FOUND): Session not found or inactive.
            VoiceError(SESSION_EXPIRED): Session has expired.
            VoiceError(TRANSCRIPTION_FAILED): No completed transcriptions.
        """
        sid = uuid.UUID(session_id)
        pid = uuid.UUID(patient_id)
        did = uuid.UUID(doctor_id)

        # Load session with transcriptions
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

        # Validate ownership
        if session.patient_id != pid or session.doctor_id != did:
            raise VoiceError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                message="Sesion de voz no encontrada.",
                status_code=404,
            )

        # Validate context
        if session.context != "evolution":
            raise VoiceError(
                error=VoiceErrors.PARSE_FAILED,
                message=(
                    "La sesion de voz no es de tipo evolucion. "
                    "Solo se pueden estructurar notas de sesiones de evolucion."
                ),
                status_code=422,
            )

        # Check if session has expired
        if session.status == "expired" or session.expires_at < datetime.now(UTC):
            if session.status != "expired":
                session.status = "expired"
                await db.flush()
            raise VoiceError(
                error=VoiceErrors.SESSION_EXPIRED,
                message="La sesion de voz ha expirado.",
                status_code=410,
            )

        # Gather completed transcriptions
        completed_transcriptions = [
            t for t in session.transcriptions if t.status == "completed" and t.text
        ]

        if not completed_transcriptions:
            raise VoiceError(
                error=VoiceErrors.TRANSCRIPTION_FAILED,
                message=(
                    "No hay transcripciones completadas en esta sesion. "
                    "Espere a que finalice la transcripcion o suba un archivo de audio."
                ),
                status_code=422,
            )

        # Assemble all transcription text in chunk order
        completed_transcriptions.sort(key=lambda t: t.chunk_index)
        assembled_text = " ".join(t.text for t in completed_transcriptions)

        # Create VoiceClinicalNote with status=processing
        tid = uuid.UUID(template_id) if template_id else None
        note = VoiceClinicalNote(
            session_id=sid,
            patient_id=pid,
            doctor_id=did,
            input_text=assembled_text,
            structured_note={},
            linked_teeth=None,
            linked_cie10_codes=[],
            linked_cups_codes=[],
            template_id=tid,
            model_used=_MODEL,
            input_tokens=0,
            output_tokens=0,
            status="processing",
            is_active=True,
        )
        db.add(note)
        await db.flush()

        logger.info(
            "Voice clinical note created: note=%s session=%s status=processing",
            str(note.id)[:8],
            session_id[:8],
        )

        # Publish structuring job to clinical queue
        await publish_message(
            "clinical",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="voice_notes.structure",
                payload={
                    "note_id": str(note.id),
                    "input_text": assembled_text,
                    "template_id": template_id,
                },
            ),
        )

        return _note_to_dict(note)

    # ── 2. Complete Structuring (worker callback) ────────────────────────

    async def complete_structuring(
        self,
        *,
        db: AsyncSession,
        note_id: str,
        structured_note: dict[str, Any],
        linked_teeth: list[int] | None,
        linked_cie10: list[dict[str, str]],
        linked_cups: list[dict[str, str]],
        model_used: str,
        input_tokens: int,
        output_tokens: int,
    ) -> dict[str, Any]:
        """Update a VoiceClinicalNote after Claude returns successfully.

        Called by the clinical worker after SOAP structuring completes.

        Args:
            db: Tenant-scoped async DB session.
            note_id: UUID string of the VoiceClinicalNote.
            structured_note: Parsed SOAP JSON from Claude.
            linked_teeth: List of FDI tooth numbers extracted.
            linked_cie10: List of CIE-10 code dicts extracted.
            linked_cups: List of CUPS code dicts extracted.
            model_used: Claude model identifier used.
            input_tokens: Input token count from API response.
            output_tokens: Output token count from API response.

        Returns:
            dict representation of the updated VoiceClinicalNote.

        Raises:
            ResourceNotFoundError: Note not found.
        """
        nid = uuid.UUID(note_id)

        result = await db.execute(
            select(VoiceClinicalNote).where(
                VoiceClinicalNote.id == nid,
                VoiceClinicalNote.is_active.is_(True),
            )
        )
        note = result.scalar_one_or_none()

        if note is None:
            raise ResourceNotFoundError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                resource_name="VoiceClinicalNote",
            )

        note.structured_note = structured_note
        note.linked_teeth = linked_teeth
        note.linked_cie10_codes = linked_cie10
        note.linked_cups_codes = linked_cups
        note.model_used = model_used
        note.input_tokens = input_tokens
        note.output_tokens = output_tokens
        note.status = "completed"

        await db.flush()

        # Log AI usage
        try:
            usage_log = AIUsageLog(
                doctor_id=note.doctor_id,
                feature="voice_clinical_notes",
                model=model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            db.add(usage_log)
            await db.flush()
        except Exception:
            logger.warning(
                "Failed to log AI usage for voice clinical note: note=%s",
                note_id[:8],
            )

        logger.info(
            "Voice clinical note structured: note=%s tokens=%d+%d status=completed",
            note_id[:8],
            input_tokens,
            output_tokens,
        )

        return _note_to_dict(note)

    # ── 3. Fail Structuring (worker callback) ────────────────────────────

    async def fail_structuring(
        self,
        *,
        db: AsyncSession,
        note_id: str,
        error_message: str,
    ) -> dict[str, Any]:
        """Mark a VoiceClinicalNote as failed after a structuring error.

        Called by the clinical worker when Claude or parsing fails.

        Args:
            db: Tenant-scoped async DB session.
            note_id: UUID string of the VoiceClinicalNote.
            error_message: Human-readable error description.

        Returns:
            dict representation of the updated VoiceClinicalNote.

        Raises:
            ResourceNotFoundError: Note not found.
        """
        nid = uuid.UUID(note_id)

        result = await db.execute(
            select(VoiceClinicalNote).where(
                VoiceClinicalNote.id == nid,
                VoiceClinicalNote.is_active.is_(True),
            )
        )
        note = result.scalar_one_or_none()

        if note is None:
            raise ResourceNotFoundError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                resource_name="VoiceClinicalNote",
            )

        note.status = "failed"
        note.error_message = error_message

        await db.flush()

        logger.warning(
            "Voice clinical note structuring failed: note=%s",
            note_id[:8],
        )

        return _note_to_dict(note)

    # ── 4. Get Note ──────────────────────────────────────────────────────

    async def get_note(
        self,
        *,
        db: AsyncSession,
        note_id: str,
        patient_id: str,
    ) -> dict[str, Any]:
        """Retrieve a voice clinical note.

        Args:
            db: Tenant-scoped async DB session.
            note_id: UUID string of the VoiceClinicalNote.
            patient_id: UUID string of the patient (for access control).

        Returns:
            dict representation of the VoiceClinicalNote.

        Raises:
            ResourceNotFoundError: Note not found or does not belong to patient.
        """
        nid = uuid.UUID(note_id)
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(VoiceClinicalNote).where(
                VoiceClinicalNote.id == nid,
                VoiceClinicalNote.patient_id == pid,
                VoiceClinicalNote.is_active.is_(True),
            )
        )
        note = result.scalar_one_or_none()

        if note is None:
            raise ResourceNotFoundError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                resource_name="VoiceClinicalNote",
            )

        return _note_to_dict(note)

    # ── 5. Save as Evolution ─────────────────────────────────────────────

    async def save_as_evolution(
        self,
        *,
        db: AsyncSession,
        note_id: str,
        patient_id: str,
        doctor_id: str,
        edited_note: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save the structured SOAP note as a ClinicalRecord evolution note.

        Takes the Claude-structured SOAP note (or a doctor-edited version)
        and creates a ClinicalRecord row with type='evolution_note'. Updates
        the VoiceClinicalNote status to 'saved' and links the clinical record.

        Args:
            db: Tenant-scoped async DB session.
            note_id: UUID string of the VoiceClinicalNote.
            patient_id: UUID string of the patient.
            doctor_id: UUID string of the doctor saving the note.
            edited_note: Optional doctor-edited SOAP note dict. If None,
                uses the original structured_note from Claude.

        Returns:
            dict representation of the updated VoiceClinicalNote with
            clinical_record_id set.

        Raises:
            ResourceNotFoundError: Note not found.
            VoiceError(PARSE_FAILED): Note is not in a saveable state.
        """
        nid = uuid.UUID(note_id)
        pid = uuid.UUID(patient_id)
        did = uuid.UUID(doctor_id)

        result = await db.execute(
            select(VoiceClinicalNote).where(
                VoiceClinicalNote.id == nid,
                VoiceClinicalNote.patient_id == pid,
                VoiceClinicalNote.is_active.is_(True),
            )
        )
        note = result.scalar_one_or_none()

        if note is None:
            raise ResourceNotFoundError(
                error=VoiceErrors.SESSION_NOT_FOUND,
                resource_name="VoiceClinicalNote",
            )

        # Only completed notes can be saved
        if note.status not in ("completed",):
            raise VoiceError(
                error=VoiceErrors.PARSE_FAILED,
                message=(
                    f"La nota clinica no se puede guardar en estado '{note.status}'. "
                    "Solo notas completadas pueden guardarse como evolucion."
                ),
                status_code=422,
            )

        # Use the edited note if provided, otherwise use the original
        final_note = edited_note if edited_note is not None else note.structured_note

        # Build ClinicalRecord content with SOAP structure and source metadata
        record_content = {
            "soap": final_note,
            "source": "voice_dictation",
            "voice_note_id": str(note.id),
            "voice_session_id": str(note.session_id),
            "ai_model": note.model_used,
            "doctor_edited": edited_note is not None,
        }

        # Determine tooth numbers from the note
        tooth_numbers = note.linked_teeth

        # Create ClinicalRecord
        clinical_record = ClinicalRecord(
            patient_id=pid,
            doctor_id=did,
            type="evolution_note",
            content=record_content,
            tooth_numbers=tooth_numbers,
            template_id=note.template_id,
            is_editable=True,
            edit_locked_at=datetime.now(UTC) + timedelta(hours=24),
            is_active=True,
        )
        db.add(clinical_record)
        await db.flush()

        # Update VoiceClinicalNote
        note.status = "saved"
        note.reviewed_at = datetime.now(UTC)
        note.clinical_record_id = clinical_record.id

        # If the doctor provided an edited note, store it as the structured_note
        if edited_note is not None:
            note.structured_note = edited_note

        await db.flush()

        logger.info(
            "Voice clinical note saved as evolution: note=%s record=%s",
            note_id[:8],
            str(clinical_record.id)[:8],
        )

        return _note_to_dict(note)


# Module-level singleton
voice_clinical_notes_service = VoiceClinicalNotesService()
