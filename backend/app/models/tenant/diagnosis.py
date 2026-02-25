"""Diagnosis model — lives in each tenant schema.

One table:
  - Diagnosis: patient CIE-10 diagnosis linked to a doctor and optionally a tooth.
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


class Diagnosis(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A CIE-10 diagnosis for a patient.

    Linked to the diagnosing doctor. Optionally linked to a specific tooth
    (FDI notation). Severity tracks clinical urgency. Status tracks resolution.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('mild', 'moderate', 'severe')",
            name="chk_diagnoses_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'resolved')",
            name="chk_diagnoses_status",
        ),
        Index("idx_diagnoses_patient", "patient_id"),
        Index("idx_diagnoses_doctor", "doctor_id"),
        Index("idx_diagnoses_cie10", "cie10_code"),
        Index("idx_diagnoses_status", "status"),
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

    # CIE-10 classification
    cie10_code: Mapped[str] = mapped_column(String(10), nullable=False)
    cie10_description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Clinical assessment
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="moderate")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional tooth reference (FDI notation)
    tooth_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Resolution tracking
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Diagnosis patient={self.patient_id} "
            f"cie10={self.cie10_code} status={self.status}>"
        )
