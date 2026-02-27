"""Feature flag model — platform-wide feature toggles (public schema)."""

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureFlag(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    """Platform feature flag for controlling feature rollout.

    Flags can be scoped globally, per-plan, or per-tenant:
      - scope="global": applies to all tenants
      - scope="plan": applies to tenants on a matching plan (plan_filter)
      - scope="tenant": applies to a specific tenant (tenant_id)

    When enabled=False, the feature is off regardless of scope.
    """

    __tablename__ = "feature_flags"

    flag_name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    scope: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plan_filter: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<FeatureFlag {self.flag_name} enabled={self.enabled}>"
