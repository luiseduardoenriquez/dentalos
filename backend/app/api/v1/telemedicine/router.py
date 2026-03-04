"""Telemedicine API routes — Sprint 29-30 GAP-09.

Endpoint map:
  POST  /appointments/{appointment_id}/video-session
        — Create a video session for an appointment (requires telemedicine:write)

  GET   /appointments/{appointment_id}/video-session
        — Get current session info for an appointment (requires telemedicine:read)

  POST  /video-sessions/{session_id}/end
        — End an active video session (requires telemedicine:write)

  GET   /portal/video-sessions/{appointment_id}/join
        — Patient portal: get patient-specific join URL (portal JWT required)

Security:
  - All staff endpoints require 'telemedicine:read' or 'telemedicine:write' permission.
  - The portal endpoint requires a valid portal JWT (scope='portal', sub='pat_...').
  - join_url_doctor is NEVER returned to portal endpoints.
  - PHI is NEVER logged anywhere in this module.
  - The add-on gate is enforced inside the service layer.

Tenant settings are read from clinic_settings JSONB to check add-on status.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.database import get_tenant_db
from app.core.exceptions import DentalOSError
from app.schemas.video_session import (
    VideoSessionCreate,
    VideoSessionJoinResponse,
    VideoSessionResponse,
)
from app.services.telemedicine_service import telemedicine_service

logger = logging.getLogger("dentalos.api.telemedicine")

router = APIRouter(tags=["telemedicine"])


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_tenant_settings(db: AsyncSession) -> dict:
    """Fetch the clinic_settings JSONB for the current tenant.

    Returns an empty dict if no settings row exists.
    """
    result = await db.execute(
        text("SELECT settings FROM clinic_settings LIMIT 1")
    )
    row = result.one_or_none()
    if row is None:
        return {}
    settings_data = row[0]
    if isinstance(settings_data, dict):
        return settings_data
    return {}


# ── Staff endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/appointments/{appointment_id}/video-session",
    response_model=VideoSessionResponse,
    status_code=201,
    summary="Crear sesión de telemedicina",
    description=(
        "Crea una sesión de video para una cita confirmada o en progreso. "
        "Genera URLs de acceso para el doctor (moderador) y el paciente. "
        "Requiere el complemento de Telemedicina activo."
    ),
)
async def create_video_session(
    appointment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("telemedicine:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> VideoSessionResponse:
    """Create a telemedicine video session for the specified appointment.

    The appointment must be in 'confirmed' or 'in_progress' status.
    Returns separate join URLs for the doctor (moderator privileges) and
    patient. The telemedicine add-on must be active for the tenant.
    """
    tenant_settings = await _get_tenant_settings(db)

    result = await telemedicine_service.create_session(
        db=db,
        appointment_id=str(appointment_id),
        tenant_id=current_user.tenant.tenant_id,
        tenant_settings=tenant_settings,
    )
    await db.commit()
    return VideoSessionResponse(**result)


@router.get(
    "/appointments/{appointment_id}/video-session",
    response_model=VideoSessionResponse,
    summary="Obtener sesión de telemedicina",
    description="Retorna la sesión de video más reciente para la cita especificada.",
)
async def get_video_session(
    appointment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("telemedicine:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> VideoSessionResponse:
    """Get the current video session for an appointment.

    Returns the most recent VideoSession record linked to this appointment.
    Raises 404 if no session exists.
    """
    result = await telemedicine_service.get_session(
        db=db,
        appointment_id=str(appointment_id),
    )
    return VideoSessionResponse(**result)


@router.post(
    "/video-sessions/{session_id}/end",
    response_model=VideoSessionResponse,
    summary="Finalizar sesión de telemedicina",
    description=(
        "Marca la sesión como finalizada, calcula la duración, elimina la sala "
        "en el proveedor y recupera la URL de grabación si está disponible."
    ),
)
async def end_video_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("telemedicine:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> VideoSessionResponse:
    """End an active video session.

    Updates the session status to 'ended', calculates duration_seconds,
    deletes the Daily.co room, and attempts to retrieve the recording URL.
    Provider errors during room deletion are logged but do not fail the request.
    """
    result = await telemedicine_service.end_session(
        db=db,
        session_id=str(session_id),
    )
    await db.commit()
    return VideoSessionResponse(**result)


# ── Patient portal endpoint ───────────────────────────────────────────────────


@router.get(
    "/portal/video-sessions/{appointment_id}/join",
    response_model=VideoSessionJoinResponse,
    summary="Unirse a sesión de telemedicina (portal paciente)",
    description=(
        "Retorna la URL de acceso para el paciente autenticado. "
        "Solo se devuelve el enlace del paciente — el enlace del doctor nunca se expone aquí."
    ),
)
async def get_patient_join_url(
    appointment_id: uuid.UUID,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> VideoSessionJoinResponse:
    """Return the patient-specific join URL for a telemedicine session.

    The authenticated portal patient must own the appointment. If the patient
    does not own the appointment or no active session exists, returns 404
    (deliberately conflated to avoid information leakage).

    Only the patient join URL is returned — the doctor URL is never exposed
    on portal endpoints.
    """
    result = await telemedicine_service.get_patient_join_url(
        db=db,
        appointment_id=str(appointment_id),
        patient_id=portal_user.patient_id,
    )
    return VideoSessionJoinResponse(
        join_url=result["join_url"],
        session_id=result["session_id"],
    )
