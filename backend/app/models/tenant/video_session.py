"""VideoSession model — lives in each tenant schema.

One table:
  - VideoSession: a telemedicine video call linked to an appointment.

Status lifecycle:
  created → waiting → active → ended

Security:
  - PHI (patient names, phone numbers) is NEVER stored in this table.
  - join_url_doctor and join_url_patient contain signed Daily.co tokens;
    they are treated as secrets and NEVER logged.
  - All operations are tenant-scoped via the AsyncSession search_path.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class VideoSession(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A telemedicine video session linked to a scheduled appointment.

    Status transitions:
        created   — room created, URLs generated, not yet joined by anyone
        waiting   — doctor has joined, waiting for patient
        active    — both parties have joined the session
        ended     — session explicitly ended by staff or expired

    Soft delete is not applicable here — ended sessions remain in the table
    for audit and recording retrieval purposes.
    """

    __tablename__ = "video_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'waiting', 'active', 'ended')",
            name="chk_video_sessions_status",
        ),
        CheckConstraint(
            "provider IN ('daily')",
            name="chk_video_sessions_provider",
        ),
        # Primary lookup: find session by appointment
        Index("idx_video_sessions_appointment", "appointment_id"),
        # Filter by status for monitoring dashboards
        Index("idx_video_sessions_status", "status"),
        # Order active sessions by creation time
        Index("idx_video_sessions_created", "created_at"),
    )

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="daily",
        server_default="daily",
    )
    provider_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="created",
        server_default="created",
    )
    # Join URLs contain short-lived Daily.co meeting tokens — never log these
    join_url_doctor: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    join_url_patient: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Recording URL provided by Daily.co cloud recording (may be None)
    recording_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<VideoSession {self.id} "
            f"provider={self.provider} status={self.status}>"
        )
