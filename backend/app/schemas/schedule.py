"""Doctor schedule and availability schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Schedule Schemas ─────────────────────────────────────────────────────────


class BreakSlot(BaseModel):
    """A break window within a working day, in HH:MM format."""

    start: str = Field(description="Break start time in HH:MM format")
    end: str = Field(description="Break end time in HH:MM format")


class DoctorScheduleDay(BaseModel):
    """Working hours configuration for a single day of the week."""

    day_of_week: int = Field(ge=0, le=6, description="0=Monday through 6=Sunday")
    is_working: bool = True
    start_time: str | None = None  # HH:MM
    end_time: str | None = None  # HH:MM
    breaks: list[BreakSlot] = Field(default_factory=list)
    appointment_duration_defaults: dict[str, int] = Field(
        default_factory=lambda: {
            "consultation": 30,
            "procedure": 60,
            "emergency": 30,
            "follow_up": 20,
        },
        description="Default duration in minutes per appointment type",
    )


class DoctorScheduleUpdate(BaseModel):
    """Replaces the full weekly schedule for a doctor."""

    schedule: list[DoctorScheduleDay]


class DoctorScheduleResponse(BaseModel):
    """Current weekly schedule for a doctor."""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    schedule: list[DoctorScheduleDay]


# ─── Availability Block Schemas ───────────────────────────────────────────────


class AvailabilityBlockCreate(BaseModel):
    """Fields required to create a blocking period in a doctor's calendar."""

    start_time: datetime
    end_time: datetime
    reason: str = Field(
        pattern=r"^(vacation|conference|personal|sick_leave|training|other)$"
    )
    description: str | None = None
    is_recurring: bool = False
    recurring_until: date | None = None


class AvailabilityBlockResponse(BaseModel):
    """Full detail for a single availability block."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    reason: str
    description: str | None = None
    is_recurring: bool
    recurring_until: date | None = None
    created_at: datetime


# ─── Free-Slot Schemas ────────────────────────────────────────────────────────


class AvailabilitySlot(BaseModel):
    """A single time slot and whether it is bookable."""

    start_time: datetime
    end_time: datetime
    available: bool = True


class AvailabilityResponse(BaseModel):
    """Date-keyed availability grid for a doctor over a date range."""

    doctor_id: str
    date_from: str
    date_to: str
    slot_duration_minutes: int
    slots: dict[str, list[AvailabilitySlot]]  # date string → list of slots
