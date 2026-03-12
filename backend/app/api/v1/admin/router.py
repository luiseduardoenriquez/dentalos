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
    AddonUsageResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminNotificationListResponse,
    AdminTOTPSetupResponse,
    AdminTOTPVerifyRequest,
    AnnouncementCreateRequest,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
    AuditLogListResponse,
    BulkOperationRequest,
    BulkOperationResponse,
    AlertRuleCreateRequest,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertRuleUpdateRequest,
    BroadcastCreateRequest,
    BroadcastHistoryResponse,
    BroadcastSendResponse,
    CohortAnalysisResponse,
    ComplianceDashboardResponse,
    CrossTenantUserListResponse,
    DatabaseMetricsResponse,
    DataRetentionResponse,
    FeatureAdoptionResponse,
    ExtendTrialRequest,
    FeatureFlagCreateRequest,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
    FlagChangeHistoryEntry,
    ImpersonateRequest,
    ImpersonateResponse,
    JobMonitorResponse,
    MaintenanceStatusResponse,
    MaintenanceToggleRequest,
    OnboardingFunnelResponse,
    PlanChangeHistoryResponse,
    PlanResponse,
    PlanUpdateRequest,
    PlatformAnalyticsResponse,
    RevenueDashboardResponse,
    ScheduledReportCreateRequest,
    ScheduledReportListResponse,
    ScheduledReportResponse,
    ScheduledReportUpdateRequest,
    SecurityAlertListResponse,
    SuperadminCreateRequest,
    SupportMessageCreateRequest,
    SupportMessageItem,
    SupportThreadDetailResponse,
    SupportThreadListResponse,
    TenantHealthListResponse,
    ApiUsageMetricsResponse,
    CatalogCodeCreateRequest,
    CatalogCodeItem,
    CatalogCodeListResponse,
    CatalogCodeUpdateRequest,
    DefaultPriceItem,
    DefaultPriceListResponse,
    DefaultPriceUpsertRequest,
    GeoIntelligenceResponse,
    GlobalTemplateDetailResponse,
    GlobalTemplateListResponse,
    GlobalTemplateUpdateRequest,
    TenantComparisonResponse,
    SuperadminResponse,
    SuperadminUpdateRequest,
    SystemHealthResponse,
    TenantCreateRequest,
    TenantDetailResponse,
    TenantListResponse,
    TenantUpdateRequest,
    TrialListResponse,
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


# ─── SA-R02: Trial Management ─────────────────────────────────────────────


@router.get("/trials", response_model=TrialListResponse, tags=["admin-trials"])
async def list_trials(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TrialListResponse:
    """List all tenants with active trials."""
    return await admin_service.list_trials(db=db)


@router.post(
    "/tenants/{tenant_id}/extend-trial",
    tags=["admin-trials"],
)
async def extend_trial(
    tenant_id: str,
    body: ExtendTrialRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict:
    """Extend a tenant's trial period."""
    result = await admin_service.extend_trial(db=db, tenant_id=tenant_id, days=body.days)
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="extend_trial",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"days": body.days},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


# ─── SA-O04: Maintenance Mode ─────────────────────────────────────────────


@router.get("/maintenance", response_model=MaintenanceStatusResponse, tags=["admin-maintenance"])
async def get_maintenance_status(
    admin: Superadmin = Depends(get_current_admin),
) -> MaintenanceStatusResponse:
    """Get current maintenance mode status."""
    return await admin_service.get_maintenance_status()


@router.post("/maintenance", response_model=MaintenanceStatusResponse, tags=["admin-maintenance"])
async def toggle_maintenance(
    body: MaintenanceToggleRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> MaintenanceStatusResponse:
    """Toggle platform maintenance mode."""
    result = await admin_service.set_maintenance_mode(
        enabled=body.enabled,
        message=body.message,
        scheduled_end=body.scheduled_end,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="toggle_maintenance",
        resource_type="system",
        details={"enabled": body.enabled, "message": body.message},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


# ─── SA-O01: Job Monitor ──────────────────────────────────────────────────


@router.get("/jobs", response_model=JobMonitorResponse, tags=["admin-jobs"])
async def get_job_stats(
    admin: Superadmin = Depends(get_current_admin),
) -> JobMonitorResponse:
    """Get RabbitMQ queue stats for job monitoring."""
    return await admin_service.get_job_monitor_stats()


# ─── SA-E01: Announcements ────────────────────────────────────────────────


@router.get("/announcements", response_model=AnnouncementListResponse, tags=["admin-announcements"])
async def list_announcements(
    active_only: bool = Query(False),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AnnouncementListResponse:
    """List all announcements."""
    return await admin_service.list_announcements(db=db, active_only=active_only)


@router.post(
    "/announcements",
    response_model=AnnouncementResponse,
    status_code=201,
    tags=["admin-announcements"],
)
async def create_announcement(
    body: AnnouncementCreateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AnnouncementResponse:
    """Create a new platform announcement."""
    result = await admin_service.create_announcement(
        db=db,
        admin_id=str(admin.id),
        title=body.title,
        body=body.body,
        announcement_type=body.announcement_type,
        visibility=body.visibility,
        visibility_filter=body.visibility_filter,
        is_dismissable=body.is_dismissable,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="create_announcement",
        resource_type="announcement",
        resource_id=result.id,
        details={"title": body.title},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.put(
    "/announcements/{announcement_id}",
    response_model=AnnouncementResponse,
    tags=["admin-announcements"],
)
async def update_announcement(
    announcement_id: str,
    body: AnnouncementUpdateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AnnouncementResponse:
    """Update an existing announcement."""
    result = await admin_service.update_announcement(
        db=db,
        announcement_id=announcement_id,
        **body.model_dump(exclude_none=True),
    )
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="update_announcement",
        resource_type="announcement",
        resource_id=announcement_id,
        details=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return result


@router.delete(
    "/announcements/{announcement_id}",
    tags=["admin-announcements"],
)
async def delete_announcement(
    announcement_id: str,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict[str, str]:
    """Deactivate an announcement."""
    await admin_service.delete_announcement(db=db, announcement_id=announcement_id)
    ip, ua = _get_client_info(request)
    await admin_service.log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="delete_announcement",
        resource_type="announcement",
        resource_id=announcement_id,
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return {"status": "deactivated"}


# ─── SA-R01: Revenue Dashboard ─────────────────────────────────────────────


@router.get("/analytics/revenue", response_model=RevenueDashboardResponse, tags=["admin-revenue"])
async def revenue_dashboard(
    months: int = Query(default=12, ge=3, le=24),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> RevenueDashboardResponse:
    """Revenue dashboard with KPIs, monthly trends, and breakdowns."""
    return await admin_service.get_revenue_dashboard(db=db, months=months)


# ─── SA-R03: Add-on Usage ─────────────────────────────────────────────────


@router.get("/analytics/addons", response_model=AddonUsageResponse, tags=["admin-addons"])
async def addon_usage(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AddonUsageResponse:
    """Add-on adoption metrics and per-tenant usage."""
    return await admin_service.get_addon_usage(db=db)


# ─── SA-G03: Onboarding Funnel ────────────────────────────────────────────


@router.get("/analytics/onboarding", response_model=OnboardingFunnelResponse, tags=["admin-onboarding"])
async def onboarding_funnel(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> OnboardingFunnelResponse:
    """Onboarding funnel metrics — step completion rates and stuck tenants."""
    return await admin_service.get_onboarding_funnel(db=db)


# ─── SA-U01: Cross-Tenant User Search ─────────────────────────────────────


@router.get("/users", response_model=CrossTenantUserListResponse, tags=["admin-users"])
async def search_users(
    search: str = Query(..., min_length=2, description="Search by email, name"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: str | None = Query(default=None),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> CrossTenantUserListResponse:
    """Search users across all tenant schemas."""
    return await admin_service.search_users_cross_tenant(
        db=db, search=search, page=page, page_size=page_size, role=role,
    )


# ─── SA-O02: Database Metrics ─────────────────────────────────────────────


@router.get("/metrics/database", response_model=DatabaseMetricsResponse, tags=["admin-database"])
async def database_metrics(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> DatabaseMetricsResponse:
    """PostgreSQL performance and size metrics."""
    return await admin_service.get_database_metrics(db=db)


# ─── SA-A03: Bulk Operations ──────────────────────────────────────────────


@router.post("/tenants/bulk", response_model=BulkOperationResponse, tags=["admin-bulk"])
async def bulk_tenant_operation(
    body: BulkOperationRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> BulkOperationResponse:
    """Execute a bulk action on multiple tenants."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return await admin_service.execute_bulk_operation(
        db=db,
        tenant_ids=body.tenant_ids,
        action=body.action,
        admin_id=str(admin.id),
        plan_id=body.plan_id,
        trial_days=body.trial_days,
        ip_address=ip,
        user_agent=ua,
    )


# ─── SA-C01: Compliance Dashboard ─────────────────────────────────────────


@router.get("/compliance", response_model=ComplianceDashboardResponse, tags=["admin-compliance"])
async def compliance_dashboard(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ComplianceDashboardResponse:
    """Compliance status for Colombian tenants (Resolucion 1888)."""
    return await admin_service.get_compliance_dashboard(db=db)


# ─── SA-C02: Security Alerts ──────────────────────────────────────────────


@router.get("/security/alerts", response_model=SecurityAlertListResponse, tags=["admin-security"])
async def security_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SecurityAlertListResponse:
    """Security alerts from audit log analysis."""
    return await admin_service.get_security_alerts(
        db=db, page=page, page_size=page_size,
    )


# ─── SA-C03: Data Retention ───────────────────────────────────────────────


@router.get("/retention", response_model=DataRetentionResponse, tags=["admin-retention"])
async def data_retention(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> DataRetentionResponse:
    """Data retention policies and archivable tenants."""
    return await admin_service.get_data_retention(db=db)


# ─── SA-U02: Tenant Usage Analytics ───────────────────────────────────────


@router.get("/analytics/tenant-health", response_model=TenantHealthListResponse, tags=["admin-intelligence"])
async def tenant_health(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantHealthListResponse:
    """Per-tenant usage metrics and health scores."""
    return await admin_service.get_tenant_health(db=db)


# ─── SA-G01: Cohort Analysis ──────────────────────────────────────────────


@router.get("/analytics/cohorts", response_model=CohortAnalysisResponse, tags=["admin-intelligence"])
async def cohort_analysis(
    months: int = Query(default=12, ge=3, le=24),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> CohortAnalysisResponse:
    """Monthly cohort retention matrix."""
    return await admin_service.get_cohort_analysis(db=db, months=months)


# ─── SA-G02: Feature Adoption ─────────────────────────────────────────────


@router.get("/analytics/feature-adoption", response_model=FeatureAdoptionResponse, tags=["admin-intelligence"])
async def feature_adoption(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> FeatureAdoptionResponse:
    """Feature adoption matrix across all active tenants."""
    return await admin_service.get_feature_adoption(db=db)


# ─── SA-E02: Broadcast Messaging ──────────────────────────────────────────


@router.post("/broadcast", response_model=BroadcastSendResponse, status_code=201, tags=["admin-broadcast"])
async def send_broadcast(
    body: BroadcastCreateRequest,
    request: Request,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> BroadcastSendResponse:
    """Queue a broadcast email to clinic owners."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    result = await admin_service.send_broadcast(
        db=db, subject=body.subject, body=body.body,
        admin_id=str(admin.id), template=body.template,
        filter_plan=body.filter_plan, filter_country=body.filter_country,
        filter_status=body.filter_status,
    )
    await admin_service.log_admin_action(
        db=db, admin_id=str(admin.id), action="send_broadcast",
        resource_type="broadcast", resource_id=result.broadcast_id,
        details={"subject": body.subject, "recipients": result.recipients_count},
        ip_address=ip, user_agent=ua,
    )
    return result


@router.get("/broadcast/history", response_model=BroadcastHistoryResponse, tags=["admin-broadcast"])
async def broadcast_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> BroadcastHistoryResponse:
    """Broadcast send history."""
    return await admin_service.get_broadcast_history(
        db=db, page=page, page_size=page_size,
    )


# ─── SA-A01: Alert Rules ──────────────────────────────────────────────────


@router.get("/alert-rules", response_model=AlertRuleListResponse, tags=["admin-alerts"])
async def list_alert_rules(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AlertRuleListResponse:
    """List all automated alert rules."""
    return await admin_service.list_alert_rules(db=db)


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=201, tags=["admin-alerts"])
async def create_alert_rule(
    body: AlertRuleCreateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AlertRuleResponse:
    """Create an automated alert rule."""
    return await admin_service.create_alert_rule(
        db=db, name=body.name, condition=body.condition,
        threshold=body.threshold, channel=body.channel,
        is_active=body.is_active, admin_id=str(admin.id),
    )


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse, tags=["admin-alerts"])
async def update_alert_rule(
    rule_id: str,
    body: AlertRuleUpdateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> AlertRuleResponse:
    """Update an alert rule."""
    updates = body.model_dump(exclude_unset=True)
    return await admin_service.update_alert_rule(
        db=db, rule_id=rule_id, updates=updates,
    )


@router.delete("/alert-rules/{rule_id}", tags=["admin-alerts"])
async def delete_alert_rule(
    rule_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict:
    """Delete an alert rule."""
    await admin_service.delete_alert_rule(db=db, rule_id=rule_id)
    return {"status": "deleted"}


# ─── SA-A02: Scheduled Reports ────────────────────────────────────────────


@router.get("/scheduled-reports", response_model=ScheduledReportListResponse, tags=["admin-reports"])
async def list_scheduled_reports(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ScheduledReportListResponse:
    """List all scheduled reports."""
    return await admin_service.list_scheduled_reports(db=db)


@router.post("/scheduled-reports", response_model=ScheduledReportResponse, status_code=201, tags=["admin-reports"])
async def create_scheduled_report(
    body: ScheduledReportCreateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ScheduledReportResponse:
    """Create a scheduled report."""
    return await admin_service.create_scheduled_report(
        db=db, name=body.name, report_type=body.report_type,
        schedule=body.schedule, recipients=body.recipients,
        is_active=body.is_active, admin_id=str(admin.id),
    )


@router.put("/scheduled-reports/{report_id}", response_model=ScheduledReportResponse, tags=["admin-reports"])
async def update_scheduled_report(
    report_id: str,
    body: ScheduledReportUpdateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ScheduledReportResponse:
    """Update a scheduled report."""
    updates = body.model_dump(exclude_unset=True)
    return await admin_service.update_scheduled_report(
        db=db, report_id=report_id, updates=updates,
    )


@router.delete("/scheduled-reports/{report_id}", tags=["admin-reports"])
async def delete_scheduled_report(
    report_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> dict:
    """Delete a scheduled report."""
    await admin_service.delete_scheduled_report(db=db, report_id=report_id)
    return {"status": "deleted"}


# ─── SA-E03: Support Chat ─────────────────────────────────────────────────


@router.get("/support/threads", response_model=SupportThreadListResponse, tags=["admin-support"])
async def list_support_threads(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SupportThreadListResponse:
    """List all support threads."""
    return await admin_service.list_support_threads(db=db)


@router.get("/support/threads/{tenant_id}", response_model=SupportThreadDetailResponse, tags=["admin-support"])
async def get_support_thread(
    tenant_id: str,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SupportThreadDetailResponse:
    """Get or create a support thread for a tenant."""
    return await admin_service.get_support_thread(db=db, tenant_id=tenant_id)


@router.post("/support/threads/{tenant_id}/messages", response_model=SupportMessageItem, status_code=201, tags=["admin-support"])
async def send_support_message(
    tenant_id: str,
    body: SupportMessageCreateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> SupportMessageItem:
    """Send a message in a support thread."""
    return await admin_service.send_support_message(
        db=db, tenant_id=tenant_id, content=body.content,
        sender_type="admin", sender_id=str(admin.id),
        sender_name=admin.name,
    )


# ─── SA-K03: Default Price Catalog (MUST be before /catalog/{catalog_type}) ───


@router.get("/catalog/prices", response_model=DefaultPriceListResponse, tags=["admin-catalog"])
async def list_default_prices(
    country_code: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> DefaultPriceListResponse:
    """List default procedure prices."""
    return await admin_service.list_default_prices(
        db=db, country_code=country_code, search=search, page=page, page_size=page_size,
    )


@router.post("/catalog/prices", response_model=DefaultPriceItem, status_code=201, tags=["admin-catalog"])
async def upsert_default_price(
    body: DefaultPriceUpsertRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> DefaultPriceItem:
    """Create or update a default price entry."""
    return await admin_service.upsert_default_price(
        db=db, data=body, admin_id=str(admin.id),
    )


# ─── SA-K01: Catalog Administration ─────────────────────────────────────


@router.get("/catalog/{catalog_type}", response_model=CatalogCodeListResponse, tags=["admin-catalog"])
async def list_catalog_codes(
    catalog_type: str,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> CatalogCodeListResponse:
    """List CIE-10 or CUPS codes."""
    if catalog_type not in ("cie10", "cups"):
        raise HTTPException(status_code=400, detail="catalog_type must be 'cie10' or 'cups'")
    return await admin_service.list_catalog_codes(
        db=db, catalog_type=catalog_type, search=search, page=page, page_size=page_size,
    )


@router.post("/catalog/{catalog_type}", response_model=CatalogCodeItem, status_code=201, tags=["admin-catalog"])
async def create_catalog_code(
    catalog_type: str,
    body: CatalogCodeCreateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> CatalogCodeItem:
    """Create a new CIE-10 or CUPS code."""
    if catalog_type not in ("cie10", "cups"):
        raise HTTPException(status_code=400, detail="catalog_type must be 'cie10' or 'cups'")
    return await admin_service.create_catalog_code(db=db, catalog_type=catalog_type, data=body)


@router.put("/catalog/{catalog_type}/{code_id}", response_model=CatalogCodeItem, tags=["admin-catalog"])
async def update_catalog_code(
    catalog_type: str,
    code_id: str,
    body: CatalogCodeUpdateRequest,
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> CatalogCodeItem:
    """Update a CIE-10 or CUPS code."""
    if catalog_type not in ("cie10", "cups"):
        raise HTTPException(status_code=400, detail="catalog_type must be 'cie10' or 'cups'")
    return await admin_service.update_catalog_code(
        db=db, catalog_type=catalog_type, code_id=code_id, data=body,
    )


# ─── SA-K02: Global Template Management ─────────────────────────────────


@router.get("/templates", response_model=GlobalTemplateListResponse, tags=["admin-templates"])
async def list_global_templates(
    template_type: str | None = Query(None),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> GlobalTemplateListResponse:
    """List global consent and evolution templates."""
    return await admin_service.list_global_templates(db=db, template_type=template_type)


@router.get("/templates/{template_id}", response_model=GlobalTemplateDetailResponse, tags=["admin-templates"])
async def get_global_template(
    template_id: str,
    template_type: str = Query("consent"),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> GlobalTemplateDetailResponse:
    """Get a global template with full content."""
    return await admin_service.get_global_template(
        db=db, template_id=template_id, template_type=template_type,
    )


@router.put("/templates/{template_id}", response_model=GlobalTemplateDetailResponse, tags=["admin-templates"])
async def update_global_template(
    template_id: str,
    body: GlobalTemplateUpdateRequest,
    template_type: str = Query("consent"),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> GlobalTemplateDetailResponse:
    """Update a global template."""
    return await admin_service.update_global_template(
        db=db, template_id=template_id, template_type=template_type, data=body,
    )


# ─── SA-U03: Tenant Comparison ───────────────────────────────────────────


@router.get("/analytics/benchmark", response_model=TenantComparisonResponse, tags=["admin-analytics"])
async def compare_tenants(
    tenant_ids: str = Query(..., description="Comma-separated tenant IDs (2-5)"),
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> TenantComparisonResponse:
    """Compare 2-5 tenants side by side."""
    ids = [tid.strip() for tid in tenant_ids.split(",") if tid.strip()]
    return await admin_service.compare_tenants(db=db, tenant_ids=ids)


# ─── SA-O03: API Usage Metrics ───────────────────────────────────────────


@router.get("/metrics/api", response_model=ApiUsageMetricsResponse, tags=["admin-metrics"])
async def get_api_usage_metrics(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> ApiUsageMetricsResponse:
    """Get API usage metrics."""
    return await admin_service.get_api_usage_metrics(db=db)


# ─── SA-G04: Geographic Intelligence ─────────────────────────────────────


@router.get("/analytics/geo", response_model=GeoIntelligenceResponse, tags=["admin-analytics"])
async def get_geo_intelligence(
    admin: Superadmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_public_db),
) -> GeoIntelligenceResponse:
    """Get geographic expansion intelligence."""
    return await admin_service.get_geo_intelligence(db=db)
