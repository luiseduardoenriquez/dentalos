"""Admin announcement model for platform-wide communications."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class AdminAnnouncement(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    __tablename__ = "admin_announcements"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    announcement_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="info"
    )
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="all"
    )
    visibility_filter: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    is_dismissable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("superadmins.id"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AdminAnnouncement {self.title[:30]}>"
