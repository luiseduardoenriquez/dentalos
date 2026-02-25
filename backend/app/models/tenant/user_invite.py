"""UserInvite model — pending team member invitations."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class UserInvite(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    __tablename__ = "user_invites"
    __table_args__ = (
        CheckConstraint(
            "role IN ('doctor', 'assistant', 'receptionist')",
            name="chk_invites_role",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'expired', 'cancelled')",
            name="chk_invites_status",
        ),
    )

    # Invite details
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Inviter
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Token
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    inviter: Mapped["User"] = relationship(
        back_populates="sent_invites", foreign_keys=[invited_by]
    )

    def __repr__(self) -> str:
        return f"<UserInvite {self.email} ({self.role}) status={self.status}>"
