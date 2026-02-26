"""FastAPI dependency injection for compliance adapters (ADR-007).

Resolves the correct ComplianceAdapter from the current tenant's country_code.
Chain: get_current_user -> resolve_tenant -> get_compliance -> adapter.
"""

from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.auth.context import AuthenticatedUser
from app.compliance.base import ComplianceAdapter
from app.compliance.registry import get_compliance_adapter
from app.core.exceptions import ComplianceError
from app.core.tenant import TenantContext


async def resolve_tenant(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TenantContext:
    """Extract the TenantContext from the authenticated user.

    This dependency ensures authentication has occurred and the tenant
    context is available before compliance resolution.
    """
    return current_user.tenant


async def get_compliance(
    tenant: TenantContext = Depends(resolve_tenant),
) -> ComplianceAdapter:
    """Resolve the compliance adapter for the current tenant's country.

    Injected into route handlers that perform country-specific operations.
    """
    return get_compliance_adapter(tenant.country_code)


async def require_colombia(
    adapter: ComplianceAdapter = Depends(get_compliance),
) -> ComplianceAdapter:
    """Gate access to Colombia-only features.

    Raises ComplianceError if the tenant's country is not Colombia.
    Used for endpoints that are exclusively for Colombian regulatory
    requirements (RIPS export, RDA dashboard, DIAN e-invoicing).
    """
    if adapter.country_code != "CO":
        raise ComplianceError(
            error="COMPLIANCE_country_required",
            message="This feature requires a Colombia tenant.",
            status_code=403,
        )
    return adapter
