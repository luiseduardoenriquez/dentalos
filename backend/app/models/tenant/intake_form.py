"""Intake form models — templates and submissions."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class IntakeFormTemplate(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A reusable intake form template with field definitions."""

    __tablename__ = "intake_form_templates"
    __table_args__ = (
        Index("idx_intake_templates_active", "is_active"),
        Index("idx_intake_templates_default", "is_default"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    consent_template_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )


class IntakeSubmission(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A patient's completed intake form submission."""

    __tablename__ = "intake_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'reviewed', 'approved', 'rejected')",
            name="chk_intake_submissions_status",
        ),
        Index("idx_intake_submissions_status", "status"),
        Index("idx_intake_submissions_appointment", "appointment_id"),
        Index("idx_intake_submissions_patient", "patient_id"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_form_templates.id"), nullable=False,
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True,
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
