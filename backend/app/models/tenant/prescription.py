"""Prescription model — lives in each tenant schema.

One table:
  - Prescription: a medical prescription issued by a doctor for a patient.
    Medications are stored as a JSONB array for flexibility.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Prescription(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A medical prescription for a patient.

    Medications are stored as a JSONB array of objects:
    [
        {
            "name": "Amoxicilina",
            "dosis": "500mg",
            "frecuencia": "Cada 8 horas",
            "duracion_dias": 7,
            "via": "oral",
            "instrucciones": "Tomar después de comidas"
        }
    ]

    Linked optionally to a diagnosis for clinical context.
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "prescriptions"
    __table_args__ = (
        Index("idx_prescriptions_patient", "patient_id"),
        Index("idx_prescriptions_doctor", "doctor_id"),
        Index("idx_prescriptions_created_at", "created_at"),
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

    # Medications — JSONB array (see docstring for schema)
    medications: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Optional diagnosis link
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id"),
        nullable=True,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Prescription patient={self.patient_id} "
            f"doctor={self.doctor_id}>"
        )
