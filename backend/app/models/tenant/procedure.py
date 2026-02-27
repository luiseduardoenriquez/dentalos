"""Procedure model — lives in each tenant schema.

One table:
  - Procedure: a completed clinical procedure linked to a patient, doctor,
    CUPS code, and optionally a treatment plan item and clinical record.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Procedure(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A completed clinical procedure for a patient.

    Links to CUPS code, optional treatment plan item (UNIQUE — one procedure
    per plan item), optional clinical record, and optional tooth/zones.

    Materials used and procedure zones are stored as JSONB for flexibility.
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "procedures"
    __table_args__ = (
        Index("idx_procedures_patient", "patient_id"),
        Index("idx_procedures_doctor", "doctor_id"),
        Index("idx_procedures_cups", "cups_code"),
        Index("idx_procedures_created_at", "created_at"),
        Index("idx_procedures_clinical_record", "clinical_record_id"),
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

    # CUPS classification
    cups_code: Mapped[str] = mapped_column(String(10), nullable=False)
    cups_description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Tooth and zone details
    tooth_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    zones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Materials used — array of {name, quantity, lot_number}
    materials_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Duration
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Treatment plan item link — UNIQUE (one procedure per plan item)
    treatment_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plan_items.id"),
        nullable=True,
        unique=True,
    )

    # Clinical record link
    clinical_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinical_records.id"),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Procedure patient={self.patient_id} "
            f"cups={self.cups_code} tooth={self.tooth_number}>"
        )
