"""Waitlist entry model — lives in each tenant schema.

One table:
  - WaitlistEntry: a patient waiting for an opening with an optional doctor
    and scheduling preferences. The notification service scans waiting entries
    whenever a slot is freed and bumps notification_count on each contact.
"""

import uuid
from datetime import date, datetime, time

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
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class WaitlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A patient on the appointment waitlist.

    Status transitions:
        waiting → notified → scheduled
        waiting | notified → expired | cancelled

    preferred_days is a JSONB array of integers (0=Monday … 6=Sunday).
    preferred_time_from / preferred_time_to define the acceptable time window.
    valid_until caps when the entry should auto-expire.

    The notification service increments notification_count and stamps
    last_notified_at each time it contacts the patient.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('waiting', 'notified', 'scheduled', 'expired', 'cancelled')",
            name="chk_waitlist_entries_status",
        ),
        Index("idx_waitlist_entries_status", "status"),
        Index("idx_waitlist_entries_patient", "patient_id"),
    )

    # Patient reference
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Optional doctor preference (null = any available doctor)
    preferred_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Procedure hint — free text (not a FK; may not map to a catalog item yet)
    procedure_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Scheduling preferences
    preferred_days: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    preferred_time_from: Mapped[time | None] = mapped_column(Time, nullable=True)
    preferred_time_to: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Expiry
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")

    # Notification tracking
    notification_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<WaitlistEntry patient={self.patient_id} "
            f"status={self.status} doctor={self.preferred_doctor_id}>"
        )
