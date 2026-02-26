"""Appointment model — lives in each tenant schema.

One table:
  - Appointment: a scheduled visit between a patient and a doctor.
    Links optionally to a treatment plan item for auto-flow.
    Status lifecycle: scheduled → confirmed → in_progress → completed | cancelled | no_show.
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A scheduled appointment between a patient and a doctor.

    Status transitions:
        scheduled → confirmed → in_progress → completed
        scheduled | confirmed | in_progress → cancelled
        confirmed | in_progress → no_show

    Linked to a TreatmentPlanItem when the appointment originates from the
    auto-flow (Odontogram → Treatment Plan → Quotation → Appointment).

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "type IN ('consultation', 'procedure', 'emergency', 'follow_up')",
            name="chk_appointments_type",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show')",
            name="chk_appointments_status",
        ),
        # Primary scheduling lookup — agenda view queries by doctor + day + status
        Index("idx_appointments_doctor_start_status", "doctor_id", "start_time", "status"),
        # Patient history view
        Index("idx_appointments_patient_start", "patient_id", "start_time"),
        # Slot-availability checks need a plain start_time index
        Index("idx_appointments_start_time", "start_time"),
        # Cursor-based pagination (ordered by start_time, then id as tiebreaker)
        Index("idx_appointments_cursor", "start_time", "id"),
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

    # Scheduling
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Classification
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")

    # Optional link to a treatment plan item (auto-flow)
    treatment_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plan_items.id"),
        nullable=True,
    )

    # Cancellation details
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by_patient: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # No-show and completion timestamps
    no_show_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment patient={self.patient_id} "
            f"doctor={self.doctor_id} start={self.start_time} status={self.status}>"
        )
