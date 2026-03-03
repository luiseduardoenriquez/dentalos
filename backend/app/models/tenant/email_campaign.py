"""Email marketing campaign models — campaigns and per-recipient tracking.

Security invariants:
  - PHI is NEVER logged (no patient emails or names in log lines).
  - Recipients are stored per-campaign; their email is cached at send time
    so the column captures historical state even if the patient updates it.
  - Soft delete on campaigns only (recipients are never hard-deleted either —
    they form an audit trail for unsubscribe proof).
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class EmailCampaign(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A one-shot email marketing campaign.

    Lifecycle: draft → scheduled (optional) → sending → sent | cancelled.
    A campaign can only be edited while in 'draft' status.
    """

    __tablename__ = "email_campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'sent', 'cancelled')",
            name="chk_email_campaigns_status",
        ),
        Index("idx_email_campaigns_status", "status"),
        Index("idx_email_campaigns_created_by", "created_by"),
        Index("idx_email_campaigns_scheduled_at", "scheduled_at"),
        Index("idx_email_campaigns_is_active", "is_active"),
    )

    # Content
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Targeting
    segment_filters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Engagement counters — incremented atomically by the tracking service
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bounce_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsubscribe_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Ownership
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Soft delete — campaigns are never hard-deleted
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<EmailCampaign name={self.name!r} status={self.status}>"


class EmailCampaignRecipient(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-recipient delivery and engagement tracking for an email campaign.

    One row per (campaign, patient) pair. The email address is captured at
    send time — if the patient later changes their email this row is
    unaffected, preserving an accurate audit trail.
    """

    __tablename__ = "email_campaign_recipients"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "patient_id", name="uq_email_recipients_campaign_patient"
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'opened', 'clicked', 'bounced', 'unsubscribed')",
            name="chk_email_recipients_status",
        ),
        Index("idx_email_recipients_campaign", "campaign_id"),
        Index("idx_email_recipients_patient", "patient_id"),
        Index("idx_email_recipients_status", "status"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_campaigns.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    # Email captured at enqueue time; immutable thereafter
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    # Delivery lifecycle
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    clicked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<EmailCampaignRecipient campaign={self.campaign_id!s:.8} "
            f"patient={self.patient_id!s:.8} status={self.status}>"
        )
