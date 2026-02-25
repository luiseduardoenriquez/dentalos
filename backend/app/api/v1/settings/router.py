"""Tenant settings routes (T-06 through T-09)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.schemas.tenant import (
    PlanLimitsResponse,
    PlanUsageResponse,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)
from app.services.tenant_settings_service import (
    get_plan_limits,
    get_plan_usage,
    get_tenant_settings,
    update_tenant_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


# ─── T-06: Get current tenant settings ─────────────


@router.get("", response_model=TenantSettingsResponse)
async def get_settings(
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsResponse:
    """Get current tenant settings (clinic_owner only)."""
    result = await get_tenant_settings(
        tenant_id=current_user.tenant.tenant_id,
        db=db,
    )
    return TenantSettingsResponse(**result)


# ─── T-07: Update tenant settings ──────────────────


@router.put("", response_model=TenantSettingsResponse)
async def update_settings(
    body: TenantSettingsUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsResponse:
    """Update tenant settings (clinic_owner only)."""
    updates = body.model_dump(exclude_unset=True)
    result = await update_tenant_settings(
        tenant_id=current_user.tenant.tenant_id,
        updates=updates,
        db=db,
    )
    return TenantSettingsResponse(**result)


# ─── T-08: Plan usage stats ────────────────────────


@router.get("/usage", response_model=PlanUsageResponse)
async def get_usage(
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> PlanUsageResponse:
    """Get plan usage stats (clinic_owner only)."""
    result = await get_plan_usage(
        tenant_id=current_user.tenant.tenant_id,
        schema_name=current_user.tenant.schema_name,
        db=db,
    )
    return PlanUsageResponse(**result)


# ─── T-09: Plan limits check ───────────────────────


@router.get("/plan-limits", response_model=PlanLimitsResponse)
async def get_limits(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanLimitsResponse:
    """Get plan limits (any authenticated user)."""
    result = await get_plan_limits(
        tenant_id=current_user.tenant.tenant_id,
        db=db,
    )
    return PlanLimitsResponse(**result)
