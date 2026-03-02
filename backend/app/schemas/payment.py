"""Payment request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    """Fields required to record a payment."""

    amount: int = Field(..., gt=0, description="Amount in cents (COP), must be > 0")
    payment_method: str = Field(
        ..., pattern=r"^(cash|card|transfer|nequi|daviplata|other)$"
    )
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class PaymentResponse(BaseModel):
    """Payment detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_id: str
    patient_id: str
    amount: int
    payment_method: str
    reference_number: str | None = None
    received_by: str
    notes: str | None = None
    payment_date: datetime
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    """Paginated list of payments."""

    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
