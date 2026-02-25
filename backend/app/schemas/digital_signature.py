"""Digital signature request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CanvasMetadata(BaseModel):
    """Metadata about the signing canvas."""

    width: int = Field(default=400, ge=100, le=2000)
    height: int = Field(default=200, ge=50, le=1000)
    device_pixel_ratio: float = Field(default=1.0, ge=0.5, le=4.0)


class SignatureCreate(BaseModel):
    """Fields required to create a digital signature."""

    document_type: str
    document_id: str
    signer_type: str = Field(default="patient")
    signature_image: str = Field(..., min_length=1)
    canvas_metadata: CanvasMetadata | None = None


class SignatureResponse(BaseModel):
    """Full signature detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_type: str
    document_id: str
    signer_type: str
    signer_id: str
    signature_hash: str
    image_hash: str
    signed_at: datetime
    ip_address: str | None = None
    created_at: datetime
    updated_at: datetime


class SignatureVerifyResponse(BaseModel):
    """Result of verifying a signature."""

    model_config = ConfigDict(from_attributes=True)

    signature_id: str
    is_valid: bool
    computed_hash: str
    stored_hash: str
    verified_at: datetime
