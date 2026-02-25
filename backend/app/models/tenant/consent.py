"""Consent models — live in each tenant schema.

Two tables:
  - ConsentTemplate: per-tenant customizable consent form templates
  - Consent: a signed (or pending) informed consent document for a patient
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin

_CONSENT_CATEGORIES = (
    "'general','surgery','sedation','orthodontics',"
    "'implants','endodontics','pediatric'"
)


class ConsentTemplate(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-tenant consent form template.

    Tenant templates can override or extend the builtin public templates.
    Content is stored as HTML with Jinja2-style variable placeholders
    (e.g., {{patient_name}}, {{doctor_name}}).
    """

    __tablename__ = "consent_templates"
    __table_args__ = (
        CheckConstraint(
            f"category IN ({_CONSENT_CATEGORIES})",
            name="chk_consent_templates_category",
        ),
        Index("idx_consent_templates_category", "category"),
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
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<ConsentTemplate name={self.name!r} "
            f"category={self.category} v={self.version}>"
        )


class Consent(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An informed consent document for a patient.

    Status transitions: draft → pending_signatures → signed | voided.
    Content is rendered from template at creation time and snapshot is stored
    for immutability. Content hash (SHA-256) is computed at signing.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_signatures', 'signed', 'voided')",
            name="chk_consents_status",
        ),
        Index("idx_consents_patient", "patient_id"),
        Index("idx_consents_status", "status"),
        Index("idx_consents_template", "template_id"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Template reference
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Consent content
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_rendered: Mapped[str] = mapped_column(Text, nullable=False)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")

    # Signing timestamps
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Voiding
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Consent patient={self.patient_id} "
            f"title={self.title!r} status={self.status}>"
        )
