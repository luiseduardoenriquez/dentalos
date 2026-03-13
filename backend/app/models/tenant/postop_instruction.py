"""Post-operative instruction model — tracks instructions sent to patients."""

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class PostopInstruction(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A post-operative instruction sent to a specific patient.

    Links to a PostopTemplate (optional) and records delivery/read status.
    """

    __tablename__ = "postop_instructions"
    __table_args__ = (
        Index("idx_postop_instructions_patient", "patient_id"),
        Index("idx_postop_instructions_sent_at", "sent_at"),
    )

    patient_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    template_id: Mapped["UUID | None"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("postop_templates.id"), nullable=True
    )
    procedure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instruction_content: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="portal"
    )
    doctor_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    sent_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    read_at: Mapped["DateTime | None"] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
