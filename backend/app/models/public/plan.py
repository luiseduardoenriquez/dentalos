"""Plan model — subscription plans for tenants."""


from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Limits
    max_patients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_doctors: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_storage_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Features
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Pricing
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    billing_period: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    pricing_model: Mapped[str] = mapped_column(
        String(20), nullable=False, default="per_doctor"
    )
    included_doctors: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    additional_doctor_price_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    tenants: Mapped[list["Tenant"]] = relationship(back_populates="plan")

    def __repr__(self) -> str:
        return f"<Plan {self.name} ({self.slug})>"
