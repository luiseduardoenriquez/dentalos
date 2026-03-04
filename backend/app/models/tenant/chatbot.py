"""AI Virtual Receptionist (Chatbot) models -- VP-16.

Stores chatbot conversations and messages for both WhatsApp and web
widget channels.  ChatbotConversation optionally links to an existing
WhatsAppConversation for channel unification.

Security:
  - PHI (patient names, message content) is NEVER logged.
  - All operations are tenant-scoped via the AsyncSession search_path.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class ChatbotConversation(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A chatbot conversation session.

    Conversations can originate from WhatsApp (linked via
    whatsapp_conversation_id) or from the embeddable web widget.
    patient_id is nullable -- anonymous web visitors don't have a
    patient record until identified.
    """

    __tablename__ = "chatbot_conversations"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('whatsapp', 'web')",
            name="chk_chatbot_conversations_channel",
        ),
        CheckConstraint(
            "status IN ('active', 'resolved', 'escalated')",
            name="chk_chatbot_conversations_status",
        ),
        Index("idx_chatbot_conversations_status", "status"),
        Index("idx_chatbot_conversations_channel", "channel"),
        Index("idx_chatbot_conversations_patient", "patient_id"),
        Index(
            "idx_chatbot_conversations_whatsapp",
            "whatsapp_conversation_id",
        ),
        Index("idx_chatbot_conversations_started", "started_at"),
    )

    whatsapp_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="web"
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    intent_history: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ChatbotConversation {self.id} "
            f"channel={self.channel} status={self.status}>"
        )


class ChatbotMessage(UUIDPrimaryKeyMixin, TenantBase):
    """A single message within a chatbot conversation.

    role values:
      - 'user'      -- message from the patient / visitor
      - 'assistant'  -- bot-generated reply
      - 'system'     -- internal system event (e.g. escalation notice)
    """

    __tablename__ = "chatbot_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="chk_chatbot_messages_role",
        ),
        Index(
            "idx_chatbot_messages_conversation",
            "conversation_id",
            "created_at",
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbot_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    intent: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ChatbotMessage {self.id} "
            f"role={self.role} intent={self.intent}>"
        )
