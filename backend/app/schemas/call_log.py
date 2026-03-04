"""Pydantic schemas for call log endpoints -- VP-18."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CallLogResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID | None = None
    phone_number: str
    direction: str
    status: str
    duration_seconds: int | None = None
    staff_id: uuid.UUID | None = None
    twilio_call_sid: str | None = None
    notes: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CallLogListResponse(BaseModel):
    items: list[CallLogResponse]
    total: int
    page: int
    page_size: int


class CallLogUpdateNotes(BaseModel):
    notes: str = Field(..., min_length=1, max_length=2000)
