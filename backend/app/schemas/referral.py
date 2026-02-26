"""Referral request/response schemas — P-15."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ─────────────────────────────────────────────────────────


class ReferralCreate(BaseModel):
    """Create a referral from the current doctor to another."""

    to_doctor_id: str
    reason: str = Field(..., min_length=1, max_length=2000)
    priority: str = Field(default="normal", pattern=r"^(urgent|normal|low)$")
    specialty: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class ReferralUpdate(BaseModel):
    """Update a referral status."""

    status: str = Field(..., pattern=r"^(accepted|completed|declined)$")
    notes: str | None = Field(default=None, max_length=2000)


# ─── Response Schemas ────────────────────────────────────────────────────────


class ReferralResponse(BaseModel):
    """Full referral detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    from_doctor_id: str
    from_doctor_name: str | None = None
    to_doctor_id: str
    to_doctor_name: str | None = None
    reason: str
    priority: str
    specialty: str | None = None
    status: str
    notes: str | None = None
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReferralListResponse(BaseModel):
    """Paginated list of referrals."""

    items: list[ReferralResponse]
    total: int
    page: int
    page_size: int
