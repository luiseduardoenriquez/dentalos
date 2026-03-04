"""Pydantic v2 schemas for Telemedicine video session API.

All field names are snake_case per DentalOS convention.
Monetary values are not involved here. Timestamps are UTC datetimes.

Schema naming:
  VideoSessionCreate   — POST /appointments/{id}/video-session request body
  VideoSessionResponse — standard response for staff-facing endpoints
  VideoSessionJoinResponse — minimal response for patient portal join URL
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VideoSessionCreate(BaseModel):
    """Request body for creating a telemedicine video session.

    The video provider is automatically selected (Daily.co in production,
    mock in development). Only the appointment_id is required — all other
    parameters (room name, max participants, expiry) are derived internally.
    """

    appointment_id: uuid.UUID = Field(
        ...,
        description="UUID of the appointment this session is linked to",
    )


class VideoSessionResponse(BaseModel):
    """Full video session response for staff-facing endpoints.

    join_url_doctor and join_url_patient contain short-lived Daily.co
    meeting tokens embedded as query parameters. These should be treated
    as secrets and MUST NOT be logged.
    """

    id: uuid.UUID = Field(..., description="Video session UUID")
    appointment_id: uuid.UUID = Field(..., description="Linked appointment UUID")
    provider: str = Field(..., description="Video provider identifier (e.g. 'daily')")
    status: str = Field(
        ...,
        description="Session status: created | waiting | active | ended",
    )
    join_url_doctor: str | None = Field(
        default=None,
        description="Doctor (moderator) join URL — contains meeting token",
    )
    join_url_patient: str | None = Field(
        default=None,
        description="Patient join URL — contains meeting token",
    )
    started_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the session became active",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the session ended",
    )
    duration_seconds: int | None = Field(
        default=None,
        description="Session duration in seconds (set when status=ended)",
    )
    recording_url: str | None = Field(
        default=None,
        description="Cloud recording download URL (available after processing)",
    )
    created_at: datetime = Field(..., description="UTC timestamp when the session was created")

    model_config = {"from_attributes": True}


class VideoSessionListItem(BaseModel):
    """Single item in the paginated video session list.

    Includes joined data from appointments, patients and users (doctor)
    that the frontend needs to display the telemedicine sessions table.
    """

    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_name: str = Field(..., description="Patient full name (first + last)")
    doctor_name: str = Field(..., description="Doctor display name from users.name")
    scheduled_at: datetime | None = Field(
        default=None,
        description="Appointment start_time (used as scheduled_at in the UI)",
    )
    status: str = Field(..., description="Session status: created | waiting | active | ended")
    duration_minutes: int | None = Field(
        default=None,
        description="Session duration in minutes (derived from duration_seconds)",
    )
    created_at: datetime
    join_url_doctor: str | None = None

    model_config = {"from_attributes": True}


class VideoSessionListResponse(BaseModel):
    """Paginated list of video sessions for the telemedicine dashboard."""

    items: list[VideoSessionListItem]
    total: int
    page: int
    page_size: int


class VideoSessionJoinResponse(BaseModel):
    """Minimal response returned to the patient portal for joining a session.

    Contains only the patient-specific join URL (never the doctor URL) and
    the session ID for reference.
    """

    join_url: str = Field(
        ...,
        description="Patient join URL including Daily.co meeting token",
    )
    session_id: uuid.UUID = Field(
        ...,
        description="Video session UUID for client-side reference",
    )
