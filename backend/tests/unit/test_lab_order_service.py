"""Unit tests for LabOrderService (VP-22 Dental Lab Orders / Sprint 31-32).

Tests cover:
  - create_lab: creates DentalLab, returns dict
  - list_labs: returns list
  - create_order: creates with status=pending
  - update_order: updates mutable fields
  - advance_status: all valid transitions + timestamps + notification
  - advance_status invalid transition and already_delivered
  - get_order: returns dict, not found raises ResourceNotFoundError
  - list_orders: paginated
  - get_overdue_orders: returns only overdue orders
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import LabOrderErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.lab_order_service import LabOrderService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_dental_lab(**overrides) -> MagicMock:
    """Build a mock DentalLab ORM row."""
    lab = MagicMock()
    lab.id = overrides.get("id", uuid.uuid4())
    lab.name = overrides.get("name", "Laboratorio Dental Premium")
    lab.contact_name = overrides.get("contact_name", "Dr. López")
    lab.phone = overrides.get("phone", "+573002345678")
    lab.email = overrides.get("email", "lab@premium.co")
    lab.address = overrides.get("address", "Calle 50 # 20-30")
    lab.city = overrides.get("city", "Bogotá")
    lab.notes = overrides.get("notes", None)
    lab.is_active = overrides.get("is_active", True)
    lab.created_at = overrides.get("created_at", datetime.now(UTC))
    lab.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return lab


def _make_lab_order(**overrides) -> MagicMock:
    """Build a mock LabOrder ORM row."""
    order = MagicMock()
    order.id = overrides.get("id", uuid.uuid4())
    order.patient_id = overrides.get("patient_id", uuid.uuid4())
    order.treatment_plan_id = overrides.get("treatment_plan_id", None)
    order.lab_id = overrides.get("lab_id", None)
    order.order_type = overrides.get("order_type", "crown")
    order.specifications = overrides.get("specifications", "Porcelana IPS e.max")
    order.status = overrides.get("status", "pending")
    order.due_date = overrides.get("due_date", date.today() + timedelta(days=7))
    order.sent_at = overrides.get("sent_at", None)
    order.ready_at = overrides.get("ready_at", None)
    order.delivered_at = overrides.get("delivered_at", None)
    order.cost_cents = overrides.get("cost_cents", 150000)
    order.notes = overrides.get("notes", None)
    order.created_by = overrides.get("created_by", uuid.uuid4())
    order.is_active = overrides.get("is_active", True)
    order.deleted_at = overrides.get("deleted_at", None)
    order.created_at = overrides.get("created_at", datetime.now(UTC))
    order.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return order


def _make_lab_create(**overrides) -> MagicMock:
    """Build a mock DentalLabCreate Pydantic model."""
    m = MagicMock()
    m.name = overrides.get("name", "Laboratorio Dental Premium")
    m.contact_name = overrides.get("contact_name", "Dr. López")
    m.phone = overrides.get("phone", "+573002345678")
    m.email = overrides.get("email", "lab@premium.co")
    m.address = overrides.get("address", "Calle 50 # 20-30")
    m.city = overrides.get("city", "Bogotá")
    m.notes = overrides.get("notes", None)
    return m


def _make_order_create(**overrides) -> MagicMock:
    """Build a mock LabOrderCreate Pydantic model."""
    m = MagicMock()
    m.patient_id = overrides.get("patient_id", str(uuid.uuid4()))
    m.treatment_plan_id = overrides.get("treatment_plan_id", None)
    m.lab_id = overrides.get("lab_id", None)
    m.order_type = overrides.get("order_type", "crown")
    m.specifications = overrides.get("specifications", "Porcelana IPS e.max")
    m.due_date = overrides.get("due_date", date.today() + timedelta(days=7))
    m.cost_cents = overrides.get("cost_cents", 150000)
    m.notes = overrides.get("notes", None)
    return m


def _make_order_update(**overrides) -> MagicMock:
    """Build a mock LabOrderUpdate Pydantic model."""
    m = MagicMock()
    m.lab_id = overrides.get("lab_id", None)
    m.order_type = overrides.get("order_type", None)
    m.specifications = overrides.get("specifications", None)
    m.due_date = overrides.get("due_date", None)
    m.cost_cents = overrides.get("cost_cents", None)
    m.notes = overrides.get("notes", None)
    return m


# ── TestCreateLab ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateLab:
    """Tests for LabOrderService.create_lab."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.add = MagicMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = LabOrderService()

    async def test_create_lab(self):
        """Creates DentalLab, calls db.add and db.flush, returns dict."""
        lab = _make_dental_lab()
        data = _make_lab_create()

        with patch(
            "app.services.lab_order_service.DentalLab",
            return_value=lab,
        ):
            result = await self.service.create_lab(self.db, data)

        self.db.add.assert_called_once()
        self.db.flush.assert_called_once()
        assert "id" in result
        assert result["name"] == lab.name


# ── TestListLabs ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListLabs:
    """Tests for LabOrderService.list_labs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = LabOrderService()

    async def test_list_labs(self):
        """Returns a list of lab dicts."""
        labs = [_make_dental_lab() for _ in range(3)]
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = labs
        self.db.execute.return_value = items_result

        result = await self.service.list_labs(self.db)

        assert isinstance(result, list)
        assert len(result) == 3
        for lab_dict in result:
            assert "id" in lab_dict


# ── TestCreateOrder ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateOrder:
    """Tests for LabOrderService.create_order."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.add = MagicMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = LabOrderService()

    async def test_create_order(self):
        """Creates LabOrder with status=pending, returns dict."""
        order = _make_lab_order(status="pending")
        data = _make_order_create()
        created_by = uuid.uuid4()

        with patch(
            "app.services.lab_order_service.LabOrder",
            return_value=order,
        ):
            result = await self.service.create_order(self.db, data, created_by)

        self.db.add.assert_called_once()
        self.db.flush.assert_called_once()
        assert result["status"] == "pending"
        assert "id" in result


# ── TestUpdateOrder ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateOrder:
    """Tests for LabOrderService.update_order."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = LabOrderService()

    async def test_update_order(self):
        """Non-terminal order can be updated — returns updated dict."""
        order = _make_lab_order(status="pending", notes=None)
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        data = _make_order_update(notes="Verificar el color A2")

        result = await self.service.update_order(self.db, order.id, data)

        assert order.notes == "Verificar el color A2"
        self.db.flush.assert_called()


# ── TestAdvanceStatus ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAdvanceStatus:
    """Tests for LabOrderService.advance_status."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = LabOrderService()
        self.tenant_id = "tn_test123"

    async def test_advance_status_pending_to_sent(self):
        """pending → sent_to_lab: valid transition, sets sent_at."""
        order = _make_lab_order(status="pending", sent_at=None)
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        result = await self.service.advance_status(
            self.db, order.id, "sent_to_lab", self.tenant_id
        )

        assert order.status == "sent_to_lab"
        assert order.sent_at is not None

    async def test_advance_status_sent_to_in_progress(self):
        """sent_to_lab → in_progress: valid transition."""
        order = _make_lab_order(status="sent_to_lab")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        await self.service.advance_status(
            self.db, order.id, "in_progress", self.tenant_id
        )

        assert order.status == "in_progress"

    async def test_advance_status_in_progress_to_ready(self):
        """in_progress → ready: valid transition, sets ready_at, enqueues notification."""
        order = _make_lab_order(status="in_progress", ready_at=None)
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        with patch(
            "app.services.lab_order_service.publish_message",
            new_callable=AsyncMock,
        ) as mock_publish:
            await self.service.advance_status(
                self.db, order.id, "ready", self.tenant_id
            )

        assert order.status == "ready"
        assert order.ready_at is not None
        mock_publish.assert_called_once()

    async def test_advance_status_ready_to_delivered(self):
        """ready → delivered: valid transition, sets delivered_at."""
        order = _make_lab_order(status="ready", delivered_at=None)
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        with patch(
            "app.services.lab_order_service.publish_message",
            new_callable=AsyncMock,
        ):
            result = await self.service.advance_status(
                self.db, order.id, "delivered", self.tenant_id
            )

        assert order.status == "delivered"
        assert order.delivered_at is not None

    async def test_advance_status_to_cancelled(self):
        """Any non-terminal state → cancelled is allowed."""
        order = _make_lab_order(status="in_progress")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        await self.service.advance_status(
            self.db, order.id, "cancelled", self.tenant_id
        )

        assert order.status == "cancelled"

    async def test_advance_status_invalid_transition(self):
        """Invalid transition raises INVALID_STATUS_TRANSITION (422)."""
        order = _make_lab_order(status="pending")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        with pytest.raises(DentalOSError) as exc_info:
            # pending → delivered is not a valid direct transition
            await self.service.advance_status(
                self.db, order.id, "delivered", self.tenant_id
            )

        assert exc_info.value.error == LabOrderErrors.INVALID_STATUS_TRANSITION
        assert exc_info.value.status_code == 422

    async def test_advance_status_already_delivered(self):
        """Delivered order raises ALREADY_DELIVERED (409)."""
        order = _make_lab_order(status="delivered")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.advance_status(
                self.db, order.id, "ready", self.tenant_id
            )

        assert exc_info.value.error == LabOrderErrors.ALREADY_DELIVERED
        assert exc_info.value.status_code == 409


# ── TestGetOrder ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetOrder:
    """Tests for LabOrderService.get_order."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = LabOrderService()

    async def test_get_order(self):
        """Known order_id returns the order dict."""
        order = _make_lab_order()
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = order
        self.db.execute.return_value = orm_result

        result = await self.service.get_order(self.db, order.id)

        assert result["id"] == str(order.id)
        assert result["order_type"] == order.order_type

    async def test_get_order_not_found(self):
        """Unknown order_id raises ResourceNotFoundError."""
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = orm_result

        with pytest.raises(ResourceNotFoundError):
            await self.service.get_order(self.db, uuid.uuid4())


# ── TestListOrders ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListOrders:
    """Tests for LabOrderService.list_orders."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = LabOrderService()

    async def test_list_orders(self):
        """Returns paginated result with items, total, page, page_size."""
        orders = [_make_lab_order() for _ in range(4)]

        count_result = MagicMock()
        count_result.scalar_one.return_value = 4

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = orders

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.list_orders(self.db, page=1, page_size=20)

        assert result["total"] == 4
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 4


# ── TestGetOverdueOrders ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetOverdueOrders:
    """Tests for LabOrderService.get_overdue_orders."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = LabOrderService()

    async def test_get_overdue_orders(self):
        """Returns only orders with due_date < today that are not delivered/cancelled."""
        past_date = date.today() - timedelta(days=5)
        overdue = [
            _make_lab_order(status="pending", due_date=past_date),
            _make_lab_order(status="sent_to_lab", due_date=past_date),
        ]

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = overdue

        self.db.execute.return_value = items_result

        result = await self.service.get_overdue_orders(self.db)

        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert item["status"] not in ("delivered", "cancelled")
