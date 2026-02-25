"""Medical history timeline schemas."""

from datetime import datetime

from pydantic import BaseModel


class MedicalHistoryEvent(BaseModel):
    """A single event in the medical history timeline."""

    event_id: str
    event_type: str
    event_code: str | None = None
    event_description: str | None = None
    event_date: datetime


class MedicalHistoryResponse(BaseModel):
    """Cursor-paginated medical history timeline."""

    items: list[MedicalHistoryEvent]
    next_cursor: str | None = None
    has_more: bool
