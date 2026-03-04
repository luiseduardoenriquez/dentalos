"""Call log model -- VP-18 VoIP Screen Pop / Sprint 31-32.

Tracks inbound and outbound phone calls with patient matching for screen-pop.
PHI (phone numbers) — never log raw values.
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class CallLog(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A logged phone call (inbound or outbound) with optional patient matching.

    Status lifecycle: ringing → in_progress → completed
                                            → missed
                                            → voicemail
    """

    __tablename__ = "call_logs"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="chk_call_logs_direction",
        ),
        CheckConstraint(
            "status IN ('ringing', 'in_progress', 'completed', 'missed', 'voicemail')",
            name="chk_call_logs_status",
        ),
        Index("idx_call_logs_patient", "patient_id"),
        Index("idx_call_logs_phone", "phone_number"),
        Index("idx_call_logs_started_at", "started_at"),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'ringing'"),
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    twilio_call_sid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<CallLog direction={self.direction} status={self.status}>"
