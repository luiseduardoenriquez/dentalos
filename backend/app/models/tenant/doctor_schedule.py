"""Doctor schedule models — live in each tenant schema.

Two tables:
  - DoctorSchedule:    weekly recurring availability per doctor (one row per day of week)
  - AvailabilityBlock: ad-hoc time blocks when a doctor is NOT available
                       (vacations, conferences, sick leave, etc.)
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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class DoctorSchedule(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Weekly recurring schedule for a doctor.

    One row per (doctor, day_of_week) — enforced by unique constraint.
    day_of_week follows ISO: 0=Monday … 6=Sunday.
    When is_working=False, start_time/end_time are null and the day is blocked.

    breaks is a JSONB array of {start: "HH:MM", end: "HH:MM"} objects representing
    lunch breaks or other intra-day gaps.

    appointment_duration_defaults is a JSONB map that pre-fills duration when
    the scheduler creates a new appointment of each type.
    """

    __tablename__ = "doctor_schedules"
    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="chk_doctor_schedules_day_of_week",
        ),
        UniqueConstraint("user_id", "day_of_week", name="uq_doctor_schedules_user_day"),
        Index("idx_doctor_schedules_user", "user_id"),
    )

    # Doctor reference
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Day (0=Monday, 6=Sunday)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)

    # Working flag — when False, start_time/end_time/breaks are irrelevant
    is_working: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Working hours (null when is_working=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Intra-day breaks — [{start: "HH:MM", end: "HH:MM"}, ...]
    breaks: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )

    # Default appointment durations in minutes per type
    appointment_duration_defaults: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text(
            '\'{"consultation": 30, "procedure": 60, "emergency": 30, "follow_up": 20}\'::jsonb'
        ),
        default=lambda: {
            "consultation": 30,
            "procedure": 60,
            "emergency": 30,
            "follow_up": 20,
        },
    )

    def __repr__(self) -> str:
        return (
            f"<DoctorSchedule user={self.user_id} "
            f"day={self.day_of_week} working={self.is_working}>"
        )


class AvailabilityBlock(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Ad-hoc time block indicating a doctor is NOT available.

    Used for vacations, conferences, sick leave, and similar one-off absences.
    Recurring blocks (e.g. weekly training) are supported via is_recurring +
    recurring_until — the service layer expands them when computing free slots.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "availability_blocks"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('vacation', 'conference', 'personal', 'sick_leave', 'training', 'other')",
            name="chk_availability_blocks_reason",
        ),
        # Slot-availability queries always filter by doctor + time window
        Index("idx_availability_blocks_doctor_time", "doctor_id", "start_time", "end_time"),
    )

    # Doctor reference
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Time window
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Classification
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Recurrence
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurring_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<AvailabilityBlock doctor={self.doctor_id} "
            f"reason={self.reason} start={self.start_time}>"
        )
