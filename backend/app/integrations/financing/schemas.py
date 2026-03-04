"""Pydantic v2 schemas for financing provider integrations.

All monetary values are in cents (integer) to avoid floating-point issues.
Field names are snake_case per DentalOS convention.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# -- Result DTOs --------------------------------------------------------------


class EligibilityResult(BaseModel):
    """Result of a financing eligibility check from a provider."""

    eligible: bool = Field(..., description="Whether the patient is eligible for financing")
    max_amount_cents: int | None = Field(
        default=None,
        description="Maximum financeable amount in COP cents",
    )
    min_amount_cents: int | None = Field(
        default=None,
        description="Minimum financeable amount in COP cents",
    )
    available_installments: list[int] = Field(
        default_factory=list,
        description="List of valid installment counts (e.g. [3, 6, 12, 24])",
    )
    reason: str | None = Field(
        default=None,
        description="Human-readable reason when not eligible (no PHI)",
    )


class ApplicationResult(BaseModel):
    """Result of a financing application submission."""

    provider_reference: str = Field(
        ...,
        description="Provider-assigned application identifier",
    )
    status: str = Field(
        ...,
        description="Initial application status (e.g. pending, approved, rejected)",
    )
    redirect_url: str | None = Field(
        default=None,
        description="URL to redirect the patient for provider onboarding flow",
    )


class ApplicationStatusResult(BaseModel):
    """Current status of a financing application from the provider."""

    provider_reference: str = Field(
        ...,
        description="Provider-assigned application identifier",
    )
    status: str = Field(
        ...,
        description="Current application status",
    )
    approved_amount_cents: int | None = Field(
        default=None,
        description="Approved financing amount in COP cents (null until approved)",
    )
    disbursed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when funds were disbursed (null until disbursed)",
    )
