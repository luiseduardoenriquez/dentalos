"""Membership service — plan management, subscriptions, and discount lookup.

Security invariants:
  - PHI is NEVER logged.
  - Financial data in COP cents.
  - Soft-delete only.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import MembershipErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.membership import (
    MembershipPlan,
    MembershipSubscription,
    MembershipUsageLog,
)
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.membership")


class MembershipService:
    """Stateless membership service."""

    # ── Plan CRUD ─────────────────────────────────────────────────────────────

    async def create_plan(
        self, *, db: AsyncSession, created_by: str, **fields: Any,
    ) -> dict[str, Any]:
        """Create a new membership plan."""
        plan = MembershipPlan(
            name=fields["name"],
            description=fields.get("description"),
            monthly_price_cents=fields["monthly_price_cents"],
            annual_price_cents=fields.get("annual_price_cents"),
            benefits=fields.get("benefits"),
            discount_percentage=fields.get("discount_percentage", 0),
            status="active",
            is_active=True,
            created_by=uuid.UUID(created_by),
        )
        db.add(plan)
        await db.flush()
        await db.refresh(plan)
        logger.info("Membership plan created: id=%s", str(plan.id)[:8])
        return self._plan_to_dict(plan)

    async def list_plans(
        self, *, db: AsyncSession, include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """List membership plans."""
        conditions = [MembershipPlan.is_active.is_(True)]
        if not include_archived:
            conditions.append(MembershipPlan.status == "active")
        result = await db.execute(
            select(MembershipPlan)
            .where(*conditions)
            .order_by(MembershipPlan.monthly_price_cents)
        )
        return [self._plan_to_dict(p) for p in result.scalars().all()]

    async def update_plan(
        self, *, db: AsyncSession, plan_id: str, **fields: Any,
    ) -> dict[str, Any]:
        """Update a membership plan."""
        plan = await self._get_plan(db, plan_id)
        for key, value in fields.items():
            if value is not None and hasattr(plan, key):
                setattr(plan, key, value)
        await db.flush()
        await db.refresh(plan)
        logger.info("Membership plan updated: id=%s", str(plan.id)[:8])
        return self._plan_to_dict(plan)

    # ── Subscription Management ───────────────────────────────────────────────

    async def subscribe_patient(
        self, *, db: AsyncSession, patient_id: str, plan_id: str,
        start_date: date, payment_method: str | None = None,
        created_by: str,
    ) -> dict[str, Any]:
        """Subscribe a patient to a membership plan."""
        pid = uuid.UUID(patient_id)
        plid = uuid.UUID(plan_id)

        # Validate plan exists
        plan = await self._get_plan(db, plan_id)

        # Check no active subscription already exists
        existing = await db.execute(
            select(MembershipSubscription.id).where(
                MembershipSubscription.patient_id == pid,
                MembershipSubscription.status == "active",
                MembershipSubscription.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DentalOSError(
                error=MembershipErrors.ALREADY_SUBSCRIBED,
                message="El paciente ya tiene una membresía activa.",
                status_code=409,
            )

        from dateutil.relativedelta import relativedelta
        next_billing = start_date + relativedelta(months=1)

        sub = MembershipSubscription(
            patient_id=pid,
            plan_id=plid,
            status="active",
            start_date=start_date,
            next_billing_date=next_billing,
            payment_method=payment_method,
            created_by=uuid.UUID(created_by),
            is_active=True,
        )
        db.add(sub)
        await db.flush()
        await db.refresh(sub)

        logger.info("Patient subscribed to plan: plan=%s", str(plid)[:8])
        return self._subscription_to_dict(
            sub, plan_name=plan.name, discount=plan.discount_percentage,
            monthly_price_cents=plan.monthly_price_cents, benefits=plan.benefits,
        )

    async def list_subscriptions(
        self, *, db: AsyncSession, status: str | None = None,
        patient_id: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> dict[str, Any]:
        """List subscriptions with optional filters."""
        offset = (page - 1) * page_size
        conditions = [MembershipSubscription.is_active.is_(True)]
        if status:
            conditions.append(MembershipSubscription.status == status)
        if patient_id:
            conditions.append(MembershipSubscription.patient_id == uuid.UUID(patient_id))

        total = (await db.execute(
            select(func.count(MembershipSubscription.id)).where(*conditions)
        )).scalar_one()

        result = await db.execute(
            select(
                MembershipSubscription,
                MembershipPlan.name,
                MembershipPlan.discount_percentage,
                MembershipPlan.monthly_price_cents,
                MembershipPlan.benefits,
            )
            .join(MembershipPlan, MembershipSubscription.plan_id == MembershipPlan.id)
            .where(*conditions)
            .order_by(MembershipSubscription.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = result.all()

        return {
            "items": [
                self._subscription_to_dict(
                    r[0], plan_name=r[1], discount=r[2],
                    monthly_price_cents=r[3], benefits=r[4],
                )
                for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def cancel_subscription(
        self, *, db: AsyncSession, subscription_id: str,
    ) -> dict[str, Any]:
        """Cancel an active or paused subscription."""
        sub = await self._get_subscription(db, subscription_id)
        if sub.status not in ("active", "paused"):
            raise DentalOSError(
                error=MembershipErrors.CANNOT_CANCEL,
                message=f"No se puede cancelar una suscripción con estado '{sub.status}'.",
                status_code=409,
            )
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(sub)
        logger.info("Subscription cancelled: id=%s", str(sub.id)[:8])
        return self._subscription_to_dict(sub)

    async def pause_subscription(
        self, *, db: AsyncSession, subscription_id: str,
    ) -> dict[str, Any]:
        """Pause an active subscription."""
        sub = await self._get_subscription(db, subscription_id)
        if sub.status != "active":
            raise DentalOSError(
                error=MembershipErrors.CANNOT_PAUSE,
                message="Solo se pueden pausar suscripciones activas.",
                status_code=409,
            )
        sub.status = "paused"
        sub.paused_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(sub)
        logger.info("Subscription paused: id=%s", str(sub.id)[:8])
        return self._subscription_to_dict(sub)

    # ── Discount Lookup (used by invoice_service) ─────────────────────────────

    async def get_active_membership_discount(
        self, *, db: AsyncSession, patient_id: uuid.UUID,
    ) -> tuple[int, uuid.UUID | None]:
        """Return (discount_percentage, subscription_id) or (0, None)."""
        result = await db.execute(
            select(MembershipSubscription.id, MembershipPlan.discount_percentage)
            .join(MembershipPlan, MembershipSubscription.plan_id == MembershipPlan.id)
            .where(
                MembershipSubscription.patient_id == patient_id,
                MembershipSubscription.status == "active",
                MembershipSubscription.is_active.is_(True),
                MembershipPlan.is_active.is_(True),
            )
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return 0, None
        return row.discount_percentage, row.id

    async def log_usage(
        self, *, db: AsyncSession, subscription_id: uuid.UUID,
        invoice_id: uuid.UUID, discount_applied_cents: int,
        service_id: uuid.UUID | None = None,
    ) -> None:
        """Log a membership discount usage."""
        log = MembershipUsageLog(
            subscription_id=subscription_id,
            service_id=service_id,
            invoice_id=invoice_id,
            discount_applied_cents=discount_applied_cents,
        )
        db.add(log)
        await db.flush()

    # ── Dashboard Stats ───────────────────────────────────────────────────────

    async def get_dashboard(self, *, db: AsyncSession) -> dict[str, Any]:
        """Get membership dashboard stats."""
        active = (await db.execute(
            select(func.count(MembershipSubscription.id)).where(
                MembershipSubscription.status == "active",
                MembershipSubscription.is_active.is_(True),
            )
        )).scalar_one()

        paused = (await db.execute(
            select(func.count(MembershipSubscription.id)).where(
                MembershipSubscription.status == "paused",
                MembershipSubscription.is_active.is_(True),
            )
        )).scalar_one()

        # Monthly revenue from active subscriptions
        revenue = (await db.execute(
            select(func.coalesce(func.sum(MembershipPlan.monthly_price_cents), 0))
            .join(MembershipSubscription, MembershipSubscription.plan_id == MembershipPlan.id)
            .where(
                MembershipSubscription.status == "active",
                MembershipSubscription.is_active.is_(True),
            )
        )).scalar_one()

        # Churn: cancelled in last 30 days / (active + cancelled in last 30d)
        thirty_days_ago = datetime.now(UTC) - __import__("datetime").timedelta(days=30)
        cancelled_30d = (await db.execute(
            select(func.count(MembershipSubscription.id)).where(
                MembershipSubscription.status == "cancelled",
                MembershipSubscription.cancelled_at >= thirty_days_ago,
                MembershipSubscription.is_active.is_(True),
            )
        )).scalar_one()

        total_for_churn = active + cancelled_30d
        churn = round((cancelled_30d / total_for_churn * 100) if total_for_churn > 0 else 0.0, 1)

        return {
            "active_count": active,
            "paused_count": paused,
            "total_monthly_revenue_cents": revenue,
            "churn_rate_percent": churn,
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get_plan(self, db: AsyncSession, plan_id: str) -> MembershipPlan:
        result = await db.execute(
            select(MembershipPlan).where(
                MembershipPlan.id == uuid.UUID(plan_id),
                MembershipPlan.is_active.is_(True),
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ResourceNotFoundError(
                error=MembershipErrors.PLAN_NOT_FOUND,
                resource_name="MembershipPlan",
            )
        return plan

    async def _get_subscription(self, db: AsyncSession, sub_id: str) -> MembershipSubscription:
        result = await db.execute(
            select(MembershipSubscription).where(
                MembershipSubscription.id == uuid.UUID(sub_id),
                MembershipSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            raise ResourceNotFoundError(
                error=MembershipErrors.SUBSCRIPTION_NOT_FOUND,
                resource_name="MembershipSubscription",
            )
        return sub

    def _plan_to_dict(self, plan: MembershipPlan) -> dict[str, Any]:
        return {
            "id": str(plan.id),
            "name": plan.name,
            "description": plan.description,
            "monthly_price_cents": plan.monthly_price_cents,
            "annual_price_cents": plan.annual_price_cents,
            "benefits": plan.benefits,
            "discount_percentage": plan.discount_percentage,
            "status": plan.status,
            "is_active": plan.is_active,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    def _subscription_to_dict(
        self, sub: MembershipSubscription,
        plan_name: str | None = None,
        discount: int = 0,
        monthly_price_cents: int = 0,
        benefits: dict | None = None,
    ) -> dict[str, Any]:
        return {
            "id": str(sub.id),
            "patient_id": str(sub.patient_id),
            "plan_id": str(sub.plan_id),
            "plan_name": plan_name,
            "monthly_price_cents": monthly_price_cents,
            "discount_percentage": discount,
            "benefits": benefits,
            "status": sub.status,
            "start_date": sub.start_date,
            "next_billing_date": sub.next_billing_date,
            "cancelled_at": sub.cancelled_at,
            "paused_at": sub.paused_at,
            "payment_method": sub.payment_method,
            "is_active": sub.is_active,
            "created_at": sub.created_at,
            "updated_at": sub.updated_at,
        }


membership_service = MembershipService()
