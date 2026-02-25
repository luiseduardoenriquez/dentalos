"""Consent request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsentTemplateCreate(BaseModel):
    """Fields to create a tenant consent template."""

    name: str = Field(..., min_length=1, max_length=300)
    category: str
    description: str | None = None
    content: str = Field(..., min_length=1)
    signature_positions: list[dict] | None = None


class ConsentTemplateResponse(BaseModel):
    """Consent template detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    description: str | None = None
    content: str
    signature_positions: dict | None = None
    version: int
    is_active: bool
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime


class ConsentTemplateListResponse(BaseModel):
    """List of consent templates."""

    items: list[ConsentTemplateResponse]
    total: int


class ConsentCreate(BaseModel):
    """Fields required to create a new consent document."""

    template_id: str | None = None
    title: str = Field(..., min_length=1, max_length=300)
    content_rendered: str | None = None


class SignConsentRequest(BaseModel):
    """Request body for signing a consent."""

    signature_image: str = Field(..., min_length=1)
    signer_type: str = Field(default="patient")


class VoidConsentRequest(BaseModel):
    """Request body for voiding a consent."""

    reason: str = Field(..., min_length=20, max_length=1000)


class ConsentResponse(BaseModel):
    """Full consent detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    template_id: str | None = None
    title: str
    content_rendered: str
    content_hash: str | None = None
    status: str
    signed_at: datetime | None = None
    locked_at: datetime | None = None
    voided_at: datetime | None = None
    voided_by: str | None = None
    void_reason: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConsentListResponse(BaseModel):
    """Paginated list of consents."""

    items: list[ConsentResponse]
    total: int
    page: int
    page_size: int
