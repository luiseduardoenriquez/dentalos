"""Tooth photo request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ToothPhotoResponse(BaseModel):
    """Full tooth photo detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    tooth_number: int
    s3_key: str
    thumbnail_s3_key: str | None = None
    file_size_bytes: int
    mime_type: str
    uploaded_by: str
    photo_url: str | None = None
    thumbnail_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ToothPhotoListResponse(BaseModel):
    """List of tooth photos."""

    items: list[ToothPhotoResponse]
    total: int
