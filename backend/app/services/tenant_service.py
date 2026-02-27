"""Tenant service — lookup, provisioning, and cache management."""
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import asdict

from slugify import slugify
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, get_cached, set_cached
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError, TenantError
from app.core.tenant import TenantContext, validate_schema_name
from app.models.public.tenant import Tenant

logger = logging.getLogger("dentalos.tenant")

TENANT_CACHE_TTL = 300  # 5 minutes
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _cache_key(tenant_id: str) -> str:
    """Build Redis cache key for tenant metadata."""
    short_id = str(tenant_id).replace("-", "")[:12]
    return f"dentalos:{short_id}:config:tenant_meta"


async def get_tenant_with_plan(tenant_id: str, db: AsyncSession) -> TenantContext:
    """Resolve a tenant by ID — Redis cache first, DB fallback.

    Returns a TenantContext with plan features and limits.
    """
    cache_key = _cache_key(tenant_id)

    # Try Redis cache
    cached = await get_cached(cache_key)
    if cached:
        return TenantContext(**cached)

    # DB fallback
    stmt = (
        select(Tenant)
        .where(Tenant.id == uuid.UUID(tenant_id))
        .where(Tenant.status.in_(["active", "suspended"]))
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise ResourceNotFoundError(error="TENANT_not_found", resource_name="Tenant")

    plan = tenant.plan  # Eagerly loaded via relationship

    ctx = TenantContext(
        tenant_id=str(tenant.id),
        schema_name=tenant.schema_name,
        plan_id=str(tenant.plan_id),
        plan_name=plan.name if plan else "unknown",
        country_code=tenant.country_code,
        timezone=tenant.timezone,
        currency_code=tenant.currency_code,
        status=tenant.status,
        features={**(plan.features if plan else {}), **(tenant.addons or {})},
        limits={
            "max_patients": plan.max_patients if plan else 0,
            "max_doctors": plan.max_doctors if plan else 0,
            "max_users": plan.max_users if plan else 0,
            "max_storage_mb": plan.max_storage_mb if plan else 0,
        },
    )

    # Cache in Redis
    await set_cached(cache_key, asdict(ctx), TENANT_CACHE_TTL)

    return ctx


async def invalidate_tenant_cache(tenant_id: str) -> None:
    """Invalidate the cached tenant context."""
    await cache_delete(_cache_key(tenant_id))


def generate_schema_name() -> str:
    """Generate a unique tenant schema name: tn_{8 hex chars}."""
    return f"{settings.tenant_schema_prefix}{uuid.uuid4().hex[:8]}"


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a clinic name."""
    base = slugify(name, max_length=80)
    if not base:
        base = "clinic"
    suffix = uuid.uuid4().hex[:4]
    return f"{base}-{suffix}"


async def provision_tenant_schema(schema_name: str, db: AsyncSession) -> None:
    """Create a new tenant schema and run initial migrations.

    Creates the PostgreSQL schema and runs Alembic tenant migrations.
    If migrations fail, the schema is dropped for cleanup.
    """
    if not validate_schema_name(schema_name):
        raise TenantError(
            error="TENANT_invalid_schema",
            message=f"Invalid schema name: {schema_name}",
            status_code=400,
        )

    # Create the schema
    await db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await db.commit()

    # Run tenant migrations
    result = subprocess.run(  # noqa: S603, ASYNC221
        [
            sys.executable, "-m", "alembic",
            "-c", "alembic_tenant/alembic.ini",
            "upgrade", "head",
            "-x", f"schema={schema_name}",
        ],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
    )

    if result.returncode != 0:
        logger.error(
            "Failed to run tenant migrations for %s: %s",
            schema_name, result.stderr,
        )
        # Cleanup: drop the schema
        await db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await db.commit()
        raise TenantError(
            error="TENANT_provision_failed",
            message="Failed to provision tenant schema.",
            status_code=500,
        )

    logger.info("Provisioned tenant schema: %s", schema_name)
