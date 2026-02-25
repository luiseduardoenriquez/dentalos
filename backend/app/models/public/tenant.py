"""Tenant model — represents a clinic/organization."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'suspended', 'cancelled')",
            name="chk_tenants_status",
        ),
    )

    # Identity
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    schema_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Location & Config
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="CO")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="America/Bogota")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="es-CO")

    # Plan
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False,
    )

    # Owner
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Onboarding
    onboarding_step: Mapped[int] = mapped_column(default=0, nullable=False)

    # Settings & Features
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Lifecycle dates
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    plan: Mapped["Plan"] = relationship(back_populates="tenants", lazy="joined")
    memberships: Mapped[list["UserTenantMembership"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.name} ({self.slug})>"
