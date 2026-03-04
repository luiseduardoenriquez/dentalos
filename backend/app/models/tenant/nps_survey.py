"""NPSSurveyResponse model — VP-21 NPS/CSAT Surveys.

Tracks NPS (0-10) and optional CSAT (1-5) survey responses sent to patients
after appointments. Separate from the existing 1-5 satisfaction_surveys table.

Security invariants:
  - PHI is NEVER logged (no patient names, emails, phone numbers).
  - Survey tokens are cryptographically random (secrets.token_urlsafe) and single-use.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class NPSSurveyResponse(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An NPS/CSAT survey sent to a patient after an appointment."""

    __tablename__ = "nps_survey_responses"
    __table_args__ = (
        CheckConstraint(
            "nps_score >= 0 AND nps_score <= 10",
            name="chk_nps_survey_responses_nps_score",
        ),
        CheckConstraint(
            "csat_score IS NULL OR (csat_score >= 1 AND csat_score <= 5)",
            name="chk_nps_survey_responses_csat_score",
        ),
        CheckConstraint(
            "channel_sent IN ('whatsapp', 'sms', 'email')",
            name="chk_nps_survey_responses_channel",
        ),
        UniqueConstraint("survey_token", name="uq_nps_survey_responses_token"),
        Index("idx_nps_survey_responses_patient", "patient_id"),
        Index("idx_nps_survey_responses_token", "survey_token"),
        Index("idx_nps_survey_responses_appointment", "appointment_id"),
        Index("idx_nps_survey_responses_doctor", "doctor_id"),
        Index("idx_nps_survey_responses_responded_at", "responded_at"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    nps_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    csat_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_sent: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="whatsapp"
    )
    survey_token: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<NPSSurveyResponse id={str(self.id)[:8]} "
            f"nps={self.nps_score} responded={self.responded_at is not None}>"
        )
