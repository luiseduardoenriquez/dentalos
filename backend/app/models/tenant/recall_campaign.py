"""Recall campaign models — campaigns and recipient tracking."""

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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class RecallCampaign(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A recall or reactivation campaign targeting inactive patients."""

    __tablename__ = "recall_campaigns"
    __table_args__ = (
        CheckConstraint(
            "type IN ('recall', 'reactivation', 'treatment_followup', 'birthday')",
            name="chk_recall_campaigns_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')",
            name="chk_recall_campaigns_status",
        ),
        Index("idx_recall_campaigns_status", "status"),
        Index("idx_recall_campaigns_type", "type"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    message_templates: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="whatsapp")
    schedule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecallCampaignRecipient(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A patient targeted by a recall campaign with delivery tracking."""

    __tablename__ = "recall_campaign_recipients"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'opened', 'clicked', 'booked', 'failed', 'opted_out')",
            name="chk_recall_recipients_status",
        ),
        Index("idx_recall_recipients_campaign", "campaign_id"),
        Index("idx_recall_recipients_patient", "patient_id"),
        Index("idx_recall_recipients_status", "status"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recall_campaigns.id"), nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    booked_appointment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
