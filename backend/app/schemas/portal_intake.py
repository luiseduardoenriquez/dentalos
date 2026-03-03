"""Pydantic schemas for portal intake and membership actions — PP-13, VP-10."""

from typing import Any

from pydantic import BaseModel


class PortalIntakeSubmission(BaseModel):
    """Patient submits pre-appointment intake form."""

    form_data: dict[str, Any]  # JSON answers to intake questions
    appointment_id: str | None = None  # Optional link to upcoming appointment


class PortalCancellationRequest(BaseModel):
    """Patient requests membership cancellation."""

    reason: str | None = None
