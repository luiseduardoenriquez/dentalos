"""Voice Clinical Notes API routes (AI-03).

Endpoints:
  POST /voice/sessions/{session_id}/structure    → Trigger SOAP structuring
  GET  /voice/clinical-notes/{note_id}           → Get structured note
  POST /voice/clinical-notes/{note_id}/save      → Save as evolution record
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.compliance.deps import resolve_tenant
from app.core.database import get_tenant_db
from app.core.error_codes import VoiceErrors
from app.core.exceptions import DentalOSError
from app.schemas.voice_clinical_note import (
    VoiceClinicalNoteResponse,
    VoiceClinicalNoteStructureRequest,
    VoiceClinicalNoteSaveRequest,
)
from app.services.voice_clinical_notes_service import voice_clinical_notes_service

router = APIRouter(prefix="/voice", tags=["voice-clinical-notes"])


@router.post(
    "/sessions/{session_id}/structure",
    response_model=VoiceClinicalNoteResponse,
    status_code=201,
)
async def structure_clinical_note(
    session_id: uuid.UUID,
    body: VoiceClinicalNoteStructureRequest | None = None,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:write")
    ),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Trigger SOAP structuring of a voice session's transcription.

    The voice session must have context='evolution' and completed transcriptions.
    Requires: voice_enabled add-on.
    """
    if not tenant.features.get("voice_enabled"):
        raise DentalOSError(
            status_code=402,
            error=VoiceErrors.ADDON_REQUIRED,
            message="El módulo de Dictado por Voz requiere el add-on AI Voice.",
            details={"addon": "voice_enabled", "price": "$10/doctor/mes"},
        )

    template_id = None
    if body and body.template_id:
        template_id = uuid.UUID(body.template_id)

    return await voice_clinical_notes_service.structure_note(
        db=db,
        session_id=session_id,
        patient_id=None,  # resolved from session
        doctor_id=current_user.user_id,
        template_id=template_id,
        tenant_id=tenant.tenant_id,
    )


@router.get(
    "/clinical-notes/{note_id}",
    response_model=VoiceClinicalNoteResponse,
)
async def get_clinical_note(
    note_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:read")
    ),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a structured clinical note (supports polling while processing)."""
    return await voice_clinical_notes_service.get_note(
        db=db,
        note_id=note_id,
    )


@router.post(
    "/clinical-notes/{note_id}/save",
    response_model=VoiceClinicalNoteResponse,
)
async def save_clinical_note(
    note_id: uuid.UUID,
    body: VoiceClinicalNoteSaveRequest | None = None,
    current_user: AuthenticatedUser = Depends(
        require_permission("clinical_records:write")
    ),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Save a structured note as a clinical evolution record.

    Optionally pass edited_note to override the AI-generated content.
    """
    edited_note = body.edited_note if body else None
    return await voice_clinical_notes_service.save_as_evolution(
        db=db,
        note_id=note_id,
        doctor_id=current_user.user_id,
        edited_note=edited_note,
    )
