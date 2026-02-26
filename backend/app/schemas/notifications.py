"""Notification request/response schemas — N-01 through N-04, U-09."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class NotificationType(StrEnum):
    appointment_reminder = "appointment_reminder"
    appointment_confirmed = "appointment_confirmed"
    appointment_cancelled = "appointment_cancelled"
    new_patient = "new_patient"
    payment_received = "payment_received"
    payment_overdue = "payment_overdue"
    treatment_plan_approved = "treatment_plan_approved"
    consent_signed = "consent_signed"
    message_received = "message_received"
    referral_received = "referral_received"
    inventory_alert = "inventory_alert"
    system_update = "system_update"


class NotificationChannel(StrEnum):
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"
    in_app = "in_app"


class NotificationStatusFilter(StrEnum):
    read = "read"
    unread = "unread"
    all = "all"


# ─── Response Schemas ─────────────────────────────────────────────────────────


class NotificationMetadata(BaseModel):
    resource_type: str | None = None
    resource_id: str | None = None
    action_url: str | None = None


class NotificationResponse(BaseModel):
    """Single notification detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    body: str
    read_at: datetime | None = None
    created_at: datetime
    meta_data: dict = Field(default_factory=dict)


class NotificationPagination(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False
    total_unread: int = 0


class NotificationListResponse(BaseModel):
    """Cursor-paginated notification list."""

    data: list[NotificationResponse]
    pagination: NotificationPagination


# ─── Mark Read Schemas ────────────────────────────────────────────────────────


class MarkAllReadRequest(BaseModel):
    type: str | None = Field(default=None, max_length=64)


class MarkAllReadResponse(BaseModel):
    marked_count: int
    type_filter: str | None = None


# ─── Preference Schemas ──────────────────────────────────────────────────────


class PreferenceChannel(BaseModel):
    email: bool = True
    sms: bool = False
    whatsapp: bool = False
    in_app: Literal[True] = True


class NotificationPreferenceResponse(BaseModel):
    """Full preferences matrix — event_type → channel booleans."""

    preferences: dict[str, PreferenceChannel]


class PreferenceUpdate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    channel: str = Field(..., min_length=1, max_length=16)
    enabled: bool


class UpdatePreferencesRequest(BaseModel):
    preferences: list[PreferenceUpdate] = Field(..., min_length=1, max_length=50)
