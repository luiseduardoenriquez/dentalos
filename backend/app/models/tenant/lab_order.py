"""Dental lab order models -- VP-22 / Sprint 31-32.

Two tables:
  - DentalLab: directory of external dental laboratories used by the clinic.
  - LabOrder: a work order sent to a dental lab for a patient's restoration,
    prosthesis, appliance, or other lab work.

Clinical data is NEVER hard-deleted (regulatory requirement).
All monetary values in COP cents.
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
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class DentalLab(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An external dental laboratory that the clinic sends work orders to.

    Each tenant maintains its own directory of labs. Labs can be temporarily
    deactivated (is_active=False) without deleting historic order records.
    """

    __tablename__ = "dental_labs"

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)

    # Location
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete / active status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    def __repr__(self) -> str:
        return f"<DentalLab name={self.name!r} city={self.city!r}>"


class LabOrder(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A work order dispatched to an external dental laboratory.

    Status lifecycle:
        pending → sent_to_lab → in_progress → ready → delivered
        (any non-delivered state) → cancelled

    order_type: crown | bridge | denture | implant_abutment | retainer | other
    All monetary values in COP cents.
    """

    __tablename__ = "lab_orders"
    __table_args__ = (
        CheckConstraint(
            "order_type IN ('crown', 'bridge', 'denture', 'implant_abutment', 'retainer', 'other')",
            name="chk_lab_orders_order_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent_to_lab', 'in_progress', 'ready', 'delivered', 'cancelled')",
            name="chk_lab_orders_status",
        ),
        Index("idx_lab_orders_patient", "patient_id"),
        Index("idx_lab_orders_lab", "lab_id"),
        Index("idx_lab_orders_status", "status"),
        Index("idx_lab_orders_due_date", "due_date"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional link to the treatment plan that generated this order
    treatment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plans.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lab assignment (nullable — can be created before choosing a lab)
    lab_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dental_labs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Work order details
    order_type: Mapped[str] = mapped_column(String(30), nullable=False)
    specifications: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Timestamps set automatically on status transitions
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when status transitions to sent_to_lab",
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when status transitions to ready",
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when status transitions to delivered",
    )

    # Financials
    cost_cents: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Lab cost in COP cents",
    )

    # Free-text notes for the lab or internal staff
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<LabOrder order_type={self.order_type!r} "
            f"status={self.status!r} patient={self.patient_id}>"
        )
