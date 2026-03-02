"""Expense request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    """Body for creating a new expense record."""

    category_id: str
    amount_cents: int = Field(..., gt=0)
    description: str | None = None
    expense_date: date
    receipt_url: str | None = Field(default=None, max_length=500)


class ExpenseCategoryResponse(BaseModel):
    """Response schema for an expense category."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_default: bool
    is_active: bool


class ExpenseResponse(BaseModel):
    """Response schema for a single expense record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    amount_cents: int
    description: str | None = None
    expense_date: date
    receipt_url: str | None = None
    recorded_by: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    """Paginated list of expense records."""

    items: list[ExpenseResponse]
    total: int
    page: int
    page_size: int


class ProfitLossResponse(BaseModel):
    """Profit and loss summary for a given date range."""

    period_start: date
    period_end: date
    total_revenue_cents: int
    total_expenses_cents: int
    net_profit_cents: int
    revenue_by_method: dict[str, int]
    expenses_by_category: dict[str, int]
