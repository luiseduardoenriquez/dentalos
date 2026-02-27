"""Superadmin models — platform-level administrators (public schema)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class Superadmin(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    """Platform-level superadmin account.

    Superadmins live in a separate table from regular users. They
    authenticate with their own JWT flow (aud="dentalos-admin") and
    optionally require TOTP for MFA. An IP allowlist can restrict
    login to known addresses.
    """

    __tablename__ = "superadmins"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # TOTP / MFA
    totp_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Security
    ip_allowlist: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    # Audit
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    sessions: Mapped[list["AdminSession"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Superadmin {self.email}>"


class AdminSession(UUIDPrimaryKeyMixin, PublicBase):
    """Active session for a superadmin login.

    Tracks IP and user-agent for audit trail. Sessions have a fixed
    expiry (1 hour, matching admin JWT TTL).
    """

    __tablename__ = "admin_sessions"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("superadmins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Client info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    admin: Mapped["Superadmin"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<AdminSession admin={self.admin_id} created={self.created_at}>"
