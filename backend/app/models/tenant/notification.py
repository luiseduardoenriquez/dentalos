"""Notification models — in-app notifications, preferences, and delivery tracking."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """In-app notification storage.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "idx_notifications_user_feed",
            "user_id",
            "deleted_at",
            "created_at",
            "id",
        ),
        Index("idx_notifications_user_read", "user_id", "read_at"),
        Index("idx_notifications_user_type", "user_id", "type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Notification {self.id} type={self.type} user={self.user_id}>"


class NotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-user notification channel preferences (lazy-initialized).

    Stores a JSONB dict of event_type → channel booleans.
    in_app is always true and read-only.
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<NotificationPreference user={self.user_id}>"


class NotificationDeliveryLog(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-channel delivery tracking for notification dispatch."""

    __tablename__ = "notification_delivery_logs"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            "channel",
            name="uq_delivery_log_idempotency",
        ),
    )

    notification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<NotificationDeliveryLog {self.id} channel={self.channel} status={self.status}>"
