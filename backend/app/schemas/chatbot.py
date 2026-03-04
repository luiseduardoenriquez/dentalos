"""AI Virtual Receptionist (Chatbot) request/response schemas -- VP-16.

Covers chatbot conversations, messages, web widget input, and config
management.  All JSON field names use snake_case per project convention.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ─────────────────────────────────────────────────────────


class ChatbotMessageInput(BaseModel):
    """Input for an authenticated (WhatsApp-routed) chatbot message."""

    message: str = Field(..., min_length=1, max_length=1000)


class ChatbotWebMessageInput(BaseModel):
    """Input for the public web widget chatbot endpoint.

    session_id is an opaque string that tracks the web conversation
    across multiple requests.  If omitted on the first call, the server
    creates a new conversation and returns its id.
    """

    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Existing chatbot conversation id to continue.",
    )


class ChatbotConfigUpdate(BaseModel):
    """Partial update of the tenant's chatbot configuration.

    All fields are optional; only supplied fields are merged into the
    existing config JSONB.
    """

    enabled: bool | None = None
    greeting_message: str | None = Field(default=None, max_length=500)
    faq_entries: list[dict] | None = None
    business_hours_text: str | None = Field(default=None, max_length=500)
    escalation_message: str | None = Field(default=None, max_length=500)


# ─── Response Schemas ────────────────────────────────────────────────────────


class ChatbotMessageResponse(BaseModel):
    """Single chatbot message detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    intent: str | None = None
    confidence_score: float | None = None
    created_at: datetime


class ChatbotConversationResponse(BaseModel):
    """Single chatbot conversation summary, optionally with messages."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    patient_id: str | None = None
    patient_name: str | None = None
    patient_phone: str | None = None
    status: str
    last_intent: str | None = None
    intent_confidence: float | None = None
    intent_history: list[Any] = Field(default_factory=list)
    started_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
    message_count: int = 0
    messages: list[ChatbotMessageResponse] | None = None


class ConversationListResponse(BaseModel):
    """Paginated list of chatbot conversations."""

    items: list[ChatbotConversationResponse]
    total: int
    page: int
    page_size: int


class ChatbotConfigResponse(BaseModel):
    """Full chatbot configuration returned to staff."""

    enabled: bool = False
    greeting_message: str = ""
    faq_entries: list[dict] = Field(default_factory=list)
    business_hours_text: str = ""
    escalation_message: str = ""


class ChatbotPublicConfigResponse(BaseModel):
    """Public-safe subset of chatbot configuration for the web widget."""

    enabled: bool = False
    greeting_message: str = ""
