"""Intake form template and submission schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class IntakeFieldDefinition(BaseModel):
    """A single field in an intake form template."""
    name: str
    label: str
    type: str = Field(pattern=r"^(text|select|date|checkbox|file|signature|textarea|email|phone|number)$")
    required: bool = False
    options: list[str] | None = None
    placeholder: str | None = None


class IntakeTemplateCreate(BaseModel):
    """Create a new intake form template."""
    name: str = Field(min_length=1, max_length=200)
    fields: list[IntakeFieldDefinition]
    consent_template_ids: list[str] | None = None
    is_default: bool = False


class IntakeTemplateUpdate(BaseModel):
    """Update an existing intake form template."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    fields: list[IntakeFieldDefinition] | None = None
    consent_template_ids: list[str] | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class IntakeTemplateResponse(BaseModel):
    """Intake form template details."""
    id: str
    name: str
    fields: list[dict]
    consent_template_ids: list[str] | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class IntakeSubmissionCreate(BaseModel):
    """Submit an intake form (public or portal)."""
    template_id: str
    appointment_id: str | None = None
    data: dict


class IntakeSubmissionResponse(BaseModel):
    """Intake submission details."""
    id: str
    template_id: str
    patient_id: str | None = None
    appointment_id: str | None = None
    data: dict
    status: str
    submitted_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
