"""Audit log model — immutable audit trail per tenant schema."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TenantBase):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "create", "update", "delete", "login", "logout"
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "user", "patient", "odontogram"
    resource_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # UUID as string
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {"field": {"old": ..., "new": ...}}
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # No updated_at — audit logs are immutable.
    # No is_active / deleted_at — audit logs are never soft-deleted.
