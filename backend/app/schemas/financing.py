"""Pydantic v2 schemas for patient financing -- VP-11 / Sprint 29-30.

All monetary values are in cents (integer) to avoid floating-point issues.
Field names are snake_case per DentalOS convention.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Valid financing providers supported by DentalOS
_VALID_PROVIDERS = {"addi", "sistecredito", "mercadopago"}


# -- Request schemas ----------------------------------------------------------


class FinancingRequestCreate(BaseModel):
    """Request body to create a new financing application for an invoice."""

    provider: str = Field(
        ...,
        description="Financing provider: addi | sistecredito | mercadopago",
    )
    installments: int = Field(
        ...,
        ge=1,
        le=60,
        description="Number of monthly installments requested",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Ensure provider is one of the supported values."""
        if v not in _VALID_PROVIDERS:
            raise ValueError(
                f"Proveedor inválido. Opciones válidas: {', '.join(sorted(_VALID_PROVIDERS))}"
            )
        return v


# -- Response schemas ---------------------------------------------------------


class FinancingApplicationResponse(BaseModel):
    """Full detail of a financing application."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    invoice_id: str | None = None
    provider: str
    status: str
    amount_cents: int
    installments: int
    interest_rate_bps: int | None = None
    provider_reference: str | None = None
    requested_at: datetime
    approved_at: datetime | None = None
    disbursed_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FinancingEligibilityResponse(BaseModel):
    """Response for a financing eligibility check."""

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
        description="Valid installment counts offered by the provider",
    )
    reason: str | None = Field(
        default=None,
        description="Human-readable reason when not eligible",
    )


class FinancingApplicationListResponse(BaseModel):
    """Paginated list of financing applications."""

    items: list[FinancingApplicationResponse]
    total: int
    page: int
    page_size: int


class FinancingReportResponse(BaseModel):
    """Aggregate financing report for clinic owners."""

    total_applications: int = Field(
        ...,
        description="Total number of financing applications",
    )
    total_amount_cents: int = Field(
        ...,
        description="Sum of all application amounts in COP cents",
    )
    by_provider: dict[str, int] = Field(
        ...,
        description="Application count grouped by provider",
    )
    by_status: dict[str, int] = Field(
        ...,
        description="Application count grouped by status",
    )
