"""WhatsApp bidirectional chat models -- VP-12.

Stores conversations, messages, and quick replies for the WhatsApp chat
inbox feature.  Conversations link to patients by phone number; unknown
phones remain patient_id = NULL until manually matched.

Security:
  - PHI (patient names, phone numbers, message content) is NEVER logged.
  - All operations are tenant-scoped via the AsyncSession search_path.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class WhatsAppConversation(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A WhatsApp conversation thread tied to a single phone number.

    patient_id is nullable -- an inbound message from an unknown phone
    creates a conversation without a patient link until staff matches it.
    """

    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived', 'closed')",
            name="chk_whatsapp_conversations_status",
        ),
        Index("idx_whatsapp_conversations_phone", "phone_number"),
        Index("idx_whatsapp_conversations_patient", "patient_id"),
        Index("idx_whatsapp_conversations_status", "status"),
        Index(
            "idx_whatsapp_conversations_last_msg",
            "last_message_at",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=True,
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_inbound_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unread_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    def __repr__(self) -> str:
        return (
            f"<WhatsAppConversation {self.id} "
            f"status={self.status} unread={self.unread_count}>"
        )


class WhatsAppMessage(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single WhatsApp message within a conversation.

    direction = 'inbound'  -> patient sent to clinic
    direction = 'outbound' -> clinic staff sent to patient
    """

    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="chk_whatsapp_messages_direction",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'read', 'failed')",
            name="chk_whatsapp_messages_status",
        ),
        Index("idx_whatsapp_messages_conversation", "conversation_id", "created_at"),
        Index("idx_whatsapp_messages_wa_id", "whatsapp_message_id"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_conversations.id"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    media_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    media_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    whatsapp_message_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    sent_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<WhatsAppMessage {self.id} "
            f"dir={self.direction} status={self.status}>"
        )


class WhatsAppQuickReply(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Pre-written quick reply templates for the chat inbox.

    Staff can click a quick reply to auto-fill message content.
    """

    __tablename__ = "whatsapp_quick_replies"
    __table_args__ = (
        Index("idx_whatsapp_quick_replies_category", "category"),
        Index("idx_whatsapp_quick_replies_sort", "sort_order"),
    )

    title: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    body: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WhatsAppQuickReply {self.id} title='{self.title}'>"
