"""Admin/superadmin API routes — AD-01 through AD-07.

Endpoint map:
  POST /admin/auth/login              — AD-01: Admin login (rate limited)
  POST /admin/auth/totp/setup         — TOTP setup
  POST /admin/auth/totp/verify        — TOTP verify
  GET  /admin/tenants                 — AD-02: List tenants (with filters)
  GET  /admin/tenants/{tenant_id}     — AD-02: Tenant detail
  POST /admin/tenants                 — AD-02: Create tenant
  PUT  /admin/tenants/{tenant_id}     — AD-02: Update tenant
  POST /admin/tenants/{tenant_id}/suspend — AD-02: Toggle suspension
  GET  /admin/plans                   — AD-03: List plans
  PUT  /admin/plans/{plan_id}         — AD-03: Update plan
  GET  /admin/plans/{plan_id}/history — AD-03: Plan change history
  GET  /admin/analytics               — AD-04: Platform analytics
  GET  /admin/feature-flags           — AD-05: List feature flags
  POST /admin/feature-flags           — AD-05: Create feature flag
  PUT  /admin/feature-flags/{flag_id} — AD-05: Update feature flag
  GET  /admin/feature-flags/{flag_id}/history — AD-05: Flag change history
  GET  /admin/health                  — AD-06: System health check
  POST /admin/tenants/{tenant_id}/impersonate — AD-07: Impersonate tenant
  GET  /admin/audit-log               — Audit log
  GET  /admin/export                  — CSV export
  GET  /admin/superadmins             — Superadmin list
  POST /admin/superadmins             — Create superadmin
  PUT  /admin/superadmins/{admin_id}  — Update superadmin
  DELETE /admin/superadmins/{admin_id} — Deactivate superadmin
"""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
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
    AdminNotificationListResponse,
    AdminTOTPSetupResponse,
    AdminTOTPVerifyRequest,
    AuditLogListResponse,
    FeatureFlagCreateRequest,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
    FlagChangeHistoryEntry,
    ImpersonateRequest,
    ImpersonateResponse,
    PlanChangeHistoryResponse,
    PlanResponse,
    PlanUpdateRequest,
    PlatformAnalyticsResponse,
    SuperadminCreateRequest,
    SuperadminResponse,
    SuperadminUpdateRequest,
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
    """Extract and validate admin JWT, return the Superadmin model instance."""
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


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _get_client_info(request: Request) -> tuple[str, str | None]:
    """Extract IP address and user-agent from request."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent")
    return ip, ua


# ─── AD-01: Admin Login ─────────────────────────────────────────────────────


@router.post("/auth/login", response_model=AdminLoginResponse)
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_public_db),
) -> AdminLoginResponse:
    """Authenticate a superadmin (email + password + optional TOTP)."""
    ip_address, user_agent = _get_client_info(request)

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
    plan_id: str | None = Query(default=None),
    country_code: str | None = Query(default=None),
    created_after: str | None = Query(default=None),
    created_before: str | None = Query(default=None),
    sort_by: str = Query(default="created_at", pattern="^(name|created_at|status)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantListResponse:
    """List tenants with optional search, status, plan, country, date filters."""
    return await admin_service.list_tenants(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        plan_id=plan_id,
        country_code=country_code,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        sort_order=sort_order,
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
    request: Request,
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
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="create_tenant",
        resource_type="tenant",
        resource_id=result.id,
        details={"name": body.name, "owner_email": body.owner_email},
        ip_address=ip,
        user_agent=ua,
    )
    await admin_service.create_admin_notification(
        db=db,
        title="Nueva clinica registrada",
        message=f"La clinica {body.name} ({body.owner_email}) fue creada exitosamente.",
        notification_type="success",
        resource_type="tenant",
        resource_id=uuid.UUID(result.id),
    )
    await db.commit()
    return result


@router.put("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    request: Request,
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
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="update_tenant",
        resource_type="tenant",
        resource_id=tenant_id,
        details=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.post(
    "/tenants/{tenant_id}/suspend",
    response_model=TenantDetailResponse,
)
async def suspend_tenant(
    tenant_id: str,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantDetailResponse:
    """Toggle tenant suspension (idempotent)."""
    result = await admin_service.suspend_tenant(db=db, tenant_id=tenant_id)
    ip, ua = _get_client_info(request)
    action = "unsuspend_tenant" if result.status == "active" else "suspend_tenant"
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action=action,
        resource_type="tenant",
        resource_id=tenant_id,
        ip_address=ip,
        user_agent=ua,
    )
    if result.status == "suspended":
        await admin_service.create_admin_notification(
            db=db,
            title="Clinica suspendida",
            message=f"La clinica {result.name} fue suspendida.",
            notification_type="warning",
            resource_type="tenant",
            resource_id=uuid.UUID(result.id),
        )
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
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> PlanResponse:
    """Update a subscription plan (changes are tracked)."""
    result = await admin_service.update_plan(
        db=db,
        plan_id=plan_id,
        admin_id=str(admin.id),
        price_cents=body.price_cents,
        max_patients=body.max_patients,
        max_doctors=body.max_doctors,
        features=body.features,
        is_active=body.is_active,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="update_plan",
        resource_type="plan",
        resource_id=plan_id,
        details=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.get("/plans/{plan_id}/history", response_model=PlanChangeHistoryResponse)
async def plan_change_history(
    plan_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> PlanChangeHistoryResponse:
    """Get change history for a plan."""
    return await admin_service.get_plan_change_history(db=db, plan_id=plan_id)


# ─── AD-04: Platform Analytics ───────────────────────────────────────────────


@router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def platform_analytics(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> PlatformAnalyticsResponse:
    """Platform-level analytics: tenants, users, MRR, MAU, churn, distributions."""
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
    request: Request,
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
        expires_at=body.expires_at,
        reason=body.reason,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="create_flag",
        resource_type="feature_flag",
        resource_id=result.id,
        details={"flag_name": body.flag_name, "enabled": body.enabled},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.put("/feature-flags/{flag_id}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_id: str,
    body: FeatureFlagUpdateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> FeatureFlagResponse:
    """Update an existing feature flag (changes are tracked)."""
    result = await admin_service.update_feature_flag(
        db=db,
        flag_id=flag_id,
        admin_id=str(admin.id),
        enabled=body.enabled,
        scope=body.scope,
        plan_filter=body.plan_filter,
        tenant_id=body.tenant_id,
        description=body.description,
        expires_at=body.expires_at,
        reason=body.reason,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="update_flag",
        resource_type="feature_flag",
        resource_id=flag_id,
        details=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.get(
    "/feature-flags/{flag_id}/history",
    response_model=list[FlagChangeHistoryEntry],
)
async def feature_flag_history(
    flag_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> list[FlagChangeHistoryEntry]:
    """Get change history for a feature flag."""
    return await admin_service.get_flag_change_history(db=db, flag_id=flag_id)


# ─── AD-06: System Health ───────────────────────────────────────────────────


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SystemHealthResponse:
    """Check health of all platform dependencies with latency details."""
    return await admin_service.check_system_health(db=db)


# ─── AD-07: Tenant Impersonation ────────────────────────────────────────────


@router.post(
    "/tenants/{tenant_id}/impersonate",
    response_model=ImpersonateResponse,
)
async def impersonate_tenant(
    tenant_id: str,
    body: ImpersonateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ImpersonateResponse:
    """Generate a tenant-scoped JWT for support/debugging (requires reason)."""
    result = await admin_service.impersonate_tenant(
        db=db,
        admin_id=str(admin.id),
        tenant_id=tenant_id,
        reason=body.reason,
        duration_minutes=body.duration_minutes,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="impersonate",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"reason": body.reason, "duration_minutes": body.duration_minutes},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


# ─── Audit Log ──────────────────────────────────────────────────────────────


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    admin_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AuditLogListResponse:
    """Get paginated admin audit log with filters."""
    return await admin_service.get_admin_audit_logs(
        db=db,
        page=page,
        page_size=page_size,
        action_filter=action,
        admin_id_filter=admin_id,
        date_from=date_from,
        date_to=date_to,
    )


# ─── Export ─────────────────────────────────────────────────────────────────


@router.get("/export")
async def export_data(
    export_type: str = Query(pattern="^(tenants|audit)$"),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> StreamingResponse:
    """Export tenants or audit log as CSV."""
    if export_type == "tenants":
        csv_data = await admin_service.export_tenants_csv(db=db)
        filename = "dentalos_tenants.csv"
    else:
        csv_data = await admin_service.export_audit_csv(db=db)
        filename = "dentalos_audit_log.csv"

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Superadmin Management ──────────────────────────────────────────────────


@router.get("/superadmins", response_model=list[SuperadminResponse])
async def list_superadmins(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> list[SuperadminResponse]:
    """List all superadmin accounts."""
    return await admin_service.list_superadmins(db=db)


@router.post(
    "/superadmins",
    response_model=SuperadminResponse,
    status_code=201,
)
async def create_superadmin(
    body: SuperadminCreateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SuperadminResponse:
    """Create a new superadmin account."""
    result = await admin_service.create_superadmin(
        db=db,
        email=body.email,
        password=body.password,
        name=body.name,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="create_superadmin",
        resource_type="superadmin",
        resource_id=result.id,
        details={"email": body.email},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.put("/superadmins/{admin_id}", response_model=SuperadminResponse)
async def update_superadmin(
    admin_id: str,
    body: SuperadminUpdateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SuperadminResponse:
    """Update a superadmin account."""
    result = await admin_service.update_superadmin(
        db=db,
        admin_id=admin_id,
        name=body.name,
        is_active=body.is_active,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="update_superadmin",
        resource_type="superadmin",
        resource_id=admin_id,
        details=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.delete("/superadmins/{admin_id}", status_code=200)
async def delete_superadmin(
    admin_id: str,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict[str, str]:
    """Deactivate a superadmin account (cannot deactivate yourself)."""
    await admin_service.delete_superadmin(
        db=db,
        admin_id=admin_id,
        current_admin_id=str(admin.id),
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="delete_superadmin",
        resource_type="superadmin",
        resource_id=admin_id,
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return {"status": "deactivated"}


# ── Notifications ────────────────────────────────────────────────────────────


@router.get("/notifications", response_model=AdminNotificationListResponse, tags=["admin-notifications"])
async def list_admin_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AdminNotificationListResponse:
    """List notifications for the current admin."""
    result = await admin_service.get_admin_notifications(
        db=db, admin_id=admin.id, page=page, page_size=page_size, unread_only=unread_only
    )
    return result


@router.post("/notifications/{notification_id}/read", tags=["admin-notifications"])
async def mark_notification_read(
    notification_id: UUID,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict[str, str]:
    """Mark a single notification as read."""
    success = await admin_service.mark_notification_read(
        db=db, notification_id=notification_id, admin_id=admin.id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return {"status": "ok"}


@router.post("/notifications/read-all", tags=["admin-notifications"])
async def mark_all_notifications_read(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict[str, object]:
    """Mark all notifications as read for the current admin."""
    count = await admin_service.mark_all_notifications_read(db=db, admin_id=admin.id)
    await db.commit()
    return {"status": "ok", "marked_count": count}
