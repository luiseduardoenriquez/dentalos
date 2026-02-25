"""UserTenantMembership — maps users to tenants with roles (public schema)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class UserTenantMembership(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    __tablename__ = "user_tenant_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
        CheckConstraint(
            "role IN ('clinic_owner', 'doctor', 'assistant', 'receptionist')",
            name="chk_membership_role",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="chk_membership_status",
        ),
    )

    # User ID lives in tenant schema — no FK enforced at DB level
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Tenant FK
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role & status
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Audit
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership user={self.user_id} tenant={self.tenant_id} role={self.role}>"
