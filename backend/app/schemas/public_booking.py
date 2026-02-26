"""Public booking schemas — no JWT required.

These schemas are used by the /api/v1/public/{slug}/booking endpoints which
allow patients to self-book without an existing session.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── Request Schemas ──────────────────────────────────────────────────────────


class PublicBookingRequest(BaseModel):
    """All fields needed to self-book an appointment.

    If a patient with the given document number already exists in the tenant,
    the appointment is linked to their existing record. Otherwise a new
    patient record is created automatically.
    """

    doctor_id: str
    start_time: datetime
    type: str = Field(
        default="consultation",
        pattern=r"^(consultation|procedure|follow_up)$",
    )
    # Patient identification
    patient_first_name: str = Field(min_length=1, max_length=200)
    patient_last_name: str = Field(min_length=1, max_length=200)
    patient_document_type: str = Field(default="CC")
    patient_document_number: str = Field(pattern=r"^[0-9]{6,12}$")
    patient_phone: str = Field(pattern=r"^\+?[0-9]{7,15}$")
    patient_email: str | None = None
    captcha_token: str | None = None  # CAPTCHA stub; validated server-side when present
    notes: str | None = None


# ─── Response Schemas ─────────────────────────────────────────────────────────


class BookingConfigResponse(BaseModel):
    """Public configuration shown on the self-booking page.

    Lists available doctors and the next 30 days that have open slots.
    """

    clinic_name: str
    clinic_slug: str
    doctors: list[dict]  # [{id, name, specialties}]
    appointment_types: list[str]
    available_dates: list[str]  # ISO date strings for the next 30 days


class PublicBookingResponse(BaseModel):
    """Confirmation returned after a successful self-booking."""

    appointment_id: str
    patient_id: str
    doctor_name: str
    start_time: datetime
    end_time: datetime
    type: str
    status: str
    confirmation_message: str
