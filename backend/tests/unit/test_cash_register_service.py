"""Unit tests for the CashRegisterService class.

Tests cover:
  - open_register: success, already_open (409)
  - close_register: success, not found (404)
  - record_movement: creates movement record
  - get_current: returns open register with totals, returns None when none open
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.error_codes import CashRegisterErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.cash_register_service import CashRegisterService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_register(**overrides) -> MagicMock:
    register = MagicMock()
    register.id = overrides.get("id", uuid.uuid4())
    register.name = overrides.get("name", "Caja Principal")
    register.location = overrides.get("location", "Consultorio 1")
    register.status = overrides.get("status", "open")
    register.opened_by = overrides.get("opened_by", uuid.uuid4())
    register.opened_at = overrides.get("opened_at", datetime.now(UTC))
    register.opening_balance_cents = overrides.get("opening_balance_cents", 100000)
    register.closing_balance_cents = overrides.get("closing_balance_cents", None)
    register.closed_by = overrides.get("closed_by", None)
    register.closed_at = overrides.get("closed_at", None)
    register.movements = overrides.get("movements", [])
    register.created_at = datetime.now(UTC)
    register.updated_at = datetime.now(UTC)
    return register


def _make_movement(**overrides) -> MagicMock:
    movement = MagicMock()
    movement.id = overrides.get("id", uuid.uuid4())
    movement.register_id = overrides.get("register_id", uuid.uuid4())
    movement.type = overrides.get("type", "income")
    movement.amount_cents = overrides.get("amount_cents", 50000)
    movement.payment_method = overrides.get("payment_method", "cash")
    movement.reference_id = overrides.get("reference_id", None)
    movement.reference_type = overrides.get("reference_type", None)
    movement.description = overrides.get("description", "Pago consulta")
    movement.recorded_by = overrides.get("recorded_by", uuid.uuid4())
    movement.created_at = datetime.now(UTC)
    return movement


# ── open_register ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestOpenRegister:
    async def test_open_register_success(self):
        """open_register must call db.add and db.flush when no register is open."""
        service = CashRegisterService()
        db = AsyncMock()

        # No existing open register
        no_open_result = MagicMock()
        no_open_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_open_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        register = _make_register()

        async def fake_refresh(obj):
            obj.id = register.id
            obj.name = register.name
            obj.location = register.location
            obj.status = register.status
            obj.opened_by = register.opened_by
            obj.opened_at = register.opened_at
            obj.opening_balance_cents = register.opening_balance_cents
            obj.closing_balance_cents = None
            obj.closed_by = None
            obj.closed_at = None
            obj.created_at = register.created_at
            obj.updated_at = register.updated_at

        db.refresh = fake_refresh

        result = await service.open_register(
            db=db,
            user_id=uuid.uuid4(),
            name="Caja Principal",
            location="Consultorio 1",
            opening_balance_cents=100000,
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_open_register_returns_dict(self):
        """open_register must return a dict with register details."""
        service = CashRegisterService()
        db = AsyncMock()

        no_open_result = MagicMock()
        no_open_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_open_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        register = _make_register(opening_balance_cents=200000)

        async def fake_refresh(obj):
            obj.id = register.id
            obj.name = register.name
            obj.location = register.location
            obj.status = "open"
            obj.opened_by = register.opened_by
            obj.opened_at = register.opened_at
            obj.opening_balance_cents = 200000
            obj.closing_balance_cents = None
            obj.closed_by = None
            obj.closed_at = None
            obj.created_at = register.created_at
            obj.updated_at = register.updated_at

        db.refresh = fake_refresh

        result = await service.open_register(
            db=db,
            user_id=uuid.uuid4(),
            name="Caja Secundaria",
            location=None,
            opening_balance_cents=200000,
        )

        assert "id" in result
        assert result["status"] == "open"

    async def test_open_register_already_open_raises_409(self):
        """open_register must raise ALREADY_OPEN (409) when a register is already open."""
        service = CashRegisterService()
        db = AsyncMock()

        existing_id = uuid.uuid4()
        already_open_result = MagicMock()
        already_open_result.scalar_one_or_none.return_value = existing_id
        db.execute = AsyncMock(return_value=already_open_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.open_register(
                db=db,
                user_id=uuid.uuid4(),
                name="Nueva Caja",
                location=None,
                opening_balance_cents=50000,
            )

        assert exc_info.value.error == CashRegisterErrors.ALREADY_OPEN
        assert exc_info.value.status_code == 409

    async def test_open_register_already_open_does_not_add(self):
        """open_register must not call db.add when another register is already open."""
        service = CashRegisterService()
        db = AsyncMock()

        already_open_result = MagicMock()
        already_open_result.scalar_one_or_none.return_value = uuid.uuid4()
        db.execute = AsyncMock(return_value=already_open_result)
        db.add = MagicMock()

        with pytest.raises(DentalOSError):
            await service.open_register(
                db=db,
                user_id=uuid.uuid4(),
                name="Caja X",
                location=None,
                opening_balance_cents=0,
            )

        db.add.assert_not_called()


# ── close_register ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCloseRegister:
    async def test_close_register_sets_status_closed(self):
        """close_register must update status to 'closed' on the register."""
        service = CashRegisterService()
        db = AsyncMock()

        register = _make_register(status="open")
        register_result = MagicMock()
        register_result.scalar_one_or_none.return_value = register
        db.execute = AsyncMock(return_value=register_result)
        db.flush = AsyncMock()

        async def fake_refresh(obj):
            obj.status = "closed"
            obj.closed_at = datetime.now(UTC)
            obj.closing_balance_cents = 150000

        db.refresh = fake_refresh

        user_id = uuid.uuid4()
        await service.close_register(
            db=db,
            user_id=user_id,
            register_id=register.id,
            closing_balance_cents=150000,
        )

        assert register.status == "closed"
        assert register.closing_balance_cents == 150000

    async def test_close_register_not_found_raises_404(self):
        """close_register must raise ResourceNotFoundError when register not found or not open."""
        service = CashRegisterService()
        db = AsyncMock()

        not_found_result = MagicMock()
        not_found_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=not_found_result)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.close_register(
                db=db,
                user_id=uuid.uuid4(),
                register_id=uuid.uuid4(),
                closing_balance_cents=0,
            )

        assert exc_info.value.error == CashRegisterErrors.NOT_FOUND

    async def test_close_register_flushes(self):
        """close_register must call db.flush() after updating the register."""
        service = CashRegisterService()
        db = AsyncMock()

        register = _make_register(status="open")
        register_result = MagicMock()
        register_result.scalar_one_or_none.return_value = register
        db.execute = AsyncMock(return_value=register_result)
        db.flush = AsyncMock()

        async def fake_refresh(obj):
            pass

        db.refresh = fake_refresh

        await service.close_register(
            db=db,
            user_id=uuid.uuid4(),
            register_id=register.id,
            closing_balance_cents=100000,
        )

        db.flush.assert_called_once()


# ── record_movement ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRecordMovement:
    async def test_record_movement_calls_add_and_flush(self):
        """record_movement must add a new CashMovement and flush the session."""
        service = CashRegisterService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        movement = _make_movement()

        async def fake_refresh(obj):
            obj.id = movement.id
            obj.register_id = movement.register_id
            obj.type = movement.type
            obj.amount_cents = movement.amount_cents
            obj.payment_method = movement.payment_method
            obj.reference_id = movement.reference_id
            obj.reference_type = movement.reference_type
            obj.description = movement.description
            obj.recorded_by = movement.recorded_by
            obj.created_at = movement.created_at

        db.refresh = fake_refresh

        result = await service.record_movement(
            db=db,
            register_id=uuid.uuid4(),
            type="income",
            amount_cents=75000,
            recorded_by=uuid.uuid4(),
            payment_method="cash",
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_record_movement_returns_dict_with_type(self):
        """record_movement must return a dict containing the movement type."""
        service = CashRegisterService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        movement = _make_movement(type="expense", amount_cents=30000)

        async def fake_refresh(obj):
            obj.id = movement.id
            obj.register_id = movement.register_id
            obj.type = "expense"
            obj.amount_cents = 30000
            obj.payment_method = movement.payment_method
            obj.reference_id = None
            obj.reference_type = None
            obj.description = movement.description
            obj.recorded_by = movement.recorded_by
            obj.created_at = movement.created_at

        db.refresh = fake_refresh

        result = await service.record_movement(
            db=db,
            register_id=uuid.uuid4(),
            type="expense",
            amount_cents=30000,
            recorded_by=uuid.uuid4(),
        )

        assert result["type"] == "expense"
        assert result["amount_cents"] == 30000


# ── get_current ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetCurrentRegister:
    async def test_returns_none_when_no_open_register(self):
        """get_current must return None when no register is open."""
        service = CashRegisterService()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_current(db=db)

        assert result is None

    async def test_returns_register_with_computed_totals(self):
        """get_current must include net_balance_cents, total_income_cents, total_expense_cents."""
        service = CashRegisterService()
        db = AsyncMock()

        income_movement = _make_movement(type="income", amount_cents=100000)
        expense_movement = _make_movement(type="expense", amount_cents=30000)

        register = _make_register(
            opening_balance_cents=50000,
            movements=[income_movement, expense_movement],
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = register
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_current(db=db)

        assert result is not None
        assert result["total_income_cents"] == 100000
        assert result["total_expense_cents"] == 30000
        # net = opening (50000) + income (100000) - expense (30000) = 120000
        assert result["net_balance_cents"] == 120000

    async def test_returns_movements_list(self):
        """get_current must include a 'movements' key in the response."""
        service = CashRegisterService()
        db = AsyncMock()

        movement = _make_movement(type="income", amount_cents=25000)
        register = _make_register(opening_balance_cents=0, movements=[movement])

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = register
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_current(db=db)

        assert "movements" in result
        assert len(result["movements"]) == 1
