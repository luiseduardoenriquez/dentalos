"""Public consent template model — lives in the public schema.

One table:
  - PublicConsentTemplate: builtin consent templates shared across all tenants.
    Tenants can override these with their own templates in the tenant schema.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin

_CONSENT_CATEGORIES = (
    "'general','surgery','sedation','orthodontics',"
    "'implants','endodontics','pediatric'"
)


class PublicConsentTemplate(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    """Builtin consent form template shared across all tenants.

    These are system-provided templates that clinics can use as-is or
    customize into their own tenant-level templates. Marked with
    builtin=True so they can be distinguished from user-created templates.
    """

    __tablename__ = "consent_templates"
    __table_args__ = (
        CheckConstraint(
            f"category IN ({_CONSENT_CATEGORIES})",
            name="chk_public_consent_templates_category",
        ),
        Index("idx_public_consent_templates_category", "category"),
        {"schema": "public"},
    )

    # Template metadata
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content — HTML with variable placeholders
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Signature positions — JSONB array of {role, label, required}
    signature_positions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Builtin flag
    builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<PublicConsentTemplate name={self.name!r} "
            f"category={self.category} builtin={self.builtin}>"
        )
