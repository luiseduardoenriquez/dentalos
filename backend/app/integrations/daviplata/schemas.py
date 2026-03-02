"""Pydantic v2 schemas for Daviplata QR payment integration.

All monetary values are in cents (integer) to avoid floating-point issues.
Field names are snake_case per DentalOS convention.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# -- Request / internal DTOs --------------------------------------------------


class DaviplataQRRequest(BaseModel):
    """Internal DTO for requesting a Daviplata QR code generation."""

    amount_cents: int = Field(..., gt=0, description="Amount in COP cents")
    reference: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="DentalOS payment reference (e.g. invoice UUID)",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=140,
        description="Payment description shown to payer (no PHI)",
    )


# -- Response DTOs -------------------------------------------------------------


class DaviplataQRResponse(BaseModel):
    """Response after successfully generating a Daviplata QR code."""

    qr_code_url: str = Field(..., description="URL to the rendered QR image")
    payment_id: str = Field(..., description="Daviplata-assigned payment identifier")
    status: str = Field(
        default="pending",
        description="Initial payment status",
    )
    expires_at: datetime = Field(
        ...,
        description="UTC timestamp when the QR code expires",
    )


class DaviplataPaymentStatus(BaseModel):
    """Current status of a Daviplata payment."""

    payment_id: str
    status: str = Field(
        ...,
        description="One of: pending, completed, expired, rejected",
    )
    amount_cents: int = Field(..., gt=0)
    reference: str
    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when payment completed (null if not yet)",
    )


# -- Webhook inbound ----------------------------------------------------------


class DaviplataWebhookPayload(BaseModel):
    """Payload received from Daviplata webhook notifications."""

    event_type: str = Field(..., description="Daviplata event type identifier")
    payment_id: str
    amount_cents: int = Field(..., gt=0)
    reference: str
    status: str = Field(
        ...,
        description="One of: pending, completed, expired, rejected",
    )
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the event",
    )
