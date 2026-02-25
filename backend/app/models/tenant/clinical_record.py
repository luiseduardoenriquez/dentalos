"""Clinical record models — live in each tenant schema.

Two tables:
  - ClinicalRecord: examination, evolution note, or procedure entry
  - Anamnesis:      one-per-patient medical/dental history form
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalRecord(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single clinical record entry (examination, evolution note, or procedure).

    Content is stored as structured JSONB so templates can vary per record type.
    Records become non-editable 24 hours after creation (edit_locked_at).
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "clinical_records"
    __table_args__ = (
        CheckConstraint(
            "type IN ('examination', 'evolution_note', 'procedure')",
            name="chk_clinical_records_type",
        ),
        Index("idx_clinical_records_patient", "patient_id"),
        Index("idx_clinical_records_doctor", "doctor_id"),
        Index("idx_clinical_records_type", "type"),
        Index("idx_clinical_records_created_at", "created_at"),
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

    # Record data
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Optional tooth references — array of FDI numbers involved in this record
    tooth_numbers: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
    )

    # Template link (nullable — freeform records have no template)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Edit window — locked 24 h after creation
    is_editable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    edit_locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ClinicalRecord patient={self.patient_id} "
            f"type={self.type} doctor={self.doctor_id}>"
        )


class Anamnesis(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Patient medical and dental history form.

    One row per patient (enforced by UNIQUE on patient_id).
    All sections are JSONB to allow variable-depth structured data
    without schema migrations as the intake form evolves.
    """

    __tablename__ = "anamnesis"
    __table_args__ = (
        UniqueConstraint("patient_id", name="uq_anamnesis_patient"),
    )

    # Owner
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
        unique=True,
    )

    # History sections — all nullable so partial saves are allowed
    allergies: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    medications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    medical_history: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dental_history: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    family_history: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    habits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Last editor
    last_updated_by: Mapped[uuid.UUID | None] = mapped_column(
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
        return f"<Anamnesis patient={self.patient_id}>"
