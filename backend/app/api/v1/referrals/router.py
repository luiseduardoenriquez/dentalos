"""Referral API routes — P-15.

Endpoint map:
  PUT /referrals/{referral_id} — Update referral status
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.referral import ReferralResponse, ReferralUpdate
from app.services.referral_service import referral_service

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.put("/{referral_id}", response_model=ReferralResponse)
async def update_referral(
    referral_id: str,
    body: ReferralUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("patients:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ReferralResponse:
    """Update a referral status (accept, complete, or decline)."""
    result = await referral_service.update_referral_status(
        db=db,
        referral_id=referral_id,
        updater_id=current_user.user_id,
        status=body.status,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="patient_referral",
        resource_id=result["id"],
    )

    return ReferralResponse(**result)
