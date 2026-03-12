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
    AuditLogEntry,
    AuditLogListResponse,
    CountryDistributionItem,
    FeatureFlagResponse,
    FlagChangeHistoryEntry,
    ImpersonateResponse,
    PlanChangeHistoryEntry,
    PlanChangeHistoryResponse,
    PlanDistributionItem,
    PlanResponse,
    PlatformAnalyticsResponse,
    ServiceHealthDetail,
    SuperadminResponse,
    SystemHealthResponse,
    TenantDetailResponse,
    TenantListResponse,
    TenantSummary,
    TopTenantItem,
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


# Module-level singleton
admin_service = AdminService()
