"""Post-operative instruction request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostopTemplateCreate(BaseModel):
    procedure_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    instruction_content: str = Field(..., min_length=1)
    channel_preference: str = Field(
        default="all", pattern=r"^(whatsapp|email|portal|all)$"
    )
    is_default: bool = False


class PostopTemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    instruction_content: str | None = Field(default=None, min_length=1)
    channel_preference: str | None = Field(
        default=None, pattern=r"^(whatsapp|email|portal|all)$"
    )
    is_default: bool | None = None
    is_active: bool | None = None


class PostopTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    procedure_type: str
    title: str
    instruction_content: str
    channel_preference: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PostopTemplateListResponse(BaseModel):
    items: list[PostopTemplateResponse]
    total: int


class PostopSendRequest(BaseModel):
    """Request to send post-op instructions to a patient."""

    procedure_type: str = Field(..., min_length=1, max_length=50)
    template_id: str | None = None  # If None, use default for procedure_type


class PostopSendResponse(BaseModel):
    sent: bool
    channel: str
    patient_id: str
    template_id: str
