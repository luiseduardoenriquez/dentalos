"""Appointment request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ──────────────────────────────────────────────────────────


class AppointmentCreate(BaseModel):
    """Fields required to create a new appointment."""

    patient_id: str
    doctor_id: str
    start_time: datetime
    type: str = Field(pattern=r"^(consultation|procedure|emergency|follow_up)$")
    duration_minutes: int | None = None  # auto-calculated from type if omitted
    treatment_plan_item_id: str | None = None
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    """Fields that can be updated on an existing appointment."""

    start_time: datetime | None = None
    duration_minutes: int | None = None
    type: str | None = Field(
        default=None, pattern=r"^(consultation|procedure|emergency|follow_up)$"
    )
    notes: str | None = None


class CancelRequest(BaseModel):
    """Request body for cancelling an appointment."""

    reason: str = Field(min_length=1, max_length=500)
    cancelled_by_patient: bool = False


class CompleteRequest(BaseModel):
    """Request body for marking an appointment as completed."""

    completion_notes: str | None = None


class NoShowRequest(BaseModel):
    """Empty body for the no-show action endpoint."""

    pass  # noqa: PIE790 — intentional empty class for action endpoint


class RescheduleRequest(BaseModel):
    """Minimal payload for drag-drop reschedule.

    duration_minutes is optional; when omitted the original value is preserved.
    """

    start_time: datetime
    duration_minutes: int | None = None


class ConfirmRequest(BaseModel):
    """Confirm via JWT (staff) or HMAC token from a patient reminder email."""

    token: str | None = None


# ─── Response Schemas ─────────────────────────────────────────────────────────


class AppointmentResponse(BaseModel):
    """Full appointment detail — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    type: str
    status: str
    treatment_plan_item_id: str | None = None
    cancellation_reason: str | None = None
    cancelled_by_patient: bool = False
    no_show_at: datetime | None = None
    completed_at: datetime | None = None
    completion_notes: str | None = None
    created_by: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Joined fields — populated by the service layer when available
    patient_name: str | None = None
    doctor_name: str | None = None


class AppointmentListResponse(BaseModel):
    """Cursor-based paginated list of appointments."""

    items: list[AppointmentResponse]
    total: int
    next_cursor: str | None = None


# ─── Calendar Schemas ─────────────────────────────────────────────────────────


class CalendarDaySlot(BaseModel):
    """A single appointment slot in the calendar view."""

    id: str
    patient_id: str
    patient_name: str | None = None
    doctor_id: str
    doctor_name: str | None = None
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    type: str
    status: str


class CalendarResponse(BaseModel):
    """Calendar view: date-keyed dict; empty dates are included as empty lists."""

    dates: dict[str, list[CalendarDaySlot]]
    date_from: str
    date_to: str
