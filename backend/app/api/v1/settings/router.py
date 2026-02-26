"""Tenant settings routes (T-06 through T-09) and reminder config (AP-17, AP-18)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission, require_role
from app.core.audit import audit_action
from app.core.database import get_db, get_tenant_db
from app.schemas.reminder import ReminderConfigResponse, ReminderConfigUpdate
from app.schemas.tenant import (
    PlanLimitsResponse,
    PlanUsageResponse,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)
from app.services.reminder_service import reminder_service
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


# ─── Reminder Configuration Endpoints (AP-17, AP-18) ─────────────────────────
#
# Note: These endpoints use get_tenant_db (not get_db) because reminder_configs
# lives in the per-tenant schema, not in the public schema.


@router.get("/reminders", response_model=ReminderConfigResponse)
async def get_reminder_config(
    current_user: AuthenticatedUser = Depends(require_permission("reminders:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ReminderConfigResponse:
    """Return the tenant's appointment reminder configuration (AP-17).

    If no configuration has been saved yet, a default row is returned
    (24h SMS reminder, max 3 rules). The row is persisted on first PUT.
    """
    result = await reminder_service.get_config(db=db)
    return ReminderConfigResponse(**result)


@router.put("/reminders", response_model=ReminderConfigResponse)
async def update_reminder_config(
    body: ReminderConfigUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("reminders:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ReminderConfigResponse:
    """Update the tenant's appointment reminder configuration (AP-18).

    Replaces only the provided fields; omitted fields are left unchanged.
    The reminders list defines the dispatch schedule (e.g. 48h email + 24h SMS).
    """
    result = await reminder_service.update_config(
        db=db,
        reminders=[r.model_dump() for r in body.reminders] if body.reminders is not None else None,
        default_channels=body.default_channels,
        max_reminders_allowed=body.max_reminders_allowed,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="reminder_config",
        resource_id="tenant",
    )

    return ReminderConfigResponse(**result)
