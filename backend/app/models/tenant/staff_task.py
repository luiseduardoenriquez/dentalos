"""Staff task model — lightweight internal task tracking."""
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class StaffTask(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Lightweight task for staff follow-up (delinquency, acceptance, manual).

    task_type:
      - delinquency: auto-created when invoice is overdue past threshold
      - acceptance:  auto-created when quotation has not been accepted
      - manual:      created directly by staff

    Status lifecycle: open -> in_progress -> completed | dismissed
                      open -> dismissed (shortcut)
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "staff_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('delinquency', 'acceptance', 'manual')",
            name="chk_staff_tasks_type",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'dismissed')",
            name="chk_staff_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="chk_staff_tasks_priority",
        ),
        Index("idx_staff_tasks_status", "status"),
        Index("idx_staff_tasks_type", "task_type"),
        Index("idx_staff_tasks_assigned", "assigned_to"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, server_default="normal")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    # Generic reference to the source record (invoice_id, quotation_id, etc.)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Extra context stored as JSONB (threshold days for delinquency, etc.)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<StaffTask type={self.task_type} status={self.status} "
            f"priority={self.priority}>"
        )
