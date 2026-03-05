"""Patient referral program staff endpoints.

Endpoint map:
  GET  /referral-program/stats   -- Aggregate referral program stats (clinic_owner)
  POST /referral-program/toggle  -- Toggle program on/off (clinic_owner)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission, require_role
from app.core.database import get_db, get_tenant_db
from app.schemas.referral_program import (
    ReferralProgramStatsResponse,
    ReferralProgramToggleRequest,
)
from app.services.referral_program_service import referral_program_service
from app.services.tenant_settings_service import get_tenant_settings, update_tenant_settings

router = APIRouter(prefix="/referral-program", tags=["referral-program"])


@router.get("/stats", response_model=ReferralProgramStatsResponse)
async def get_referral_stats(
    current_user: AuthenticatedUser = Depends(require_permission("referral_program:read")),
    tenant_db: AsyncSession = Depends(get_tenant_db),
    public_db: AsyncSession = Depends(get_db),
) -> dict:
    """Get referral program statistics. Requires referral_program:read permission."""
    settings = await get_tenant_settings(
        tenant_id=current_user.tenant.tenant_id, db=public_db,
    )
    return await referral_program_service.get_program_stats(
        db=tenant_db, tenant_settings=settings.get("settings"),
    )


@router.post("/toggle", response_model=ReferralProgramStatsResponse)
async def toggle_referral_program(
    body: ReferralProgramToggleRequest,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    tenant_db: AsyncSession = Depends(get_tenant_db),
    public_db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle the referral program on or off. Clinic owner only."""
    updated = await update_tenant_settings(
        tenant_id=current_user.tenant.tenant_id,
        updates={"settings": {"referral_program_active": body.is_active}},
        db=public_db,
    )
    return await referral_program_service.get_program_stats(
        db=tenant_db, tenant_settings=updated.get("settings"),
    )
