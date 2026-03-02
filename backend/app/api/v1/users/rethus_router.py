"""RETHUS verification endpoints — VP-07.

Endpoint map:
  GET  /users/{user_id}/rethus-verification  — Read current RETHUS status (users:read)
  POST /users/{user_id}/rethus-verification  — Trigger RETHUS verification (users:write)
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.rethus import RETHUSVerificationTrigger
from app.services.rethus_verification_service import rethus_verification_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/rethus-verification")
async def get_rethus_verification(
    user_id: UUID,
    current_user: AuthenticatedUser = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get current RETHUS verification status for a user.

    Returns the persisted verification status, the RETHUS number on record,
    and the timestamp of the last successful verification.  Professional name
    and specialty are NOT returned here (PHI stored but not surfaced in reads).

    Requires: users:read permission.
    """
    return await rethus_verification_service.check_status(
        db=db,
        user_id=user_id,
    )


@router.post("/{user_id}/rethus-verification", status_code=200)
async def trigger_rethus_verification(
    user_id: UUID,
    body: RETHUSVerificationTrigger,
    current_user: AuthenticatedUser = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Trigger RETHUS verification for a user.

    Calls the RETHUS adapter with the supplied registry number, updates the
    user's verification status, and returns the result.  This endpoint is
    intended for clinic owners managing their clinical staff.

    The response includes professional_name, profession, and specialty only
    when the lookup succeeds; these are derived from the adapter's live
    response and are not stored in a retrievable form.

    Requires: users:write permission (clinic_owner in practice).
    """
    return await rethus_verification_service.verify_user(
        db=db,
        user_id=user_id,
        rethus_number=body.rethus_number,
    )
