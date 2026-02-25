"""Service catalog (price list) API routes — B-14, B-15.

Endpoint map:
  GET /services              — B-14: List service catalog entries (cursor-paginated)
  PUT /services/{service_id} — B-15: Update a service catalog entry

The service catalog is the tenant's price list: a mapping of CUPS codes to
clinic-specific names, prices, and categories. Built-in entries are seeded
from the CUPS catalog at tenant creation; clinics can override names and
prices but cannot change the underlying CUPS code.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.service_catalog import (
    ServiceCatalogListResponse,
    ServiceCatalogResponse,
    ServiceCatalogUpdate,
)
from app.services.service_catalog_service import service_catalog_service

router = APIRouter(prefix="/services", tags=["service-catalog"])


# ─── B-14: List services ──────────────────────────────────────────────────────


@router.get("/", response_model=ServiceCatalogListResponse)
async def list_services(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> ServiceCatalogListResponse:
    """Return a cursor-paginated list of service catalog entries.

    Optionally filtered by category and/or a name/code search query.
    Results are ordered by category then name. No audit event is emitted
    (read-only).
    """
    result = await service_catalog_service.list_services(
        db=db,
        cursor=cursor,
        limit=limit,
        category=category,
        search=search,
    )
    return ServiceCatalogListResponse(**result)


# ─── B-15: Update service ─────────────────────────────────────────────────────


@router.put("/{service_id}", response_model=ServiceCatalogResponse)
async def update_service(
    service_id: str,
    body: ServiceCatalogUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("billing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ServiceCatalogResponse:
    """Update a service catalog entry for the current tenant.

    Only name, default_price, category, and is_active are editable.
    The underlying CUPS code is immutable after seeding. Returns 404 if
    the service does not exist in the tenant's catalog. Emits an update
    audit event on success.
    """
    result = await service_catalog_service.update_service(
        db=db,
        service_id=service_id,
        name=body.name,
        default_price=body.default_price,
        category=body.category,
        is_active=body.is_active,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="BILLING_service_not_found",
            resource_name="ServiceCatalog",
        )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="service_catalog",
        resource_id=service_id,
    )

    return ServiceCatalogResponse(**result)
