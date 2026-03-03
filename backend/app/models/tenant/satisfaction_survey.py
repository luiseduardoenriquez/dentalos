"""SatisfactionSurvey model — VP-09 Reputation Management.

Tracks post-appointment satisfaction surveys and routes responses
to either Google Reviews (promoters) or private feedback (detractors).
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


class SatisfactionSurvey(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A post-appointment satisfaction survey sent to a patient."""

    __tablename__ = "satisfaction_surveys"
    __table_args__ = (
        CheckConstraint(
            "score >= 1 AND score <= 5",
            name="chk_satisfaction_surveys_score",
        ),
        CheckConstraint(
            "channel_sent IN ('whatsapp', 'sms', 'email')",
            name="chk_satisfaction_surveys_channel",
        ),
        CheckConstraint(
            "routed_to IN ('google_review', 'private_feedback')",
            name="chk_satisfaction_surveys_routed_to",
        ),
        UniqueConstraint("survey_token", name="uq_satisfaction_surveys_token"),
        Index("idx_satisfaction_surveys_patient", "patient_id"),
        Index("idx_satisfaction_surveys_token", "survey_token"),
        Index("idx_satisfaction_surveys_appointment", "appointment_id"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True,
    )
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_sent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    survey_token: Mapped[str] = mapped_column(String(64), nullable=False)
    routed_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
