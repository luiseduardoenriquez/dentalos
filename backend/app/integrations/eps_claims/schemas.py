"""Pydantic schemas for EPS claims integration -- VP-19 / Sprint 31-32.

These schemas represent the data contract with the external EPS claims API.
They are distinct from the app-level Pydantic schemas in app/schemas/eps_claim.py,
which represent the REST API contract with DentalOS frontend clients.

Security:
  - patient_document_number is PHI — NEVER logged at any level.
  - All monetary values in COP cents.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EPSClaimProcedure(BaseModel):
    """A single procedure line item within an EPS claim submission."""

    cups_code: str = Field(..., description="CUPS procedure code (6 digits)")
    description: str = Field(..., description="Human-readable procedure name")
    quantity: int = Field(default=1, ge=1, description="Number of units performed")
    unit_cost_cents: int = Field(
        ..., gt=0, description="Unit cost in COP cents"
    )


class EPSClaimSubmitRequest(BaseModel):
    """Payload sent to the EPS API when submitting a new claim.

    Security: patient_document_number is PHI — never log this field.
    """

    eps_code: str = Field(..., description="Official EPS code (e.g. EPS010)")
    # PHI — never logged
    patient_document_type: str = Field(
        ..., description="Colombian document type: CC, TI, CE, PA, RC, MS"
    )
    patient_document_number: str = Field(
        ..., description="Patient document number. PHI — never log this."
    )
    claim_type: str = Field(
        ..., description="outpatient | emergency | hospitalization | dental"
    )
    procedures: list[EPSClaimProcedure] = Field(
        ..., description="Procedure line items included in the claim"
    )
    total_amount_cents: int = Field(
        ..., gt=0, description="Total claim value in COP cents"
    )
    copay_amount_cents: int = Field(
        default=0, ge=0, description="Patient copay amount in COP cents"
    )


class EPSClaimSubmitResponse(BaseModel):
    """Response received from the EPS API after submitting a claim."""

    external_claim_id: str = Field(
        ..., description="Unique identifier assigned by the EPS system"
    )
    status: str = Field(
        ..., description="Initial claim status: submitted | acknowledged"
    )
    message: str | None = Field(
        default=None, description="Optional human-readable message from the EPS API"
    )


class EPSClaimStatusResponse(BaseModel):
    """Current status of a claim as reported by the EPS API."""

    external_claim_id: str = Field(..., description="EPS-assigned claim identifier")
    status: str = Field(
        ..., description="Current status: submitted | acknowledged | paid | rejected"
    )
    paid_amount_cents: int | None = Field(
        default=None, description="Amount paid by EPS in COP cents (set when paid)"
    )
    error_message: str | None = Field(
        default=None, description="Error detail from EPS when status=rejected"
    )
