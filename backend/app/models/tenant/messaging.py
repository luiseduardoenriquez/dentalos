"""Messaging models — threads, messages, and participants per tenant."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class MessageThread(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A message thread between clinic staff and a patient.

    Threads are scoped to a single patient but may involve multiple staff members.
    """

    __tablename__ = "message_threads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'closed', 'archived')",
            name="chk_message_threads_status",
        ),
        Index("idx_message_threads_patient", "patient_id"),
        Index("idx_message_threads_patient_last_msg", "patient_id", "last_message_at"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open"
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MessageThread {self.id} patient={self.patient_id} status={self.status}>"


class Message(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single message within a thread.

    sender_type indicates whether the message is from a patient or staff member.
    sender_id is polymorphic — it references a user ID for staff or patient ID for patients.
    """

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('patient', 'staff')",
            name="chk_messages_sender_type",
        ),
        Index("idx_messages_thread_created", "thread_id", "created_at"),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_threads.id"),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} thread={self.thread_id} sender={self.sender_type}>"


class ThreadParticipant(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Tracks who participates in a thread and their last read position."""

    __tablename__ = "thread_participants"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_thread_participants_thread_user"),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_threads.id"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<ThreadParticipant thread={self.thread_id} user={self.user_id}>"
