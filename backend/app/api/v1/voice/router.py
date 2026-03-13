"""Voice-to-odontogram API routes -- V-01 through V-05.

Endpoint map:
  POST /voice/sessions                          -- V-01: Create voice session
  POST /voice/sessions/{session_id}/upload      -- V-02: Upload audio chunk
  GET  /voice/sessions/{session_id}             -- V-03a: Get session + transcription status
  POST /voice/sessions/{session_id}/parse       -- V-03b: Parse transcriptions
  POST /voice/sessions/{session_id}/apply       -- V-04: Apply findings to odontogram
  GET  /voice/settings                          -- V-05a: Get voice settings
  PUT  /voice/settings                          -- V-05b: Update voice settings
"""

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission, require_role
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.voice import (
    ApplyRequest,
    ApplyResponse,
    AudioUploadResponse,
    FeedbackCreate,
    FeedbackResponse,
    ParseResponse,
    VoiceSessionCreate,
    VoiceSessionListResponse,
    VoiceSessionResponse,
    VoiceSettingsResponse,
    VoiceSettingsUpdate,
)
from app.services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


# ── V-01: Create Voice Session ───────────────────────────────────────────────


@router.post(
    "/sessions",
    response_model=VoiceSessionResponse,
    status_code=201,
)
async def create_voice_session(
    body: VoiceSessionCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> VoiceSessionResponse:
    """Start a new voice dictation session.

    Opens a session linked to a patient and doctor with a 30-minute TTL.
    Requires the AI Voice add-on to be enabled for the tenant.
    """
    result = await voice_service.create_session(
        db=db,
        patient_id=body.patient_id,
        doctor_id=current_user.user_id,
        tenant_id=current_user.tenant.tenant_id,
        context=body.context,
    )

    return VoiceSessionResponse(**result)


# ── V-01b: List Voice Sessions (QA Review) ───────────────────────────────────


@router.get(
    "/sessions",
    response_model=VoiceSessionListResponse,
)
async def list_voice_sessions(
    patient_id: str | None = Query(None),
    doctor_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> VoiceSessionListResponse:
    """List past voice sessions with pagination.

    Supports filtering by patient_id and/or doctor_id. Returns doctor
    and patient names for QA review display. Audio URLs are only
    generated on individual session detail fetch.
    """
    result = await voice_service.list_sessions(
        db=db,
        patient_id=patient_id,
        doctor_id=doctor_id,
        page=page,
        page_size=page_size,
    )

    return VoiceSessionListResponse(**result)


# ── V-02: Upload Audio Chunk ─────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/upload",
    response_model=AudioUploadResponse,
)
async def upload_audio(
    session_id: str,
    request: Request,
    audio: UploadFile = File(...),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AudioUploadResponse:
    """Upload an audio chunk for transcription.

    Accepts audio files in webm, ogg, wav, mpeg, or mp4 format.
    The audio is stored in S3 and a transcription job is queued.

    Supports idempotent retries via X-Idempotency-Key header: if a
    transcription with the same session_id + key already exists, the
    existing result is returned without creating a duplicate.
    """
    audio_data = await audio.read()
    content_type = audio.content_type or "audio/webm"

    result = await voice_service.upload_audio(
        db=db,
        session_id=session_id,
        tenant_id=current_user.tenant.tenant_id,
        audio_data=audio_data,
        content_type=content_type,
        idempotency_key=x_idempotency_key,
    )

    return AudioUploadResponse(**result)


# ── V-03a: Get Session Status ────────────────────────────────────────────────


@router.get(
    "/sessions/{session_id}",
    response_model=VoiceSessionResponse,
)
async def get_session_status(
    session_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> VoiceSessionResponse:
    """Get session detail including transcription statuses.

    Poll this endpoint to check when transcriptions have completed
    before triggering the parse step.
    """
    result = await voice_service.get_status(
        db=db,
        session_id=session_id,
    )

    return VoiceSessionResponse(**result)


# ── V-03b: Parse Transcriptions ──────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/parse",
    response_model=ParseResponse,
)
async def parse_transcriptions(
    session_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ParseResponse:
    """Parse all completed transcriptions into structured dental findings.

    Concatenates text from all transcription chunks and runs the NLP
    pipeline (Claude LLM in production, stub in MVP). Returns findings
    ready for the doctor to review before applying.
    """
    result = await voice_service.parse_transcription(
        db=db,
        session_id=session_id,
    )

    return ParseResponse(**result)


# ── V-04: Apply Findings to Odontogram ───────────────────────────────────────


@router.post(
    "/sessions/{session_id}/apply",
    response_model=ApplyResponse,
)
async def apply_findings(
    session_id: str,
    body: ApplyRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ApplyResponse:
    """Apply doctor-confirmed findings to the odontogram.

    Review-before-apply: the doctor reviews parsed findings and confirms
    which ones to commit. Only confirmed findings are written to the
    odontogram via bulk_update.
    """
    # Convert Pydantic VoiceFinding models to dicts for the service
    findings_dicts = [f.model_dump() for f in body.confirmed_findings]

    result = await voice_service.apply_findings(
        db=db,
        session_id=session_id,
        tenant_id=current_user.tenant.tenant_id,
        doctor_id=current_user.user_id,
        confirmed_findings=findings_dicts,
    )

    # Audit the apply action
    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="apply_voice_findings",
        resource_type="voice_session",
        resource_id=session_id,
        changes={
            "applied_count": result["applied_count"],
            "skipped_count": result["skipped_count"],
        },
    )

    return ApplyResponse(**result)


# ── V-05: Submit Feedback ────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/feedback",
    response_model=FeedbackResponse,
)
async def submit_feedback(
    session_id: str,
    body: FeedbackCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("voice:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> FeedbackResponse:
    """Submit correction feedback on parsed voice findings.

    Doctors can report which findings were incorrect -- wrong tooth number,
    wrong condition, or entirely rejected. This data is stored for
    accuracy tracking and model improvement.
    """
    result = await voice_service.submit_feedback(
        db=db,
        session_id=session_id,
        findings_corrections=[c.model_dump() for c in body.findings_corrections],
        notes=body.notes,
    )

    # Audit the feedback action
    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="submit_voice_feedback",
        resource_type="voice_session",
        resource_id=session_id,
        changes={
            "correction_count": result["correction_count"],
            "correction_rate": result["correction_rate"],
        },
    )

    return FeedbackResponse(**result)


# ── V-05a: Get Voice Settings ────────────────────────────────────────────────


@router.get(
    "/settings",
    response_model=VoiceSettingsResponse,
)
async def get_voice_settings(
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> VoiceSettingsResponse:
    """Get voice feature configuration for this clinic.

    Only accessible to clinic owners.
    """
    result = await voice_service.get_voice_settings(db=db)
    return VoiceSettingsResponse(**result)


# ── V-05b: Update Voice Settings ─────────────────────────────────────────────


@router.put(
    "/settings",
    response_model=VoiceSettingsResponse,
)
async def update_voice_settings(
    body: VoiceSettingsUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> VoiceSettingsResponse:
    """Update voice feature configuration for this clinic.

    Only accessible to clinic owners. Controls whether the voice
    add-on is enabled and rate limit thresholds.
    """
    result = await voice_service.update_voice_settings(
        db=db,
        voice_enabled=body.voice_enabled,
        max_session_duration_seconds=body.max_session_duration_seconds,
        max_sessions_per_hour=body.max_sessions_per_hour,
    )

    return VoiceSettingsResponse(**result)
