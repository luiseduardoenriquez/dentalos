"""Admin/superadmin API routes — AD-01 through AD-07.

Endpoint map:
  POST /admin/auth/login              — AD-01: Admin login (rate limited)
  POST /admin/auth/totp/setup         — TOTP setup
  POST /admin/auth/totp/verify        — TOTP verify
  GET  /admin/tenants                 — AD-02: List tenants
  GET  /admin/plans                   — AD-03: List plans
  PUT  /admin/plans/{plan_id}         — AD-03: Update plan
  GET  /admin/analytics               — AD-04: Platform analytics
  GET  /admin/feature-flags           — AD-05: List feature flags
  POST /admin/feature-flags           — AD-05: Create feature flag
  PUT  /admin/feature-flags/{flag_id} — AD-05: Update feature flag
  GET  /admin/health                  — AD-06: System health check
  POST /admin/tenants/{tenant_id}/impersonate — AD-07: Impersonate tenant
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from jose import JWTError, jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db as get_public_db
from app.core.exceptions import AuthError
from app.core.security import _load_public_key
from app.models.public.superadmin import Superadmin
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminTOTPSetupResponse,
    AdminTOTPVerifyRequest,
    FeatureFlagCreateRequest,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
    ImpersonateResponse,
    PlanResponse,
    PlanUpdateRequest,
    PlatformAnalyticsResponse,
    SystemHealthResponse,
    TenantCreateRequest,
    TenantDetailResponse,
    TenantListResponse,
    TenantUpdateRequest,
)
from app.services.admin_auth_service import admin_auth_service
from app.services.admin_service import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Admin Auth Dependency ───────────────────────────────────────────────────


async def get_current_admin(
    authorization: str = Header(..., description="Bearer <admin_jwt>"),
    db: AsyncSession = Depends(get_public_db),
) -> Superadmin:
    """Extract and validate admin JWT, return the Superadmin model instance.

    Admin tokens use aud="dentalos-admin" and role="superadmin".
    """
    if not authorization.startswith("Bearer "):
        raise AuthError(
            error="AUTH_invalid_token",
            message="Invalid authorization header.",
        )

    token = authorization[7:]

    try:
        payload = jose_jwt.decode(
            token,
            _load_public_key(),
            algorithms=[settings.jwt_algorithm],
            audience="dentalos-admin",
            issuer=settings.jwt_issuer,
        )
    except JWTError:
        raise AuthError(
            error="AUTH_invalid_token",
            message="Invalid or expired admin token.",
        )

    if payload.get("role") != "superadmin":
        raise AuthError(
            error="AUTH_insufficient_role",
            message="Superadmin access required.",
            status_code=403,
        )

    # Extract admin_id from sub claim (format: "admin_{uuid}")
    sub: str = payload.get("sub", "")
    if not sub.startswith("admin_"):
        raise AuthError(
            error="AUTH_invalid_token",
            message="Invalid admin token subject.",
        )
    admin_id = sub.replace("admin_", "")

    result = await db.execute(
        select(Superadmin).where(
            Superadmin.id == uuid.UUID(admin_id),
            Superadmin.is_active.is_(True),
        )
    )
    admin = result.scalar_one_or_none()

    if admin is None:
        raise AuthError(
            error="AUTH_admin_not_found",
            message="Admin account not found or deactivated.",
            status_code=404,
        )

    return admin


# ─── AD-01: Admin Login ─────────────────────────────────────────────────────


@router.post("/auth/login", response_model=AdminLoginResponse)
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_public_db),
) -> AdminLoginResponse:
    """Authenticate a superadmin (email + password + optional TOTP)."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    result = await admin_auth_service.authenticate_admin(
        db=db,
        email=body.email,
        password=body.password,
        totp_code=body.totp_code,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()
    return result


# ─── TOTP Setup ─────────────────────────────────────────────────────────────


@router.post("/auth/totp/setup", response_model=AdminTOTPSetupResponse)
async def totp_setup(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AdminTOTPSetupResponse:
    """Generate a TOTP secret for the current admin."""
    result = await admin_auth_service.setup_totp(
        db=db,
        admin_id=admin.id,
    )
    await db.commit()
    return result


@router.post("/auth/totp/verify", status_code=200)
async def totp_verify(
    body: AdminTOTPVerifyRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict[str, str]:
    """Confirm TOTP setup by verifying a code."""
    await admin_auth_service.verify_totp_setup(
        db=db,
        admin_id=admin.id,
        totp_code=body.totp_code,
    )
    await db.commit()
    return {"status": "totp_enabled"}


# ─── AD-02: Tenant Management ───────────────────────────────────────────────


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantListResponse:
    """List tenants with optional search and status filter."""
    return await admin_service.list_tenants(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant_detail(
    tenant_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantDetailResponse:
    """Get full tenant detail by ID."""
    return await admin_service.get_tenant_detail(db=db, tenant_id=tenant_id)


@router.post(
    "/tenants",
    response_model=TenantDetailResponse,
    status_code=201,
)
async def create_tenant(
    body: TenantCreateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantDetailResponse:
    """Create a new tenant (clinic) with schema provisioning."""
    result = await admin_service.create_tenant(
        db=db,
        name=body.name,
        owner_email=body.owner_email,
        plan_id=body.plan_id,
        country_code=body.country_code,
        timezone=body.timezone,
        currency_code=body.currency_code,
    )
    await db.commit()
    return result


@router.put("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantDetailResponse:
    """Update a tenant's name, plan, settings, or status."""
    result = await admin_service.update_tenant(
        db=db,
        tenant_id=tenant_id,
        name=body.name,
        plan_id=body.plan_id,
        settings=body.settings,
        is_active=body.is_active,
    )
    await db.commit()
    return result


@router.post(
    "/tenants/{tenant_id}/suspend",
    response_model=TenantDetailResponse,
)
async def suspend_tenant(
    tenant_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantDetailResponse:
    """Toggle tenant suspension (idempotent)."""
    result = await admin_service.suspend_tenant(db=db, tenant_id=tenant_id)
    await db.commit()
    return result


# ─── AD-03: Plan Management ─────────────────────────────────────────────────


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> list[PlanResponse]:
    """List all subscription plans."""
    return await admin_service.list_plans(db=db)


@router.put("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    body: PlanUpdateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> PlanResponse:
    """Update a subscription plan."""
    result = await admin_service.update_plan(
        db=db,
        plan_id=plan_id,
        price_cents=body.price_cents,
        max_patients=body.max_patients,
        max_doctors=body.max_doctors,
        features=body.features,
        is_active=body.is_active,
    )
    await db.commit()
    return result


# ─── AD-04: Platform Analytics ───────────────────────────────────────────────


@router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def platform_analytics(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> PlatformAnalyticsResponse:
    """Platform-level analytics: tenants, users, MRR, MAU."""
    return await admin_service.get_platform_analytics(db=db)


# ─── AD-05: Feature Flags ───────────────────────────────────────────────────


@router.get("/feature-flags", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> list[FeatureFlagResponse]:
    """List all feature flags."""
    return await admin_service.list_feature_flags(db=db)


@router.post(
    "/feature-flags",
    response_model=FeatureFlagResponse,
    status_code=201,
)
async def create_feature_flag(
    body: FeatureFlagCreateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> FeatureFlagResponse:
    """Create a new feature flag."""
    result = await admin_service.create_feature_flag(
        db=db,
        flag_name=body.flag_name,
        enabled=body.enabled,
        scope=body.scope,
        plan_filter=body.plan_filter,
        tenant_id=body.tenant_id,
        description=body.description,
    )
    await db.commit()
    return result


@router.put("/feature-flags/{flag_id}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_id: str,
    body: FeatureFlagUpdateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> FeatureFlagResponse:
    """Update an existing feature flag."""
    result = await admin_service.update_feature_flag(
        db=db,
        flag_id=flag_id,
        enabled=body.enabled,
        scope=body.scope,
        plan_filter=body.plan_filter,
        tenant_id=body.tenant_id,
        description=body.description,
    )
    await db.commit()
    return result


# ─── AD-06: System Health ───────────────────────────────────────────────────


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SystemHealthResponse:
    """Check health of all platform dependencies."""
    return await admin_service.check_system_health(db=db)


# ─── AD-07: Tenant Impersonation ────────────────────────────────────────────


@router.post(
    "/tenants/{tenant_id}/impersonate",
    response_model=ImpersonateResponse,
)
async def impersonate_tenant(
    tenant_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ImpersonateResponse:
    """Generate a tenant-scoped JWT for support/debugging."""
    result = await admin_service.impersonate_tenant(
        db=db,
        admin_id=str(admin.id),
        tenant_id=tenant_id,
    )
    await db.commit()
    return result
