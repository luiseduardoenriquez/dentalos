"""Reminder configuration schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Sub-models ───────────────────────────────────────────────────────────────


class ReminderRule(BaseModel):
    """A single reminder rule: when to send and via which channels."""

    hours_before: int = Field(
        ge=1,
        le=168,
        description="Hours before the appointment at which to dispatch the reminder",
    )
    channels: list[str] = Field(
        description="Delivery channels to use: sms, email, whatsapp"
    )


# ─── Request Schemas ──────────────────────────────────────────────────────────


class ReminderConfigUpdate(BaseModel):
    """Fields that can be updated in the tenant reminder configuration."""

    reminders: list[ReminderRule] | None = None
    default_channels: list[str] | None = None
    max_reminders_allowed: int | None = Field(default=None, ge=1, le=10)


# ─── Response Schemas ─────────────────────────────────────────────────────────


class ReminderConfigResponse(BaseModel):
    """Current reminder configuration for a tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    reminders: list[ReminderRule]
    default_channels: list[str]
    max_reminders_allowed: int
    created_at: datetime
    updated_at: datetime
