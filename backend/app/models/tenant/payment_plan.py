"""Payment plan models — live in each tenant schema.

Two tables:
  - PaymentPlan: plan header with total amount and installment count.
  - PaymentPlanInstallment: individual installments with due dates.
"""

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class PaymentPlan(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A payment plan for an invoice, split into installments.

    Only one active plan per invoice. Status: active -> completed | cancelled.
    """

    __tablename__ = "payment_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="chk_payment_plans_status",
        ),
        Index("idx_payment_plans_invoice", "invoice_id"),
    )

    # Invoice link
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )

    # Patient link
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Plan details
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_installments: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Created by
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    installments: Mapped[list["PaymentPlanInstallment"]] = relationship(
        back_populates="plan",
        lazy="selectin",
        order_by="PaymentPlanInstallment.installment_number",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentPlan invoice={self.invoice_id} "
            f"installments={self.num_installments} status={self.status}>"
        )


class PaymentPlanInstallment(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single installment within a payment plan.

    Tracks due date, payment status, and link to the actual payment record.
    """

    __tablename__ = "payment_plan_installments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'overdue')",
            name="chk_installments_status",
        ),
        Index("idx_installments_plan", "plan_id"),
        Index("idx_installments_due_date", "due_date"),
    )

    # Parent plan
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_plans.id"),
        nullable=False,
    )

    # Installment details
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Payment tracking
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id"),
        nullable=True,
    )

    # Relationships
    plan: Mapped["PaymentPlan"] = relationship(back_populates="installments")

    def __repr__(self) -> str:
        return (
            f"<Installment plan={self.plan_id} "
            f"number={self.installment_number} status={self.status}>"
        )
