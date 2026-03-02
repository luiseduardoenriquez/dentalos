"""Patient referral program staff endpoints.

Endpoint map:
  GET  /referral-program/stats  -- Aggregate referral program stats (clinic_owner)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.referral_program import ReferralProgramStatsResponse
from app.services.referral_program_service import referral_program_service

router = APIRouter(prefix="/referral-program", tags=["referral-program"])


@router.get("/stats", response_model=ReferralProgramStatsResponse)
async def get_referral_stats(
    current_user: AuthenticatedUser = Depends(require_permission("referral_program:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get referral program statistics. Requires referral_program:read permission."""
    return await referral_program_service.get_program_stats(db=db)
