"""AI radiograph analysis model — lives in each tenant schema (AI-01).

One table:
  - RadiographAnalysis: stores AI-generated findings from dental radiograph
    analysis, linked to a patient's document (X-ray image).

The add-on gate (feature flag: ai_radiograph) is enforced in the service
layer, not at the DB level.

Clinical data is NEVER hard-deleted (regulatory requirement).
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class RadiographAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An AI-generated radiograph analysis for a patient.

    Created when a doctor requests AI analysis of a dental radiograph.
    The analysis runs async via RabbitMQ worker (Claude Vision API).

    Status transitions:
      processing -> completed   (worker finished successfully)
      processing -> failed      (worker encountered an error)
      completed  -> reviewed    (doctor reviewed all findings)

    The findings JSONB column stores an array of finding objects:
      [
        {
          "tooth_number": "46",
          "finding_type": "caries",
          "severity": "high",
          "description": "Caries extensa en cara oclusal...",
          "location_detail": "occlusal",
          "confidence": 0.92,
          "suggested_action": "Restauración con resina compuesta",
          "review_action": null,
          "review_note": null
        },
        ...
      ]

    After review, each finding gains review_action (accept/reject/modify)
    and optional review_note fields.
    """

    __tablename__ = "radiograph_analyses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'reviewed')",
            name="chk_radiograph_analyses_status",
        ),
        CheckConstraint(
            "radiograph_type IN ('periapical', 'bitewing', 'panoramic', "
            "'cephalometric', 'occlusal')",
            name="chk_radiograph_analyses_type",
        ),
        Index("idx_radiograph_analyses_patient", "patient_id"),
        Index("idx_radiograph_analyses_doctor", "doctor_id"),
        Index("idx_radiograph_analyses_status", "status"),
        Index("idx_radiograph_analyses_created", "created_at"),
        Index("idx_radiograph_analyses_document", "document_id"),
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

    # Source document (FK to patient_documents — the X-ray image)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_documents.id"),
        nullable=False,
    )

    # Radiograph metadata
    radiograph_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    # AI output
    findings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    radiograph_quality: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Model tracking
    model_used: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="processing"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review tracking
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<RadiographAnalysis patient={self.patient_id} "
            f"type={self.radiograph_type} status={self.status}>"
        )
