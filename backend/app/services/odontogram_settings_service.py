"""Odontogram settings service — tenant-scoped display preferences.

Persists odontogram display configuration to the Tenant.settings JSONB
column under the key "odontogram". Uses the same pattern as
tenant_settings_service for reading/writing the public.tenants row.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.public.tenant import Tenant

logger = logging.getLogger("dentalos.odontogram_settings")

# Default settings for new tenants
_DEFAULTS: dict[str, Any] = {
    "default_view": "classic",
    "default_zoom": "full",
    "auto_save_dictation": False,
    "condition_colors": {},
}

_SETTINGS_KEY = "odontogram"


async def _get_tenant_or_raise(tenant_id: str, db: AsyncSession) -> Tenant:
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


async def get_odontogram_settings(
    *,
    tenant_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get odontogram settings for the current tenant.

    Reads the "odontogram" key from the Tenant.settings JSONB column.
    Missing keys are filled from defaults.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)

    stored = (tenant.settings or {}).get(_SETTINGS_KEY, {})

    # Merge defaults with stored values (stored takes precedence)
    return {**_DEFAULTS, **stored}


async def update_odontogram_settings(
    *,
    tenant_id: str,
    db: AsyncSession,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update odontogram settings for the current tenant.

    Shallow-merges updates into the "odontogram" key of the
    Tenant.settings JSONB column and flushes to DB.
    """
    tenant = await _get_tenant_or_raise(tenant_id, db)

    # Read existing odontogram settings
    all_settings = dict(tenant.settings or {})
    current_odo = dict(all_settings.get(_SETTINGS_KEY, {}))

    # Merge only known keys with non-None values
    for key, value in updates.items():
        if value is not None and key in _DEFAULTS:
            current_odo[key] = value

    # Write back into the tenant settings JSONB
    all_settings[_SETTINGS_KEY] = current_odo
    tenant.settings = all_settings

    await db.flush()

    logger.info(
        "Odontogram settings updated: tenant=%s view=%s zoom=%s",
        tenant_id[:8],
        current_odo.get("default_view"),
        current_odo.get("default_zoom"),
    )

    return {**_DEFAULTS, **current_odo}
