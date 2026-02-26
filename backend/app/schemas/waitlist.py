"""Waitlist request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ──────────────────────────────────────────────────────────


class WaitlistEntryCreate(BaseModel):
    """Fields required to add a patient to the waitlist."""

    patient_id: str
    preferred_doctor_id: str | None = None
    procedure_type: str | None = None
    preferred_days: list[int] = Field(
        default_factory=list,
        description="Preferred days of week as integers: 0=Monday through 6=Sunday",
    )
    preferred_time_from: str | None = None  # HH:MM
    preferred_time_to: str | None = None  # HH:MM
    valid_until: date | None = None


class WaitlistNotifyRequest(BaseModel):
    """Optional custom message sent when notifying a waitlist patient."""

    message: str | None = None


# ─── Response Schemas ─────────────────────────────────────────────────────────


class WaitlistEntryResponse(BaseModel):
    """Full detail for a single waitlist entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    preferred_doctor_id: str | None = None
    procedure_type: str | None = None
    preferred_days: list[int]
    preferred_time_from: str | None = None
    preferred_time_to: str | None = None
    valid_until: date | None = None
    status: str
    notification_count: int
    last_notified_at: datetime | None = None
    created_at: datetime
    # Joined — populated by the service layer when available
    patient_name: str | None = None


class WaitlistListResponse(BaseModel):
    """Cursor-based paginated list of waitlist entries."""

    items: list[WaitlistEntryResponse]
    total: int
    next_cursor: str | None = None
