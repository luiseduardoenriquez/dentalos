"""Messaging request/response schemas — MS-01 through MS-05."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ─────────────────────────────────────────────────────────


class ThreadCreate(BaseModel):
    """Create a new message thread with an initial message."""

    patient_id: str
    subject: str | None = Field(default=None, max_length=200)
    initial_message: str = Field(..., min_length=1, max_length=2000)


class MessageSend(BaseModel):
    """Send a message in an existing thread."""

    body: str = Field(..., min_length=1, max_length=2000)


# ─── Response Schemas ────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    """Single message detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    thread_id: str
    sender_type: str
    sender_id: str
    sender_name: str | None = None
    body: str
    attachments: dict | None = None
    read_at: datetime | None = None
    created_at: datetime


class ThreadResponse(BaseModel):
    """Thread summary for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    subject: str | None = None
    status: str
    created_by: str
    last_message_at: datetime
    unread_count: int = 0
    created_at: datetime


class ThreadDetailResponse(ThreadResponse):
    """Thread with messages included."""

    messages: list[MessageResponse] = []


class ThreadPagination(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False


class ThreadListResponse(BaseModel):
    """Cursor-paginated thread list."""

    data: list[ThreadResponse]
    pagination: ThreadPagination


class MessageListResponse(BaseModel):
    """Cursor-paginated message list within a thread."""

    data: list[MessageResponse]
    pagination: ThreadPagination
