"""Membership models — plans, subscriptions, and usage tracking."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class MembershipPlan(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A membership plan that patients can subscribe to."""

    __tablename__ = "membership_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="chk_membership_plans_status",
        ),
        Index("idx_membership_plans_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    annual_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benefits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    discount_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )


class MembershipSubscription(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A patient's subscription to a membership plan."""

    __tablename__ = "membership_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'paused', 'cancelled', 'expired')",
            name="chk_membership_subscriptions_status",
        ),
        Index("idx_membership_subscriptions_patient", "patient_id"),
        Index("idx_membership_subscriptions_plan", "plan_id"),
        Index("idx_membership_subscriptions_status", "status"),
        Index("idx_membership_subscriptions_billing", "next_billing_date"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_plans.id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MembershipUsageLog(UUIDPrimaryKeyMixin, TenantBase):
    """Log of membership discount usage for auditing."""

    __tablename__ = "membership_usage_log"
    __table_args__ = (
        Index("idx_membership_usage_subscription", "subscription_id"),
        Index("idx_membership_usage_used_at", "used_at"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_subscriptions.id"), nullable=False,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    discount_applied_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
