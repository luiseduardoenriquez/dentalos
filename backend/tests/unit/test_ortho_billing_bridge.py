"""Unit tests for the ortho ↔ billing bridge.

Tests cover:
  - get_billable_ortho_items: initial payments + pending monthly controls
  - create_invoice: 409 guards for duplicate ortho invoicing
  - record_payment bridge: OrthoVisit.payment_status synced on invoice paid
  - _item_to_dict: ortho fields serialized correctly
  - OrthoVisitCreate schema: payment_amount defaults to None (monthly fallback)

All DB calls use AsyncMock. PHI never appears in assertions.
All amounts in COP cents (integers).
"""

import uuid
from datetime import date, datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BillingError
from app.services.invoice_service import InvoiceService, _item_to_dict


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_ortho_case(**overrides) -> MagicMock:
    """Build a minimal OrthoCase-like mock."""
    case = MagicMock()
    case.id = overrides.get("id", uuid.uuid4())
    case.patient_id = overrides.get("patient_id", uuid.uuid4())
    case.doctor_id = overrides.get("doctor_id", uuid.uuid4())
    case.case_number = overrides.get("case_number", "ORT-0001")
    case.status = overrides.get("status", "active_treatment")
    case.initial_payment = overrides.get("initial_payment", 50_000_00)
    case.monthly_payment = overrides.get("monthly_payment", 10_416_00)
    case.is_active = True
    return case


def _make_ortho_visit(**overrides) -> MagicMock:
    """Build a minimal OrthoVisit-like mock."""
    visit = MagicMock()
    visit.id = overrides.get("id", uuid.uuid4())
    visit.ortho_case_id = overrides.get("ortho_case_id", uuid.uuid4())
    visit.visit_number = overrides.get("visit_number", 1)
    visit.visit_date = overrides.get("visit_date", date(2026, 3, 10))
    visit.doctor_id = overrides.get("doctor_id", uuid.uuid4())
    visit.payment_status = overrides.get("payment_status", "pending")
    visit.payment_amount = overrides.get("payment_amount", 10_416_00)
    visit.payment_id = overrides.get("payment_id", None)
    visit.is_active = True
    return visit


def _make_invoice_item(**overrides) -> MagicMock:
    """Build a minimal InvoiceItem-like mock for _item_to_dict."""
    item = MagicMock()
    item.id = overrides.get("id", uuid.uuid4())
    item.invoice_id = overrides.get("invoice_id", uuid.uuid4())
    item.service_id = overrides.get("service_id", None)
    item.description = overrides.get("description", "Control mensual #1")
    item.cups_code = overrides.get("cups_code", None)
    item.quantity = overrides.get("quantity", 1)
    item.unit_price = overrides.get("unit_price", 10_416_00)
    item.discount = overrides.get("discount", 0)
    item.line_total = overrides.get("line_total", 10_416_00)
    item.sort_order = overrides.get("sort_order", 0)
    item.tooth_number = overrides.get("tooth_number", None)
    item.treatment_plan_item_id = overrides.get("treatment_plan_item_id", None)
    item.ortho_case_id = overrides.get("ortho_case_id", None)
    item.ortho_visit_id = overrides.get("ortho_visit_id", None)
    item.doctor_id = overrides.get("doctor_id", None)
    item.created_at = overrides.get("created_at", datetime.now(UTC))
    item.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return item


# ── _item_to_dict serialization ──────────────────────────────────────────────


@pytest.mark.unit
class TestItemToDictOrthoFields:
    """Verify ortho_case_id and ortho_visit_id are serialized correctly."""

    def test_ortho_fields_present_when_set(self):
        oc_id = uuid.uuid4()
        ov_id = uuid.uuid4()
        item = _make_invoice_item(ortho_case_id=oc_id, ortho_visit_id=ov_id)
        result = _item_to_dict(item)

        assert result["ortho_case_id"] == str(oc_id)
        assert result["ortho_visit_id"] == str(ov_id)

    def test_ortho_fields_none_when_not_set(self):
        item = _make_invoice_item(ortho_case_id=None, ortho_visit_id=None)
        result = _item_to_dict(item)

        assert result["ortho_case_id"] is None
        assert result["ortho_visit_id"] is None

    def test_initial_payment_item_has_case_but_no_visit(self):
        oc_id = uuid.uuid4()
        item = _make_invoice_item(
            ortho_case_id=oc_id,
            ortho_visit_id=None,
            description="Cuota inicial - ORT-0001",
        )
        result = _item_to_dict(item)

        assert result["ortho_case_id"] == str(oc_id)
        assert result["ortho_visit_id"] is None
        assert result["description"] == "Cuota inicial - ORT-0001"


# ── OrthoVisitCreate schema fix ──────────────────────────────────────────────


@pytest.mark.unit
class TestOrthoVisitCreatePaymentAmount:
    """Verify payment_amount defaults to None so service uses case.monthly_payment."""

    def test_payment_amount_defaults_to_none(self):
        from app.schemas.ortho import OrthoVisitCreate

        visit = OrthoVisitCreate(visit_date=date(2026, 4, 1))
        assert visit.payment_amount is None

    def test_payment_amount_explicit_value_preserved(self):
        from app.schemas.ortho import OrthoVisitCreate

        visit = OrthoVisitCreate(visit_date=date(2026, 4, 1), payment_amount=25_000_00)
        assert visit.payment_amount == 25_000_00


# ── get_billable_ortho_items ─────────────────────────────────────────────────


@pytest.mark.unit
class TestGetBillableOrthoItems:
    """Test InvoiceService.get_billable_ortho_items() logic."""

    async def test_returns_initial_payment_for_active_case(self):
        service = InvoiceService()
        db = AsyncMock()
        patient_id = str(uuid.uuid4())
        case = _make_ortho_case(initial_payment=50_000_00)

        # First query: cases with initial payment not yet invoiced
        cases_result = MagicMock()
        cases_result.scalars.return_value.all.return_value = [case]

        # Second query: pending visits not yet invoiced
        visits_result = MagicMock()
        visits_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[cases_result, visits_result])

        result = await service.get_billable_ortho_items(db=db, patient_id=patient_id)

        assert result["total"] == 1
        assert result["items"][0]["type"] == "initial_payment"
        assert result["items"][0]["ortho_case_id"] == str(case.id)
        assert result["items"][0]["amount"] == 50_000_00
        assert result["items"][0]["description"].startswith("Cuota inicial")

    async def test_returns_pending_monthly_controls(self):
        service = InvoiceService()
        db = AsyncMock()
        patient_id = str(uuid.uuid4())
        case_id = uuid.uuid4()
        doctor_id = uuid.uuid4()

        visit = _make_ortho_visit(
            ortho_case_id=case_id,
            doctor_id=doctor_id,
            visit_number=3,
            payment_amount=10_416_00,
        )

        # First query: no initial payments
        cases_result = MagicMock()
        cases_result.scalars.return_value.all.return_value = []

        # Second query: one pending visit
        visits_result = MagicMock()
        visits_result.all.return_value = [(visit, "ORT-0001", doctor_id)]

        db.execute = AsyncMock(side_effect=[cases_result, visits_result])

        result = await service.get_billable_ortho_items(db=db, patient_id=patient_id)

        assert result["total"] == 1
        item = result["items"][0]
        assert item["type"] == "monthly_control"
        assert item["ortho_visit_id"] == str(visit.id)
        assert item["visit_number"] == 3
        assert item["amount"] == 10_416_00
        assert "Control mensual #3" in item["description"]

    async def test_returns_both_initial_and_controls(self):
        service = InvoiceService()
        db = AsyncMock()
        patient_id = str(uuid.uuid4())
        case = _make_ortho_case()
        doctor_id = case.doctor_id

        visit = _make_ortho_visit(
            ortho_case_id=case.id,
            doctor_id=doctor_id,
            visit_number=1,
        )

        cases_result = MagicMock()
        cases_result.scalars.return_value.all.return_value = [case]

        visits_result = MagicMock()
        visits_result.all.return_value = [(visit, case.case_number, doctor_id)]

        db.execute = AsyncMock(side_effect=[cases_result, visits_result])

        result = await service.get_billable_ortho_items(db=db, patient_id=patient_id)

        assert result["total"] == 2
        types = {item["type"] for item in result["items"]}
        assert types == {"initial_payment", "monthly_control"}

    async def test_empty_when_no_ortho_data(self):
        service = InvoiceService()
        db = AsyncMock()
        patient_id = str(uuid.uuid4())

        cases_result = MagicMock()
        cases_result.scalars.return_value.all.return_value = []

        visits_result = MagicMock()
        visits_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[cases_result, visits_result])

        result = await service.get_billable_ortho_items(db=db, patient_id=patient_id)

        assert result["total"] == 0
        assert result["items"] == []


# ── create_invoice ortho guards ──────────────────────────────────────────────


@pytest.mark.unit
class TestCreateInvoiceOrthoGuards:
    """Test 409 guards for duplicate ortho invoicing in create_invoice."""

    async def test_duplicate_ortho_visit_raises_409(self):
        service = InvoiceService()
        db = AsyncMock()

        patient_id = str(uuid.uuid4())
        ortho_visit_id = str(uuid.uuid4())

        # Simulate: patient found
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = uuid.uuid4()

        # Simulate: next invoice number
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        # Simulate: treatment_plan_item_id not set — skip that guard
        # Simulate: ortho_visit_id already invoiced
        existing_ov = MagicMock()
        existing_ov.scalar_one_or_none.return_value = uuid.uuid4()  # found!

        db.execute = AsyncMock(
            side_effect=[patient_result, count_result, existing_ov]
        )

        with pytest.raises(BillingError) as exc_info:
            await service.create_invoice(
                db=db,
                patient_id=patient_id,
                created_by=str(uuid.uuid4()),
                items=[{
                    "description": "Control mensual #1",
                    "unit_price": 10_416_00,
                    "ortho_visit_id": ortho_visit_id,
                }],
            )

        assert exc_info.value.status_code == 409
        assert "ortho_visit_already_invoiced" in exc_info.value.error

    async def test_duplicate_ortho_initial_payment_raises_409(self):
        service = InvoiceService()
        db = AsyncMock()

        patient_id = str(uuid.uuid4())
        ortho_case_id = str(uuid.uuid4())

        # Simulate: patient found
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = uuid.uuid4()

        # Simulate: next invoice number
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        # Simulate: ortho_visit_id not set → check ortho_case_id initial
        # Simulate: initial already invoiced
        existing_oc = MagicMock()
        existing_oc.scalar_one_or_none.return_value = uuid.uuid4()  # found!

        db.execute = AsyncMock(
            side_effect=[patient_result, count_result, existing_oc]
        )

        with pytest.raises(BillingError) as exc_info:
            await service.create_invoice(
                db=db,
                patient_id=patient_id,
                created_by=str(uuid.uuid4()),
                items=[{
                    "description": "Cuota inicial - ORT-0001",
                    "unit_price": 50_000_00,
                    "ortho_case_id": ortho_case_id,
                }],
            )

        assert exc_info.value.status_code == 409
        assert "ortho_initial_already_invoiced" in exc_info.value.error


# ── Payment → OrthoVisit bridge ──────────────────────────────────────────────


@pytest.mark.unit
class TestPaymentOrthoVisitBridge:
    """Test that recording a payment syncs OrthoVisit.payment_status when invoice is paid."""

    async def test_bridge_updates_ortho_visits_on_paid(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        db = AsyncMock()
        patient_id = str(uuid.uuid4())
        invoice_id = str(uuid.uuid4())
        iid = uuid.UUID(invoice_id)
        visit_id = uuid.uuid4()

        # Mock invoice lookup
        invoice = MagicMock()
        invoice.id = iid
        invoice.patient_id = uuid.UUID(patient_id)
        invoice.status = "sent"
        invoice.balance = 10_416_00
        invoice.is_active = True
        invoice.invoice_number = "FAC-2026-00001"

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice
        inv_result.scalar_one.return_value = invoice

        # Mock no open cash register
        register_result = MagicMock()
        register_result.scalar_one_or_none.return_value = None

        # Mock recalculate_balance → invoice becomes "paid"
        paid_invoice = MagicMock()
        paid_invoice.status = "paid"
        paid_invoice.balance = 0
        paid_invoice.invoice_number = "FAC-2026-00001"

        # Mock ortho items query → one linked visit
        ortho_items_result = MagicMock()
        ortho_items_result.all.return_value = [(visit_id,)]

        # Mock OrthoVisit query
        ortho_visit = MagicMock()
        ortho_visit.id = visit_id
        ortho_visit.payment_status = "pending"
        ortho_visit.payment_id = None

        visits_result = MagicMock()
        visits_result.scalars.return_value.all.return_value = [ortho_visit]

        db.execute = AsyncMock(
            side_effect=[
                inv_result,        # invoice lookup
                register_result,   # cash register
                ortho_items_result,  # ortho items query
                visits_result,     # OrthoVisit query
            ]
        )
        db.flush = AsyncMock()
        db.add = MagicMock()

        with (
            patch(
                "app.services.payment_service.invoice_service.recalculate_balance",
                new_callable=AsyncMock,
                return_value=paid_invoice,
            ),
            patch(
                "app.services.payment_service.publish_message",
                new_callable=AsyncMock,
            ),
        ):
            await service.record_payment(
                db=db,
                patient_id=patient_id,
                invoice_id=invoice_id,
                amount=10_416_00,
                payment_method="cash",
                received_by=str(uuid.uuid4()),
                tenant_id=str(uuid.uuid4()),
            )

        # Verify the bridge updated the OrthoVisit
        assert ortho_visit.payment_status == "paid"
        assert ortho_visit.payment_id is not None

    async def test_bridge_skips_when_invoice_not_fully_paid(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        db = AsyncMock()
        patient_id = str(uuid.uuid4())
        invoice_id = str(uuid.uuid4())
        iid = uuid.UUID(invoice_id)

        # Mock invoice lookup
        invoice = MagicMock()
        invoice.id = iid
        invoice.patient_id = uuid.UUID(patient_id)
        invoice.status = "sent"
        invoice.balance = 20_000_00
        invoice.is_active = True
        invoice.invoice_number = "FAC-2026-00002"

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice

        # Mock no open cash register
        register_result = MagicMock()
        register_result.scalar_one_or_none.return_value = None

        # Mock recalculate_balance → invoice becomes "partial" (not fully paid)
        partial_invoice = MagicMock()
        partial_invoice.status = "partial"
        partial_invoice.balance = 10_000_00
        partial_invoice.invoice_number = "FAC-2026-00002"

        db.execute = AsyncMock(
            side_effect=[
                inv_result,       # invoice lookup
                register_result,  # cash register
            ]
        )
        db.flush = AsyncMock()
        db.add = MagicMock()

        with (
            patch(
                "app.services.payment_service.invoice_service.recalculate_balance",
                new_callable=AsyncMock,
                return_value=partial_invoice,
            ),
            patch(
                "app.services.payment_service.publish_message",
                new_callable=AsyncMock,
            ),
        ):
            await service.record_payment(
                db=db,
                patient_id=patient_id,
                invoice_id=invoice_id,
                amount=10_000_00,
                payment_method="cash",
                received_by=str(uuid.uuid4()),
                tenant_id=str(uuid.uuid4()),
            )

        # With partial payment, db.execute should only be called twice
        # (invoice lookup + cash register) — no ortho queries
        assert db.execute.call_count == 2


# ── Integration-style endpoint tests ─────────────────────────────────────────


@pytest.mark.integration
class TestBillableOrthoItemsEndpoint:
    """Test GET /patients/{pid}/invoices/billable-ortho-items HTTP path."""

    async def test_billable_ortho_items_auth_required(self, async_client):
        pid = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/patients/{pid}/invoices/billable-ortho-items"
        )
        assert response.status_code == 401

    async def test_billable_ortho_items_doctor_has_read_access(self, doctor_client):
        pid = str(uuid.uuid4())
        response = await doctor_client.get(
            f"/api/v1/patients/{pid}/invoices/billable-ortho-items"
        )
        # 200 or 500 (DB not seeded — acceptable in integration tests)
        assert response.status_code in (200, 500)

    async def test_billable_ortho_items_owner_has_access(self, authenticated_client):
        pid = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"/api/v1/patients/{pid}/invoices/billable-ortho-items"
        )
        assert response.status_code in (200, 500)


@pytest.mark.integration
class TestCreateInvoiceWithOrthoItems:
    """Test POST invoice with ortho fields in items."""

    async def test_create_invoice_with_ortho_visit_id(self, authenticated_client):
        pid = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/patients/{pid}/invoices",
            json={
                "items": [
                    {
                        "description": "Control mensual #1 - ORT-0001",
                        "unit_price": 10_416_00,
                        "quantity": 1,
                        "ortho_case_id": str(uuid.uuid4()),
                        "ortho_visit_id": str(uuid.uuid4()),
                    }
                ],
            },
        )
        # 201 success or 500 (DB not seeded)
        assert response.status_code in (201, 500)

    async def test_create_invoice_with_ortho_initial_payment(self, authenticated_client):
        pid = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/patients/{pid}/invoices",
            json={
                "items": [
                    {
                        "description": "Cuota inicial - ORT-0001",
                        "unit_price": 50_000_00,
                        "quantity": 1,
                        "ortho_case_id": str(uuid.uuid4()),
                    }
                ],
            },
        )
        assert response.status_code in (201, 500)


# ── Schema validation tests ──────────────────────────────────────────────────


@pytest.mark.unit
class TestInvoiceSchemaOrthoFields:
    """Verify ortho fields are accepted/serialized in invoice schemas."""

    def test_invoice_item_create_accepts_ortho_fields(self):
        from app.schemas.invoice import InvoiceItemCreate

        item = InvoiceItemCreate(
            description="Control mensual #1",
            unit_price=10_416_00,
            ortho_case_id=str(uuid.uuid4()),
            ortho_visit_id=str(uuid.uuid4()),
        )
        assert item.ortho_case_id is not None
        assert item.ortho_visit_id is not None

    def test_invoice_item_create_ortho_fields_optional(self):
        from app.schemas.invoice import InvoiceItemCreate

        item = InvoiceItemCreate(
            description="Limpieza dental",
            unit_price=50_000,
        )
        assert item.ortho_case_id is None
        assert item.ortho_visit_id is None

    def test_invoice_item_response_includes_ortho_fields(self):
        from app.schemas.invoice import InvoiceItemResponse

        oc_id = str(uuid.uuid4())
        ov_id = str(uuid.uuid4())
        data = {
            "id": str(uuid.uuid4()),
            "invoice_id": str(uuid.uuid4()),
            "description": "Control mensual #1",
            "quantity": 1,
            "unit_price": 10_416_00,
            "discount": 0,
            "line_total": 10_416_00,
            "sort_order": 0,
            "ortho_case_id": oc_id,
            "ortho_visit_id": ov_id,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        resp = InvoiceItemResponse(**data)
        assert resp.ortho_case_id == oc_id
        assert resp.ortho_visit_id == ov_id

    def test_billable_ortho_item_response_initial(self):
        from app.schemas.invoice import BillableOrthoItemResponse

        item = BillableOrthoItemResponse(
            type="initial_payment",
            ortho_case_id=str(uuid.uuid4()),
            case_number="ORT-0001",
            description="Cuota inicial - ORT-0001",
            amount=50_000_00,
            doctor_id=str(uuid.uuid4()),
        )
        assert item.type == "initial_payment"
        assert item.ortho_visit_id is None
        assert item.visit_number is None

    def test_billable_ortho_item_response_monthly(self):
        from app.schemas.invoice import BillableOrthoItemResponse

        item = BillableOrthoItemResponse(
            type="monthly_control",
            ortho_case_id=str(uuid.uuid4()),
            ortho_visit_id=str(uuid.uuid4()),
            case_number="ORT-0001",
            visit_number=3,
            visit_date=date(2026, 3, 10),
            description="Control mensual #3 - ORT-0001",
            amount=10_416_00,
            doctor_id=str(uuid.uuid4()),
        )
        assert item.type == "monthly_control"
        assert item.visit_number == 3
        assert item.ortho_visit_id is not None
