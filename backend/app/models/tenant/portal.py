"""Portal models — patient portal credentials and invitations."""

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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class PortalCredentials(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Patient portal login credentials."""

    __tablename__ = "portal_credentials"
    __table_args__ = (
        UniqueConstraint("patient_id", name="uq_portal_credentials_patient"),
        Index("idx_portal_credentials_patient_id", "patient_id"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<PortalCredentials patient_id={self.patient_id}>"


class PortalInvitation(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Portal invitation token tracking."""

    __tablename__ = "portal_invitations"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'whatsapp')",
            name="chk_portal_invitations_channel",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'accepted', 'expired')",
            name="chk_portal_invitations_status",
        ),
        Index("idx_portal_invitations_patient_id", "patient_id"),
        Index("idx_portal_invitations_token_hash", "token_hash"),
        Index(
            "idx_portal_invitations_expires",
            "expires_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(15), nullable=False)
    status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="pending"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PortalInvitation patient_id={self.patient_id} status={self.status}>"
