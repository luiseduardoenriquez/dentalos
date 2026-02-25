"""User model — lives in each tenant schema."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email_lower", func.lower("email"), unique=True),
        CheckConstraint(
            "role IN ('clinic_owner', 'doctor', 'assistant', 'receptionist')",
            name="chk_users_role",
        ),
    )

    # Identity
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Role
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Professional
    professional_license: Mapped[str | None] = mapped_column(String(50), nullable=True)
    specialties: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Security
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sent_invites: Mapped[list["UserInvite"]] = relationship(
        back_populates="inviter", foreign_keys="UserInvite.invited_by"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
