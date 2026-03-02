"""EPS insurance verification endpoints — VP-06.

Endpoint map:
  GET  /patients/{patient_id}/eps-verification  — Latest EPS status (patients:read)
  POST /patients/{patient_id}/eps-verification  — Trigger manual lookup (patients:write)
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.services.eps_verification_service import eps_verification_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/{patient_id}/eps-verification")
async def get_eps_verification(
    patient_id: UUID,
    current_user: AuthenticatedUser = Depends(require_permission("patients:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get the latest EPS insurance verification for a patient.

    Returns the most recent ADRES BDUA lookup result from cache or database.
    When no verification has been run yet, returns a pending status dict.
    The raw_response from ADRES is never included in this response.

    Requires: patients:read permission.
    """
    return await eps_verification_service.get_latest_verification(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
    )


@router.post("/{patient_id}/eps-verification", status_code=200)
async def trigger_eps_verification(
    patient_id: UUID,
    current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Trigger a manual EPS insurance verification for a patient.

    Calls the ADRES BDUA adapter with the patient's document type and number,
    persists a new EPSVerification record, and updates the Redis cache.
    Use this endpoint to refresh stale verification data or run a first-time
    lookup for a patient who was created before auto-verification was enabled.

    Requires: patients:write permission.
    """
    return await eps_verification_service.verify_patient(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
    )
