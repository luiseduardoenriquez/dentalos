"""Cash register request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CashRegisterOpenRequest(BaseModel):
    """Body for opening a new cash register session."""

    name: str = Field(..., min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    opening_balance_cents: int = Field(default=0, ge=0)


class CashRegisterCloseRequest(BaseModel):
    """Body for closing the current open register."""

    closing_balance_cents: int = Field(..., ge=0)
    notes: str | None = None


class CashMovementResponse(BaseModel):
    """Response schema for a single cash movement."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    register_id: str
    type: str
    amount_cents: int
    payment_method: str | None = None
    reference_id: str | None = None
    reference_type: str | None = None
    description: str | None = None
    recorded_by: str
    created_at: datetime


class CashRegisterResponse(BaseModel):
    """Response schema for a cash register session (without movements)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    location: str | None = None
    status: str
    opened_by: str | None = None
    opened_at: datetime | None = None
    opening_balance_cents: int
    closing_balance_cents: int | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CashRegisterDetailResponse(CashRegisterResponse):
    """Response schema for a cash register session with movements and computed totals."""

    movements: list[CashMovementResponse] = []
    total_income_cents: int = 0
    total_expense_cents: int = 0
    net_balance_cents: int = 0


class CashRegisterHistoryResponse(BaseModel):
    """Paginated list of closed cash register sessions."""

    items: list[CashRegisterResponse]
    total: int
    page: int
    page_size: int
