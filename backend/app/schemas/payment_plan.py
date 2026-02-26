"""Payment plan request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentPlanCreate(BaseModel):
    """Fields required to create a payment plan."""

    num_installments: int = Field(..., ge=2, le=24)
    first_due_date: date


class InstallmentResponse(BaseModel):
    """Single installment detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    installment_number: int
    amount: int
    due_date: date
    status: str
    paid_at: datetime | None = None
    payment_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PaymentPlanResponse(BaseModel):
    """Payment plan detail with installments."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_id: str
    patient_id: str
    total_amount: int
    num_installments: int
    status: str
    created_by: str
    is_active: bool
    installments: list[InstallmentResponse] = []
    created_at: datetime
    updated_at: datetime
