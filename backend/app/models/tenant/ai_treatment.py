"""AI treatment suggestion model -- lives in each tenant schema.

One table:
  - AITreatmentSuggestion: stores AI-generated treatment recommendations
    linked to a patient's odontogram conditions and service catalog.

The add-on gate (tenant_features["ai_treatment_advisor"]) is enforced
in the service layer, not at the DB level.

Clinical data is NEVER hard-deleted (regulatory requirement).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class AITreatmentSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An AI-generated set of treatment suggestions for a patient.

    Created when a doctor requests AI recommendations based on the
    patient's current odontogram conditions and medical context.

    Status transitions:
      pending_review -> reviewed   (doctor reviews each suggestion item)
      reviewed       -> applied    (accepted items converted to a treatment plan)
      pending_review -> rejected   (doctor dismisses all suggestions)

    The suggestions JSONB column stores an array of suggestion items:
      [
        {
          "cups_code": "990110",
          "cups_description": "Consulta de primera vez",
          "tooth_number": "11",
          "rationale": "...",
          "confidence": "high",
          "priority_order": 1,
          "estimated_cost": 150000,
          "action": null
        },
        ...
      ]

    After review, each item gains an "action" field: "accept", "modify", or "reject".
    """

    __tablename__ = "ai_treatment_suggestions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review', 'reviewed', 'applied', 'rejected')",
            name="chk_ai_treatment_suggestions_status",
        ),
        Index("idx_ai_treatment_suggestions_patient", "patient_id"),
        Index("idx_ai_treatment_suggestions_doctor", "doctor_id"),
        Index("idx_ai_treatment_suggestions_status", "status"),
        Index("idx_ai_treatment_suggestions_created", "created_at"),
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

    # Context snapshots -- stored at generation time for reproducibility
    odontogram_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    patient_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # AI output -- array of suggestion items
    suggestions: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Model tracking
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending_review"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Link to created treatment plan (set when status -> applied)
    treatment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AITreatmentSuggestion patient={self.patient_id} "
            f"doctor={self.doctor_id} status={self.status}>"
        )
