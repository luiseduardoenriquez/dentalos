"""Unit tests for the ExpenseService class.

Tests cover:
  - create_expense: success, auto-hooks into open cash register
  - list_expenses: category and date filtering
  - get_profit_loss: revenue vs expenses calculation
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import ExpenseErrors
from app.core.exceptions import ResourceNotFoundError
from app.services.expense_service import ExpenseService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_category(**overrides) -> MagicMock:
    category = MagicMock()
    category.id = overrides.get("id", uuid.uuid4())
    category.name = overrides.get("name", "Arriendo")
    category.is_default = overrides.get("is_default", True)
    category.is_active = overrides.get("is_active", True)
    return category


def _make_expense(**overrides) -> MagicMock:
    expense = MagicMock()
    expense.id = overrides.get("id", uuid.uuid4())
    expense.category_id = overrides.get("category_id", uuid.uuid4())
    expense.amount_cents = overrides.get("amount_cents", 500000)
    expense.description = overrides.get("description", "Arriendo mensual")
    expense.expense_date = overrides.get("expense_date", date.today())
    expense.receipt_url = overrides.get("receipt_url", None)
    expense.recorded_by = overrides.get("recorded_by", uuid.uuid4())
    expense.is_active = overrides.get("is_active", True)
    expense.created_at = datetime.now(UTC)
    expense.updated_at = datetime.now(UTC)
    return expense


# ── create_expense ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateExpense:
    async def test_create_expense_calls_add_and_flush(self):
        """create_expense must persist the new Expense via add + flush."""
        service = ExpenseService()
        db = AsyncMock()

        category = _make_category()
        category_result = MagicMock()
        category_result.scalar_one_or_none.return_value = category
        db.execute = AsyncMock(return_value=category_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        expense = _make_expense()

        async def fake_refresh(obj):
            obj.id = expense.id
            obj.category_id = expense.category_id
            obj.amount_cents = expense.amount_cents
            obj.description = expense.description
            obj.expense_date = expense.expense_date
            obj.receipt_url = expense.receipt_url
            obj.recorded_by = expense.recorded_by
            obj.is_active = True
            obj.created_at = expense.created_at
            obj.updated_at = expense.updated_at

        db.refresh = fake_refresh

        # Patch cash register to return None (no open register)
        with patch(
            "app.services.expense_service.cash_register_service"
        ) as mock_cr_service:
            mock_cr_service.get_current = AsyncMock(return_value=None)

            result = await service.create_expense(
                db=db,
                category_id=str(category.id),
                amount_cents=500000,
                recorded_by=uuid.uuid4(),
                expense_date=date.today(),
            )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_create_expense_returns_dict_with_amount(self):
        """create_expense must return a dict containing the amount in COP cents."""
        service = ExpenseService()
        db = AsyncMock()

        category = _make_category()
        category_result = MagicMock()
        category_result.scalar_one_or_none.return_value = category
        db.execute = AsyncMock(return_value=category_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        expense = _make_expense(amount_cents=250000)

        async def fake_refresh(obj):
            obj.id = expense.id
            obj.category_id = expense.category_id
            obj.amount_cents = 250000
            obj.description = expense.description
            obj.expense_date = expense.expense_date
            obj.receipt_url = expense.receipt_url
            obj.recorded_by = expense.recorded_by
            obj.is_active = True
            obj.created_at = expense.created_at
            obj.updated_at = expense.updated_at

        db.refresh = fake_refresh

        with patch(
            "app.services.expense_service.cash_register_service"
        ) as mock_cr_service:
            mock_cr_service.get_current = AsyncMock(return_value=None)

            result = await service.create_expense(
                db=db,
                category_id=str(category.id),
                amount_cents=250000,
                recorded_by=uuid.uuid4(),
                expense_date=date.today(),
            )

        assert result["amount_cents"] == 250000

    async def test_create_expense_invalid_category_raises_404(self):
        """create_expense must raise ResourceNotFoundError for an unknown category."""
        service = ExpenseService()
        db = AsyncMock()

        not_found_result = MagicMock()
        not_found_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=not_found_result)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.create_expense(
                db=db,
                category_id=str(uuid.uuid4()),
                amount_cents=100000,
                recorded_by=uuid.uuid4(),
                expense_date=date.today(),
            )

        assert exc_info.value.error == ExpenseErrors.CATEGORY_NOT_FOUND


@pytest.mark.unit
class TestCreateExpenseHooksCashRegister:
    async def test_auto_records_cash_movement_when_register_open(self):
        """create_expense must call cash_register_service.record_movement when a register is open."""
        service = ExpenseService()
        db = AsyncMock()

        category = _make_category()
        category_result = MagicMock()
        category_result.scalar_one_or_none.return_value = category
        db.execute = AsyncMock(return_value=category_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        expense = _make_expense()
        open_register = {"id": str(uuid.uuid4()), "status": "open"}

        async def fake_refresh(obj):
            obj.id = expense.id
            obj.category_id = expense.category_id
            obj.amount_cents = expense.amount_cents
            obj.description = expense.description
            obj.expense_date = expense.expense_date
            obj.receipt_url = expense.receipt_url
            obj.recorded_by = expense.recorded_by
            obj.is_active = True
            obj.created_at = expense.created_at
            obj.updated_at = expense.updated_at

        db.refresh = fake_refresh

        with patch(
            "app.services.expense_service.cash_register_service"
        ) as mock_cr_service:
            mock_cr_service.get_current = AsyncMock(return_value=open_register)
            mock_cr_service.record_movement = AsyncMock(return_value={})

            await service.create_expense(
                db=db,
                category_id=str(category.id),
                amount_cents=500000,
                recorded_by=uuid.uuid4(),
                expense_date=date.today(),
            )

            mock_cr_service.record_movement.assert_called_once()

    async def test_no_cash_movement_when_no_open_register(self):
        """create_expense must not call record_movement when no register is open."""
        service = ExpenseService()
        db = AsyncMock()

        category = _make_category()
        category_result = MagicMock()
        category_result.scalar_one_or_none.return_value = category
        db.execute = AsyncMock(return_value=category_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        expense = _make_expense()

        async def fake_refresh(obj):
            obj.id = expense.id
            obj.category_id = expense.category_id
            obj.amount_cents = expense.amount_cents
            obj.description = expense.description
            obj.expense_date = expense.expense_date
            obj.receipt_url = expense.receipt_url
            obj.recorded_by = expense.recorded_by
            obj.is_active = True
            obj.created_at = expense.created_at
            obj.updated_at = expense.updated_at

        db.refresh = fake_refresh

        with patch(
            "app.services.expense_service.cash_register_service"
        ) as mock_cr_service:
            mock_cr_service.get_current = AsyncMock(return_value=None)
            mock_cr_service.record_movement = AsyncMock()

            await service.create_expense(
                db=db,
                category_id=str(category.id),
                amount_cents=500000,
                recorded_by=uuid.uuid4(),
                expense_date=date.today(),
            )

            mock_cr_service.record_movement.assert_not_called()


# ── list_expenses ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListExpensesWithFilters:
    async def test_list_expenses_returns_paginated_response(self):
        """list_expenses must return a dict with items, total, page, page_size."""
        service = ExpenseService()
        db = AsyncMock()

        expense = _make_expense()

        # First execute: COUNT query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Second execute: SELECT query
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [expense]
        rows_result = MagicMock()
        rows_result.scalars.return_value = scalars_mock

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        result = await service.list_expenses(db=db)

        assert "items" in result
        assert "total" in result
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20

    async def test_list_expenses_empty_returns_zero_total(self):
        """list_expenses must return total=0 when no expenses match."""
        service = ExpenseService()
        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        rows_result = MagicMock()
        rows_result.scalars.return_value = scalars_mock

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        result = await service.list_expenses(db=db)

        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_expenses_with_category_filter(self):
        """list_expenses with category_id must execute two queries without error."""
        service = ExpenseService()
        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [_make_expense(), _make_expense()]
        rows_result = MagicMock()
        rows_result.scalars.return_value = scalars_mock

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        result = await service.list_expenses(
            db=db,
            category_id=str(uuid.uuid4()),
            date_from=date(2026, 1, 1),
            date_to=date(2026, 3, 31),
        )

        assert result["total"] == 2
        assert len(result["items"]) == 2


# ── get_profit_loss ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetProfitLoss:
    async def test_get_profit_loss_returns_expected_keys(self):
        """get_profit_loss must return a dict with all required financial keys."""
        service = ExpenseService()
        db = AsyncMock()

        # Revenue rows (payment_method → amount)
        revenue_result = MagicMock()
        revenue_result.all.return_value = [("cash", 500000), ("card", 300000)]

        # Expense rows (category_name → amount)
        expense_result = MagicMock()
        expense_result.all.return_value = [("Arriendo", 200000), ("Servicios", 50000)]

        db.execute = AsyncMock(side_effect=[revenue_result, expense_result])

        result = await service.get_profit_loss(
            db=db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 3, 31),
        )

        assert "total_revenue_cents" in result
        assert "total_expenses_cents" in result
        assert "net_profit_cents" in result
        assert "revenue_by_method" in result
        assert "expenses_by_category" in result

    async def test_get_profit_loss_net_calculation(self):
        """get_profit_loss net_profit_cents = total_revenue - total_expenses."""
        service = ExpenseService()
        db = AsyncMock()

        revenue_result = MagicMock()
        revenue_result.all.return_value = [("cash", 800000)]

        expense_result = MagicMock()
        expense_result.all.return_value = [("Arriendo", 200000), ("Servicios", 50000)]

        db.execute = AsyncMock(side_effect=[revenue_result, expense_result])

        result = await service.get_profit_loss(
            db=db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 3, 31),
        )

        assert result["total_revenue_cents"] == 800000
        assert result["total_expenses_cents"] == 250000
        assert result["net_profit_cents"] == 550000

    async def test_get_profit_loss_no_revenue(self):
        """get_profit_loss with zero revenue must return negative net_profit."""
        service = ExpenseService()
        db = AsyncMock()

        revenue_result = MagicMock()
        revenue_result.all.return_value = []

        expense_result = MagicMock()
        expense_result.all.return_value = [("Arriendo", 100000)]

        db.execute = AsyncMock(side_effect=[revenue_result, expense_result])

        result = await service.get_profit_loss(
            db=db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result["total_revenue_cents"] == 0
        assert result["net_profit_cents"] == -100000

    async def test_get_profit_loss_includes_date_range(self):
        """get_profit_loss result must echo back the date range."""
        service = ExpenseService()
        db = AsyncMock()

        revenue_result = MagicMock()
        revenue_result.all.return_value = []
        expense_result = MagicMock()
        expense_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[revenue_result, expense_result])

        date_from = date(2026, 2, 1)
        date_to = date(2026, 2, 28)

        result = await service.get_profit_loss(db=db, date_from=date_from, date_to=date_to)

        assert result["period_start"] == date_from
        assert result["period_end"] == date_to
