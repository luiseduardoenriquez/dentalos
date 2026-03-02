"""Recall campaign schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class RecallScheduleStep(BaseModel):
    """A single step in a recall campaign sequence."""
    day_offset: int = Field(ge=0)
    channel: str = Field(pattern=r"^(whatsapp|sms|email)$")
    message_template: str


class RecallCampaignCreate(BaseModel):
    """Create a new recall campaign."""
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern=r"^(recall|reactivation|treatment_followup|birthday)$")
    filters: dict | None = None
    message_templates: dict | None = None
    channel: str = Field(default="whatsapp", pattern=r"^(whatsapp|sms|email|multi)$")
    schedule: list[RecallScheduleStep] | None = None


class RecallCampaignUpdate(BaseModel):
    """Update an existing recall campaign."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    filters: dict | None = None
    message_templates: dict | None = None
    channel: str | None = Field(default=None, pattern=r"^(whatsapp|sms|email|multi)$")
    schedule: list[RecallScheduleStep] | None = None


class RecallCampaignResponse(BaseModel):
    """Recall campaign details with aggregated stats."""
    id: str
    name: str
    type: str
    filters: dict | None = None
    message_templates: dict | None = None
    channel: str
    schedule: list[dict] | None = None
    status: str
    created_by: str | None = None
    activated_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Aggregated stats
    total_recipients: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    booked_count: int = 0
    failed_count: int = 0


class RecallRecipientResponse(BaseModel):
    """A recipient in a recall campaign."""
    id: str
    campaign_id: str
    patient_id: str
    patient_name: str | None = None
    status: str
    current_step: int
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    responded_at: datetime | None = None
    booked_appointment_id: str | None = None
    opted_out: bool
