"""Superadmin tenant management routes (T-01 through T-05)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_role
from app.core.database import get_db
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantDetailResponse,
    TenantListResponse,
    TenantUpdateRequest,
)
from app.services.tenant_settings_service import (
    admin_create_tenant,
    admin_get_tenant,
    admin_list_tenants,
    admin_suspend_tenant,
    admin_update_tenant,
)

router = APIRouter(prefix="/admin/tenants", tags=["admin-tenants"])


# ─── T-01: Create tenant ───────────────────────────


@router.post("", status_code=201, response_model=TenantDetailResponse)
async def create_tenant(
    body: TenantCreateRequest,
    current_user: AuthenticatedUser = Depends(require_role(["superadmin"])),
    db: AsyncSession = Depends(get_db),
) -> TenantDetailResponse:
    """Create and provision a new tenant (superadmin only)."""
    tenant = await admin_create_tenant(
        name=body.name,
        owner_email=body.owner_email,
        country_code=body.country_code,
        plan_id=body.plan_id,
        phone=body.phone,
        db=db,
    )
    detail = await admin_get_tenant(str(tenant.id), db)
    return TenantDetailResponse(**detail)


# ─── T-02: Get tenant detail ───────────────────────


@router.get("/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["superadmin"])),
    db: AsyncSession = Depends(get_db),
) -> TenantDetailResponse:
    """Get full tenant details (superadmin only)."""
    detail = await admin_get_tenant(tenant_id, db)
    return TenantDetailResponse(**detail)


# ─── T-03: List tenants ────────────────────────────


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    current_user: AuthenticatedUser = Depends(require_role(["superadmin"])),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> TenantListResponse:
    """List all tenants with pagination (superadmin only)."""
    result = await admin_list_tenants(page=page, page_size=page_size, db=db)
    return TenantListResponse(**result)


# ─── T-04: Update tenant ───────────────────────────


@router.put("/{tenant_id}", response_model=TenantDetailResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_role(["superadmin"])),
    db: AsyncSession = Depends(get_db),
) -> TenantDetailResponse:
    """Update tenant metadata (superadmin only)."""
    updates = body.model_dump(exclude_unset=True)
    detail = await admin_update_tenant(tenant_id=tenant_id, updates=updates, db=db)
    return TenantDetailResponse(**detail)


# ─── T-05: Suspend tenant ──────────────────────────


@router.post("/{tenant_id}/suspend", response_model=TenantDetailResponse)
async def suspend_tenant(
    tenant_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["superadmin"])),
    db: AsyncSession = Depends(get_db),
) -> TenantDetailResponse:
    """Suspend a tenant (superadmin only)."""
    detail = await admin_suspend_tenant(tenant_id=tenant_id, db=db)
    return TenantDetailResponse(**detail)
