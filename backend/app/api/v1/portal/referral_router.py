"""Patient portal referral program endpoints.

Endpoint map:
  GET  /portal/referral          -- Get patient's referral code + URL + pending count
  GET  /portal/referral/rewards  -- List rewards with Spanish field names
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.config import settings
from app.core.database import get_db, get_tenant_db
from app.models.public.tenant import Tenant
from app.schemas.referral_program import (
    PortalReferralResponse,
    PortalReferralRewardListResponse,
)
from app.services.referral_program_service import referral_program_service

router = APIRouter(prefix="/portal/referral", tags=["portal-referral"])


@router.get("", response_model=PortalReferralResponse)
async def get_my_referral_code(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
    public_db: AsyncSession = Depends(get_db),
) -> dict:
    """Get or create referral code with shareable URL for the current patient."""
    tenant_id = uuid.UUID(portal_user.tenant.tenant_id)
    result = await public_db.execute(
        select(Tenant.slug).where(Tenant.id == tenant_id)
    )
    tenant_slug = result.scalar_one()

    return await referral_program_service.get_portal_referral_data(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_slug=tenant_slug,
        base_url=settings.frontend_url,
    )


@router.get("/rewards", response_model=PortalReferralRewardListResponse)
async def get_my_rewards(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get all referral rewards for the current patient (Spanish field names)."""
    return await referral_program_service.get_portal_rewards(
        db=db,
        patient_id=portal_user.patient_id,
    )
