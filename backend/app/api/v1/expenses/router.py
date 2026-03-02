"""Expenses API routes — GAP-03.

Endpoint map:
  POST /expenses                   — Record a new expense
  GET  /expenses                   — List expenses with optional filters
  GET  /expenses/categories        — List active expense categories
  GET  /expenses/profit-loss       — Profit & loss summary for a date range
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.expense import (
    ExpenseCategoryResponse,
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ProfitLossResponse,
)
from app.services.expense_service import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    body: ExpenseCreate,
    current_user: AuthenticatedUser = Depends(require_permission("expenses:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ExpenseResponse:
    """Record a new clinic expense.

    If a cash register is currently open, a matching cash movement is automatically
    created so the register balance stays accurate.
    """
    result = await expense_service.create_expense(
        db=db,
        category_id=body.category_id,
        amount_cents=body.amount_cents,
        description=body.description,
        expense_date=body.expense_date,
        receipt_url=body.receipt_url,
        recorded_by=current_user.user_id,
    )
    return ExpenseResponse(**result)


@router.get("", response_model=ExpenseListResponse)
async def list_expenses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("expenses:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ExpenseListResponse:
    """List expenses with optional date range and category filters."""
    result = await expense_service.list_expenses(
        db=db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ExpenseListResponse(**result)


@router.get("/categories", response_model=list[ExpenseCategoryResponse])
async def list_expense_categories(
    current_user: AuthenticatedUser = Depends(require_permission("expenses:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[ExpenseCategoryResponse]:
    """List all active expense categories, defaults shown first."""
    results = await expense_service.list_categories(db=db)
    return [ExpenseCategoryResponse(**r) for r in results]


@router.get("/profit-loss", response_model=ProfitLossResponse)
async def get_profit_loss(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: AuthenticatedUser = Depends(require_permission("expenses:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProfitLossResponse:
    """Return a profit and loss summary for a date range.

    Revenue is sourced from recorded payments; expenses from expense records.
    Both are aggregated and returned alongside the net profit figure.
    """
    result = await expense_service.get_profit_loss(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )
    return ProfitLossResponse(**result)
