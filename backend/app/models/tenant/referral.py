"""Patient referral model — referrals between doctors within a tenant."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class PatientReferral(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Referral from one doctor to another within the same clinic.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "patient_referrals"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('urgent', 'normal', 'low')",
            name="chk_patient_referrals_priority",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'completed', 'declined')",
            name="chk_patient_referrals_status",
        ),
        CheckConstraint(
            "from_doctor_id != to_doctor_id",
            name="chk_patient_referrals_different_doctors",
        ),
        Index("idx_patient_referrals_patient", "patient_id"),
        Index("idx_patient_referrals_to_doctor_status", "to_doctor_id", "status"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    from_doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    to_doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="normal"
    )
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete — clinical data is never hard-deleted
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PatientReferral {self.id} from={self.from_doctor_id} to={self.to_doctor_id} status={self.status}>"
