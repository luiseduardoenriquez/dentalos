"""Tenant settings routes (T-06 through T-09) and reminder config (AP-17, AP-18)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission, require_role
from app.core.audit import audit_action
from app.core.database import get_db, get_tenant_db
from app.schemas.odontogram_settings import OdontogramSettingsResponse, OdontogramSettingsUpdate
from app.schemas.reminder import ReminderConfigResponse, ReminderConfigUpdate
from app.schemas.tenant import (
    AddonToggleRequest,
    AddonsResponse,
    AvailablePlansResponse,
    ChangePlanRequest,
    ChangePlanResponse,
    PlanLimitsResponse,
    PlanUsageResponse,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)
from app.services.odontogram_settings_service import get_odontogram_settings, update_odontogram_settings
from app.services.reminder_service import reminder_service
from app.services.tenant_settings_service import (
    change_plan,
    get_addons,
    get_plan_limits,
    get_plan_usage,
    get_tenant_settings,
    list_available_plans,
    toggle_addon,
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


# ─── Plan Upgrade Endpoints ───────────────────────────────────────────────────


@router.get("/available-plans", response_model=AvailablePlansResponse)
async def get_available_plans(
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> AvailablePlansResponse:
    """List all available plans for upgrade (clinic_owner only)."""
    result = await list_available_plans(
        tenant_id=current_user.tenant.tenant_id,
        db=db,
    )
    return AvailablePlansResponse(**result)


@router.post("/change-plan", response_model=ChangePlanResponse)
async def change_plan_endpoint(
    body: ChangePlanRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> ChangePlanResponse:
    """Change the tenant's subscription plan (clinic_owner only)."""
    result = await change_plan(
        tenant_id=current_user.tenant.tenant_id,
        schema_name=current_user.tenant.schema_name,
        plan_id=body.plan_id,
        db=db,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="change_plan",
        resource_type="plan",
        resource_id=body.plan_id,
    )

    return ChangePlanResponse(**result)


# ─── Add-on Endpoints ─────────────────────────────────────────────────────────


@router.get("/addons", response_model=AddonsResponse)
async def get_addons_endpoint(
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> AddonsResponse:
    """Get current add-on state for the tenant (clinic_owner only)."""
    result = await get_addons(
        tenant_id=current_user.tenant.tenant_id,
        db=db,
    )
    return AddonsResponse(**result)


@router.put("/addons", response_model=AddonsResponse)
async def toggle_addon_endpoint(
    body: AddonToggleRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> AddonsResponse:
    """Toggle an add-on feature for the tenant (clinic_owner only)."""
    result = await toggle_addon(
        tenant_id=current_user.tenant.tenant_id,
        addon=body.addon,
        enabled=body.enabled,
        db=db,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="toggle_addon",
        resource_type="addon",
        resource_id=body.addon,
    )

    return AddonsResponse(**result)


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


# ─── Odontogram Configuration Endpoints (FE-S-04) ───────────────────────────


@router.get("/odontogram", response_model=OdontogramSettingsResponse)
async def get_odontogram_config(
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> OdontogramSettingsResponse:
    """Return the tenant's odontogram display configuration.

    If no configuration has been saved, returns sensible defaults
    (classic grid view, full dentition zoom, auto-save disabled).
    Reads from the public.tenants settings JSONB column.
    """
    result = await get_odontogram_settings(
        tenant_id=current_user.tenant.tenant_id,
        db=db,
    )
    return OdontogramSettingsResponse(**result)


@router.put("/odontogram", response_model=OdontogramSettingsResponse)
async def update_odontogram_config(
    body: OdontogramSettingsUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_db),
) -> OdontogramSettingsResponse:
    """Update the tenant's odontogram display configuration.

    Persists to the public.tenants settings JSONB column under the
    "odontogram" key.
    """
    result = await update_odontogram_settings(
        tenant_id=current_user.tenant.tenant_id,
        db=db,
        updates=body.model_dump(exclude_unset=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="odontogram_settings",
        resource_id="tenant",
    )

    return OdontogramSettingsResponse(**result)
