"""Post-operative instruction template model."""
from sqlalchemy import Boolean, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class PostopTemplate(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Template for post-operative instructions sent to patients."""

    __tablename__ = "postop_templates"
    __table_args__ = (
        CheckConstraint(
            "channel_preference IN ('whatsapp', 'email', 'portal', 'all')",
            name="chk_postop_templates_channel",
        ),
        Index("idx_postop_templates_procedure_type", "procedure_type"),
        Index("idx_postop_templates_active", "is_active"),
    )

    procedure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instruction_content: Mapped[str] = mapped_column(Text, nullable=False)
    channel_preference: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="all"
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
