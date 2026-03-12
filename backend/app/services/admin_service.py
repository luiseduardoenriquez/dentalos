"""Admin service — tenant management, plans, analytics, feature flags, health.

Provides the business logic for superadmin operations on the DentalOS
platform. All queries target the public schema since admin operations
are cross-tenant by nature.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError
from app.core.redis import redis_client
from app.core.security import _load_private_key
from app.models.public.feature_flag import FeatureFlag
from app.models.public.plan import Plan
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership
from app.schemas.admin import (
    FeatureFlagResponse,
    ImpersonateResponse,
    PlanResponse,
    PlatformAnalyticsResponse,
    SystemHealthResponse,
    TenantDetailResponse,
    TenantListResponse,
    TenantSummary,
)

logger = logging.getLogger("dentalos.admin")

# Impersonation JWT TTL: 1 hour
_IMPERSONATION_TOKEN_EXPIRE_MINUTES = 60


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
    ) -> TenantListResponse:
        """List all tenants with summary information.

        Supports pagination, text search (on name/slug), and status filtering.
        User counts are derived from public.user_tenant_memberships.
        Patient counts are estimated (0 for MVP — requires cross-schema query).
        """
        # Base query
        base_filter = []
        if status:
            base_filter.append(Tenant.status == status)
        if search:
            search_term = f"%{search.strip().lower()}%"
            base_filter.append(
                func.lower(Tenant.name).like(search_term)
                | func.lower(Tenant.slug).like(search_term)
            )

        # Count total
        count_stmt = select(func.count(Tenant.id)).where(*base_filter)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Fetch tenants with plan join
        offset = (page - 1) * page_size
        stmt = (
            select(Tenant)
            .where(*base_filter)
            .order_by(Tenant.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()

        # Batch user counts — single GROUP BY instead of one COUNT per tenant
        tenant_ids = [t.id for t in tenants]
        user_counts: dict = {}
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

        # Build summaries with user counts
        items: list[TenantSummary] = []
        for tenant in tenants:
            plan = tenant.plan  # Eagerly loaded via relationship

            items.append(
                TenantSummary(
                    id=str(tenant.id),
                    name=tenant.name,
                    slug=tenant.slug,
                    plan_name=plan.name if plan else "unknown",
                    status=tenant.status,
                    user_count=user_counts.get(tenant.id, 0),
                    patient_count=0,  # Cross-schema query; 0 for MVP
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
            # Reactivate
            tenant.status = "active"
            tenant.suspended_at = None
            logger.info("Tenant reactivated: %s", tenant.name)
        else:
            # Suspend
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

        return [
            PlanResponse(
                id=str(p.id),
                name=p.name,
                slug=p.slug,
                price_cents=p.price_cents,
                max_patients=p.max_patients,
                max_doctors=p.max_doctors,
                features=p.features,
                is_active=p.is_active,
            )
            for p in plans
        ]

    async def update_plan(
        self,
        *,
        db: AsyncSession,
        plan_id: str,
        price_cents: int | None = None,
        max_patients: int | None = None,
        max_doctors: int | None = None,
        features: dict | None = None,
        is_active: bool | None = None,
    ) -> PlanResponse:
        """Update a subscription plan's configuration."""
        result = await db.execute(
            select(Plan).where(Plan.id == uuid.UUID(plan_id))
        )
        plan = result.scalar_one_or_none()

        if plan is None:
            raise ResourceNotFoundError(
                error="SYSTEM_plan_not_found",
                resource_name="Plan",
            )

        if price_cents is not None:
            plan.price_cents = price_cents
        if max_patients is not None:
            plan.max_patients = max_patients
        if max_doctors is not None:
            plan.max_doctors = max_doctors
        if features is not None:
            plan.features = features
        if is_active is not None:
            plan.is_active = is_active

        await db.flush()

        logger.info("Plan updated: %s (%s)", plan.name, plan.slug)

        return PlanResponse(
            id=str(plan.id),
            name=plan.name,
            slug=plan.slug,
            price_cents=plan.price_cents,
            max_patients=plan.max_patients,
            max_doctors=plan.max_doctors,
            features=plan.features,
            is_active=plan.is_active,
        )

    # ─── Platform Analytics ─────────────────────────────

    async def get_platform_analytics(
        self, *, db: AsyncSession
    ) -> PlatformAnalyticsResponse:
        """Aggregate platform-wide analytics.

        For MVP, patient_count and MAU are estimated. Churn rate
        is stubbed at 0.0 until billing history is available.
        """
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

        # MRR estimate: sum of plan prices for active tenants
        mrr_result = await db.execute(
            select(func.coalesce(func.sum(Plan.price_cents), 0))
            .select_from(Tenant)
            .join(Plan, Plan.id == Tenant.plan_id)
            .where(Tenant.status == "active")
        )
        mrr_cents = mrr_result.scalar() or 0

        # MAU estimate: active memberships updated in last 30 days
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        mau_result = await db.execute(
            select(func.count(UserTenantMembership.id)).where(
                UserTenantMembership.status == "active",
                UserTenantMembership.updated_at >= thirty_days_ago,
            )
        )
        mau = mau_result.scalar() or 0

        return PlatformAnalyticsResponse(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users,
            total_patients=0,  # Cross-schema; 0 for MVP
            mrr_cents=mrr_cents,
            mau=mau,
            churn_rate=0.0,  # Stub for MVP
        )

    # ─── Feature Flags ──────────────────────────────────

    async def list_feature_flags(
        self, *, db: AsyncSession
    ) -> list[FeatureFlagResponse]:
        """List all feature flags."""
        result = await db.execute(
            select(FeatureFlag).order_by(FeatureFlag.flag_name.asc())
        )
        flags = result.scalars().all()

        return [
            FeatureFlagResponse(
                id=str(f.id),
                flag_name=f.flag_name,
                scope=f.scope,
                plan_filter=f.plan_filter,
                tenant_id=str(f.tenant_id) if f.tenant_id else None,
                enabled=f.enabled,
                description=f.description,
            )
            for f in flags
        ]

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
    ) -> FeatureFlagResponse:
        """Create a new feature flag."""
        flag = FeatureFlag(
            flag_name=flag_name.strip(),
            enabled=enabled,
            scope=scope,
            plan_filter=plan_filter,
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            description=description,
        )
        db.add(flag)
        await db.flush()

        logger.info("Feature flag created: %s (enabled=%s)", flag.flag_name, flag.enabled)

        return FeatureFlagResponse(
            id=str(flag.id),
            flag_name=flag.flag_name,
            scope=flag.scope,
            plan_filter=flag.plan_filter,
            tenant_id=str(flag.tenant_id) if flag.tenant_id else None,
            enabled=flag.enabled,
            description=flag.description,
        )

    async def update_feature_flag(
        self,
        *,
        db: AsyncSession,
        flag_id: str,
        enabled: bool | None = None,
        scope: str | None = None,
        plan_filter: str | None = None,
        tenant_id: str | None = None,
        description: str | None = None,
    ) -> FeatureFlagResponse:
        """Update an existing feature flag."""
        result = await db.execute(
            select(FeatureFlag).where(FeatureFlag.id == uuid.UUID(flag_id))
        )
        flag = result.scalar_one_or_none()

        if flag is None:
            raise ResourceNotFoundError(
                error="SYSTEM_feature_flag_not_found",
                resource_name="FeatureFlag",
            )

        if enabled is not None:
            flag.enabled = enabled
        if scope is not None:
            flag.scope = scope
        if plan_filter is not None:
            flag.plan_filter = plan_filter
        if tenant_id is not None:
            flag.tenant_id = uuid.UUID(tenant_id)
        if description is not None:
            flag.description = description

        await db.flush()

        logger.info("Feature flag updated: %s (enabled=%s)", flag.flag_name, flag.enabled)

        return FeatureFlagResponse(
            id=str(flag.id),
            flag_name=flag.flag_name,
            scope=flag.scope,
            plan_filter=flag.plan_filter,
            tenant_id=str(flag.tenant_id) if flag.tenant_id else None,
            enabled=flag.enabled,
            description=flag.description,
        )

    # ─── System Health ──────────────────────────────────

    async def check_system_health(
        self, *, db: AsyncSession
    ) -> SystemHealthResponse:
        """Check health of all platform dependencies.

        Returns individual status for PostgreSQL, Redis, RabbitMQ, and
        storage. RabbitMQ and storage are stubbed to True for MVP.
        """
        now = datetime.now(UTC)

        # PostgreSQL
        pg_healthy = False
        try:
            result = await db.execute(text("SELECT 1"))
            pg_healthy = result.scalar() == 1
        except Exception:
            logger.warning("Health check: PostgreSQL is unhealthy")

        # Redis
        redis_healthy = False
        try:
            pong = await redis_client.ping()
            redis_healthy = bool(pong)
        except Exception:
            logger.warning("Health check: Redis is unhealthy")

        # RabbitMQ — stub for MVP (would check connection in production)
        rabbitmq_healthy = True

        # Storage (S3/MinIO) — stub for MVP (would list bucket in production)
        storage_healthy = True

        all_healthy = all([pg_healthy, redis_healthy, rabbitmq_healthy, storage_healthy])

        return SystemHealthResponse(
            status="healthy" if all_healthy else "degraded",
            postgres=pg_healthy,
            redis=redis_healthy,
            rabbitmq=rabbitmq_healthy,
            storage=storage_healthy,
            timestamp=now.isoformat(),
        )

    # ─── Tenant Impersonation ───────────────────────────

    async def impersonate_tenant(
        self,
        *,
        db: AsyncSession,
        admin_id: str,
        tenant_id: str,
    ) -> ImpersonateResponse:
        """Generate a clinic_owner-scoped JWT for a specific tenant.

        Used by superadmins to access a tenant's dashboard for support
        or debugging. The JWT includes an "impersonated" flag so all
        actions can be traced back to the admin.
        """
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

        # Generate a real tenant JWT with impersonation markers
        access_token = self._generate_impersonation_jwt(
            admin_id=admin_id,
            tenant_id=str(tenant.id),
            tenant_schema=tenant.schema_name,
        )

        logger.info(
            "Admin %s... impersonating tenant %s... as clinic_owner",
            admin_id[:8],
            str(tenant.id)[:8],
        )

        return ImpersonateResponse(
            access_token=access_token,
            token_type="bearer",
            tenant_id=str(tenant.id),
            impersonated_as="clinic_owner",
        )

    # ─── Private Helpers ────────────────────────────────

    def _generate_impersonation_jwt(
        self,
        admin_id: str,
        tenant_id: str,
        tenant_schema: str,
    ) -> str:
        """Create an RS256 JWT that impersonates a clinic_owner.

        The token is a real tenant JWT (with tid claim) but includes
        extra claims to mark it as impersonated for audit purposes:
          - impersonated: true
          - impersonated_by: admin_{admin_id}

        Uses the standard dentalos-api audience so regular tenant
        endpoints accept it.
        """
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
            "iat": now,
            "exp": now + timedelta(minutes=_IMPERSONATION_TOKEN_EXPIRE_MINUTES),
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


# Module-level singleton
admin_service = AdminService()
