"""Tenant context management for multi-tenant request isolation."""
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

_current_tenant: ContextVar["TenantContext | None"] = ContextVar(
    "current_tenant", default=None
)

SCHEMA_NAME_PATTERN = re.compile(r"^tn_[a-f0-9]{8,12}$")


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context for the current request."""

    tenant_id: str
    schema_name: str
    plan_id: str
    plan_name: str
    country_code: str
    timezone: str
    currency_code: str
    status: str
    features: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)


def validate_schema_name(schema_name: str) -> bool:
    """Validate that a schema name matches the expected pattern."""
    return bool(SCHEMA_NAME_PATTERN.match(schema_name))


def get_current_tenant() -> "TenantContext | None":
    """Get the current tenant context, or None if not set."""
    return _current_tenant.get()


def get_current_tenant_or_raise() -> "TenantContext":
    """Get the current tenant context, raising TenantError if not set."""
    tenant = _current_tenant.get()
    if tenant is None:
        from app.core.exceptions import TenantError

        raise TenantError(
            error="TENANT_not_resolved",
            message="Tenant context not established.",
            status_code=403,
        )
    return tenant


def set_current_tenant(tenant: "TenantContext") -> None:
    """Set the tenant context for the current request."""
    _current_tenant.set(tenant)


def clear_current_tenant() -> None:
    """Clear the tenant context."""
    _current_tenant.set(None)
