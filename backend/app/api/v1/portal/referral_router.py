"""Patient portal referral program endpoints.

Endpoint map:
  GET  /portal/referral          -- Get or create the patient's referral code
  GET  /portal/referral/rewards  -- List all rewards for the patient
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.database import get_tenant_db
from app.schemas.referral_program import ReferralCodeResponse, ReferralRewardListResponse
from app.services.referral_program_service import referral_program_service

router = APIRouter(prefix="/portal/referral", tags=["portal-referral"])


@router.get("", response_model=ReferralCodeResponse)
async def get_my_referral_code(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get or create a referral code for the current patient."""
    return await referral_program_service.get_or_create_code(
        db=db,
        patient_id=portal_user.patient_id,
    )


@router.get("/rewards", response_model=ReferralRewardListResponse)
async def get_my_rewards(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get all referral rewards for the current patient."""
    return await referral_program_service.get_patient_rewards(
        db=db,
        patient_id=portal_user.patient_id,
    )
