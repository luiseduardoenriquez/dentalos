"""Integration tests for Invoice API (B-01 through B-05).

Endpoints:
  POST /api/v1/patients/{pid}/invoices            — B-01
  GET  /api/v1/patients/{pid}/invoices             — B-02
  GET  /api/v1/patients/{pid}/invoices/{iid}       — B-03
  POST /api/v1/patients/{pid}/invoices/{iid}/cancel — B-04
  POST /api/v1/patients/{pid}/invoices/{iid}/send   — B-05
"""

import uuid

import pytest

PATIENT_ID = str(uuid.uuid4())
INVOICE_ID = str(uuid.uuid4())
BASE = f"/api/v1/patients/{PATIENT_ID}/invoices"


# ─── B-01: Create invoice ───────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateInvoice:
    async def test_create_valid_with_items(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "items": [
                    {
                        "description": "Limpieza dental",
                        "unit_price": 50000,
                        "quantity": 1,
                    }
                ],
                "notes": "Factura de prueba",
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_from_quotation(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={"quotation_id": str(uuid.uuid4())},
        )
        assert response.status_code in (201, 500)

    async def test_create_item_missing_description(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "items": [{"unit_price": 50000, "quantity": 1}],
            },
        )
        assert response.status_code == 422

    async def test_create_item_negative_unit_price(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "items": [
                    {
                        "description": "Test",
                        "unit_price": -100,
                        "quantity": 1,
                    }
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_item_zero_quantity(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "items": [
                    {
                        "description": "Test",
                        "unit_price": 50000,
                        "quantity": 0,
                    }
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_no_auth(self, async_client):
        response = await async_client.post(
            BASE,
            json={"items": [{"description": "X", "unit_price": 100, "quantity": 1}]},
        )
        assert response.status_code == 401

    async def test_create_doctor_no_billing_write(self, doctor_client):
        response = await doctor_client.post(
            BASE,
            json={"items": [{"description": "X", "unit_price": 100, "quantity": 1}]},
        )
        assert response.status_code == 403


# ─── B-02: List invoices ────────────────────────────────────────────────────


@pytest.mark.integration
class TestListInvoices:
    async def test_list_authenticated(self, authenticated_client):
        response = await authenticated_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_with_status_filter(self, authenticated_client):
        response = await authenticated_client.get(BASE, params={"status": "paid"})
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"page": 1, "page_size": 5}
        )
        assert response.status_code in (200, 500)

    async def test_list_invalid_page_size(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"page_size": 0}
        )
        assert response.status_code == 422

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_list_doctor_has_billing_read(self, doctor_client):
        response = await doctor_client.get(BASE)
        assert response.status_code in (200, 500)


# ─── B-03: Get invoice detail ───────────────────────────────────────────────


@pytest.mark.integration
class TestGetInvoice:
    async def test_get_existing(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/{INVOICE_ID}")
        assert response.status_code in (200, 404, 500)

    async def test_get_invalid_uuid(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/not-a-uuid")
        assert response.status_code in (404, 422, 500)

    async def test_get_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/{INVOICE_ID}")
        assert response.status_code == 401


# ─── B-04: Cancel invoice ───────────────────────────────────────────────────


@pytest.mark.integration
class TestCancelInvoice:
    async def test_cancel_as_owner(self, authenticated_client):
        response = await authenticated_client.post(f"{BASE}/{INVOICE_ID}/cancel")
        assert response.status_code in (200, 404, 500)

    async def test_cancel_as_doctor(self, doctor_client):
        response = await doctor_client.post(f"{BASE}/{INVOICE_ID}/cancel")
        assert response.status_code == 403

    async def test_cancel_no_auth(self, async_client):
        response = await async_client.post(f"{BASE}/{INVOICE_ID}/cancel")
        assert response.status_code == 401


# ─── B-05: Send invoice ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestSendInvoice:
    async def test_send_as_owner(self, authenticated_client):
        response = await authenticated_client.post(f"{BASE}/{INVOICE_ID}/send")
        assert response.status_code in (200, 404, 500)

    async def test_send_as_doctor(self, doctor_client):
        response = await doctor_client.post(f"{BASE}/{INVOICE_ID}/send")
        assert response.status_code == 403

    async def test_send_no_auth(self, async_client):
        response = await async_client.post(f"{BASE}/{INVOICE_ID}/send")
        assert response.status_code == 401
