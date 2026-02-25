"""Treatment plan models — live in each tenant schema.

Two tables:
  - TreatmentPlan: a group of planned procedures for a patient
  - TreatmentPlanItem: individual line item within a plan
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class TreatmentPlan(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A treatment plan grouping planned procedures for a patient.

    Tracks total estimated and actual costs in cents (COP).
    Status transitions: draft → active → completed | cancelled.
    Active requires approval (digital signature).

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "treatment_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'cancelled')",
            name="chk_treatment_plans_status",
        ),
        Index("idx_treatment_plans_patient", "patient_id"),
        Index("idx_treatment_plans_doctor", "doctor_id"),
        Index("idx_treatment_plans_status", "status"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Plan metadata
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Cost tracking — always cents (COP)
    total_cost_estimated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Approval
    signature_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    items: Mapped[list["TreatmentPlanItem"]] = relationship(
        back_populates="plan",
        lazy="selectin",
        order_by="TreatmentPlanItem.priority_order",
    )

    def __repr__(self) -> str:
        return (
            f"<TreatmentPlan patient={self.patient_id} "
            f"status={self.status} name={self.name!r}>"
        )


class TreatmentPlanItem(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single line item within a treatment plan.

    Links to CUPS code with estimated and actual costs in cents.
    Status transitions: pending → scheduled → completed | cancelled.
    procedure_id is set when the actual procedure is recorded (UNIQUE).
    """

    __tablename__ = "treatment_plan_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'scheduled', 'completed', 'cancelled')",
            name="chk_treatment_plan_items_status",
        ),
        Index("idx_treatment_plan_items_plan", "treatment_plan_id"),
        Index("idx_treatment_plan_items_status", "status"),
    )

    # Parent plan
    treatment_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plans.id"),
        nullable=False,
    )

    # CUPS classification
    cups_code: Mapped[str] = mapped_column(String(10), nullable=False)
    cups_description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Tooth reference (optional)
    tooth_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cost — always cents (COP)
    estimated_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Ordering
    priority_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Linked procedure (set when procedure is recorded)
    procedure_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        unique=True,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    plan: Mapped["TreatmentPlan"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<TreatmentPlanItem plan={self.treatment_plan_id} "
            f"cups={self.cups_code} status={self.status}>"
        )
