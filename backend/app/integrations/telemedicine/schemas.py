"""Pydantic v2 schemas for Telemedicine video session integration.

These are internal DTOs shared between the abstract base, production service
(Daily.co), and mock service. They are NOT the API request/response schemas
(those live in app.schemas.video_session).

All field names are snake_case per DentalOS convention.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RoomResult(BaseModel):
    """Result returned after successfully creating a Daily.co room."""

    room_name: str = Field(..., description="Unique room name used as the Daily.co room identifier")
    room_url: str = Field(..., description="Base URL for the room (without join token)")
    provider_session_id: str = Field(
        ..., description="Provider-assigned identifier for the session (Daily.co room id)"
    )
    created_at: datetime = Field(..., description="UTC timestamp when the room was created")


class JoinTokenResult(BaseModel):
    """Result returned after generating a meeting join token."""

    token: str = Field(..., description="Short-lived Daily.co meeting token")
    join_url: str = Field(
        ..., description="Full join URL including token query parameter"
    )
