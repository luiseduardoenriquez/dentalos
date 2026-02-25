"""Onboarding wizard route (T-10)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_role
from app.core.database import get_db
from app.schemas.tenant import OnboardingStepRequest, OnboardingStepResponse
from app.services.tenant_settings_service import process_onboarding_step

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ─── T-10: Multi-step onboarding wizard ────────────


@router.post("", response_model=OnboardingStepResponse)
async def submit_onboarding_step(
    body: OnboardingStepRequest,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStepResponse:
    """Submit a single onboarding step (clinic_owner only).

    Steps 0-4: each step stores its data in tenant.settings
    and advances the onboarding_step counter. Completing step 4
    activates the tenant.
    """
    result = await process_onboarding_step(
        tenant_id=current_user.tenant.tenant_id,
        step=body.step,
        data=body.data,
        db=db,
    )
    return OnboardingStepResponse(**result)
