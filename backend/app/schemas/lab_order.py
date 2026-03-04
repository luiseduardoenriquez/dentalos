"""Pydantic v2 schemas for dental lab order management -- VP-22 / Sprint 31-32.

All monetary values are in cents (integer) to avoid floating-point issues.
Field names are snake_case per DentalOS convention.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# -- DentalLab schemas --------------------------------------------------------


class DentalLabCreate(BaseModel):
    """Request body to create a new dental lab entry."""

    name: str = Field(..., max_length=200, description="Lab name")
    contact_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None)


class DentalLabUpdate(BaseModel):
    """Request body to update an existing dental lab entry.

    All fields are optional — only provided fields will be updated.
    """

    name: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class DentalLabResponse(BaseModel):
    """Full representation of a dental lab."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# -- LabOrder schemas ----------------------------------------------------------


class LabOrderCreate(BaseModel):
    """Request body to create a new lab work order."""

    patient_id: str = Field(..., description="UUID of the patient")
    treatment_plan_id: str | None = Field(
        default=None,
        description="UUID of the linked treatment plan (optional)",
    )
    lab_id: str | None = Field(
        default=None,
        description="UUID of the dental lab (optional — can be assigned later)",
    )
    order_type: str = Field(
        ...,
        description="Type: crown | bridge | denture | implant_abutment | retainer | other",
    )
    specifications: dict = Field(
        default_factory=dict,
        description="Free-form JSONB specifications for the lab (shade, material, tooth numbers, etc.)",
    )
    due_date: date | None = Field(
        default=None,
        description="Expected delivery date from the lab",
    )
    cost_cents: int | None = Field(
        default=None,
        ge=0,
        description="Agreed lab cost in COP cents",
    )
    notes: str | None = Field(default=None)


class LabOrderUpdate(BaseModel):
    """Request body to update an existing lab order.

    Only fields related to order details are updatable here.
    Use the /advance endpoint for status transitions.
    """

    lab_id: str | None = Field(default=None)
    order_type: str | None = Field(default=None)
    specifications: dict | None = Field(default=None)
    due_date: date | None = Field(default=None)
    cost_cents: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None)


class LabOrderResponse(BaseModel):
    """Full representation of a lab work order."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    treatment_plan_id: str | None = None
    lab_id: str | None = None
    order_type: str
    specifications: dict
    status: str
    due_date: date | None = None
    sent_at: datetime | None = None
    ready_at: datetime | None = None
    delivered_at: datetime | None = None
    cost_cents: int | None = None
    notes: str | None = None
    created_by: str | None = None
    is_active: bool
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LabOrderListResponse(BaseModel):
    """Paginated list of lab work orders."""

    items: list[LabOrderResponse]
    total: int
    page: int
    page_size: int


class LabOrderStatusUpdate(BaseModel):
    """Request body for the /advance status transition endpoint."""

    status: str = Field(
        ...,
        description=(
            "Target status. Valid transitions: "
            "pending→sent_to_lab, sent_to_lab→in_progress, "
            "in_progress→ready, ready→delivered. "
            "Any non-delivered state may also transition to cancelled."
        ),
    )
