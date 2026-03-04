"""Pydantic v2 schemas for EPS claims API endpoints -- VP-19 / Sprint 31-32.

These are the REST API schemas for DentalOS frontend clients.  They are
separate from the integration-level schemas in
app/integrations/eps_claims/schemas.py which define the external EPS API
contract.

All JSON fields are snake_case.  Monetary values are always in COP cents.
UUIDs are serialised as strings for JSON transport.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# -- Nested sub-schema --------------------------------------------------------


class EPSClaimProcedureItem(BaseModel):
    """A single procedure line item embedded in an EPS claim."""

    cups_code: str = Field(..., description="CUPS procedure code (6 digits)")
    description: str = Field(..., description="Human-readable procedure name")
    quantity: int = Field(default=1, ge=1, description="Number of units performed")
    unit_cost_cents: int = Field(..., gt=0, description="Unit cost in COP cents")


# -- Request schemas ----------------------------------------------------------


class EPSClaimCreate(BaseModel):
    """Request body to create a new EPS claim draft."""

    patient_id: str = Field(..., description="UUID of the patient")
    eps_code: str = Field(
        ..., min_length=1, max_length=20, description="Official EPS code (e.g. EPS010)"
    )
    eps_name: str = Field(
        ..., min_length=1, max_length=200, description="Human-readable EPS name"
    )
    claim_type: str = Field(
        ...,
        pattern="^(outpatient|emergency|hospitalization|dental)$",
        description="outpatient | emergency | hospitalization | dental",
    )
    procedures: list[EPSClaimProcedureItem] = Field(
        ..., description="Procedure line items to include in the claim"
    )
    total_amount_cents: int = Field(..., gt=0, description="Total claim value in COP cents")
    copay_amount_cents: int = Field(
        default=0, ge=0, description="Patient copay amount in COP cents"
    )


class EPSClaimUpdate(BaseModel):
    """Request body to update a draft EPS claim.

    All fields are optional.  Only claims in status=draft can be updated.
    """

    eps_code: str | None = Field(
        default=None, min_length=1, max_length=20
    )
    eps_name: str | None = Field(
        default=None, min_length=1, max_length=200
    )
    claim_type: str | None = Field(
        default=None,
        pattern="^(outpatient|emergency|hospitalization|dental)$",
    )
    procedures: list[EPSClaimProcedureItem] | None = Field(default=None)
    total_amount_cents: int | None = Field(default=None, gt=0)
    copay_amount_cents: int | None = Field(default=None, ge=0)


# -- Response schemas ---------------------------------------------------------


class EPSClaimResponse(BaseModel):
    """Full detail of an EPS claim."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    eps_code: str
    eps_name: str
    claim_type: str
    procedures: list[dict]
    total_amount_cents: int
    copay_amount_cents: int
    status: str
    external_claim_id: str | None = None
    error_message: str | None = None
    submitted_at: datetime | None = None
    acknowledged_at: datetime | None = None
    response_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class EPSClaimListResponse(BaseModel):
    """Paginated list of EPS claims."""

    items: list[EPSClaimResponse]
    total: int
    page: int
    page_size: int
