"""WhatsApp bidirectional chat request/response schemas -- VP-12.

Covers conversations, messages, quick replies, and the SSE stream.
All JSON field names use snake_case per project convention.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ─────────────────────────────────────────────────────────


class SendMessageRequest(BaseModel):
    """Send a free-form or template message in a conversation."""

    content: str = Field(..., min_length=1, max_length=4096)
    media_url: str | None = Field(default=None, max_length=500)


class AssignRequest(BaseModel):
    """Assign a conversation to a staff user."""

    user_id: str = Field(..., min_length=1)


# ─── Response Schemas ────────────────────────────────────────────────────────


class ConversationResponse(BaseModel):
    """Single WhatsApp conversation summary."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str | None = None
    phone_number: str
    status: str
    assigned_to: str | None = None
    last_message_at: datetime
    unread_count: int = 0
    created_at: datetime


class ConversationListResponse(BaseModel):
    """Paginated list of WhatsApp conversations."""

    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    """Single WhatsApp message detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    direction: str
    content: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    whatsapp_message_id: str | None = None
    status: str
    sent_by: str | None = None
    created_at: datetime


class MessageListResponse(BaseModel):
    """Paginated list of messages within a conversation."""

    items: list[MessageResponse]
    total: int
    page: int
    page_size: int


class QuickReplyResponse(BaseModel):
    """A quick reply template for the chat inbox."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    body: str
    category: str | None = None
    sort_order: int = 0
