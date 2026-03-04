"""Expense service — record and query clinic operating expenses.

Security invariants:
  - PHI is NEVER logged.
  - All monetary values in COP cents.
  - Soft-delete only — financial records are never hard-deleted.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ExpenseErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.expense import Expense, ExpenseCategory
from app.models.tenant.payment import Payment

logger = logging.getLogger("dentalos.expenses")


class ExpenseService:
    """Stateless expense service."""

    # ── Expenses ─────────────────────────────────────────────────────────────

    async def create_expense(
        self,
        *,
        db: AsyncSession,
        category_id: str,
        amount_cents: int,
        recorded_by: uuid.UUID,
        expense_date: date,
        description: str | None = None,
        receipt_url: str | None = None,
    ) -> dict[str, Any]:
        """Create an expense and auto-record it in the open cash register, if any."""
        # Validate category exists and is active
        category = await self._get_category(db, category_id)

        expense = Expense(
            category_id=uuid.UUID(category_id),
            amount_cents=amount_cents,
            description=description,
            expense_date=expense_date,
            receipt_url=receipt_url,
            recorded_by=recorded_by,
            is_active=True,
        )
        db.add(expense)
        await db.flush()
        await db.refresh(expense)

        # Auto-register as a cash movement if a register is currently open
        from app.services.cash_register_service import cash_register_service

        current_register = await cash_register_service.get_current(db=db)
        if current_register:
            await cash_register_service.record_movement(
                db=db,
                register_id=uuid.UUID(current_register["id"]),
                type="expense",
                amount_cents=amount_cents,
                reference_id=expense.id,
                reference_type="expense",
                description=description or category.name,
                recorded_by=recorded_by,
            )

        logger.info("Expense created: id=%s category=%s", str(expense.id)[:8], str(expense.category_id)[:8])
        return self._expense_to_dict(expense)

    async def list_expenses(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Return paginated expenses with optional filters. Excludes soft-deleted records."""
        offset = (page - 1) * page_size
        conditions = [Expense.is_active.is_(True)]

        if category_id:
            conditions.append(Expense.category_id == uuid.UUID(category_id))
        if date_from:
            conditions.append(Expense.expense_date >= date_from)
        if date_to:
            conditions.append(Expense.expense_date <= date_to)

        total = (
            await db.execute(
                select(func.count(Expense.id)).where(and_(*conditions))
            )
        ).scalar_one()

        result = await db.execute(
            select(Expense)
            .where(and_(*conditions))
            .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        expenses = result.scalars().all()

        return {
            "items": [self._expense_to_dict(e) for e in expenses],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Categories ────────────────────────────────────────────────────────────

    async def list_categories(self, *, db: AsyncSession) -> list[dict[str, Any]]:
        """Return all active expense categories, defaults first."""
        result = await db.execute(
            select(ExpenseCategory)
            .where(ExpenseCategory.is_active.is_(True))
            .order_by(ExpenseCategory.is_default.desc(), ExpenseCategory.name)
        )
        return [self._category_to_dict(c) for c in result.scalars().all()]

    # ── Profit / Loss ─────────────────────────────────────────────────────────

    async def get_profit_loss(
        self,
        *,
        db: AsyncSession,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """Compute revenue (from payments) vs expenses for a date range.

        Revenue is grouped by payment_method; expenses by category name.
        """
        # ── Revenue from payments ────────────────────────────────────────────
        revenue_rows = (
            await db.execute(
                select(
                    Payment.payment_method,
                    func.count(Payment.id),
                    func.coalesce(func.sum(Payment.amount), 0),
                )
                .where(
                    func.date(Payment.payment_date) >= date_from,
                    func.date(Payment.payment_date) <= date_to,
                )
                .group_by(Payment.payment_method)
            )
        ).all()

        revenue_by_payment_method = [
            {"method": row[0] or "other", "count": row[1], "amount_cents": row[2]}
            for row in revenue_rows
        ]
        total_revenue = sum(r["amount_cents"] for r in revenue_by_payment_method)

        # ── Expenses by category ─────────────────────────────────────────────
        expense_rows = (
            await db.execute(
                select(
                    ExpenseCategory.id,
                    ExpenseCategory.name,
                    func.count(Expense.id),
                    func.coalesce(func.sum(Expense.amount_cents), 0),
                )
                .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
                .where(
                    Expense.is_active.is_(True),
                    Expense.expense_date >= date_from,
                    Expense.expense_date <= date_to,
                )
                .group_by(ExpenseCategory.id, ExpenseCategory.name)
            )
        ).all()

        expenses_by_category = [
            {
                "category_id": str(row[0]),
                "category_name": row[1],
                "transaction_count": row[2],
                "amount_cents": row[3],
            }
            for row in expense_rows
        ]
        total_expenses = sum(e["amount_cents"] for e in expenses_by_category)

        net_profit = total_revenue - total_expenses
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        return {
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "total_revenue_cents": total_revenue,
            "total_expenses_cents": total_expenses,
            "net_profit_cents": net_profit,
            "profit_margin_percent": round(profit_margin, 2),
            "revenue_by_payment_method": revenue_by_payment_method,
            "expenses_by_category": expenses_by_category,
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get_category(self, db: AsyncSession, category_id: str) -> ExpenseCategory:
        result = await db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.id == uuid.UUID(category_id),
                ExpenseCategory.is_active.is_(True),
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise ResourceNotFoundError(
                error=ExpenseErrors.CATEGORY_NOT_FOUND,
                resource_name="ExpenseCategory",
            )
        return category

    def _expense_to_dict(self, expense: Expense) -> dict[str, Any]:
        return {
            "id": str(expense.id),
            "category_id": str(expense.category_id),
            "amount_cents": expense.amount_cents,
            "description": expense.description,
            "expense_date": expense.expense_date,
            "receipt_url": expense.receipt_url,
            "recorded_by": str(expense.recorded_by),
            "is_active": expense.is_active,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
        }

    def _category_to_dict(self, category: ExpenseCategory) -> dict[str, Any]:
        return {
            "id": str(category.id),
            "name": category.name,
            "is_default": category.is_default,
            "is_active": category.is_active,
        }


expense_service = ExpenseService()
