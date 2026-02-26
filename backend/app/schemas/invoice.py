"""Invoice request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InvoiceItemCreate(BaseModel):
    """Fields for an invoice line item."""

    description: str = Field(..., min_length=1, max_length=500)
    cups_code: str | None = None
    service_id: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: int = Field(..., ge=0)
    discount: int = Field(default=0, ge=0)
    tooth_number: int | None = None


class InvoiceCreate(BaseModel):
    """Fields required to create a new invoice."""

    patient_id: str | None = None  # Override from path param; optional here
    quotation_id: str | None = None
    items: list[InvoiceItemCreate] | None = None
    due_date: date | None = None
    notes: str | None = None


class InvoiceItemResponse(BaseModel):
    """Single invoice item detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_id: str
    service_id: str | None = None
    description: str
    cups_code: str | None = None
    quantity: int
    unit_price: int
    discount: int
    line_total: int
    sort_order: int
    tooth_number: int | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceResponse(BaseModel):
    """Full invoice detail with items."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str
    patient_id: str
    created_by: str
    quotation_id: str | None = None
    subtotal: int
    tax: int
    total: int
    amount_paid: int
    balance: int
    status: str
    due_date: date | None = None
    paid_at: datetime | None = None
    notes: str | None = None
    items: list[InvoiceItemResponse] = []
    days_until_due: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""

    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
