"""Convenio (corporate agreement) schemas — GAP-04."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ConvenioCreate(BaseModel):
    """Create a new corporate agreement."""

    company_name: str = Field(min_length=1, max_length=200)
    contact_info: dict | None = None
    discount_rules: dict
    valid_from: date
    valid_until: date | None = None


class ConvenioUpdate(BaseModel):
    """Update an existing corporate agreement."""

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_info: dict | None = None
    discount_rules: dict | None = None
    valid_from: date | None = None
    valid_until: date | None = None


class ConvenioResponse(BaseModel):
    """Corporate agreement details."""

    id: uuid.UUID
    company_name: str
    contact_info: dict | None = None
    discount_rules: dict | None = None
    valid_from: date
    valid_until: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LinkPatientRequest(BaseModel):
    """Link a patient to a corporate agreement."""

    patient_id: str
    employee_id: str | None = None


class ConvenioListResponse(BaseModel):
    """Paginated list of corporate agreements."""

    items: list[ConvenioResponse]
    total: int
    page: int
    page_size: int
