"""Tenant settings service — settings CRUD, plan usage, and onboarding.

Business logic for tenant self-management (clinic_owner) and plan limit checks.
All functions receive an explicit db session — no global state.
"""
import logging
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, get_cached, set_cached
from app.core.exceptions import (
    ResourceNotFoundError,
    TenantError,
)
from app.models.public.plan import Plan
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership
from app.services.tenant_service import invalidate_tenant_cache

logger = logging.getLogger("dentalos.tenant_settings")


async def get_tenant_settings(
    tenant_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Load tenant from DB and return settings + clinic info.

    Returns a dict suitable for TenantSettingsResponse.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)

    return {
        "name": tenant.name,
        "phone": tenant.phone,
        "address": tenant.address,
        "logo_url": tenant.logo_url,
        "timezone": tenant.timezone,
        "currency_code": tenant.currency_code,
        "country_code": tenant.country_code,
        "locale": tenant.locale,
        "settings": tenant.settings or {},
    }


async def update_tenant_settings(
    tenant_id: str,
    updates: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Update tenant metadata and settings JSONB, then invalidate cache.

    `updates` is a dict of field_name -> new_value. Only non-None values
    are applied. The special key "settings" is deep-merged into existing JSONB.

    Returns the updated settings dict.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)

    # Apply scalar field updates
    scalar_fields = {
        "name", "phone", "address", "logo_url",
        "timezone", "currency_code", "locale",
    }
    for field_name in scalar_fields:
        value = updates.get(field_name)
        if value is not None:
            setattr(tenant, field_name, value)

    # Merge settings JSONB (shallow merge at top level)
    new_settings = updates.get("settings")
    if new_settings and isinstance(new_settings, dict):
        merged = {**(tenant.settings or {}), **new_settings}
        tenant.settings = merged

    await db.flush()
    await invalidate_tenant_cache(tenant_id)

    return {
        "name": tenant.name,
        "phone": tenant.phone,
        "address": tenant.address,
        "logo_url": tenant.logo_url,
        "timezone": tenant.timezone,
        "currency_code": tenant.currency_code,
        "country_code": tenant.country_code,
        "locale": tenant.locale,
        "settings": tenant.settings or {},
    }


async def get_plan_usage(
    tenant_id: str,
    schema_name: str,
    db: AsyncSession,
) -> dict[str, int]:
    """Count current patients, doctors, users in tenant schema, compare to plan.

    Returns a dict suitable for PlanUsageResponse.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)
    plan = tenant.plan

    if not plan:
        raise TenantError(
            error="TENANT_no_plan",
            message="Tenant has no assigned plan.",
            status_code=500,
        )

    # Count active users and doctors in the tenant schema
    user_count_result = await db.execute(
        text(
            f"SELECT "
            f"  COUNT(*) FILTER (WHERE is_active = true) AS total_users, "
            f"  COUNT(*) FILTER (WHERE is_active = true AND role = 'doctor') AS total_doctors "
            f"FROM {schema_name}.users"
        )
    )
    row = user_count_result.one()
    current_users = row.total_users
    current_doctors = row.total_doctors

    # Count patients (if the patients table exists in the tenant schema)
    current_patients = 0
    try:
        patient_count_result = await db.execute(
            text(
                f"SELECT COUNT(*) AS cnt "
                f"FROM {schema_name}.patients "
                f"WHERE is_active = true"
            )
        )
        current_patients = patient_count_result.scalar_one()
    except Exception:
        # Patients table may not exist yet (early onboarding)
        logger.debug("patients table not found in %s, defaulting to 0", schema_name)

    # Storage usage is a placeholder — real implementation would query S3/object storage
    current_storage_mb = 0

    return {
        "current_patients": current_patients,
        "max_patients": plan.max_patients,
        "current_doctors": current_doctors,
        "max_doctors": plan.max_doctors,
        "current_users": current_users,
        "max_users": plan.max_users,
        "current_storage_mb": current_storage_mb,
        "max_storage_mb": plan.max_storage_mb,
    }


async def get_plan_limits(
    tenant_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Return plan limits and features for the current tenant.

    Uses Redis cache with 10min TTL. Returns a dict suitable for
    PlanLimitsResponse.
    """
    cache_key = f"dentalos:{tenant_id}:config:plan_limits"

    # Check Redis cache first
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    tenant = await _get_tenant_or_raise(tenant_id, db)
    plan = tenant.plan

    if not plan:
        raise TenantError(
            error="TENANT_no_plan",
            message="Tenant has no assigned plan.",
            status_code=500,
        )

    result = {
        "plan_name": plan.name,
        "plan_price_monthly_cents": plan.price_cents,
        "max_patients": plan.max_patients,
        "max_doctors": plan.max_doctors,
        "max_users": plan.max_users,
        "max_storage_mb": plan.max_storage_mb,
        "features": plan.features or {},
    }

    # Cache for 10 minutes
    await set_cached(cache_key, result, ttl_seconds=600)

    return result


async def process_onboarding_step(
    tenant_id: str,
    step: int,
    data: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Process a single onboarding wizard step.

    Updates tenant.onboarding_step and merges step data into
    tenant.settings under the key "onboarding_{step}".

    Returns a dict suitable for OnboardingStepResponse.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)

    max_step = 4

    # Validate step ordering (allow re-submitting current or previous steps)
    if step > tenant.onboarding_step + 1:
        raise TenantError(
            error="TENANT_onboarding_step_invalid",
            message=f"Cannot skip to step {step}. Current step is {tenant.onboarding_step}.",
            status_code=400,
        )

    # Merge step data into settings
    current_settings = dict(tenant.settings or {})
    current_settings[f"onboarding_{step}"] = data
    tenant.settings = current_settings

    # Advance the step counter (only forward)
    if step >= tenant.onboarding_step:
        tenant.onboarding_step = step + 1

    # Mark tenant as active when onboarding completes
    completed = tenant.onboarding_step > max_step
    if completed and tenant.status == "pending":
        tenant.status = "active"

    await db.flush()
    await invalidate_tenant_cache(tenant_id)

    return {
        "current_step": tenant.onboarding_step,
        "completed": completed,
        "message": "Onboarding complete!" if completed else f"Step {step} saved.",
    }


# ─── Add-ons ──────────────────────────────────────


async def get_addons(
    tenant_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Return the current add-on state for a tenant."""
    tenant = await _get_tenant_or_raise(tenant_id, db)
    return {"addons": tenant.addons or {}}


async def toggle_addon(
    tenant_id: str,
    addon: str,
    enabled: bool,
    db: AsyncSession,
) -> dict[str, Any]:
    """Toggle an add-on feature for a tenant.

    Free-plan tenants cannot activate add-ons.
    Invalidates the tenant cache so feature_flags update immediately.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)

    # Free plan cannot activate add-ons
    plan = tenant.plan
    if plan and plan.slug == "free" and enabled:
        raise TenantError(
            error="TENANT_addon_requires_paid_plan",
            message="Los complementos requieren un plan de pago.",
            status_code=403,
        )

    current_addons = dict(tenant.addons or {})
    current_addons[addon] = enabled
    tenant.addons = current_addons

    await db.flush()
    await invalidate_tenant_cache(tenant_id)

    return {"addons": tenant.addons}


# ─── Admin: Tenant CRUD ────────────────────────────


async def admin_create_tenant(
    name: str,
    owner_email: str,
    country_code: str,
    plan_id: str,
    phone: str | None,
    db: AsyncSession,
) -> Tenant:
    """Create a new tenant record and provision its schema.

    Called by superadmin. Does NOT create the owner user account —
    that happens when the owner registers or is invited.
    """
    from app.services.tenant_service import (
        generate_schema_name,
        generate_slug,
        provision_tenant_schema,
    )

    # Validate plan exists
    plan_stmt = select(Plan).where(
        Plan.id == uuid.UUID(plan_id),
        Plan.is_active.is_(True),
    )
    plan_result = await db.execute(plan_stmt)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise ResourceNotFoundError(error="TENANT_plan_not_found", resource_name="Plan")

    # Generate unique identifiers
    slug = generate_slug(name)
    schema_name = generate_schema_name()

    # Create tenant record
    tenant = Tenant(
        slug=slug,
        schema_name=schema_name,
        name=name,
        country_code=country_code,
        owner_email=owner_email,
        phone=phone,
        plan_id=uuid.UUID(plan_id),
        status="pending",
    )
    db.add(tenant)
    await db.flush()  # Get the ID before provisioning

    # Provision the tenant schema (creates DB schema + runs migrations)
    await provision_tenant_schema(schema_name, db)

    logger.info("Admin created tenant: %s (schema: %s)", slug, schema_name)
    return tenant


async def admin_get_tenant(
    tenant_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get full tenant details including plan and member count.

    Returns a dict suitable for TenantDetailResponse.
    """
    stmt = (
        select(Tenant)
        .where(Tenant.id == uuid.UUID(tenant_id))
        .where(Tenant.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise ResourceNotFoundError(error="TENANT_not_found", resource_name="Tenant")

    # Count active members
    member_count = await _count_members(tenant.id, db)

    plan = tenant.plan
    plan_data = {
        "id": str(plan.id),
        "name": plan.name,
        "slug": plan.slug,
        "max_patients": plan.max_patients,
        "max_doctors": plan.max_doctors,
        "max_users": plan.max_users,
        "max_storage_mb": plan.max_storage_mb,
        "features": plan.features or {},
        "price_cents": plan.price_cents,
        "currency": plan.currency,
    }

    return {
        "id": str(tenant.id),
        "slug": tenant.slug,
        "schema_name": tenant.schema_name,
        "name": tenant.name,
        "country_code": tenant.country_code,
        "timezone": tenant.timezone,
        "currency_code": tenant.currency_code,
        "locale": tenant.locale,
        "owner_email": tenant.owner_email,
        "owner_user_id": str(tenant.owner_user_id) if tenant.owner_user_id else None,
        "phone": tenant.phone,
        "address": tenant.address,
        "logo_url": tenant.logo_url,
        "status": tenant.status,
        "onboarding_step": tenant.onboarding_step,
        "settings": tenant.settings or {},
        "plan": plan_data,
        "member_count": member_count,
        "trial_ends_at": tenant.trial_ends_at,
        "suspended_at": tenant.suspended_at,
        "cancelled_at": tenant.cancelled_at,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
    }


async def admin_list_tenants(
    page: int,
    page_size: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """List all tenants with pagination (superadmin).

    Returns a dict suitable for TenantListResponse.
    """
    # Count total
    count_stmt = (
        select(func.count())
        .select_from(Tenant)
        .where(Tenant.deleted_at.is_(None))
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    stmt = (
        select(Tenant)
        .where(Tenant.deleted_at.is_(None))
        .order_by(Tenant.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    items = []
    for tenant in tenants:
        member_count = await _count_members(tenant.id, db)
        plan_name = tenant.plan.name if tenant.plan else "unknown"
        items.append({
            "id": str(tenant.id),
            "slug": tenant.slug,
            "name": tenant.name,
            "country_code": tenant.country_code,
            "status": tenant.status,
            "plan_name": plan_name,
            "owner_email": tenant.owner_email,
            "member_count": member_count,
            "created_at": tenant.created_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def admin_update_tenant(
    tenant_id: str,
    updates: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Update tenant metadata (superadmin).

    Returns the updated tenant detail dict.
    """
    stmt = (
        select(Tenant)
        .where(Tenant.id == uuid.UUID(tenant_id))
        .where(Tenant.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise ResourceNotFoundError(error="TENANT_not_found", resource_name="Tenant")

    # Apply scalar field updates
    allowed_fields = {
        "name", "country_code", "timezone", "currency_code",
        "phone", "address", "logo_url",
    }
    for field_name in allowed_fields:
        value = updates.get(field_name)
        if value is not None:
            setattr(tenant, field_name, value)

    # Handle plan change
    new_plan_id = updates.get("plan_id")
    if new_plan_id is not None:
        plan_stmt = select(Plan).where(
            Plan.id == uuid.UUID(new_plan_id),
            Plan.is_active.is_(True),
        )
        plan_result = await db.execute(plan_stmt)
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ResourceNotFoundError(
                error="TENANT_plan_not_found", resource_name="Plan"
            )
        tenant.plan_id = uuid.UUID(new_plan_id)

    await db.flush()
    await invalidate_tenant_cache(tenant_id)

    # Invalidate plan limits cache on any tenant update (plan may have changed)
    await cache_delete(f"dentalos:{tenant_id}:config:plan_limits")

    return await admin_get_tenant(tenant_id, db)


async def admin_suspend_tenant(
    tenant_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Suspend a tenant (superadmin).

    Sets status to 'suspended' and records suspended_at timestamp.
    Returns the updated tenant detail dict.
    """
    from datetime import UTC, datetime

    stmt = (
        select(Tenant)
        .where(Tenant.id == uuid.UUID(tenant_id))
        .where(Tenant.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise ResourceNotFoundError(error="TENANT_not_found", resource_name="Tenant")

    if tenant.status == "suspended":
        raise TenantError(
            error="TENANT_already_suspended",
            message="Tenant is already suspended.",
            status_code=409,
        )

    tenant.status = "suspended"
    tenant.suspended_at = datetime.now(UTC)

    await db.flush()
    await invalidate_tenant_cache(tenant_id)

    logger.info("Admin suspended tenant: %s", tenant.slug)
    return await admin_get_tenant(tenant_id, db)


# ─── Helpers ────────────────────────────────────────


async def _get_tenant_or_raise(
    tenant_id: str,
    db: AsyncSession,
) -> Tenant:
    """Load a tenant by ID or raise 404."""
    stmt = (
        select(Tenant)
        .where(Tenant.id == uuid.UUID(tenant_id))
        .where(Tenant.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise ResourceNotFoundError(error="TENANT_not_found", resource_name="Tenant")

    return tenant


async def _count_members(
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Count active memberships for a tenant."""
    stmt = (
        select(func.count())
        .select_from(UserTenantMembership)
        .where(
            UserTenantMembership.tenant_id == tenant_id,
            UserTenantMembership.status == "active",
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()
