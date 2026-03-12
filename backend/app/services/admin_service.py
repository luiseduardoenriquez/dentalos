"""Admin service — tenant management, plans, analytics, feature flags, health.

Provides the business logic for superadmin operations on the DentalOS
platform. All queries target the public schema since admin operations
are cross-tenant by nature.
"""

import csv
import io
import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessValidationError, ResourceNotFoundError
from app.core.redis import redis_client
from app.core.security import _load_private_key
from app.models.public.admin_audit_log import (
    AdminAuditLog,
    AdminImpersonationSession,
    FeatureFlagChangeHistory,
    PlanChangeHistory,
)
from app.models.public.feature_flag import FeatureFlag
from app.models.public.plan import Plan
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership
from app.schemas.admin import (
    AddonMetrics,
    AddonTenantUsage,
    AddonUsageResponse,
    AnnouncementListResponse,
    AnnouncementResponse,
    AuditLogEntry,
    AuditLogListResponse,
    CountryDistributionItem,
    FeatureFlagResponse,
    FlagChangeHistoryEntry,
    ImpersonateResponse,
    JobMonitorResponse,
    MaintenanceStatusResponse,
    OnboardingFunnelResponse,
    OnboardingStepMetric,
    PlanChangeHistoryEntry,
    PlanChangeHistoryResponse,
    PlanDistributionItem,
    PlanResponse,
    PlatformAnalyticsResponse,
    QueueStatItem,
    RevenueCountryBreakdown,
    RevenueDashboardResponse,
    RevenueKPIs,
    RevenueMonthDataPoint,
    RevenuePlanBreakdown,
    ServiceHealthDetail,
    SuperadminResponse,
    SystemHealthResponse,
    TenantDetailResponse,
    TenantListResponse,
    TenantSummary,
    TopTenantItem,
    TrialListResponse,
    TrialTenantItem,
    AlertRuleListResponse,
    AlertRuleResponse,
    ArchivableTenantItem,
    BroadcastHistoryItem,
    BroadcastHistoryResponse,
    BroadcastSendResponse,
    BulkOperationResponse,
    BulkOperationResult,
    CohortAnalysisResponse,
    CohortRow,
    ComplianceDashboardResponse,
    ComplianceKPIs,
    CrossTenantUserItem,
    CrossTenantUserListResponse,
    DatabaseMetricsResponse,
    DataRetentionResponse,
    FeatureAdoptionResponse,
    FeatureAdoptionSummary,
    RetentionPolicyItem,
    ScheduledReportListResponse,
    ScheduledReportResponse,
    SecurityAlertItem,
    SecurityAlertListResponse,
    SlowQueryItem,
    SupportMessageItem,
    SupportThreadDetailResponse,
    SupportThreadItem,
    SupportThreadListResponse,
    TableSizeItem,
    TenantComplianceItem,
    TenantFeatureUsage,
    TenantHealthListResponse,
    TenantUsageMetrics,
    ApiEndpointMetric,
    ApiTenantUsage,
    ApiUsageMetricsResponse,
    CatalogCodeCreateRequest,
    CatalogCodeItem,
    CatalogCodeListResponse,
    CatalogCodeUpdateRequest,
    DefaultPriceItem,
    DefaultPriceListResponse,
    GeoCountryMetrics,
    GeoIntelligenceResponse,
    GlobalTemplateDetailResponse,
    GlobalTemplateItem,
    GlobalTemplateListResponse,
    TenantBenchmarkItem,
    TenantComparisonResponse,
)

logger = logging.getLogger("dentalos.admin")

# Redis cache keys and TTLs
_CACHE_ANALYTICS_KEY = "dentalos:admin:analytics"
_CACHE_ANALYTICS_TTL = 600  # 10 minutes
_CACHE_PATIENT_COUNTS_KEY = "dentalos:admin:patient_counts"
_CACHE_DOCTOR_COUNTS_KEY = "dentalos:admin:doctor_counts"

# Impersonation limits
_MAX_CONCURRENT_IMPERSONATIONS = 3


class AdminService:
    """Stateless admin service — all state flows through the DB session."""

    # ─── Tenant Management ──────────────────────────────

    async def list_tenants(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        plan_id: str | None = None,
        country_code: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> TenantListResponse:
        """List all tenants with filtering, sorting, and enriched data."""
        base_filter = []
        if status:
            base_filter.append(Tenant.status == status)
        if search:
            search_term = f"%{search.strip().lower()}%"
            base_filter.append(
                func.lower(Tenant.name).like(search_term)
                | func.lower(Tenant.slug).like(search_term)
            )
        if plan_id:
            base_filter.append(Tenant.plan_id == uuid.UUID(plan_id))
        if country_code:
            base_filter.append(Tenant.country_code == country_code.upper())
        if created_after:
            base_filter.append(Tenant.created_at >= datetime.fromisoformat(created_after))
        if created_before:
            base_filter.append(Tenant.created_at <= datetime.fromisoformat(created_before))

        # Count total
        count_stmt = select(func.count(Tenant.id)).where(*base_filter)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting
        sort_column = {
            "name": Tenant.name,
            "created_at": Tenant.created_at,
            "status": Tenant.status,
        }.get(sort_by, Tenant.created_at)
        order = sort_column.desc() if sort_order == "desc" else sort_column.asc()

        # Fetch tenants
        offset = (page - 1) * page_size
        stmt = (
            select(Tenant)
            .where(*base_filter)
            .order_by(order)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()

        # Batch user counts
        tenant_ids = [t.id for t in tenants]
        user_counts: dict = {}
        doctor_counts: dict = {}
        if tenant_ids:
            count_stmt = (
                select(UserTenantMembership.tenant_id, func.count(UserTenantMembership.id))
                .where(
                    UserTenantMembership.tenant_id.in_(tenant_ids),
                    UserTenantMembership.status == "active",
                )
                .group_by(UserTenantMembership.tenant_id)
            )
            count_result = await db.execute(count_stmt)
            user_counts = dict(count_result.all())

            # Doctor counts per tenant
            doc_stmt = (
                select(UserTenantMembership.tenant_id, func.count(UserTenantMembership.id))
                .where(
                    UserTenantMembership.tenant_id.in_(tenant_ids),
                    UserTenantMembership.status == "active",
                    UserTenantMembership.role == "doctor",
                )
                .group_by(UserTenantMembership.tenant_id)
            )
            doc_result = await db.execute(doc_stmt)
            doctor_counts = dict(doc_result.all())

        # Get patient counts from cache or cross-schema query
        patient_counts = await self._get_patient_counts(db)

        items: list[TenantSummary] = []
        for tenant in tenants:
            plan = tenant.plan
            schema = tenant.schema_name
            items.append(
                TenantSummary(
                    id=str(tenant.id),
                    name=tenant.name,
                    slug=tenant.slug,
                    plan_name=plan.name if plan else "unknown",
                    status=tenant.status,
                    user_count=user_counts.get(tenant.id, 0),
                    patient_count=patient_counts.get(schema, 0),
                    doctor_count=doctor_counts.get(tenant.id, 0),
                    created_at=tenant.created_at.isoformat(),
                )
            )

        return TenantListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_tenant_detail(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
    ) -> TenantDetailResponse:
        """Get full detail for a single tenant."""
        result = await db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()

        if tenant is None:
            raise ResourceNotFoundError(
                error="TENANT_not_found",
                resource_name="Tenant",
            )

        # User count
        count_result = await db.execute(
            select(func.count(UserTenantMembership.id)).where(
                UserTenantMembership.tenant_id == tenant.id,
                UserTenantMembership.status == "active",
            )
        )
        user_count = count_result.scalar() or 0

        plan = tenant.plan

        return TenantDetailResponse(
            id=str(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            schema_name=tenant.schema_name,
            owner_email=tenant.owner_email,
            owner_user_id=str(tenant.owner_user_id) if tenant.owner_user_id else None,
            country_code=tenant.country_code,
            timezone=tenant.timezone,
            currency_code=tenant.currency_code,
            locale=tenant.locale,
            plan_id=str(tenant.plan_id),
            plan_name=plan.name if plan else "unknown",
            status=tenant.status,
            phone=tenant.phone,
            address=tenant.address,
            logo_url=tenant.logo_url,
            onboarding_step=tenant.onboarding_step,
            settings=tenant.settings or {},
            addons=tenant.addons or {},
            trial_ends_at=tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            suspended_at=tenant.suspended_at.isoformat() if tenant.suspended_at else None,
            cancelled_at=tenant.cancelled_at.isoformat() if tenant.cancelled_at else None,
            user_count=user_count,
            created_at=tenant.created_at.isoformat(),
            updated_at=tenant.updated_at.isoformat(),
        )

    async def create_tenant(
        self,
        *,
        db: AsyncSession,
        name: str,
        owner_email: str,
        plan_id: str,
        country_code: str = "CO",
        timezone: str = "America/Bogota",
        currency_code: str = "COP",
    ) -> TenantDetailResponse:
        """Create a new tenant, provision schema, and run migrations."""
        from app.services.tenant_service import (
            generate_schema_name,
            generate_slug,
            provision_tenant_schema,
        )

        schema_name = generate_schema_name()
        slug = generate_slug(name)

        tenant = Tenant(
            name=name.strip(),
            slug=slug,
            schema_name=schema_name,
            owner_email=owner_email.strip().lower(),
            plan_id=uuid.UUID(plan_id),
            country_code=country_code,
            timezone=timezone,
            currency_code=currency_code,
            status="active",
        )
        db.add(tenant)
        await db.flush()

        # Provision the tenant schema and run migrations
        await provision_tenant_schema(schema_name, db)

        logger.info("Tenant created: %s (schema=%s)", tenant.name, schema_name)

        return await self.get_tenant_detail(db=db, tenant_id=str(tenant.id))

    async def update_tenant(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        name: str | None = None,
        plan_id: str | None = None,
        settings: dict | None = None,
        is_active: bool | None = None,
    ) -> TenantDetailResponse:
        """Partial update of a tenant's name, plan, settings, or status."""
        from app.services.tenant_service import invalidate_tenant_cache

        result = await db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()

        if tenant is None:
            raise ResourceNotFoundError(
                error="TENANT_not_found",
                resource_name="Tenant",
            )

        if name is not None:
            tenant.name = name.strip()
        if plan_id is not None:
            tenant.plan_id = uuid.UUID(plan_id)
        if settings is not None:
            tenant.settings = settings
        if is_active is not None:
            tenant.status = "active" if is_active else "suspended"
            if not is_active:
                tenant.suspended_at = datetime.now(UTC)
            else:
                tenant.suspended_at = None

        await db.flush()
        await invalidate_tenant_cache(tenant_id)

        logger.info("Tenant updated: %s (%s)", tenant.name, tenant.slug)

        return await self.get_tenant_detail(db=db, tenant_id=tenant_id)

    async def suspend_tenant(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
    ) -> TenantDetailResponse:
        """Toggle tenant suspension — idempotent."""
        from app.services.tenant_service import invalidate_tenant_cache

        result = await db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()

        if tenant is None:
            raise ResourceNotFoundError(
                error="TENANT_not_found",
                resource_name="Tenant",
            )

        if tenant.status == "suspended":
            tenant.status = "active"
            tenant.suspended_at = None
            logger.info("Tenant reactivated: %s", tenant.name)
        else:
            tenant.status = "suspended"
            tenant.suspended_at = datetime.now(UTC)
            logger.info("Tenant suspended: %s", tenant.name)

        await db.flush()
        await invalidate_tenant_cache(tenant_id)

        return await self.get_tenant_detail(db=db, tenant_id=tenant_id)

    # ─── Plan Management ────────────────────────────────

    async def list_plans(self, *, db: AsyncSession) -> list[PlanResponse]:
        """List all subscription plans."""
        result = await db.execute(
            select(Plan).order_by(Plan.sort_order.asc(), Plan.price_cents.asc())
        )
        plans = result.scalars().all()

        return [self._plan_to_response(p) for p in plans]

    async def update_plan(
        self,
        *,
        db: AsyncSession,
        plan_id: str,
        admin_id: str,
        price_cents: int | None = None,
        max_patients: int | None = None,
        max_doctors: int | None = None,
        features: dict | None = None,
        is_active: bool | None = None,
    ) -> PlanResponse:
        """Update a subscription plan and track changes."""
        result = await db.execute(
            select(Plan).where(Plan.id == uuid.UUID(plan_id))
        )
        plan = result.scalar_one_or_none()

        if plan is None:
            raise ResourceNotFoundError(
                error="SYSTEM_plan_not_found",
                resource_name="Plan",
            )

        # Track changes for history
        changes: list[tuple[str, Any, Any]] = []

        if price_cents is not None and price_cents != plan.price_cents:
            changes.append(("price_cents", plan.price_cents, price_cents))
            plan.price_cents = price_cents
        if max_patients is not None and max_patients != plan.max_patients:
            changes.append(("max_patients", plan.max_patients, max_patients))
            plan.max_patients = max_patients
        if max_doctors is not None and max_doctors != plan.max_doctors:
            changes.append(("max_doctors", plan.max_doctors, max_doctors))
            plan.max_doctors = max_doctors
        if features is not None and features != plan.features:
            changes.append(("features", json.dumps(plan.features), json.dumps(features)))
            plan.features = features
        if is_active is not None and is_active != plan.is_active:
            changes.append(("is_active", str(plan.is_active), str(is_active)))
            plan.is_active = is_active

        # Record change history
        for field, old_val, new_val in changes:
            db.add(PlanChangeHistory(
                plan_id=plan.id,
                admin_id=uuid.UUID(admin_id),
                field_changed=field,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
            ))

        await db.flush()

        logger.info("Plan updated: %s (%s) — %d fields changed", plan.name, plan.slug, len(changes))

        return self._plan_to_response(plan)

    async def get_plan_change_history(
        self,
        *,
        db: AsyncSession,
        plan_id: str,
    ) -> PlanChangeHistoryResponse:
        """Get the change history for a plan."""
        result = await db.execute(
            select(PlanChangeHistory)
            .where(PlanChangeHistory.plan_id == uuid.UUID(plan_id))
            .order_by(PlanChangeHistory.created_at.desc())
            .limit(100)
        )
        entries = result.scalars().all()

        count_result = await db.execute(
            select(func.count(PlanChangeHistory.id))
            .where(PlanChangeHistory.plan_id == uuid.UUID(plan_id))
        )
        total = count_result.scalar() or 0

        return PlanChangeHistoryResponse(
            items=[
                PlanChangeHistoryEntry(
                    id=str(e.id),
                    plan_id=str(e.plan_id),
                    admin_id=str(e.admin_id),
                    field_changed=e.field_changed,
                    old_value=e.old_value,
                    new_value=e.new_value,
                    created_at=e.created_at.isoformat(),
                )
                for e in entries
            ],
            total=total,
        )

    # ─── Platform Analytics ─────────────────────────────

    async def get_platform_analytics(
        self, *, db: AsyncSession
    ) -> PlatformAnalyticsResponse:
        """Aggregate platform-wide analytics with real MRR, patient counts, and churn."""
        # Total tenants
        total_result = await db.execute(select(func.count(Tenant.id)))
        total_tenants = total_result.scalar() or 0

        # Active tenants
        active_result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status == "active")
        )
        active_tenants = active_result.scalar() or 0

        # Total users (from memberships)
        users_result = await db.execute(
            select(func.count(UserTenantMembership.id)).where(
                UserTenantMembership.status == "active"
            )
        )
        total_users = users_result.scalar() or 0

        # Real patient count (cross-schema)
        patient_counts = await self._get_patient_counts(db)
        total_patients = sum(patient_counts.values())

        # Real MRR calculation
        mrr_cents = await self._calculate_real_mrr(db)

        # MAU estimate: active memberships updated in last 30 days
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        mau_result = await db.execute(
            select(func.count(UserTenantMembership.id)).where(
                UserTenantMembership.status == "active",
                UserTenantMembership.updated_at >= thirty_days_ago,
            )
        )
        mau = mau_result.scalar() or 0

        # Real churn rate
        churn_rate = await self._calculate_churn_rate(db)

        # New signups in last 30 days
        signups_result = await db.execute(
            select(func.count(Tenant.id)).where(
                Tenant.created_at >= thirty_days_ago
            )
        )
        new_signups_30d = signups_result.scalar() or 0

        # Plan distribution
        plan_dist_result = await db.execute(
            select(Plan.name, func.count(Tenant.id))
            .select_from(Tenant)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(Tenant.status == "active")
            .group_by(Plan.name)
            .order_by(func.count(Tenant.id).desc())
        )
        plan_distribution = [
            PlanDistributionItem(plan_name=name, count=count)
            for name, count in plan_dist_result.all()
        ]

        # Top tenants by MRR (top 10)
        top_tenants = await self._get_top_tenants(db, patient_counts)

        # Country distribution
        country_result = await db.execute(
            select(Tenant.country_code, func.count(Tenant.id))
            .where(Tenant.status == "active")
            .group_by(Tenant.country_code)
            .order_by(func.count(Tenant.id).desc())
        )
        country_distribution = [
            CountryDistributionItem(country=code, count=count)
            for code, count in country_result.all()
        ]

        return PlatformAnalyticsResponse(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users,
            total_patients=total_patients,
            mrr_cents=mrr_cents,
            mau=mau,
            churn_rate=churn_rate,
            new_signups_30d=new_signups_30d,
            plan_distribution=plan_distribution,
            top_tenants=top_tenants,
            country_distribution=country_distribution,
        )

    # ─── Feature Flags ──────────────────────────────────

    async def list_feature_flags(
        self, *, db: AsyncSession
    ) -> list[FeatureFlagResponse]:
        """List all feature flags with expiry and reason."""
        result = await db.execute(
            select(FeatureFlag).order_by(FeatureFlag.flag_name.asc())
        )
        flags = result.scalars().all()

        return [self._flag_to_response(f) for f in flags]

    async def create_feature_flag(
        self,
        *,
        db: AsyncSession,
        flag_name: str,
        enabled: bool = False,
        scope: str | None = None,
        plan_filter: str | None = None,
        tenant_id: str | None = None,
        description: str | None = None,
        expires_at: str | None = None,
        reason: str | None = None,
    ) -> FeatureFlagResponse:
        """Create a new feature flag."""
        flag = FeatureFlag(
            flag_name=flag_name.strip(),
            enabled=enabled,
            scope=scope,
            plan_filter=plan_filter,
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            description=description,
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            reason=reason,
        )
        db.add(flag)
        await db.flush()

        logger.info("Feature flag created: %s (enabled=%s)", flag.flag_name, flag.enabled)

        return self._flag_to_response(flag)

    async def update_feature_flag(
        self,
        *,
        db: AsyncSession,
        flag_id: str,
        admin_id: str | None = None,
        enabled: bool | None = None,
        scope: str | None = None,
        plan_filter: str | None = None,
        tenant_id: str | None = None,
        description: str | None = None,
        expires_at: str | None = None,
        reason: str | None = None,
    ) -> FeatureFlagResponse:
        """Update an existing feature flag and track changes."""
        result = await db.execute(
            select(FeatureFlag).where(FeatureFlag.id == uuid.UUID(flag_id))
        )
        flag = result.scalar_one_or_none()

        if flag is None:
            raise ResourceNotFoundError(
                error="SYSTEM_feature_flag_not_found",
                resource_name="FeatureFlag",
            )

        # Track changes
        changes: list[tuple[str, Any, Any]] = []

        if enabled is not None and enabled != flag.enabled:
            changes.append(("enabled", str(flag.enabled), str(enabled)))
            flag.enabled = enabled
        if scope is not None and scope != flag.scope:
            changes.append(("scope", flag.scope, scope))
            flag.scope = scope
        if plan_filter is not None and plan_filter != flag.plan_filter:
            changes.append(("plan_filter", flag.plan_filter, plan_filter))
            flag.plan_filter = plan_filter
        if tenant_id is not None:
            new_tid = uuid.UUID(tenant_id)
            if new_tid != flag.tenant_id:
                changes.append(("tenant_id", str(flag.tenant_id) if flag.tenant_id else None, tenant_id))
                flag.tenant_id = new_tid
        if description is not None and description != flag.description:
            changes.append(("description", flag.description, description))
            flag.description = description
        if expires_at is not None:
            new_exp = datetime.fromisoformat(expires_at)
            if new_exp != flag.expires_at:
                changes.append(("expires_at", flag.expires_at.isoformat() if flag.expires_at else None, expires_at))
                flag.expires_at = new_exp
        if reason is not None and reason != flag.reason:
            changes.append(("reason", flag.reason, reason))
            flag.reason = reason

        # Record change history if admin_id is provided
        if admin_id and changes:
            for field, old_val, new_val in changes:
                db.add(FeatureFlagChangeHistory(
                    flag_id=flag.id,
                    admin_id=uuid.UUID(admin_id),
                    field_changed=field,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                ))

        await db.flush()

        logger.info("Feature flag updated: %s (enabled=%s)", flag.flag_name, flag.enabled)

        return self._flag_to_response(flag)

    async def resolve_feature_flags(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        plan_slug: str,
    ) -> dict[str, bool]:
        """Resolve all feature flags for a tenant using inheritance.

        Resolution order: tenant override → plan default → global default.
        Expired flags are treated as disabled.
        """
        result = await db.execute(
            select(FeatureFlag).where(FeatureFlag.enabled.is_(True))
        )
        all_flags = result.scalars().all()

        now = datetime.now(UTC)
        resolved: dict[str, bool] = {}

        # Group by scope
        global_flags = {}
        plan_flags = {}
        tenant_flags = {}

        for f in all_flags:
            # Skip expired flags
            if f.expires_at and f.expires_at < now:
                continue

            if f.scope == "tenant" and f.tenant_id and str(f.tenant_id) == tenant_id:
                tenant_flags[f.flag_name] = f.enabled
            elif f.scope == "plan" and f.plan_filter == plan_slug:
                plan_flags[f.flag_name] = f.enabled
            elif f.scope == "global" or f.scope is None:
                global_flags[f.flag_name] = f.enabled

        # Merge: global → plan → tenant (later overrides earlier)
        resolved.update(global_flags)
        resolved.update(plan_flags)
        resolved.update(tenant_flags)

        return resolved

    async def get_flag_change_history(
        self,
        *,
        db: AsyncSession,
        flag_id: str,
    ) -> list[FlagChangeHistoryEntry]:
        """Get change history for a specific feature flag."""
        result = await db.execute(
            select(FeatureFlagChangeHistory)
            .where(FeatureFlagChangeHistory.flag_id == uuid.UUID(flag_id))
            .order_by(FeatureFlagChangeHistory.created_at.desc())
            .limit(50)
        )
        entries = result.scalars().all()

        return [
            FlagChangeHistoryEntry(
                id=str(e.id),
                flag_id=str(e.flag_id),
                admin_id=str(e.admin_id),
                field_changed=e.field_changed,
                old_value=e.old_value,
                new_value=e.new_value,
                created_at=e.created_at.isoformat(),
            )
            for e in entries
        ]

    # ─── System Health ──────────────────────────────────

    async def check_system_health(
        self, *, db: AsyncSession
    ) -> SystemHealthResponse:
        """Check health of all platform dependencies with latency and details."""
        from app.core.queue import get_queue_json_stats, is_connected as rmq_connected

        now = datetime.now(UTC)
        details: dict[str, ServiceHealthDetail] = {}

        # PostgreSQL
        pg_healthy = False
        pg_start = time.monotonic()
        pg_version = None
        try:
            result = await db.execute(text("SELECT version()"))
            pg_version = result.scalar()
            pg_healthy = True
        except Exception:
            logger.warning("Health check: PostgreSQL is unhealthy")
        pg_latency = (time.monotonic() - pg_start) * 1000

        details["postgres"] = ServiceHealthDetail(
            healthy=pg_healthy,
            latency_ms=round(pg_latency, 2),
            version=pg_version[:60] if pg_version else None,
        )

        # Redis
        redis_healthy = False
        redis_start = time.monotonic()
        redis_info: dict = {}
        try:
            pong = await redis_client.ping()
            redis_healthy = bool(pong)
            info = await redis_client.info("memory")
            redis_info = {
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
            }
            server_info = await redis_client.info("server")
            redis_version = server_info.get("redis_version")
        except Exception:
            logger.warning("Health check: Redis is unhealthy")
            redis_version = None
        redis_latency = (time.monotonic() - redis_start) * 1000

        details["redis"] = ServiceHealthDetail(
            healthy=redis_healthy,
            latency_ms=round(redis_latency, 2),
            version=redis_version,
            details=redis_info,
        )

        # RabbitMQ — real check
        rmq_healthy = rmq_connected()
        rmq_start = time.monotonic()
        rmq_stats = {}
        try:
            rmq_stats = await get_queue_json_stats()
        except Exception:
            logger.warning("Health check: RabbitMQ stats unavailable")
        rmq_latency = (time.monotonic() - rmq_start) * 1000

        details["rabbitmq"] = ServiceHealthDetail(
            healthy=rmq_healthy,
            latency_ms=round(rmq_latency, 2),
            details=rmq_stats,
        )

        # Storage (S3/MinIO) — verify endpoint is configured
        storage_healthy = True
        storage_start = time.monotonic()
        try:
            storage_healthy = bool(settings.s3_endpoint_url)
        except Exception:
            storage_healthy = False
            logger.warning("Health check: Storage is unhealthy")
        storage_latency = (time.monotonic() - storage_start) * 1000

        details["storage"] = ServiceHealthDetail(
            healthy=storage_healthy,
            latency_ms=round(storage_latency, 2),
        )

        all_healthy = all(d.healthy for d in details.values())

        return SystemHealthResponse(
            status="healthy" if all_healthy else "degraded",
            postgres=pg_healthy,
            redis=redis_healthy,
            rabbitmq=rmq_healthy,
            storage=storage_healthy,
            timestamp=now.isoformat(),
            service_details=details,
        )

    # ─── Tenant Impersonation ───────────────────────────

    async def impersonate_tenant(
        self,
        *,
        db: AsyncSession,
        admin_id: str,
        tenant_id: str,
        reason: str,
        duration_minutes: int = 60,
    ) -> ImpersonateResponse:
        """Generate a clinic_owner-scoped JWT for a specific tenant.

        Validates reason, checks concurrent session limits, and creates
        an impersonation session for tracking.
        """
        # Validate reason
        if len(reason.strip()) < 10:
            raise BusinessValidationError(
                message="Impersonation reason must be at least 10 characters.",
            )

        # Check concurrent active sessions
        active_count_result = await db.execute(
            select(func.count(AdminImpersonationSession.id)).where(
                AdminImpersonationSession.admin_id == uuid.UUID(admin_id),
                AdminImpersonationSession.is_active.is_(True),
                AdminImpersonationSession.expires_at > datetime.now(UTC),
            )
        )
        active_count = active_count_result.scalar() or 0
        if active_count >= _MAX_CONCURRENT_IMPERSONATIONS:
            raise BusinessValidationError(
                message=f"Maximum {_MAX_CONCURRENT_IMPERSONATIONS} concurrent impersonation sessions allowed.",
            )

        result = await db.execute(
            select(Tenant).where(
                Tenant.id == uuid.UUID(tenant_id),
                Tenant.status.in_(["active", "suspended"]),
            )
        )
        tenant = result.scalar_one_or_none()

        if tenant is None:
            raise ResourceNotFoundError(
                error="TENANT_not_found",
                resource_name="Tenant",
            )

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=duration_minutes)

        # Create impersonation session
        session = AdminImpersonationSession(
            admin_id=uuid.UUID(admin_id),
            tenant_id=tenant.id,
            reason=reason.strip(),
            started_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(session)
        await db.flush()

        # Generate JWT
        access_token = self._generate_impersonation_jwt(
            admin_id=admin_id,
            tenant_id=str(tenant.id),
            tenant_schema=tenant.schema_name,
            session_id=str(session.id),
            duration_minutes=duration_minutes,
        )

        logger.info(
            "Admin %s... impersonating tenant %s... as clinic_owner (reason: %s)",
            admin_id[:8],
            str(tenant.id)[:8],
            reason[:30],
        )

        return ImpersonateResponse(
            access_token=access_token,
            token_type="bearer",
            tenant_id=str(tenant.id),
            impersonated_as="clinic_owner",
            session_id=str(session.id),
            expires_at=expires_at.isoformat(),
        )

    # ─── Audit Log ──────────────────────────────────────

    async def log_admin_action(
        self,
        *,
        db: AsyncSession,
        admin_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Fire-and-forget: insert an audit log entry."""
        entry = AdminAuditLog(
            admin_id=uuid.UUID(admin_id),
            action=action,
            resource_type=resource_type,
            resource_id=uuid.UUID(resource_id) if resource_id else None,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
        # No flush — caller will commit as part of the transaction

    async def get_admin_audit_logs(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        action_filter: str | None = None,
        admin_id_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> AuditLogListResponse:
        """Paginated query of admin audit logs with filters."""
        from app.models.public.superadmin import Superadmin

        filters = []
        if action_filter:
            filters.append(AdminAuditLog.action == action_filter)
        if admin_id_filter:
            filters.append(AdminAuditLog.admin_id == uuid.UUID(admin_id_filter))
        if date_from:
            filters.append(AdminAuditLog.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            filters.append(AdminAuditLog.created_at <= datetime.fromisoformat(date_to))

        # Count
        count_stmt = select(func.count(AdminAuditLog.id)).where(*filters)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Fetch with admin email join
        offset = (page - 1) * page_size
        stmt = (
            select(AdminAuditLog, Superadmin.email)
            .join(Superadmin, Superadmin.id == AdminAuditLog.admin_id, isouter=True)
            .where(*filters)
            .order_by(AdminAuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items = [
            AuditLogEntry(
                id=str(entry.id),
                admin_id=str(entry.admin_id),
                admin_email=email,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=str(entry.resource_id) if entry.resource_id else None,
                details=entry.details,
                ip_address=entry.ip_address,
                created_at=entry.created_at.isoformat(),
            )
            for entry, email in rows
        ]

        return AuditLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ─── Superadmin CRUD ────────────────────────────────

    async def list_superadmins(
        self, *, db: AsyncSession
    ) -> list[SuperadminResponse]:
        """List all superadmin accounts."""
        from app.models.public.superadmin import Superadmin

        result = await db.execute(
            select(Superadmin).order_by(Superadmin.created_at.asc())
        )
        admins = result.scalars().all()

        return [
            SuperadminResponse(
                id=str(a.id),
                email=a.email,
                name=a.name,
                totp_enabled=a.totp_enabled,
                is_active=a.is_active,
                last_login_at=a.last_login_at.isoformat() if a.last_login_at else None,
                created_at=a.created_at.isoformat(),
            )
            for a in admins
        ]

    async def create_superadmin(
        self,
        *,
        db: AsyncSession,
        email: str,
        password: str,
        name: str,
    ) -> SuperadminResponse:
        """Create a new superadmin account."""
        from passlib.context import CryptContext

        from app.models.public.superadmin import Superadmin

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

        admin = Superadmin(
            email=email.strip().lower(),
            password_hash=pwd_ctx.hash(password),
            name=name.strip(),
        )
        db.add(admin)
        await db.flush()

        logger.info("Superadmin created: %s", admin.email)

        return SuperadminResponse(
            id=str(admin.id),
            email=admin.email,
            name=admin.name,
            totp_enabled=admin.totp_enabled,
            is_active=admin.is_active,
            last_login_at=None,
            created_at=admin.created_at.isoformat(),
        )

    async def update_superadmin(
        self,
        *,
        db: AsyncSession,
        admin_id: str,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> SuperadminResponse:
        """Update a superadmin account."""
        from app.models.public.superadmin import Superadmin

        result = await db.execute(
            select(Superadmin).where(Superadmin.id == uuid.UUID(admin_id))
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            raise ResourceNotFoundError(
                error="SYSTEM_superadmin_not_found",
                resource_name="Superadmin",
            )

        if name is not None:
            admin.name = name.strip()
        if is_active is not None:
            admin.is_active = is_active

        await db.flush()

        return SuperadminResponse(
            id=str(admin.id),
            email=admin.email,
            name=admin.name,
            totp_enabled=admin.totp_enabled,
            is_active=admin.is_active,
            last_login_at=admin.last_login_at.isoformat() if admin.last_login_at else None,
            created_at=admin.created_at.isoformat(),
        )

    async def delete_superadmin(
        self,
        *,
        db: AsyncSession,
        admin_id: str,
        current_admin_id: str,
    ) -> None:
        """Soft-delete (deactivate) a superadmin. Cannot delete yourself."""
        from app.models.public.superadmin import Superadmin

        if admin_id == current_admin_id:
            raise BusinessValidationError(
                message="Cannot deactivate your own superadmin account.",
            )

        result = await db.execute(
            select(Superadmin).where(Superadmin.id == uuid.UUID(admin_id))
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            raise ResourceNotFoundError(
                error="SYSTEM_superadmin_not_found",
                resource_name="Superadmin",
            )

        admin.is_active = False
        await db.flush()

        logger.info("Superadmin deactivated: %s", admin.email)

    # ─── Export ─────────────────────────────────────────

    async def export_tenants_csv(self, *, db: AsyncSession) -> str:
        """Export all tenants as CSV string."""
        result = await db.execute(
            select(Tenant).order_by(Tenant.created_at.desc())
        )
        tenants = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "name", "slug", "status", "plan_name", "country_code",
            "owner_email", "currency_code", "created_at",
        ])
        for t in tenants:
            plan = t.plan
            writer.writerow([
                str(t.id), t.name, t.slug, t.status,
                plan.name if plan else "", t.country_code,
                t.owner_email, t.currency_code,
                t.created_at.isoformat(),
            ])
        return output.getvalue()

    async def export_audit_csv(self, *, db: AsyncSession) -> str:
        """Export audit logs as CSV string (last 1000 entries)."""
        from app.models.public.superadmin import Superadmin

        result = await db.execute(
            select(AdminAuditLog, Superadmin.email)
            .join(Superadmin, Superadmin.id == AdminAuditLog.admin_id, isouter=True)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(1000)
        )
        rows = result.all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "admin_email", "action", "resource_type",
            "resource_id", "ip_address", "created_at",
        ])
        for entry, email in rows:
            writer.writerow([
                str(entry.id), email or "", entry.action,
                entry.resource_type or "", str(entry.resource_id) if entry.resource_id else "",
                entry.ip_address or "", entry.created_at.isoformat(),
            ])
        return output.getvalue()

    # ─── Trial Management (SA-R02) ───────────────────────

    async def list_trials(
        self, *, db: AsyncSession
    ) -> TrialListResponse:
        """List tenants with active trials or recently converted."""
        now = datetime.now(UTC)

        # Get tenants that have trial_ends_at set (active trials)
        result = await db.execute(
            select(Tenant, Plan)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(
                Tenant.trial_ends_at.isnot(None),
                Tenant.status.in_(["active", "pending"]),
            )
            .order_by(Tenant.trial_ends_at.asc())
        )
        trial_tenants = result.all()

        items = []
        expiring_soon = 0
        for tenant, plan in trial_tenants:
            days_remaining = None
            if tenant.trial_ends_at:
                delta = tenant.trial_ends_at - now
                days_remaining = max(0, delta.days)
                if 0 < delta.days <= 7:
                    expiring_soon += 1

            items.append(TrialTenantItem(
                id=str(tenant.id),
                name=tenant.name,
                slug=tenant.slug,
                plan_name=plan.name,
                status=tenant.status,
                owner_email=tenant.owner_email,
                trial_ends_at=tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
                days_remaining=days_remaining,
                created_at=tenant.created_at.isoformat(),
            ))

        # Conversion rate: tenants without trial (paid) vs total
        total_result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status == "active")
        )
        total_active = total_result.scalar() or 0

        paid_result = await db.execute(
            select(func.count(Tenant.id)).where(
                Tenant.status == "active",
                or_(Tenant.trial_ends_at.is_(None), Tenant.trial_ends_at < now),
            )
        )
        paid_count = paid_result.scalar() or 0

        conversion_rate = round((paid_count / total_active * 100) if total_active > 0 else 0.0, 1)

        return TrialListResponse(
            items=items,
            total=len(items),
            expiring_soon_count=expiring_soon,
            conversion_rate=conversion_rate,
        )

    async def extend_trial(
        self, *, db: AsyncSession, tenant_id: str, days: int = 14
    ) -> dict:
        """Extend a tenant's trial period by N days."""
        result = await db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ResourceNotFoundError(error="TENANT_not_found", resource_name="Tenant")

        now = datetime.now(UTC)
        if tenant.trial_ends_at and tenant.trial_ends_at > now:
            tenant.trial_ends_at = tenant.trial_ends_at + timedelta(days=days)
        else:
            tenant.trial_ends_at = now + timedelta(days=days)

        await db.flush()
        return {
            "tenant_id": str(tenant.id),
            "trial_ends_at": tenant.trial_ends_at.isoformat(),
            "days_added": days,
        }

    # ─── Maintenance Mode (SA-O04) ─────────────────────

    _MAINTENANCE_KEY = "dentalos:global:maintenance"

    async def get_maintenance_status(self) -> MaintenanceStatusResponse:
        """Get current maintenance mode status from Redis.

        Key presence = maintenance active. Key absence = maintenance off.
        """
        try:
            data = await redis_client.get(self._MAINTENANCE_KEY)
            if data:
                parsed = json.loads(data)
                return MaintenanceStatusResponse(
                    enabled=True,
                    message=parsed.get("message"),
                    scheduled_end=parsed.get("ends_at"),
                    updated_at=parsed.get("updated_at"),
                )
        except Exception:
            logger.warning("Failed to read maintenance status from Redis")

        return MaintenanceStatusResponse(enabled=False)

    async def set_maintenance_mode(
        self,
        *,
        enabled: bool,
        message: str | None = None,
        scheduled_end: str | None = None,
    ) -> MaintenanceStatusResponse:
        """Toggle maintenance mode via Redis flag.

        When enabled, sets a Redis key that ``MaintenanceMiddleware`` reads to
        return 503 on non-admin API routes. When disabled, deletes the key.
        """
        now = datetime.now(UTC)
        try:
            if enabled:
                data = {
                    "message": message or "El sistema se encuentra en mantenimiento programado.",
                    "ends_at": scheduled_end,
                    "updated_at": now.isoformat(),
                }
                await redis_client.set(self._MAINTENANCE_KEY, json.dumps(data))
            else:
                await redis_client.delete(self._MAINTENANCE_KEY)
        except Exception:
            logger.error("Failed to set maintenance status in Redis")
            raise BusinessValidationError(message="Failed to update maintenance mode.")

        logger.info("Maintenance mode %s", "enabled" if enabled else "disabled")
        return MaintenanceStatusResponse(
            enabled=enabled,
            message=message,
            scheduled_end=scheduled_end,
            updated_at=now.isoformat(),
        )

    # ─── Job Monitor (SA-O01) ──────────────────────────

    async def get_job_monitor_stats(self) -> JobMonitorResponse:
        """Get RabbitMQ queue stats for the job monitor dashboard."""
        from app.core.queue import QUEUES, get_queue_json_stats, is_connected

        connected = is_connected()
        stats = await get_queue_json_stats()

        queue_items = []
        for q_name in QUEUES:
            queue_items.append(QueueStatItem(
                name=q_name,
                connected=connected,
            ))

        return JobMonitorResponse(
            connected=connected,
            exchange=stats.get("exchange", "dentalos.direct"),
            queues=queue_items,
        )

    # ─── Announcements (SA-E01) ────────────────────────

    async def list_announcements(
        self, *, db: AsyncSession, active_only: bool = False
    ) -> AnnouncementListResponse:
        """List all announcements, optionally only active ones."""
        from app.models.public.admin_announcement import AdminAnnouncement

        filters = []
        if active_only:
            now = datetime.now(UTC)
            filters.append(AdminAnnouncement.is_active.is_(True))
            filters.append(
                or_(AdminAnnouncement.starts_at.is_(None), AdminAnnouncement.starts_at <= now)
            )
            filters.append(
                or_(AdminAnnouncement.ends_at.is_(None), AdminAnnouncement.ends_at > now)
            )

        count_q = select(func.count()).select_from(AdminAnnouncement).where(*filters)
        total = (await db.execute(count_q)).scalar() or 0

        result = await db.execute(
            select(AdminAnnouncement)
            .where(*filters)
            .order_by(AdminAnnouncement.created_at.desc())
        )
        items = result.scalars().all()

        return AnnouncementListResponse(
            items=[self._announcement_to_response(a) for a in items],
            total=total,
        )

    async def create_announcement(
        self,
        *,
        db: AsyncSession,
        admin_id: str,
        title: str,
        body: str,
        announcement_type: str = "info",
        visibility: str = "all",
        visibility_filter: dict | None = None,
        is_dismissable: bool = True,
        starts_at: str | None = None,
        ends_at: str | None = None,
    ) -> AnnouncementResponse:
        """Create a new platform announcement."""
        from app.models.public.admin_announcement import AdminAnnouncement

        announcement = AdminAnnouncement(
            title=title.strip(),
            body=body.strip(),
            announcement_type=announcement_type,
            visibility=visibility,
            visibility_filter=visibility_filter or {},
            is_dismissable=is_dismissable,
            created_by=uuid.UUID(admin_id),
            starts_at=datetime.fromisoformat(starts_at) if starts_at else None,
            ends_at=datetime.fromisoformat(ends_at) if ends_at else None,
        )
        db.add(announcement)
        await db.flush()

        logger.info("Announcement created: %s", title[:50])
        return self._announcement_to_response(announcement)

    async def update_announcement(
        self,
        *,
        db: AsyncSession,
        announcement_id: str,
        **kwargs: Any,
    ) -> AnnouncementResponse:
        """Update an existing announcement."""
        from app.models.public.admin_announcement import AdminAnnouncement

        result = await db.execute(
            select(AdminAnnouncement).where(
                AdminAnnouncement.id == uuid.UUID(announcement_id)
            )
        )
        announcement = result.scalar_one_or_none()
        if not announcement:
            raise ResourceNotFoundError(
                error="SYSTEM_announcement_not_found",
                resource_name="Announcement",
            )

        for field in [
            "title", "body", "announcement_type", "visibility",
            "visibility_filter", "is_dismissable", "is_active",
        ]:
            if kwargs.get(field) is not None:
                setattr(announcement, field, kwargs[field])

        if kwargs.get("starts_at") is not None:
            announcement.starts_at = datetime.fromisoformat(kwargs["starts_at"])
        if kwargs.get("ends_at") is not None:
            announcement.ends_at = datetime.fromisoformat(kwargs["ends_at"])

        await db.flush()
        return self._announcement_to_response(announcement)

    async def delete_announcement(
        self, *, db: AsyncSession, announcement_id: str
    ) -> None:
        """Soft-delete an announcement by deactivating it."""
        from app.models.public.admin_announcement import AdminAnnouncement

        result = await db.execute(
            select(AdminAnnouncement).where(
                AdminAnnouncement.id == uuid.UUID(announcement_id)
            )
        )
        announcement = result.scalar_one_or_none()
        if not announcement:
            raise ResourceNotFoundError(
                error="SYSTEM_announcement_not_found",
                resource_name="Announcement",
            )

        announcement.is_active = False
        await db.flush()

    async def get_active_announcements_for_tenant(
        self, *, db: AsyncSession, tenant_plan: str | None = None, tenant_country: str | None = None
    ) -> list[AnnouncementResponse]:
        """Get active announcements filtered by tenant context (clinic-facing)."""
        from app.models.public.admin_announcement import AdminAnnouncement

        now = datetime.now(UTC)
        result = await db.execute(
            select(AdminAnnouncement).where(
                AdminAnnouncement.is_active.is_(True),
                or_(AdminAnnouncement.starts_at.is_(None), AdminAnnouncement.starts_at <= now),
                or_(AdminAnnouncement.ends_at.is_(None), AdminAnnouncement.ends_at > now),
            ).order_by(AdminAnnouncement.created_at.desc())
        )
        announcements = result.scalars().all()

        filtered = []
        for a in announcements:
            if a.visibility == "all":
                filtered.append(a)
            elif a.visibility == "plan" and tenant_plan:
                plan_filter = a.visibility_filter.get("plan_slug")
                if plan_filter and plan_filter == tenant_plan:
                    filtered.append(a)
            elif a.visibility == "country" and tenant_country:
                country_filter = a.visibility_filter.get("country_code")
                if country_filter and country_filter == tenant_country:
                    filtered.append(a)

        return [self._announcement_to_response(a) for a in filtered]

    # ─── Revenue Dashboard (SA-R01) ──────────────────────

    async def get_revenue_dashboard(
        self, *, db: AsyncSession, months: int = 12
    ) -> RevenueDashboardResponse:
        """Compute revenue KPIs and monthly trend data."""
        now = datetime.now(UTC)

        # Current MRR
        current_mrr = await self._calculate_real_mrr(db)

        # Active tenants count
        active_result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status == "active")
        )
        active_count = active_result.scalar() or 1  # avoid div by zero

        # ARPA = MRR / active tenants
        arpa = current_mrr // max(active_count, 1)

        # Churn rate for LTV calc
        churn_rate = await self._calculate_churn_rate(db)
        monthly_churn = churn_rate / 100.0
        ltv = int(arpa / monthly_churn) if monthly_churn > 0 else arpa * 36

        # Monthly trend from snapshots
        monthly_trend = await self._get_revenue_trend(db, months)

        # Previous month MRR for growth
        previous_mrr = monthly_trend[-2].mrr_cents if len(monthly_trend) >= 2 else 0
        mrr_growth = round(
            ((current_mrr - previous_mrr) / previous_mrr * 100) if previous_mrr > 0 else 0.0, 1
        )

        # NRR (simplified: current MRR / previous MRR * 100)
        nrr = round((current_mrr / previous_mrr * 100) if previous_mrr > 0 else 100.0, 1)

        # Add-on revenue
        addon_revenue = await self._calculate_addon_revenue(db)

        # Plan breakdown
        plan_breakdown = await self._get_plan_revenue_breakdown(db)

        # Country breakdown
        country_breakdown = await self._get_country_revenue_breakdown(db)

        return RevenueDashboardResponse(
            kpis=RevenueKPIs(
                current_mrr_cents=current_mrr,
                previous_mrr_cents=previous_mrr,
                mrr_growth_pct=mrr_growth,
                arpa_cents=arpa,
                ltv_cents=ltv,
                nrr_pct=nrr,
                total_addon_revenue_cents=addon_revenue,
            ),
            monthly_trend=monthly_trend,
            plan_breakdown=plan_breakdown,
            country_breakdown=country_breakdown,
        )

    async def _get_revenue_trend(
        self, db: AsyncSession, months: int = 12
    ) -> list[RevenueMonthDataPoint]:
        """Build monthly revenue trend. Uses snapshots if available, else generates live."""
        now = datetime.now(UTC)

        # Try to get from snapshots table
        try:
            result = await db.execute(
                text(
                    "SELECT month, mrr_cents, active_tenants, churned_tenants, "
                    "new_tenants, addon_revenue_cents "
                    "FROM public.admin_revenue_snapshots "
                    "ORDER BY month DESC LIMIT :limit"
                ),
                {"limit": months},
            )
            rows = result.all()
            if rows:
                return [
                    RevenueMonthDataPoint(
                        month=r[0], mrr_cents=r[1], active_tenants=r[2],
                        churned_tenants=r[3], new_tenants=r[4],
                        addon_revenue_cents=r[5],
                    )
                    for r in reversed(rows)
                ]
        except Exception:
            pass

        # Fallback: generate from tenant data
        trend = []
        for i in range(months - 1, -1, -1):
            month_date = now - timedelta(days=30 * i)
            month_str = month_date.strftime("%Y-%m")

            # Count tenants active in that month
            active_q = await db.execute(
                select(func.count(Tenant.id)).where(
                    Tenant.created_at <= month_date,
                    or_(
                        Tenant.status == "active",
                        Tenant.cancelled_at > month_date,
                    ),
                )
            )
            active = active_q.scalar() or 0

            # New tenants in that month
            month_start = month_date.replace(day=1)
            new_q = await db.execute(
                select(func.count(Tenant.id)).where(
                    Tenant.created_at >= month_start,
                    Tenant.created_at < month_start + timedelta(days=32),
                )
            )
            new_count = new_q.scalar() or 0

            trend.append(RevenueMonthDataPoint(
                month=month_str,
                mrr_cents=0,  # Simplified — live calc would be expensive for each month
                active_tenants=active,
                churned_tenants=0,
                new_tenants=new_count,
            ))

        # Set current month MRR to real value
        if trend:
            trend[-1].mrr_cents = await self._calculate_real_mrr(db)

        return trend

    async def _calculate_addon_revenue(self, db: AsyncSession) -> int:
        """Calculate monthly add-on revenue from tenant addons."""
        result = await db.execute(
            select(Tenant).where(Tenant.status == "active")
        )
        tenants = result.scalars().all()
        doctor_counts = await self._get_doctor_counts(db)

        total = 0
        for t in tenants:
            addons = t.addons or {}
            doc_count = doctor_counts.get(str(t.id), 1)
            if addons.get("voice_dictation"):
                total += 1000 * doc_count  # $10/doc/mo = 1000 cents
            if addons.get("ai_radiograph"):
                total += 2000 * doc_count  # $20/doc/mo = 2000 cents

        return total

    async def _get_plan_revenue_breakdown(
        self, db: AsyncSession
    ) -> list[RevenuePlanBreakdown]:
        """MRR breakdown by plan."""
        result = await db.execute(
            select(Plan.name, func.count(Tenant.id))
            .join(Tenant, Tenant.plan_id == Plan.id)
            .where(Tenant.status == "active")
            .group_by(Plan.name)
        )
        rows = result.all()
        doctor_counts = await self._get_doctor_counts(db)

        # For each plan, calculate actual MRR
        plan_mrr: dict[str, int] = {}
        plan_result = await db.execute(
            select(Tenant, Plan)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(Tenant.status == "active")
        )
        for tenant, plan in plan_result.all():
            if plan.pricing_model == "per_doctor":
                doc_count = doctor_counts.get(str(tenant.id), 0)
                extra = max(0, doc_count - plan.included_doctors)
                mrr = plan.price_cents + (extra * plan.additional_doctor_price_cents)
            else:
                mrr = plan.price_cents
            plan_mrr[plan.name] = plan_mrr.get(plan.name, 0) + mrr

        return [
            RevenuePlanBreakdown(
                plan_name=name, mrr_cents=plan_mrr.get(name, 0), tenant_count=count
            )
            for name, count in rows
        ]

    async def _get_country_revenue_breakdown(
        self, db: AsyncSession
    ) -> list[RevenueCountryBreakdown]:
        """MRR breakdown by country."""
        result = await db.execute(
            select(Tenant.country_code, func.count(Tenant.id))
            .where(Tenant.status == "active")
            .group_by(Tenant.country_code)
        )
        rows = result.all()

        # Simplified: distribute total MRR proportionally
        total_mrr = await self._calculate_real_mrr(db)
        total_tenants = sum(count for _, count in rows) or 1

        return [
            RevenueCountryBreakdown(
                country=country,
                mrr_cents=int(total_mrr * count / total_tenants),
                tenant_count=count,
            )
            for country, count in rows
        ]

    async def take_revenue_snapshot(self, *, db: AsyncSession) -> None:
        """Create a monthly revenue snapshot (called by maintenance worker)."""
        now = datetime.now(UTC)
        month_str = now.strftime("%Y-%m")

        mrr = await self._calculate_real_mrr(db)
        addon_rev = await self._calculate_addon_revenue(db)

        active_q = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status == "active")
        )
        active = active_q.scalar() or 0

        thirty_days_ago = now - timedelta(days=30)
        churned_q = await db.execute(
            select(func.count(Tenant.id)).where(
                Tenant.status == "cancelled",
                Tenant.cancelled_at >= thirty_days_ago,
            )
        )
        churned = churned_q.scalar() or 0

        new_q = await db.execute(
            select(func.count(Tenant.id)).where(
                Tenant.created_at >= thirty_days_ago,
            )
        )
        new_count = new_q.scalar() or 0

        patient_counts = await self._get_patient_counts(db)
        total_patients = sum(patient_counts.values())

        # Upsert snapshot
        await db.execute(
            text(
                "INSERT INTO public.admin_revenue_snapshots "
                "(month, mrr_cents, active_tenants, churned_tenants, new_tenants, "
                "total_patients, addon_revenue_cents) "
                "VALUES (:month, :mrr, :active, :churned, :new, :patients, :addon) "
                "ON CONFLICT (month) DO UPDATE SET "
                "mrr_cents = :mrr, active_tenants = :active, "
                "churned_tenants = :churned, new_tenants = :new, "
                "total_patients = :patients, addon_revenue_cents = :addon"
            ),
            {
                "month": month_str, "mrr": mrr, "active": active,
                "churned": churned, "new": new_count,
                "patients": total_patients, "addon": addon_rev,
            },
        )
        await db.commit()

    # ─── Add-on Usage (SA-R03) ─────────────────────────

    async def get_addon_usage(self, *, db: AsyncSession) -> AddonUsageResponse:
        """Get add-on adoption metrics and per-tenant usage."""
        result = await db.execute(
            select(Tenant, Plan)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(Tenant.status == "active")
        )
        tenant_plans = result.all()
        doctor_counts = await self._get_doctor_counts(db)

        eligible = 0
        voice_count = 0
        radio_count = 0
        total_addon_rev = 0
        tenants_list = []

        for tenant, plan in tenant_plans:
            # All Pro+ tenants are eligible for add-ons
            eligible += 1
            addons = tenant.addons or {}
            voice = bool(addons.get("voice_dictation"))
            radio = bool(addons.get("ai_radiograph"))
            doc_count = doctor_counts.get(str(tenant.id), 1)

            if voice:
                voice_count += 1
                total_addon_rev += 1000 * doc_count
            if radio:
                radio_count += 1
                total_addon_rev += 2000 * doc_count

            tenants_list.append(AddonTenantUsage(
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                plan_name=plan.name,
                voice_enabled=voice,
                radiograph_enabled=radio,
            ))

        upsell = eligible - voice_count  # tenants without voice add-on

        return AddonUsageResponse(
            metrics=AddonMetrics(
                total_eligible_tenants=eligible,
                voice_adoption_count=voice_count,
                voice_adoption_pct=round(voice_count / max(eligible, 1) * 100, 1),
                radiograph_adoption_count=radio_count,
                radiograph_adoption_pct=round(radio_count / max(eligible, 1) * 100, 1),
                total_addon_revenue_cents=total_addon_rev,
                upsell_candidates=upsell,
            ),
            tenants=tenants_list,
        )

    # ─── Onboarding Funnel (SA-G03) ────────────────────

    _ONBOARDING_LABELS = {
        0: "Registro",
        1: "Configuracion basica",
        2: "Primer doctor",
        3: "Primer paciente",
        4: "Primera cita",
        5: "Primera factura",
        6: "Completado",
    }

    async def get_onboarding_funnel(
        self, *, db: AsyncSession
    ) -> OnboardingFunnelResponse:
        """Get onboarding step completion funnel."""
        # Count tenants at each step
        result = await db.execute(
            select(Tenant.onboarding_step, func.count(Tenant.id))
            .where(Tenant.status.in_(["active", "pending"]))
            .group_by(Tenant.onboarding_step)
            .order_by(Tenant.onboarding_step)
        )
        step_counts = {step: count for step, count in result.all()}

        total_result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status.in_(["active", "pending"]))
        )
        total = total_result.scalar() or 1

        steps = []
        for step_num in range(7):
            count = step_counts.get(step_num, 0)
            # Cumulative: tenants AT or PAST this step
            cumulative = sum(
                step_counts.get(s, 0) for s in range(step_num, 7)
            )
            steps.append(OnboardingStepMetric(
                step=step_num,
                label=self._ONBOARDING_LABELS.get(step_num, f"Paso {step_num}"),
                tenant_count=cumulative,
                pct_of_total=round(cumulative / total * 100, 1),
            ))

        # Stuck tenants: at step 0-3 for more than 7 days
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        stuck_result = await db.execute(
            select(Tenant.id, Tenant.name, Tenant.onboarding_step, Tenant.owner_email, Tenant.created_at)
            .where(
                Tenant.status.in_(["active", "pending"]),
                Tenant.onboarding_step < 4,
                Tenant.created_at < seven_days_ago,
            )
            .order_by(Tenant.onboarding_step, Tenant.created_at)
            .limit(50)
        )
        stuck = [
            {
                "tenant_id": str(r[0]),
                "name": r[1],
                "step": r[2],
                "owner_email": r[3],
                "days_since_signup": (datetime.now(UTC) - r[4]).days,
            }
            for r in stuck_result.all()
        ]

        return OnboardingFunnelResponse(
            total_tenants=total,
            steps=steps,
            stuck_tenants=stuck,
        )

    @staticmethod
    def _announcement_to_response(a: Any) -> AnnouncementResponse:
        return AnnouncementResponse(
            id=str(a.id),
            title=a.title,
            body=a.body,
            announcement_type=a.announcement_type,
            visibility=a.visibility,
            visibility_filter=a.visibility_filter,
            is_dismissable=a.is_dismissable,
            is_active=a.is_active,
            starts_at=a.starts_at.isoformat() if a.starts_at else None,
            ends_at=a.ends_at.isoformat() if a.ends_at else None,
            created_by=str(a.created_by),
            created_at=a.created_at.isoformat(),
            updated_at=a.updated_at.isoformat(),
        )

    # ─── Private Helpers ────────────────────────────────

    async def _get_patient_counts(self, db: AsyncSession) -> dict[str, int]:
        """Get patient counts per tenant schema, cached in Redis."""
        try:
            cached = await redis_client.get(_CACHE_PATIENT_COUNTS_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        # Query all tenant schemas
        schema_result = await db.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tn_%'")
        )
        schemas = [row[0] for row in schema_result.all()]

        counts: dict[str, int] = {}
        for schema in schemas:
            try:
                count_result = await db.execute(
                    text(f'SELECT COUNT(*) FROM "{schema}".patients WHERE is_active = true')  # noqa: S608
                )
                counts[schema] = count_result.scalar() or 0
            except Exception:
                counts[schema] = 0

        # Cache for 10 minutes
        try:
            await redis_client.setex(
                _CACHE_PATIENT_COUNTS_KEY,
                _CACHE_ANALYTICS_TTL,
                json.dumps(counts),
            )
        except Exception:
            pass

        return counts

    async def _get_doctor_counts(self, db: AsyncSession) -> dict[str, int]:
        """Get doctor counts per tenant (by tenant_id), for MRR calculation."""
        try:
            cached = await redis_client.get(_CACHE_DOCTOR_COUNTS_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        result = await db.execute(
            select(UserTenantMembership.tenant_id, func.count(UserTenantMembership.id))
            .where(
                UserTenantMembership.status == "active",
                UserTenantMembership.role == "doctor",
            )
            .group_by(UserTenantMembership.tenant_id)
        )
        counts = {str(tid): count for tid, count in result.all()}

        try:
            await redis_client.setex(
                _CACHE_DOCTOR_COUNTS_KEY,
                _CACHE_ANALYTICS_TTL,
                json.dumps(counts),
            )
        except Exception:
            pass

        return counts

    async def _calculate_real_mrr(self, db: AsyncSession) -> int:
        """Calculate real MRR accounting for per-doctor pricing."""
        # Get all active tenants with their plans
        result = await db.execute(
            select(Tenant, Plan)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(Tenant.status == "active")
        )
        tenant_plans = result.all()

        doctor_counts = await self._get_doctor_counts(db)

        total_mrr = 0
        for tenant, plan in tenant_plans:
            if plan.pricing_model == "per_doctor":
                doc_count = doctor_counts.get(str(tenant.id), 0)
                extra_docs = max(0, doc_count - plan.included_doctors)
                total_mrr += plan.price_cents + (extra_docs * plan.additional_doctor_price_cents)
            else:
                total_mrr += plan.price_cents

        return total_mrr

    async def _calculate_churn_rate(self, db: AsyncSession) -> float:
        """Calculate churn rate: cancelled in last 30d / active at period start."""
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

        # Cancelled in last 30 days
        cancelled_result = await db.execute(
            select(func.count(Tenant.id)).where(
                Tenant.status == "cancelled",
                Tenant.cancelled_at >= thirty_days_ago,
            )
        )
        cancelled = cancelled_result.scalar() or 0

        # Active at start of period (current active + recently cancelled)
        active_result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status == "active")
        )
        active_now = active_result.scalar() or 0

        base = active_now + cancelled
        if base == 0:
            return 0.0

        return round(cancelled / base * 100, 2)

    async def _get_top_tenants(
        self, db: AsyncSession, patient_counts: dict[str, int]
    ) -> list[TopTenantItem]:
        """Get top 10 tenants by estimated MRR."""
        result = await db.execute(
            select(Tenant, Plan)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(Tenant.status == "active")
        )
        tenant_plans = result.all()

        doctor_counts = await self._get_doctor_counts(db)

        tenants_with_mrr = []
        for tenant, plan in tenant_plans:
            if plan.pricing_model == "per_doctor":
                doc_count = doctor_counts.get(str(tenant.id), 0)
                extra = max(0, doc_count - plan.included_doctors)
                mrr = plan.price_cents + (extra * plan.additional_doctor_price_cents)
            else:
                mrr = plan.price_cents

            tenants_with_mrr.append((tenant, mrr))

        # Sort by MRR descending, take top 10
        tenants_with_mrr.sort(key=lambda x: x[1], reverse=True)

        return [
            TopTenantItem(
                tenant_id=str(t.id),
                name=t.name,
                mrr_cents=mrr,
                patients=patient_counts.get(t.schema_name, 0),
            )
            for t, mrr in tenants_with_mrr[:10]
        ]

    # ─── Admin Notifications ─────────────────────────────

    async def create_admin_notification(
        self,
        *,
        db: AsyncSession,
        title: str,
        message: str,
        notification_type: str = "info",
        admin_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
    ) -> None:
        """Create an admin notification. If admin_id is None, visible to all admins."""
        from app.models.public.admin_notification import AdminNotification

        notification = AdminNotification(
            admin_id=admin_id,
            title=title,
            message=message,
            notification_type=notification_type,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.add(notification)
        await db.flush()

    async def get_admin_notifications(
        self,
        *,
        db: AsyncSession,
        admin_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> dict:
        """Get notifications for an admin (personal + broadcast where admin_id is NULL)."""
        from app.models.public.admin_notification import AdminNotification

        base_filter = or_(
            AdminNotification.admin_id == admin_id,
            AdminNotification.admin_id.is_(None),
        )
        if unread_only:
            base_filter = and_(base_filter, AdminNotification.is_read == False)  # noqa: E712

        # Total count
        count_q = select(func.count()).select_from(AdminNotification).where(base_filter)
        total = (await db.execute(count_q)).scalar() or 0

        # Unread count (always, regardless of filter)
        unread_filter = and_(
            or_(AdminNotification.admin_id == admin_id, AdminNotification.admin_id.is_(None)),
            AdminNotification.is_read == False,  # noqa: E712
        )
        unread_q = select(func.count()).select_from(AdminNotification).where(unread_filter)
        unread_count = (await db.execute(unread_q)).scalar() or 0

        # Paginated items
        offset = (page - 1) * page_size
        items_q = (
            select(AdminNotification)
            .where(base_filter)
            .order_by(AdminNotification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(items_q)
        items = result.scalars().all()

        return {"items": items, "unread_count": unread_count, "total": total}

    async def mark_notification_read(
        self,
        *,
        db: AsyncSession,
        notification_id: uuid.UUID,
        admin_id: uuid.UUID,
    ) -> bool:
        """Mark a notification as read. Returns True if found and updated."""
        from app.models.public.admin_notification import AdminNotification

        q = (
            select(AdminNotification)
            .where(
                AdminNotification.id == notification_id,
                or_(AdminNotification.admin_id == admin_id, AdminNotification.admin_id.is_(None)),
            )
        )
        result = await db.execute(q)
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            await db.flush()
            return True
        return False

    async def mark_all_notifications_read(
        self,
        *,
        db: AsyncSession,
        admin_id: uuid.UUID,
    ) -> int:
        """Mark all notifications as read for an admin. Returns count updated."""
        from app.models.public.admin_notification import AdminNotification

        q = (
            update(AdminNotification)
            .where(
                or_(AdminNotification.admin_id == admin_id, AdminNotification.admin_id.is_(None)),
                AdminNotification.is_read == False,  # noqa: E712
            )
            .values(is_read=True)
        )
        result = await db.execute(q)
        await db.flush()
        return result.rowcount

    def _generate_impersonation_jwt(
        self,
        admin_id: str,
        tenant_id: str,
        tenant_schema: str,
        session_id: str | None = None,
        duration_minutes: int = 60,
    ) -> str:
        """Create an RS256 JWT that impersonates a clinic_owner."""
        from jose import jwt as jose_jwt

        from app.auth.permissions import get_permissions_for_role

        now = datetime.now(UTC)
        jti = f"imp_{uuid.uuid4().hex}"
        permissions = list(get_permissions_for_role("clinic_owner"))

        payload: dict[str, Any] = {
            "sub": f"admin_{admin_id}",
            "tid": f"tn_{tenant_id}" if not tenant_id.startswith("tn_") else tenant_id,
            "role": "clinic_owner",
            "perms": permissions,
            "email": "admin@dentalos.app",
            "name": "Superadmin (Impersonation)",
            "tver": 0,
            "impersonated": True,
            "impersonated_by": f"admin_{admin_id}",
            "impersonation_session_id": session_id,
            "iat": now,
            "exp": now + timedelta(minutes=duration_minutes),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": jti,
        }
        headers = {"kid": settings.jwt_key_id}
        return jose_jwt.encode(
            payload,
            _load_private_key(),
            algorithm=settings.jwt_algorithm,
            headers=headers,
        )

    @staticmethod
    def _plan_to_response(plan: Plan) -> PlanResponse:
        return PlanResponse(
            id=str(plan.id),
            name=plan.name,
            slug=plan.slug,
            price_cents=plan.price_cents,
            pricing_model=plan.pricing_model,
            included_doctors=plan.included_doctors,
            additional_doctor_price_cents=plan.additional_doctor_price_cents,
            max_patients=plan.max_patients,
            max_doctors=plan.max_doctors,
            features=plan.features,
            is_active=plan.is_active,
        )

    @staticmethod
    def _flag_to_response(flag: FeatureFlag) -> FeatureFlagResponse:
        return FeatureFlagResponse(
            id=str(flag.id),
            flag_name=flag.flag_name,
            scope=flag.scope,
            plan_filter=flag.plan_filter,
            tenant_id=str(flag.tenant_id) if flag.tenant_id else None,
            enabled=flag.enabled,
            description=flag.description,
            expires_at=flag.expires_at.isoformat() if flag.expires_at else None,
            reason=flag.reason,
        )

    # ─── SA-U01: Cross-Tenant User Search ──────────────────

    async def search_users_cross_tenant(
        self,
        *,
        db: AsyncSession,
        search: str,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
    ) -> CrossTenantUserListResponse:
        """Search users across all tenant schemas via user_tenant_memberships."""
        search_term = f"%{search.strip().lower()}%"
        offset = (page - 1) * page_size

        # Get all tenant schemas to query users table across schemas
        schemas_result = await db.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name LIKE 'tn_%' ORDER BY schema_name"
            )
        )
        schemas = [r[0] for r in schemas_result.fetchall()]

        if not schemas:
            return CrossTenantUserListResponse(
                items=[], total=0, page=page, page_size=page_size
            )

        # Build UNION ALL across tenant schemas to search by email/name
        union_parts = []
        for schema in schemas:
            union_parts.append(
                f"SELECT u.id AS user_id, u.email, u.first_name, u.last_name, "
                f"u.last_login_at, "
                f"m.role, m.status AS membership_status, m.tenant_id "
                f"FROM {schema}.users u "
                f"JOIN public.user_tenant_memberships m ON m.user_id = u.id "
                f"AND m.tenant_id = ("
                f"  SELECT t.id FROM public.tenants t WHERE t.schema_name = '{schema}' LIMIT 1"
                f") "
                f"WHERE (LOWER(u.email) LIKE :search "
                f"OR LOWER(u.first_name) LIKE :search "
                f"OR LOWER(u.last_name) LIKE :search)"
            )

        union_sql = " UNION ALL ".join(union_parts)

        role_filter = ""
        if role:
            role_filter = f" AND role = :role"

        # Count total
        count_sql = f"SELECT COUNT(*) FROM ({union_sql}) AS combined WHERE 1=1{role_filter}"
        params: dict[str, Any] = {"search": search_term}
        if role:
            params["role"] = role

        count_result = await db.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        if total == 0:
            return CrossTenantUserListResponse(
                items=[], total=0, page=page, page_size=page_size
            )

        # Fetch page
        data_sql = (
            f"SELECT user_id, email, first_name, last_name, role, "
            f"membership_status, tenant_id, last_login_at "
            f"FROM ({union_sql}) AS combined WHERE 1=1{role_filter} "
            f"ORDER BY email LIMIT :limit OFFSET :offset"
        )
        params["limit"] = page_size
        params["offset"] = offset

        data_result = await db.execute(text(data_sql), params)
        rows = data_result.fetchall()

        # Gather tenant names
        tenant_ids = list({str(r[6]) for r in rows})
        tenant_names: dict[str, str] = {}
        if tenant_ids:
            t_result = await db.execute(
                select(Tenant.id, Tenant.name).where(
                    Tenant.id.in_([uuid.UUID(tid) for tid in tenant_ids])
                )
            )
            for t in t_result.fetchall():
                tenant_names[str(t[0])] = t[1]

        # Check multi-clinic users
        user_ids = list({str(r[0]) for r in rows})
        multi_clinic: set[str] = set()
        if user_ids:
            mc_result = await db.execute(
                text(
                    "SELECT user_id FROM public.user_tenant_memberships "
                    "GROUP BY user_id HAVING COUNT(DISTINCT tenant_id) > 1"
                )
            )
            multi_clinic = {str(r[0]) for r in mc_result.fetchall()}

        items = [
            CrossTenantUserItem(
                user_id=str(r[0]),
                email=r[1],
                first_name=r[2],
                last_name=r[3],
                role=r[4],
                status=r[5],
                tenant_id=str(r[6]),
                tenant_name=tenant_names.get(str(r[6]), "Unknown"),
                last_login_at=r[7].isoformat() if r[7] else None,
                is_multi_clinic=str(r[0]) in multi_clinic,
            )
            for r in rows
        ]

        return CrossTenantUserListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    # ─── SA-O02: Database Metrics ──────────────────────────

    _CACHE_DB_METRICS_KEY = "dentalos:admin:db_metrics"
    _CACHE_DB_METRICS_TTL = 300  # 5 minutes

    async def get_database_metrics(
        self, *, db: AsyncSession
    ) -> DatabaseMetricsResponse:
        """Aggregate PostgreSQL performance and size metrics."""
        # Check cache first
        if redis_client:
            cached = await redis_client.get(self._CACHE_DB_METRICS_KEY)
            if cached:
                return DatabaseMetricsResponse(**json.loads(cached))

        # DB size
        size_result = await db.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        )
        total_db_size = size_result.scalar() or "0 bytes"

        # Schema count
        schema_result = await db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.schemata "
                "WHERE schema_name LIKE 'tn_%'"
            )
        )
        schema_count = schema_result.scalar() or 0

        # Connection pool - estimate from pg_stat_activity
        pool_result = await db.execute(
            text(
                "SELECT "
                "  COUNT(*) FILTER (WHERE state = 'active') AS active, "
                "  COUNT(*) FILTER (WHERE state = 'idle') AS idle, "
                "  (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_conn "
                "FROM pg_stat_activity WHERE datname = current_database()"
            )
        )
        pool_row = pool_result.fetchone()
        pool_active = pool_row[0] if pool_row else 0
        pool_idle = pool_row[1] if pool_row else 0
        pool_max = pool_row[2] if pool_row else 100

        # Index hit ratio
        idx_result = await db.execute(
            text(
                "SELECT COALESCE("
                "  SUM(idx_blks_hit) / NULLIF(SUM(idx_blks_hit) + SUM(idx_blks_read), 0), "
                "  0"
                ") FROM pg_statio_user_indexes"
            )
        )
        index_hit_ratio = round(float(idx_result.scalar() or 0) * 100, 2)

        # Cache hit ratio
        cache_result = await db.execute(
            text(
                "SELECT COALESCE("
                "  SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0), "
                "  0"
                ") FROM pg_statio_user_tables"
            )
        )
        cache_hit_ratio = round(float(cache_result.scalar() or 0) * 100, 2)

        # Largest tables (top 10)
        tables_result = await db.execute(
            text(
                "SELECT schemaname, relname, "
                "  pg_size_pretty(pg_total_relation_size(schemaname || '.' || relname)) AS total_size, "
                "  n_live_tup "
                "FROM pg_stat_user_tables "
                "ORDER BY pg_total_relation_size(schemaname || '.' || relname) DESC "
                "LIMIT 10"
            )
        )
        largest_tables = [
            TableSizeItem(
                schema_name=r[0],
                table_name=r[1],
                total_size=r[2],
                row_count=r[3],
            )
            for r in tables_result.fetchall()
        ]

        # Slow queries (pg_stat_statements if available)
        slow_queries: list[SlowQueryItem] = []
        try:
            sq_result = await db.execute(
                text(
                    "SELECT query, calls, mean_exec_time, total_exec_time "
                    "FROM pg_stat_statements "
                    "WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database()) "
                    "ORDER BY mean_exec_time DESC LIMIT 10"
                )
            )
            slow_queries = [
                SlowQueryItem(
                    query=r[0][:200],  # truncate for safety
                    calls=r[1],
                    mean_time_ms=round(r[2], 2),
                    total_time_ms=round(r[3], 2),
                )
                for r in sq_result.fetchall()
            ]
        except Exception:
            # pg_stat_statements extension might not be enabled —
            # rollback to clear the failed transaction state
            await db.rollback()

        # Dead tuples
        dead_result = await db.execute(
            text("SELECT COALESCE(SUM(n_dead_tup), 0) FROM pg_stat_user_tables")
        )
        dead_tuples_total = int(dead_result.scalar() or 0)

        response = DatabaseMetricsResponse(
            total_db_size=total_db_size,
            schema_count=schema_count,
            connection_pool_active=pool_active,
            connection_pool_idle=pool_idle,
            connection_pool_max=pool_max,
            index_hit_ratio=index_hit_ratio,
            cache_hit_ratio=cache_hit_ratio,
            largest_tables=largest_tables,
            slow_queries=slow_queries,
            dead_tuples_total=dead_tuples_total,
        )

        # Cache result
        if redis_client:
            await redis_client.setex(
                self._CACHE_DB_METRICS_KEY,
                self._CACHE_DB_METRICS_TTL,
                json.dumps(response.model_dump()),
            )

        return response

    # ─── SA-A03: Bulk Operations ───────────────────────────

    async def execute_bulk_operation(
        self,
        *,
        db: AsyncSession,
        tenant_ids: list[str],
        action: str,
        admin_id: str,
        plan_id: str | None = None,
        trial_days: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> BulkOperationResponse:
        """Execute a bulk action on multiple tenants."""
        results: list[BulkOperationResult] = []

        for tid in tenant_ids:
            try:
                tenant_uuid = uuid.UUID(tid)
                stmt = select(Tenant).where(Tenant.id == tenant_uuid)
                result = await db.execute(stmt)
                tenant = result.scalar_one_or_none()

                if not tenant:
                    results.append(BulkOperationResult(
                        tenant_id=tid, tenant_name="Not found",
                        success=False, error="Tenant not found",
                    ))
                    continue

                if action == "suspend":
                    if tenant.status == "suspended":
                        results.append(BulkOperationResult(
                            tenant_id=tid, tenant_name=tenant.name,
                            success=False, error="Already suspended",
                        ))
                        continue
                    tenant.status = "suspended"
                    tenant.suspended_at = datetime.now(UTC)

                elif action == "unsuspend":
                    if tenant.status != "suspended":
                        results.append(BulkOperationResult(
                            tenant_id=tid, tenant_name=tenant.name,
                            success=False, error="Not currently suspended",
                        ))
                        continue
                    tenant.status = "active"
                    tenant.suspended_at = None

                elif action == "change_plan":
                    if not plan_id:
                        results.append(BulkOperationResult(
                            tenant_id=tid, tenant_name=tenant.name,
                            success=False, error="plan_id required",
                        ))
                        continue
                    plan_result = await db.execute(
                        select(Plan).where(Plan.id == uuid.UUID(plan_id))
                    )
                    plan = plan_result.scalar_one_or_none()
                    if not plan:
                        results.append(BulkOperationResult(
                            tenant_id=tid, tenant_name=tenant.name,
                            success=False, error="Plan not found",
                        ))
                        continue
                    tenant.plan_id = plan.id

                elif action == "extend_trial":
                    days = trial_days or 14
                    if tenant.trial_ends_at:
                        base = max(tenant.trial_ends_at, datetime.now(UTC))
                    else:
                        base = datetime.now(UTC)
                    tenant.trial_ends_at = base + timedelta(days=days)

                results.append(BulkOperationResult(
                    tenant_id=tid, tenant_name=tenant.name, success=True,
                ))

                # Audit log
                await self.log_admin_action(
                    db=db,
                    admin_id=admin_id,
                    action=f"bulk_{action}",
                    resource_type="tenant",
                    resource_id=tid,
                    details={"plan_id": plan_id, "trial_days": trial_days},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            except Exception as exc:
                results.append(BulkOperationResult(
                    tenant_id=tid, tenant_name="Error",
                    success=False, error=str(exc),
                ))

        await db.commit()

        succeeded = sum(1 for r in results if r.success)
        return BulkOperationResponse(
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=results,
        )

    # ─── SA-C01: Compliance Dashboard ──────────────────────

    async def get_compliance_dashboard(
        self, *, db: AsyncSession
    ) -> ComplianceDashboardResponse:
        """Compliance status across Colombian tenants."""
        # Get Colombian tenants (Resolucion 1888 applies)
        result = await db.execute(
            select(Tenant).where(
                and_(Tenant.country_code == "CO", Tenant.status == "active")
            )
        )
        tenants = list(result.scalars().all())
        total_co = len(tenants)

        items: list[TenantComplianceItem] = []
        rips_ok = 0
        rda_ok = 0
        consent_ok = 0
        total_doctors = 0
        verified_doctors = 0

        schemas_result = await db.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name LIKE 'tn_%'"
            )
        )
        schema_names = {r[0] for r in schemas_result.fetchall()}

        for tenant in tenants:
            schema = tenant.schema_name
            if schema not in schema_names:
                continue

            # RIPS status
            rips_status = "never"
            last_rips_at = None
            try:
                rips_result = await db.execute(
                    text(
                        f"SELECT MAX(created_at) FROM {schema}.rips_reports "
                        f"WHERE is_active = true"
                    )
                )
                last_rips = rips_result.scalar()
                if last_rips:
                    last_rips_at = last_rips.isoformat()
                    days_since = (datetime.now(UTC) - last_rips).days
                    rips_status = "up_to_date" if days_since <= 30 else "overdue"
            except Exception:
                rips_status = "never"

            # RDA status
            rda_status = "never"
            last_rda_at = None
            try:
                rda_result = await db.execute(
                    text(
                        f"SELECT MAX(created_at) FROM {schema}.rda_reports "
                        f"WHERE is_active = true"
                    )
                )
                last_rda = rda_result.scalar()
                if last_rda:
                    last_rda_at = last_rda.isoformat()
                    days_since = (datetime.now(UTC) - last_rda).days
                    rda_status = "up_to_date" if days_since <= 365 else "overdue"
            except Exception:
                rda_status = "never"

            # Consent templates count
            consent_count = 0
            consent_required = 3  # minimum required templates
            try:
                ct_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.consent_templates "
                        f"WHERE is_active = true"
                    )
                )
                consent_count = ct_result.scalar() or 0
            except Exception:
                pass

            # Doctor count and RETHUS verification
            doc_count = 0
            doc_verified = 0
            try:
                doc_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.users "
                        f"WHERE role = 'doctor' AND is_active = true"
                    )
                )
                doc_count = doc_result.scalar() or 0

                ver_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.users u "
                        f"WHERE u.role = 'doctor' AND u.is_active = true "
                        f"AND EXISTS ("
                        f"  SELECT 1 FROM {schema}.rethus_verifications rv "
                        f"  WHERE rv.user_id = u.id AND rv.is_verified = true"
                        f")"
                    )
                )
                doc_verified = ver_result.scalar() or 0
            except Exception:
                pass

            total_doctors += doc_count
            verified_doctors += doc_verified

            if rips_status == "up_to_date":
                rips_ok += 1
            if rda_status == "up_to_date":
                rda_ok += 1
            if consent_count >= consent_required:
                consent_ok += 1

            items.append(TenantComplianceItem(
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                country_code=tenant.country_code,
                rips_status=rips_status,
                rda_status=rda_status,
                consent_templates_count=consent_count,
                consent_templates_required=consent_required,
                doctors_verified=doc_verified,
                doctors_total=doc_count,
                last_rips_at=last_rips_at,
                last_rda_at=last_rda_at,
            ))

        kpis = ComplianceKPIs(
            total_colombian_tenants=total_co,
            rips_compliant=rips_ok,
            rips_compliant_pct=round(rips_ok / max(total_co, 1) * 100, 1),
            rda_compliant=rda_ok,
            rda_compliant_pct=round(rda_ok / max(total_co, 1) * 100, 1),
            consent_compliant=consent_ok,
            consent_compliant_pct=round(consent_ok / max(total_co, 1) * 100, 1),
            rethus_verified_pct=round(
                verified_doctors / max(total_doctors, 1) * 100, 1
            ),
        )

        return ComplianceDashboardResponse(kpis=kpis, tenants=items)

    # ─── SA-C02: Security Alerts ───────────────────────────

    async def get_security_alerts(
        self, *, db: AsyncSession, page: int = 1, page_size: int = 50
    ) -> SecurityAlertListResponse:
        """Analyze audit logs for security-relevant events."""
        now = datetime.now(UTC)
        last_24h = now - timedelta(hours=24)
        offset = (page - 1) * page_size

        alerts: list[SecurityAlertItem] = []

        # Failed login attempts in last 24h
        failed_result = await db.execute(
            text(
                "SELECT id, admin_id, ip_address, details, created_at "
                "FROM admin_audit_logs "
                "WHERE action = 'login_failed' AND created_at >= :since "
                "ORDER BY created_at DESC LIMIT 50"
            ),
            {"since": last_24h},
        )
        failed_rows = failed_result.fetchall()
        failed_logins_24h = len(failed_rows)

        for r in failed_rows:
            alerts.append(SecurityAlertItem(
                id=str(r[0]),
                alert_type="failed_login",
                severity="warning",
                message=f"Failed login attempt from {r[2] or 'unknown IP'}",
                source_ip=r[2],
                admin_id=str(r[1]) if r[1] else None,
                details=r[3] if isinstance(r[3], dict) else {},
                created_at=r[4].isoformat(),
            ))

        # After-hours admin actions (outside 7am-10pm)
        after_hours_result = await db.execute(
            text(
                "SELECT id, admin_id, action, ip_address, details, created_at "
                "FROM admin_audit_logs "
                "WHERE created_at >= :since "
                "AND EXTRACT(HOUR FROM created_at) NOT BETWEEN 7 AND 22 "
                "AND action != 'login_failed' "
                "ORDER BY created_at DESC LIMIT 20"
            ),
            {"since": last_24h},
        )
        after_hours_rows = after_hours_result.fetchall()
        after_hours_count = len(after_hours_rows)

        for r in after_hours_rows:
            alerts.append(SecurityAlertItem(
                id=str(r[0]),
                alert_type="after_hours",
                severity="info",
                message=f"After-hours action: {r[2]}",
                source_ip=r[3],
                admin_id=str(r[1]) if r[1] else None,
                details=r[4] if isinstance(r[4], dict) else {},
                created_at=r[5].isoformat(),
            ))

        # Suspicious IPs — IPs with >5 failed logins
        suspicious_result = await db.execute(
            text(
                "SELECT ip_address, COUNT(*) AS cnt "
                "FROM admin_audit_logs "
                "WHERE action = 'login_failed' AND created_at >= :since "
                "AND ip_address IS NOT NULL "
                "GROUP BY ip_address HAVING COUNT(*) >= 5 "
                "ORDER BY cnt DESC"
            ),
            {"since": last_24h},
        )
        suspicious_ips_rows = suspicious_result.fetchall()
        suspicious_ips_count = len(suspicious_ips_rows)

        for r in suspicious_ips_rows:
            alerts.append(SecurityAlertItem(
                id=f"suspicious-{r[0]}",
                alert_type="suspicious_ip",
                severity="critical",
                message=f"IP {r[0]} has {r[1]} failed login attempts in 24h",
                source_ip=r[0],
                details={"failed_count": r[1]},
                created_at=now.isoformat(),
            ))

        # Sort by severity then time
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 3), a.created_at), reverse=True)

        total = len(alerts)
        paginated = alerts[offset: offset + page_size]

        return SecurityAlertListResponse(
            items=paginated,
            total=total,
            failed_logins_24h=failed_logins_24h,
            suspicious_ips=suspicious_ips_count,
            after_hours_actions=after_hours_count,
        )

    # ─── SA-C03: Data Retention ────────────────────────────

    async def get_data_retention(
        self, *, db: AsyncSession
    ) -> DataRetentionResponse:
        """Data retention policies and archivable tenants."""
        # Define retention policies
        policies = [
            RetentionPolicyItem(
                data_type="clinical_records",
                description="Historias clínicas y registros de evolución",
                retention_days=3650,  # 10 years (Colombian law)
                current_oldest=None,
                records_eligible=0,
            ),
            RetentionPolicyItem(
                data_type="audit_logs",
                description="Registro de auditoría administrativa",
                retention_days=1825,  # 5 years
                current_oldest=None,
                records_eligible=0,
            ),
            RetentionPolicyItem(
                data_type="notifications",
                description="Notificaciones y mensajes del sistema",
                retention_days=365,  # 1 year
                current_oldest=None,
                records_eligible=0,
            ),
            RetentionPolicyItem(
                data_type="consent_records",
                description="Consentimientos informados firmados",
                retention_days=3650,  # 10 years
                current_oldest=None,
                records_eligible=0,
            ),
        ]

        # Get oldest audit log
        try:
            oldest_audit = await db.execute(
                text("SELECT MIN(created_at) FROM admin_audit_logs")
            )
            oldest = oldest_audit.scalar()
            if oldest:
                policies[1].current_oldest = oldest.isoformat()
                cutoff = datetime.now(UTC) - timedelta(days=1825)
                count_result = await db.execute(
                    text(
                        "SELECT COUNT(*) FROM admin_audit_logs "
                        "WHERE created_at < :cutoff"
                    ),
                    {"cutoff": cutoff},
                )
                policies[1].records_eligible = count_result.scalar() or 0
        except Exception:
            pass

        # Archivable tenants: cancelled > 1 year ago
        one_year_ago = datetime.now(UTC) - timedelta(days=365)
        arch_result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.status == "cancelled",
                    Tenant.cancelled_at.isnot(None),
                    Tenant.cancelled_at < one_year_ago,
                )
            ).order_by(Tenant.cancelled_at)
        )
        archivable_tenants = [
            ArchivableTenantItem(
                tenant_id=str(t.id),
                tenant_name=t.name,
                status=t.status,
                cancelled_at=t.cancelled_at.isoformat() if t.cancelled_at else None,
                days_since_cancelled=(datetime.now(UTC) - t.cancelled_at).days
                if t.cancelled_at else 0,
            )
            for t in arch_result.scalars().all()
        ]

        return DataRetentionResponse(
            policies=policies,
            archivable_tenants=archivable_tenants,
            total_archivable=len(archivable_tenants),
        )

    # ─── SA-U02: Tenant Usage Analytics ────────────────────

    _CACHE_TENANT_HEALTH_KEY = "dentalos:admin:tenant_health"
    _CACHE_TENANT_HEALTH_TTL = 1800  # 30 minutes

    async def get_tenant_health(
        self, *, db: AsyncSession
    ) -> TenantHealthListResponse:
        """Per-tenant usage metrics and health scores."""
        # Check cache
        if redis_client:
            cached = await redis_client.get(self._CACHE_TENANT_HEALTH_KEY)
            if cached:
                return TenantHealthListResponse(**json.loads(cached))

        now = datetime.now(UTC)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)

        # Get all active tenants with plan names
        tenants_result = await db.execute(
            select(Tenant, Plan.name.label("plan_name")).join(
                Plan, Tenant.plan_id == Plan.id
            ).where(Tenant.status == "active")
        )
        rows = tenants_result.fetchall()

        schemas_result = await db.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name LIKE 'tn_%'"
            )
        )
        schema_names = {r[0] for r in schemas_result.fetchall()}

        items: list[TenantUsageMetrics] = []
        healthy = 0
        at_risk = 0
        critical = 0

        for row in rows:
            tenant = row[0]
            plan_name = row[1]
            schema = tenant.schema_name

            if schema not in schema_names:
                continue

            # Active users (7d) — users with last_login_at in last 7 days
            try:
                au_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.users "
                        f"WHERE is_active = true AND last_login_at >= :since"
                    ),
                    {"since": last_7d},
                )
                active_users_7d = au_result.scalar() or 0
            except Exception:
                active_users_7d = 0

            # Patients created (30d)
            try:
                pc_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.patients "
                        f"WHERE created_at >= :since"
                    ),
                    {"since": last_30d},
                )
                patients_30d = pc_result.scalar() or 0
            except Exception:
                patients_30d = 0

            # Appointments (30d)
            try:
                ap_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.appointments "
                        f"WHERE created_at >= :since"
                    ),
                    {"since": last_30d},
                )
                appointments_30d = ap_result.scalar() or 0
            except Exception:
                appointments_30d = 0

            # Invoices (30d)
            try:
                inv_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.invoices "
                        f"WHERE created_at >= :since"
                    ),
                    {"since": last_30d},
                )
                invoices_30d = inv_result.scalar() or 0
            except Exception:
                invoices_30d = 0

            # Clinical records (30d)
            try:
                cr_result = await db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.clinical_records "
                        f"WHERE created_at >= :since"
                    ),
                    {"since": last_30d},
                )
                records_30d = cr_result.scalar() or 0
            except Exception:
                records_30d = 0

            # Health score: 0-100 composite
            score = 0
            if active_users_7d > 0:
                score += 30
            if patients_30d > 0:
                score += 20
            if appointments_30d > 0:
                score += 20
            if invoices_30d > 0:
                score += 15
            if records_30d > 0:
                score += 15

            risk = "healthy" if score >= 50 else ("at_risk" if score >= 20 else "critical")
            if risk == "healthy":
                healthy += 1
            elif risk == "at_risk":
                at_risk += 1
            else:
                critical += 1

            items.append(TenantUsageMetrics(
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                plan_name=plan_name,
                active_users_7d=active_users_7d,
                patients_created_30d=patients_30d,
                appointments_30d=appointments_30d,
                invoices_30d=invoices_30d,
                clinical_records_30d=records_30d,
                health_score=score,
                risk_level=risk,
            ))

        # Sort by health score ascending (worst first)
        items.sort(key=lambda x: x.health_score)

        response = TenantHealthListResponse(
            items=items,
            total=len(items),
            healthy_count=healthy,
            at_risk_count=at_risk,
            critical_count=critical,
        )

        if redis_client:
            await redis_client.setex(
                self._CACHE_TENANT_HEALTH_KEY,
                self._CACHE_TENANT_HEALTH_TTL,
                json.dumps(response.model_dump()),
            )

        return response

    # ─── SA-G01: Cohort Analysis ───────────────────────────

    async def get_cohort_analysis(
        self, *, db: AsyncSession, months: int = 12
    ) -> CohortAnalysisResponse:
        """Monthly cohort retention matrix."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=months * 30)

        # Get all tenants created in the window
        result = await db.execute(
            select(Tenant).where(Tenant.created_at >= start_date).order_by(
                Tenant.created_at
            )
        )
        tenants = list(result.scalars().all())

        # Group by signup month
        cohort_map: dict[str, list[Any]] = {}
        for t in tenants:
            month_key = t.created_at.strftime("%Y-%m")
            cohort_map.setdefault(month_key, []).append(t)

        cohorts: list[CohortRow] = []
        churn_month_counts: dict[int, int] = {}

        for month_key in sorted(cohort_map.keys()):
            members = cohort_map[month_key]
            signup_count = len(members)
            retention: list[float] = []

            # Calculate retention at each month offset
            cohort_start = datetime.strptime(month_key, "%Y-%m").replace(
                tzinfo=UTC
            )
            max_months = min(
                months,
                (now.year - cohort_start.year) * 12
                + now.month
                - cohort_start.month
                + 1,
            )

            for m in range(max_months):
                check_date = cohort_start + timedelta(days=m * 30)
                still_active = 0
                for t in members:
                    # Tenant was still active at this point
                    if t.status == "active" or (
                        t.cancelled_at and t.cancelled_at > check_date
                    ):
                        still_active += 1
                    elif t.status == "active":
                        still_active += 1
                pct = round(still_active / max(signup_count, 1) * 100, 1)
                retention.append(pct)

                # Track churn month
                if m > 0 and pct < retention[m - 1]:
                    churn_month_counts[m] = churn_month_counts.get(m, 0) + 1

            cohorts.append(CohortRow(
                cohort_month=month_key,
                signup_count=signup_count,
                retention=retention,
            ))

        # Average churn month
        avg_churn_month = 0
        if churn_month_counts:
            avg_churn_month = max(churn_month_counts, key=churn_month_counts.get)

        return CohortAnalysisResponse(
            cohorts=cohorts,
            months_tracked=months,
            avg_churn_month=avg_churn_month,
        )

    # ─── SA-G02: Feature Adoption ──────────────────────────

    _FEATURES_TRACKED = [
        "odontogram", "appointments", "billing", "portal",
        "whatsapp", "voice", "ai_reports", "telemedicine",
    ]

    _FEATURE_TABLE_MAP = {
        "odontogram": "odontograms",
        "appointments": "appointments",
        "billing": "invoices",
        "portal": "portal_sessions",
        "whatsapp": "whatsapp_messages",
        "voice": "voice_commands",
        "ai_reports": "ai_report_requests",
        "telemedicine": "telemedicine_sessions",
    }

    async def get_feature_adoption(
        self, *, db: AsyncSession
    ) -> FeatureAdoptionResponse:
        """Feature adoption matrix across all active tenants."""
        # Get active tenants
        tenants_result = await db.execute(
            select(Tenant, Plan.name.label("plan_name")).join(
                Plan, Tenant.plan_id == Plan.id
            ).where(Tenant.status == "active")
        )
        rows = tenants_result.fetchall()

        schemas_result = await db.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name LIKE 'tn_%'"
            )
        )
        schema_names = {r[0] for r in schemas_result.fetchall()}

        items: list[TenantFeatureUsage] = []
        feature_counts: dict[str, int] = {f: 0 for f in self._FEATURES_TRACKED}

        for row in rows:
            tenant = row[0]
            plan_name = row[1]
            schema = tenant.schema_name

            if schema not in schema_names:
                continue

            usage: dict[str, bool] = {}
            for feature, table in self._FEATURE_TABLE_MAP.items():
                try:
                    result = await db.execute(
                        text(f"SELECT EXISTS(SELECT 1 FROM {schema}.{table} LIMIT 1)")
                    )
                    usage[feature] = result.scalar() or False
                except Exception:
                    usage[feature] = False

                if usage[feature]:
                    feature_counts[feature] += 1

            features_used = sum(1 for v in usage.values() if v)

            items.append(TenantFeatureUsage(
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                plan_name=plan_name,
                odontogram=usage.get("odontogram", False),
                appointments=usage.get("appointments", False),
                billing=usage.get("billing", False),
                portal=usage.get("portal", False),
                whatsapp=usage.get("whatsapp", False),
                voice=usage.get("voice", False),
                ai_reports=usage.get("ai_reports", False),
                telemedicine=usage.get("telemedicine", False),
                features_used=features_used,
                features_total=len(self._FEATURES_TRACKED),
            ))

        total = len(items)
        summary = [
            FeatureAdoptionSummary(
                feature_name=f,
                adoption_count=feature_counts[f],
                adoption_pct=round(feature_counts[f] / max(total, 1) * 100, 1),
            )
            for f in self._FEATURES_TRACKED
        ]

        return FeatureAdoptionResponse(
            summary=summary,
            tenants=items,
            total_tenants=total,
        )

    # ─── SA-E02: Broadcast Messaging ──────────────────────

    async def send_broadcast(
        self,
        *,
        db: AsyncSession,
        subject: str,
        body: str,
        admin_id: str,
        template: str | None = None,
        filter_plan: str | None = None,
        filter_country: str | None = None,
        filter_status: str | None = None,
    ) -> BroadcastSendResponse:
        """Queue a broadcast email to filtered clinic owners."""
        # Count recipients
        filters = []
        if filter_status:
            filters.append(Tenant.status == filter_status)
        else:
            filters.append(Tenant.status == "active")
        if filter_country:
            filters.append(Tenant.country_code == filter_country.upper())
        if filter_plan:
            filters.append(Tenant.plan_id == uuid.UUID(filter_plan))

        # Fetch recipient tenant owner emails
        result = await db.execute(
            select(Tenant.id, Tenant.owner_email, Tenant.name).where(and_(*filters))
        )
        recipients = result.fetchall()
        recipients_count = len(recipients)

        # Insert broadcast record
        broadcast_id = str(uuid.uuid4())
        await db.execute(
            text(
                "INSERT INTO admin_broadcast_history "
                "(id, subject, body, template, filter_plan, filter_country, "
                "filter_status, recipients_count, sent_by) "
                "VALUES (:id, :subject, :body, :template, :plan, :country, "
                ":status, :count, :admin_id)"
            ),
            {
                "id": broadcast_id,
                "subject": subject,
                "body": body,
                "template": template,
                "plan": filter_plan,
                "country": filter_country,
                "status": filter_status,
                "count": recipients_count,
                "admin_id": admin_id,
            },
        )
        await db.commit()

        # Queue email delivery via RabbitMQ notification worker
        from app.core.queue import publish_message
        from app.schemas.queue import QueueMessage

        for tenant_row in recipients:
            tenant_id_val = str(tenant_row.id)
            await publish_message(
                "notifications",
                QueueMessage(
                    tenant_id=tenant_id_val,
                    job_type="email.send",
                    payload={
                        "to": tenant_row.owner_email,
                        "subject": subject,
                        "body": body,
                        "template": template or "broadcast",
                        "broadcast_id": broadcast_id,
                        "tenant_name": tenant_row.name,
                    },
                    priority=3,  # Lower priority than transactional emails
                ),
            )

        return BroadcastSendResponse(
            broadcast_id=broadcast_id,
            recipients_count=recipients_count,
            status="queued",
        )

    async def get_broadcast_history(
        self, *, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> BroadcastHistoryResponse:
        """Get broadcast send history."""
        offset = (page - 1) * page_size

        count_result = await db.execute(
            text("SELECT COUNT(*) FROM admin_broadcast_history")
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            text(
                "SELECT id, subject, body, template, filter_plan, "
                "filter_country, filter_status, recipients_count, "
                "sent_by, created_at "
                "FROM admin_broadcast_history "
                "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"limit": page_size, "offset": offset},
        )
        items = [
            BroadcastHistoryItem(
                id=str(r[0]),
                subject=r[1],
                body=r[2],
                template=r[3],
                filter_plan=r[4],
                filter_country=r[5],
                filter_status=r[6],
                recipients_count=r[7],
                sent_by=str(r[8]),
                created_at=r[9].isoformat(),
            )
            for r in result.fetchall()
        ]

        return BroadcastHistoryResponse(items=items, total=total)

    # ─── SA-A01: Alert Rules ───────────────────────────────

    async def list_alert_rules(
        self, *, db: AsyncSession
    ) -> AlertRuleListResponse:
        """List all alert rules."""
        result = await db.execute(
            text(
                "SELECT id, name, condition, threshold, channel, is_active, "
                "last_triggered_at, created_at "
                "FROM admin_alert_rules ORDER BY created_at DESC"
            )
        )
        items = [
            AlertRuleResponse(
                id=str(r[0]), name=r[1], condition=r[2], threshold=r[3],
                channel=r[4], is_active=r[5],
                last_triggered_at=r[6].isoformat() if r[6] else None,
                created_at=r[7].isoformat(),
            )
            for r in result.fetchall()
        ]
        return AlertRuleListResponse(items=items, total=len(items))

    async def create_alert_rule(
        self,
        *,
        db: AsyncSession,
        name: str,
        condition: str,
        threshold: str,
        channel: str,
        is_active: bool,
        admin_id: str,
    ) -> AlertRuleResponse:
        """Create a new alert rule."""
        rule_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        await db.execute(
            text(
                "INSERT INTO admin_alert_rules "
                "(id, name, condition, threshold, channel, is_active, created_by) "
                "VALUES (:id, :name, :condition, :threshold, :channel, :active, :admin_id)"
            ),
            {
                "id": rule_id, "name": name, "condition": condition,
                "threshold": threshold, "channel": channel,
                "active": is_active, "admin_id": admin_id,
            },
        )
        await db.commit()
        return AlertRuleResponse(
            id=rule_id, name=name, condition=condition, threshold=threshold,
            channel=channel, is_active=is_active, last_triggered_at=None,
            created_at=now.isoformat(),
        )

    async def update_alert_rule(
        self,
        *,
        db: AsyncSession,
        rule_id: str,
        updates: dict[str, Any],
    ) -> AlertRuleResponse:
        """Update an alert rule."""
        set_parts = []
        params: dict[str, Any] = {"id": rule_id}
        for key, val in updates.items():
            if val is not None:
                set_parts.append(f"{key} = :{key}")
                params[key] = val
        if not set_parts:
            raise BusinessValidationError(
                error="VALIDATION_no_fields", message="No fields to update."
            )
        set_parts.append("updated_at = now()")
        set_sql = ", ".join(set_parts)
        await db.execute(
            text(f"UPDATE admin_alert_rules SET {set_sql} WHERE id = :id"),
            params,
        )
        await db.commit()

        result = await db.execute(
            text(
                "SELECT id, name, condition, threshold, channel, is_active, "
                "last_triggered_at, created_at "
                "FROM admin_alert_rules WHERE id = :id"
            ),
            {"id": rule_id},
        )
        r = result.fetchone()
        if not r:
            raise ResourceNotFoundError(
                error="SYSTEM_not_found", message="Alert rule not found."
            )
        return AlertRuleResponse(
            id=str(r[0]), name=r[1], condition=r[2], threshold=r[3],
            channel=r[4], is_active=r[5],
            last_triggered_at=r[6].isoformat() if r[6] else None,
            created_at=r[7].isoformat(),
        )

    async def delete_alert_rule(
        self, *, db: AsyncSession, rule_id: str
    ) -> None:
        """Delete an alert rule."""
        await db.execute(
            text("DELETE FROM admin_alert_rules WHERE id = :id"),
            {"id": rule_id},
        )
        await db.commit()

    # ─── SA-A02: Scheduled Reports ─────────────────────────

    async def list_scheduled_reports(
        self, *, db: AsyncSession
    ) -> ScheduledReportListResponse:
        """List all scheduled reports."""
        result = await db.execute(
            text(
                "SELECT id, name, report_type, schedule, recipients, "
                "is_active, last_run_at, next_run_at, created_at "
                "FROM admin_scheduled_reports ORDER BY created_at DESC"
            )
        )
        items = [
            ScheduledReportResponse(
                id=str(r[0]), name=r[1], report_type=r[2], schedule=r[3],
                recipients=r[4] if isinstance(r[4], list) else [],
                is_active=r[5],
                last_run_at=r[6].isoformat() if r[6] else None,
                next_run_at=r[7].isoformat() if r[7] else None,
                created_at=r[8].isoformat(),
            )
            for r in result.fetchall()
        ]
        return ScheduledReportListResponse(items=items, total=len(items))

    async def create_scheduled_report(
        self,
        *,
        db: AsyncSession,
        name: str,
        report_type: str,
        schedule: str,
        recipients: list[str],
        is_active: bool,
        admin_id: str,
    ) -> ScheduledReportResponse:
        """Create a scheduled report."""
        report_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        await db.execute(
            text(
                "INSERT INTO admin_scheduled_reports "
                "(id, name, report_type, schedule, recipients, is_active, created_by) "
                "VALUES (:id, :name, :type, :schedule, :recipients, :active, :admin_id)"
            ),
            {
                "id": report_id, "name": name, "type": report_type,
                "schedule": schedule,
                "recipients": json.dumps(recipients),
                "active": is_active, "admin_id": admin_id,
            },
        )
        await db.commit()
        return ScheduledReportResponse(
            id=report_id, name=name, report_type=report_type,
            schedule=schedule, recipients=recipients, is_active=is_active,
            last_run_at=None, next_run_at=None, created_at=now.isoformat(),
        )

    async def update_scheduled_report(
        self,
        *,
        db: AsyncSession,
        report_id: str,
        updates: dict[str, Any],
    ) -> ScheduledReportResponse:
        """Update a scheduled report."""
        set_parts = []
        params: dict[str, Any] = {"id": report_id}
        for key, val in updates.items():
            if val is not None:
                if key == "recipients":
                    set_parts.append(f"{key} = :{key}")
                    params[key] = json.dumps(val)
                else:
                    set_parts.append(f"{key} = :{key}")
                    params[key] = val
        if not set_parts:
            raise BusinessValidationError(
                error="VALIDATION_no_fields", message="No fields to update."
            )
        set_parts.append("updated_at = now()")
        set_sql = ", ".join(set_parts)
        await db.execute(
            text(f"UPDATE admin_scheduled_reports SET {set_sql} WHERE id = :id"),
            params,
        )
        await db.commit()

        result = await db.execute(
            text(
                "SELECT id, name, report_type, schedule, recipients, "
                "is_active, last_run_at, next_run_at, created_at "
                "FROM admin_scheduled_reports WHERE id = :id"
            ),
            {"id": report_id},
        )
        r = result.fetchone()
        if not r:
            raise ResourceNotFoundError(
                error="SYSTEM_not_found", message="Report not found."
            )
        return ScheduledReportResponse(
            id=str(r[0]), name=r[1], report_type=r[2], schedule=r[3],
            recipients=r[4] if isinstance(r[4], list) else [],
            is_active=r[5],
            last_run_at=r[6].isoformat() if r[6] else None,
            next_run_at=r[7].isoformat() if r[7] else None,
            created_at=r[8].isoformat(),
        )

    async def delete_scheduled_report(
        self, *, db: AsyncSession, report_id: str
    ) -> None:
        """Delete a scheduled report."""
        await db.execute(
            text("DELETE FROM admin_scheduled_reports WHERE id = :id"),
            {"id": report_id},
        )
        await db.commit()

    # ─── SA-E03: Support Chat ──────────────────────────────

    async def list_support_threads(
        self, *, db: AsyncSession
    ) -> SupportThreadListResponse:
        """List all support threads."""
        result = await db.execute(
            text(
                "SELECT t.id, t.tenant_id, tn.name AS tenant_name, "
                "t.status, t.unread_count, t.created_at, "
                "(SELECT m.content FROM admin_support_messages m "
                " WHERE m.thread_id = t.id ORDER BY m.created_at DESC LIMIT 1) AS last_msg, "
                "(SELECT m.created_at FROM admin_support_messages m "
                " WHERE m.thread_id = t.id ORDER BY m.created_at DESC LIMIT 1) AS last_msg_at "
                "FROM admin_support_threads t "
                "JOIN tenants tn ON tn.id = t.tenant_id "
                "ORDER BY t.updated_at DESC"
            )
        )
        items = []
        unread_total = 0
        for r in result.fetchall():
            unread_total += r[4]
            items.append(SupportThreadItem(
                id=str(r[0]), tenant_id=str(r[1]), tenant_name=r[2],
                status=r[3], unread_count=r[4], created_at=r[5].isoformat(),
                last_message=r[6], last_message_at=r[7].isoformat() if r[7] else None,
            ))
        return SupportThreadListResponse(
            items=items, total=len(items), unread_total=unread_total,
        )

    async def get_support_thread(
        self, *, db: AsyncSession, tenant_id: str
    ) -> SupportThreadDetailResponse:
        """Get or create a support thread for a tenant."""
        # Get or create thread
        result = await db.execute(
            text(
                "SELECT t.id, t.tenant_id, tn.name, t.status, "
                "t.unread_count, t.created_at "
                "FROM admin_support_threads t "
                "JOIN tenants tn ON tn.id = t.tenant_id "
                "WHERE t.tenant_id = :tid"
            ),
            {"tid": tenant_id},
        )
        row = result.fetchone()

        if not row:
            # Create thread
            thread_id = str(uuid.uuid4())
            await db.execute(
                text(
                    "INSERT INTO admin_support_threads (id, tenant_id) "
                    "VALUES (:id, :tid)"
                ),
                {"id": thread_id, "tid": tenant_id},
            )
            await db.commit()
            # Re-fetch
            result = await db.execute(
                text(
                    "SELECT t.id, t.tenant_id, tn.name, t.status, "
                    "t.unread_count, t.created_at "
                    "FROM admin_support_threads t "
                    "JOIN tenants tn ON tn.id = t.tenant_id "
                    "WHERE t.id = :id"
                ),
                {"id": thread_id},
            )
            row = result.fetchone()

        thread = SupportThreadItem(
            id=str(row[0]), tenant_id=str(row[1]), tenant_name=row[2],
            status=row[3], unread_count=row[4], created_at=row[5].isoformat(),
        )

        # Get messages
        msgs_result = await db.execute(
            text(
                "SELECT id, thread_id, sender_type, sender_name, "
                "content, created_at "
                "FROM admin_support_messages "
                "WHERE thread_id = :tid ORDER BY created_at ASC"
            ),
            {"tid": str(row[0])},
        )
        messages = [
            SupportMessageItem(
                id=str(m[0]), thread_id=str(m[1]), sender_type=m[2],
                sender_name=m[3], content=m[4], created_at=m[5].isoformat(),
            )
            for m in msgs_result.fetchall()
        ]

        return SupportThreadDetailResponse(thread=thread, messages=messages)

    async def send_support_message(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        content: str,
        sender_type: str,
        sender_id: str,
        sender_name: str,
    ) -> SupportMessageItem:
        """Send a message in a support thread."""
        # Ensure thread exists
        thread_result = await db.execute(
            text(
                "SELECT id FROM admin_support_threads WHERE tenant_id = :tid"
            ),
            {"tid": tenant_id},
        )
        thread_row = thread_result.fetchone()

        if not thread_row:
            thread_id = str(uuid.uuid4())
            await db.execute(
                text(
                    "INSERT INTO admin_support_threads (id, tenant_id) "
                    "VALUES (:id, :tid)"
                ),
                {"id": thread_id, "tid": tenant_id},
            )
        else:
            thread_id = str(thread_row[0])

        msg_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        await db.execute(
            text(
                "INSERT INTO admin_support_messages "
                "(id, thread_id, sender_type, sender_id, sender_name, content) "
                "VALUES (:id, :tid, :type, :sid, :name, :content)"
            ),
            {
                "id": msg_id, "tid": thread_id, "type": sender_type,
                "sid": sender_id, "name": sender_name, "content": content,
            },
        )

        # Update thread timestamp and unread count
        if sender_type == "clinic_owner":
            await db.execute(
                text(
                    "UPDATE admin_support_threads SET updated_at = now(), "
                    "unread_count = unread_count + 1 WHERE id = :id"
                ),
                {"id": thread_id},
            )
        else:
            await db.execute(
                text(
                    "UPDATE admin_support_threads SET updated_at = now(), "
                    "unread_count = 0 WHERE id = :id"
                ),
                {"id": thread_id},
            )

        await db.commit()

        return SupportMessageItem(
            id=msg_id, thread_id=thread_id, sender_type=sender_type,
            sender_name=sender_name, content=content,
            created_at=now.isoformat(),
        )


    # ─── SA-K01: Catalog Administration ──────────────────────────────────

    async def list_catalog_codes(
        self,
        db: AsyncSession,
        catalog_type: str,  # "cie10" or "cups"
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> CatalogCodeListResponse:
        """List CIE-10 or CUPS codes with optional search."""
        table = "cie10_catalog" if catalog_type == "cie10" else "cups_catalog"
        offset = (page - 1) * page_size

        where_clause = ""
        params: dict[str, Any] = {"limit": page_size, "offset": offset}
        if search:
            where_clause = "WHERE code ILIKE :search OR description ILIKE :search"
            params["search"] = f"%{search}%"

        count_q = f"SELECT COUNT(*) FROM {table} {where_clause}"
        row = await db.execute(text(count_q), params)
        total = row.scalar() or 0

        data_q = (
            f"SELECT id, code, description, category, created_at, updated_at "
            f"FROM {table} {where_clause} ORDER BY code LIMIT :limit OFFSET :offset"
        )
        rows = await db.execute(text(data_q), params)
        items = [
            CatalogCodeItem(
                id=str(r.id), code=r.code, description=r.description,
                category=r.category,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in rows.fetchall()
        ]

        return CatalogCodeListResponse(items=items, total=total, page=page, page_size=page_size)

    async def create_catalog_code(
        self,
        db: AsyncSession,
        catalog_type: str,
        data: CatalogCodeCreateRequest,
    ) -> CatalogCodeItem:
        """Create a new CIE-10 or CUPS code."""
        table = "cie10_catalog" if catalog_type == "cie10" else "cups_catalog"
        new_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        await db.execute(
            text(
                f"INSERT INTO {table} (id, code, description, category, created_at, updated_at) "
                f"VALUES (:id, :code, :desc, :cat, :now, :now)"
            ),
            {"id": new_id, "code": data.code.strip(), "desc": data.description.strip(),
             "cat": data.category, "now": now},
        )
        await db.commit()

        return CatalogCodeItem(
            id=new_id, code=data.code.strip(), description=data.description.strip(),
            category=data.category, created_at=now.isoformat(), updated_at=now.isoformat(),
        )

    async def update_catalog_code(
        self,
        db: AsyncSession,
        catalog_type: str,
        code_id: str,
        data: CatalogCodeUpdateRequest,
    ) -> CatalogCodeItem:
        """Update a CIE-10 or CUPS code."""
        table = "cie10_catalog" if catalog_type == "cie10" else "cups_catalog"
        now = datetime.now(UTC)

        # Build SET clause
        sets = ["updated_at = :now"]
        params: dict[str, Any] = {"id": code_id, "now": now}
        if data.description is not None:
            sets.append("description = :desc")
            params["desc"] = data.description.strip()
        if data.category is not None:
            sets.append("category = :cat")
            params["cat"] = data.category

        set_str = ", ".join(sets)
        await db.execute(text(f"UPDATE {table} SET {set_str} WHERE id = :id"), params)
        await db.commit()

        # Fetch updated
        row = await db.execute(
            text(f"SELECT id, code, description, category, created_at, updated_at FROM {table} WHERE id = :id"),
            {"id": code_id},
        )
        r = row.fetchone()
        if not r:
            raise ResourceNotFoundError(f"{catalog_type} code not found")

        return CatalogCodeItem(
            id=str(r.id), code=r.code, description=r.description,
            category=r.category,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )

    # ─── SA-K02: Global Template Management ────────────────────────────

    async def list_global_templates(
        self,
        db: AsyncSession,
        template_type: str | None = None,
    ) -> GlobalTemplateListResponse:
        """List global templates (consent + evolution)."""
        items: list[GlobalTemplateItem] = []

        # Consent templates from public.consent_templates
        if template_type is None or template_type == "consent":
            rows = await db.execute(
                text(
                    "SELECT id, name, category, version, is_active, created_at, updated_at "
                    "FROM consent_templates WHERE builtin = true ORDER BY name"
                )
            )
            for r in rows.fetchall():
                items.append(GlobalTemplateItem(
                    id=str(r.id), name=r.name, template_type="consent",
                    category=r.category, version=r.version, is_active=r.is_active,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                    updated_at=r.updated_at.isoformat() if r.updated_at else "",
                ))

        # Evolution templates — exist per-tenant, count builtins across schemas
        if template_type is None or template_type == "evolution":
            # Get one representative set from any tenant schema
            schema_row = await db.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name LIKE 'tn_%' LIMIT 1"
                )
            )
            schema = schema_row.scalar()
            if schema:
                try:
                    rows = await db.execute(
                        text(
                            f"SELECT id, name, procedure_type, is_active, created_at, updated_at "
                            f"FROM {schema}.evolution_templates WHERE is_builtin = true ORDER BY name"
                        )
                    )
                    for r in rows.fetchall():
                        items.append(GlobalTemplateItem(
                            id=str(r.id), name=r.name, template_type="evolution",
                            category=r.procedure_type, version=1, is_active=r.is_active,
                            created_at=r.created_at.isoformat() if r.created_at else "",
                            updated_at=r.updated_at.isoformat() if r.updated_at else "",
                        ))
                except Exception:
                    pass

        return GlobalTemplateListResponse(items=items, total=len(items))

    async def get_global_template(
        self,
        db: AsyncSession,
        template_id: str,
        template_type: str,
    ) -> GlobalTemplateDetailResponse:
        """Get a global template with full content."""
        if template_type == "consent":
            row = await db.execute(
                text(
                    "SELECT id, name, category, content, version, is_active, "
                    "created_at, updated_at FROM consent_templates WHERE id = :id"
                ),
                {"id": template_id},
            )
            r = row.fetchone()
            if not r:
                raise ResourceNotFoundError("Consent template not found")

            return GlobalTemplateDetailResponse(
                id=str(r.id), name=r.name, template_type="consent",
                category=r.category, content=r.content, version=r.version,
                is_active=r.is_active,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
        raise ResourceNotFoundError("Template not found")

    async def update_global_template(
        self,
        db: AsyncSession,
        template_id: str,
        template_type: str,
        data: "GlobalTemplateUpdateRequest",
    ) -> GlobalTemplateDetailResponse:
        """Update a global consent template."""
        from app.schemas.admin import GlobalTemplateUpdateRequest as GTU

        if template_type == "consent":
            now = datetime.now(UTC)
            sets = ["updated_at = :now"]
            params: dict[str, Any] = {"id": template_id, "now": now}

            if data.name is not None:
                sets.append("name = :name")
                params["name"] = data.name.strip()
            if data.content is not None:
                sets.append("content = :content")
                sets.append("version = version + 1")
                params["content"] = data.content
            if data.category is not None:
                sets.append("category = :category")
                params["category"] = data.category
            if data.is_active is not None:
                sets.append("is_active = :is_active")
                params["is_active"] = data.is_active

            set_str = ", ".join(sets)
            await db.execute(
                text(f"UPDATE consent_templates SET {set_str} WHERE id = :id"),
                params,
            )
            await db.commit()

            return await self.get_global_template(db, template_id, "consent")
        raise ResourceNotFoundError("Template type not supported for update")

    # ─── SA-K03: Default Price Catalog ─────────────────────────────────

    async def list_default_prices(
        self,
        db: AsyncSession,
        country_code: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DefaultPriceListResponse:
        """List default procedure prices."""
        offset = (page - 1) * page_size
        where_parts: list[str] = []
        params: dict[str, Any] = {"limit": page_size, "offset": offset}

        if country_code:
            where_parts.append("country_code = :cc")
            params["cc"] = country_code.upper()
        if search:
            where_parts.append("(cups_code ILIKE :search OR cups_description ILIKE :search)")
            params["search"] = f"%{search}%"

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        count_r = await db.execute(
            text(f"SELECT COUNT(*) FROM admin_default_prices {where_clause}"), params
        )
        total = count_r.scalar() or 0

        rows = await db.execute(
            text(
                f"SELECT id, cups_code, cups_description, country_code, price_cents, "
                f"currency_code, is_active, updated_at "
                f"FROM admin_default_prices {where_clause} "
                f"ORDER BY cups_code LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        items = [
            DefaultPriceItem(
                id=str(r.id), cups_code=r.cups_code, cups_description=r.cups_description,
                country_code=r.country_code, price_cents=r.price_cents,
                currency_code=r.currency_code, is_active=r.is_active,
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in rows.fetchall()
        ]
        return DefaultPriceListResponse(items=items, total=total, page=page, page_size=page_size)

    async def upsert_default_price(
        self,
        db: AsyncSession,
        data: "DefaultPriceUpsertRequest",
        admin_id: str,
    ) -> DefaultPriceItem:
        """Create or update a default price entry."""
        from app.schemas.admin import DefaultPriceUpsertRequest as DPU
        now = datetime.now(UTC)

        # Check if exists
        existing = await db.execute(
            text(
                "SELECT id FROM admin_default_prices "
                "WHERE cups_code = :code AND country_code = :cc"
            ),
            {"code": data.cups_code, "cc": data.country_code.upper()},
        )
        row = existing.fetchone()

        if row:
            # Update
            await db.execute(
                text(
                    "UPDATE admin_default_prices SET cups_description = :desc, "
                    "price_cents = :price, currency_code = :cur, updated_by = :admin, "
                    "updated_at = :now WHERE id = :id"
                ),
                {"desc": data.cups_description, "price": data.price_cents,
                 "cur": data.currency_code, "admin": admin_id, "now": now, "id": row.id},
            )
            price_id = str(row.id)
        else:
            # Insert
            price_id = str(uuid.uuid4())
            await db.execute(
                text(
                    "INSERT INTO admin_default_prices "
                    "(id, cups_code, cups_description, country_code, price_cents, "
                    "currency_code, updated_by, created_at, updated_at) "
                    "VALUES (:id, :code, :desc, :cc, :price, :cur, :admin, :now, :now)"
                ),
                {"id": price_id, "code": data.cups_code, "desc": data.cups_description,
                 "cc": data.country_code.upper(), "price": data.price_cents,
                 "cur": data.currency_code, "admin": admin_id, "now": now},
            )

        await db.commit()

        return DefaultPriceItem(
            id=price_id, cups_code=data.cups_code,
            cups_description=data.cups_description,
            country_code=data.country_code.upper(),
            price_cents=data.price_cents, currency_code=data.currency_code,
            is_active=True, updated_at=now.isoformat(),
        )

    # ─── SA-U03: Tenant Comparison ─────────────────────────────────────

    async def compare_tenants(
        self,
        db: AsyncSession,
        tenant_ids: list[str],
    ) -> TenantComparisonResponse:
        """Compare 2-5 tenants side by side with key metrics."""
        if len(tenant_ids) < 2 or len(tenant_ids) > 5:
            raise BusinessValidationError("Must compare between 2 and 5 tenants")

        items: list[TenantBenchmarkItem] = []
        plan_ids_seen: list[str] = []

        for tid in tenant_ids:
            # Tenant info
            t_row = await db.execute(
                text(
                    "SELECT t.id, t.name, t.schema_name, t.plan_id, p.name as plan_name "
                    "FROM tenants t JOIN plans p ON t.plan_id = p.id WHERE t.id = :tid"
                ),
                {"tid": tid},
            )
            t = t_row.fetchone()
            if not t:
                continue

            schema = t.schema_name
            plan_ids_seen.append(str(t.plan_id))

            # Cross-schema metrics
            patients = 0
            active_users = 0
            appointments_30d = 0
            invoices_30d = 0
            features_used = 0

            try:
                pr = await db.execute(text(
                    f"SELECT COUNT(*) FROM {schema}.patients WHERE is_active = true"
                ))
                patients = pr.scalar() or 0
            except Exception:
                pass

            try:
                ur = await db.execute(text(
                    f"SELECT COUNT(*) FROM {schema}.users WHERE is_active = true"
                ))
                active_users = ur.scalar() or 0
            except Exception:
                pass

            try:
                ar = await db.execute(text(
                    f"SELECT COUNT(*) FROM {schema}.appointments "
                    f"WHERE created_at >= NOW() - INTERVAL '30 days'"
                ))
                appointments_30d = ar.scalar() or 0
            except Exception:
                pass

            try:
                ir = await db.execute(text(
                    f"SELECT COUNT(*) FROM {schema}.invoices "
                    f"WHERE created_at >= NOW() - INTERVAL '30 days'"
                ))
                invoices_30d = ir.scalar() or 0
            except Exception:
                pass

            # Count features used (simplified)
            feature_tables = [
                "appointments", "invoices", "clinical_records",
                "odontogram_entries", "consent_records",
            ]
            for ft in feature_tables:
                try:
                    fr = await db.execute(text(
                        f"SELECT EXISTS(SELECT 1 FROM {schema}.{ft} LIMIT 1)"
                    ))
                    if fr.scalar():
                        features_used += 1
                except Exception:
                    pass

            # MRR calculation
            plan_row = await db.execute(
                text("SELECT price_cents FROM plans WHERE id = :pid"),
                {"pid": str(t.plan_id)},
            )
            mrr_cents = plan_row.scalar() or 0

            items.append(TenantBenchmarkItem(
                tenant_id=str(t.id), tenant_name=t.name, plan_name=t.plan_name,
                patients=patients, active_users=active_users,
                appointments_30d=appointments_30d, invoices_30d=invoices_30d,
                mrr_cents=mrr_cents, features_used=features_used,
            ))

        # Calculate plan averages
        if items:
            plan_averages = {
                "patients": sum(i.patients for i in items) // len(items),
                "active_users": sum(i.active_users for i in items) // len(items),
                "appointments_30d": sum(i.appointments_30d for i in items) // len(items),
                "invoices_30d": sum(i.invoices_30d for i in items) // len(items),
                "mrr_cents": sum(i.mrr_cents for i in items) // len(items),
                "features_used": sum(i.features_used for i in items) // len(items),
            }
        else:
            plan_averages = {}

        return TenantComparisonResponse(tenants=items, plan_averages=plan_averages)

    # ─── SA-O03: API Usage Metrics ─────────────────────────────────────

    async def get_api_usage_metrics(self, db: AsyncSession) -> ApiUsageMetricsResponse:
        """Get API usage metrics from Redis counters.

        Reads the counters populated by ``ApiMetricsMiddleware``.
        """
        try:
            total_24h = 0
            error_count = 0
            hourly_counts: list[dict] = []
            avg_latency = 0.0
            p95_latency = 0.0
            top_endpoints: list[ApiEndpointMetric] = []
            top_tenants: list[ApiTenantUsage] = []

            if redis_client:
                now = datetime.now(UTC)

                # ── Hourly buckets ──────────────────────────────────────
                for h in range(24):
                    hour_dt = now - timedelta(hours=h)
                    key = f"dentalos:api:hourly:{hour_dt.strftime('%Y%m%d%H')}"
                    val = await redis_client.get(key)
                    count = int(val) if val else 0
                    total_24h += count
                    hourly_counts.append({
                        "hour": hour_dt.strftime("%H:00"),
                        "count": count,
                    })

                # ── Error count ─────────────────────────────────────────
                err_val = await redis_client.get("dentalos:api:errors:24h")
                error_count = int(err_val) if err_val else 0

                # ── Latency from sorted set ─────────────────────────────
                sample_key = "dentalos:api:latency:samples"
                samples = await redis_client.zrangebyscore(
                    sample_key, "-inf", "+inf", withscores=True
                )
                if samples:
                    scores = sorted(float(s) for _, s in samples)
                    avg_latency = sum(scores) / len(scores)
                    p95_idx = int(len(scores) * 0.95)
                    p95_latency = scores[min(p95_idx, len(scores) - 1)]

                # ── Top endpoints (scan for dentalos:api:endpoint:*:count) ─
                ep_data: dict[str, dict] = {}
                async for key in redis_client.scan_iter(
                    match="dentalos:api:endpoint:*:count", count=200
                ):
                    # key = "dentalos:api:endpoint:GET:/api/v1/patients:count"
                    parts = key.split(":")
                    if len(parts) >= 6:
                        method = parts[3]
                        path = parts[4]
                        ep_id = f"{method}:{path}"
                        cnt_val = await redis_client.get(key)
                        err_key = key.replace(":count", ":errors")
                        lat_key = key.replace(":count", ":latency_sum")
                        err_v = await redis_client.get(err_key)
                        lat_v = await redis_client.get(lat_key)
                        cnt = int(cnt_val) if cnt_val else 0
                        errs = int(err_v) if err_v else 0
                        lat_sum = float(lat_v) if lat_v else 0.0
                        ep_data[ep_id] = {
                            "method": method,
                            "path": path,
                            "count": cnt,
                            "errors": errs,
                            "avg_latency": round(lat_sum / max(cnt, 1), 1),
                        }

                # Sort by count desc, take top 20
                sorted_eps = sorted(ep_data.values(), key=lambda x: x["count"], reverse=True)[:20]
                top_endpoints = [
                    ApiEndpointMetric(
                        method=ep["method"],
                        path=ep["path"],
                        request_count=ep["count"],
                        error_count=ep["errors"],
                        avg_latency_ms=ep["avg_latency"],
                    )
                    for ep in sorted_eps
                ]

                # ── Top tenants (scan for dentalos:api:tenant:*:count) ──
                t_data: dict[str, int] = {}
                async for key in redis_client.scan_iter(
                    match="dentalos:api:tenant:*:count", count=200
                ):
                    parts = key.split(":")
                    if len(parts) >= 5:
                        tid = parts[3]
                        val = await redis_client.get(key)
                        t_data[tid] = int(val) if val else 0

                sorted_tenants = sorted(t_data.items(), key=lambda x: x[1], reverse=True)[:10]
                top_tenants = [
                    ApiTenantUsage(tenant_id=tid, request_count=cnt)
                    for tid, cnt in sorted_tenants
                ]

            hourly_counts.reverse()
            error_rate = (error_count / total_24h * 100) if total_24h > 0 else 0.0

            return ApiUsageMetricsResponse(
                total_requests_24h=total_24h,
                error_rate_percent=round(error_rate, 2),
                avg_latency_ms=round(avg_latency, 1),
                p95_latency_ms=round(p95_latency, 1),
                top_endpoints=top_endpoints,
                top_tenants=top_tenants,
                requests_by_hour=hourly_counts,
            )
        except Exception as e:
            logger.warning("Failed to get API metrics: %s", e)
            return ApiUsageMetricsResponse(
                total_requests_24h=0, error_rate_percent=0.0,
                avg_latency_ms=0.0, p95_latency_ms=0.0,
                top_endpoints=[], top_tenants=[], requests_by_hour=[],
            )

    # ─── SA-G04: Geographic Intelligence ───────────────────────────────

    async def get_geo_intelligence(self, db: AsyncSession) -> GeoIntelligenceResponse:
        """Get geographic expansion intelligence."""
        cache_key = "dentalos:admin:geo_intelligence"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return GeoIntelligenceResponse(**data)

        # Group tenants by country
        rows = await db.execute(
            text(
                "SELECT t.country_code, COUNT(*) as total, "
                "SUM(CASE WHEN t.status = 'active' THEN 1 ELSE 0 END) as active, "
                "p.name as top_plan "
                "FROM tenants t JOIN plans p ON t.plan_id = p.id "
                "GROUP BY t.country_code, p.name "
                "ORDER BY total DESC"
            )
        )

        country_data: dict[str, dict] = {}
        for r in rows.fetchall():
            cc = r.country_code
            if cc not in country_data:
                country_data[cc] = {
                    "tenant_count": 0,
                    "active_count": 0,
                    "top_plan": r.top_plan,
                }
            country_data[cc]["tenant_count"] += r.total
            country_data[cc]["active_count"] += r.active

        # MRR per country
        mrr_rows = await db.execute(
            text(
                "SELECT t.country_code, t.currency_code, "
                "SUM(p.price_cents) as mrr "
                "FROM tenants t JOIN plans p ON t.plan_id = p.id "
                "WHERE t.status = 'active' "
                "GROUP BY t.country_code, t.currency_code"
            )
        )
        country_mrr: dict[str, tuple[int, str]] = {}
        for r in mrr_rows.fetchall():
            country_mrr[r.country_code] = (r.mrr or 0, r.currency_code or "COP")

        # Signup trends (last 12 months)
        trend_rows = await db.execute(
            text(
                "SELECT country_code, "
                "TO_CHAR(created_at, 'YYYY-MM') as month, "
                "COUNT(*) as cnt "
                "FROM tenants "
                "WHERE created_at >= NOW() - INTERVAL '12 months' "
                "GROUP BY country_code, TO_CHAR(created_at, 'YYYY-MM') "
                "ORDER BY country_code, month"
            )
        )
        country_trends: dict[str, list[dict]] = {}
        for r in trend_rows.fetchall():
            if r.country_code not in country_trends:
                country_trends[r.country_code] = []
            country_trends[r.country_code].append({"month": r.month, "count": r.cnt})

        country_names = {
            "CO": "Colombia", "MX": "México", "PE": "Perú",
            "CL": "Chile", "AR": "Argentina", "EC": "Ecuador",
            "VE": "Venezuela", "BR": "Brasil", "US": "United States",
        }

        countries: list[GeoCountryMetrics] = []
        for cc, data in country_data.items():
            mrr_val, cur = country_mrr.get(cc, (0, "COP"))
            countries.append(GeoCountryMetrics(
                country_code=cc,
                country_name=country_names.get(cc, cc),
                tenant_count=data["tenant_count"],
                active_tenant_count=data["active_count"],
                total_mrr_cents=mrr_val,
                currency_code=cur,
                signup_trend=country_trends.get(cc, []),
                top_plan=data.get("top_plan"),
            ))

        countries.sort(key=lambda c: c.tenant_count, reverse=True)
        primary = countries[0].country_code if countries else "CO"

        result = GeoIntelligenceResponse(
            countries=countries, total_countries=len(countries),
            primary_market=primary,
        )

        if redis_client:
            await redis_client.set(
                cache_key, json.dumps(result.model_dump()), ex=1800,
            )

        return result


# Module-level singleton
admin_service = AdminService()
