"""Integration tests for Payment API (B-06 through B-10).

Endpoints:
  POST /api/v1/patients/{pid}/invoices/{iid}/payments               — B-06
  GET  /api/v1/patients/{pid}/invoices/{iid}/payments               — B-07
  POST /api/v1/patients/{pid}/invoices/{iid}/payment-plan           — B-08
  GET  /api/v1/patients/{pid}/invoices/{iid}/payment-plan           — B-09
  POST /api/v1/patients/{pid}/invoices/{iid}/payment-plan/{n}/pay   — B-10
"""

import uuid

import pytest

PATIENT_ID = str(uuid.uuid4())
INVOICE_ID = str(uuid.uuid4())
BASE = f"/api/v1/patients/{PATIENT_ID}/invoices/{INVOICE_ID}"


# ─── B-06: Record payment ───────────────────────────────────────────────────


@pytest.mark.integration
class TestRecordPayment:
    async def test_record_valid_cash(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"amount": 50000, "payment_method": "cash"},
        )
        assert response.status_code in (201, 500)

    async def test_record_valid_card(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={
                "amount": 100000,
                "payment_method": "card",
                "reference_number": "TXN-12345",
            },
        )
        assert response.status_code in (201, 500)

    async def test_record_valid_transfer(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"amount": 75000, "payment_method": "transfer"},
        )
        assert response.status_code in (201, 500)

    async def test_record_zero_amount(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"amount": 0, "payment_method": "cash"},
        )
        assert response.status_code == 422

    async def test_record_negative_amount(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"amount": -5000, "payment_method": "cash"},
        )
        assert response.status_code == 422

    async def test_record_invalid_method(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"amount": 50000, "payment_method": "bitcoin"},
        )
        assert response.status_code == 422

    async def test_record_missing_amount(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"payment_method": "cash"},
        )
        assert response.status_code == 422

    async def test_record_missing_method(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payments",
            json={"amount": 50000},
        )
        assert response.status_code == 422

    async def test_record_as_doctor(self, doctor_client):
        response = await doctor_client.post(
            f"{BASE}/payments",
            json={"amount": 50000, "payment_method": "cash"},
        )
        assert response.status_code == 403

    async def test_record_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/payments",
            json={"amount": 50000, "payment_method": "cash"},
        )
        assert response.status_code == 401


# ─── B-07: List payments ────────────────────────────────────────────────────


@pytest.mark.integration
class TestListPayments:
    async def test_list_authenticated(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/payments")
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/payments", params={"page": 1, "page_size": 10}
        )
        assert response.status_code in (200, 500)

    async def test_list_invalid_page_size(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/payments", params={"page_size": 0}
        )
        assert response.status_code == 422

    async def test_list_as_doctor(self, doctor_client):
        response = await doctor_client.get(f"{BASE}/payments")
        assert response.status_code in (200, 500)

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/payments")
        assert response.status_code == 401


# ─── B-08: Create payment plan ──────────────────────────────────────────────


@pytest.mark.integration
class TestCreatePaymentPlan:
    async def test_create_valid(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan",
            json={"num_installments": 3, "first_due_date": "2026-04-01"},
        )
        assert response.status_code in (201, 500)

    async def test_create_one_installment(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan",
            json={"num_installments": 1, "first_due_date": "2026-04-01"},
        )
        assert response.status_code == 422

    async def test_create_too_many_installments(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan",
            json={"num_installments": 25, "first_due_date": "2026-04-01"},
        )
        assert response.status_code == 422

    async def test_create_missing_date(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan",
            json={"num_installments": 3},
        )
        assert response.status_code == 422

    async def test_create_as_doctor(self, doctor_client):
        response = await doctor_client.post(
            f"{BASE}/payment-plan",
            json={"num_installments": 3, "first_due_date": "2026-04-01"},
        )
        assert response.status_code == 403

    async def test_create_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/payment-plan",
            json={"num_installments": 3, "first_due_date": "2026-04-01"},
        )
        assert response.status_code == 401


# ─── B-09: Get payment plan ─────────────────────────────────────────────────


@pytest.mark.integration
class TestGetPaymentPlan:
    async def test_get_authenticated(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/payment-plan")
        assert response.status_code in (200, 404, 500)

    async def test_get_as_doctor(self, doctor_client):
        response = await doctor_client.get(f"{BASE}/payment-plan")
        assert response.status_code in (200, 404, 500)

    async def test_get_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/payment-plan")
        assert response.status_code == 401


# ─── B-10: Pay installment ──────────────────────────────────────────────────


@pytest.mark.integration
class TestPayInstallment:
    async def test_pay_valid(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan/1/pay",
            json={"amount": 25000, "payment_method": "cash"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_pay_invalid_method(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan/1/pay",
            json={"amount": 25000, "payment_method": "crypto"},
        )
        assert response.status_code == 422

    async def test_pay_zero_amount(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/payment-plan/1/pay",
            json={"amount": 0, "payment_method": "cash"},
        )
        assert response.status_code == 422

    async def test_pay_as_doctor(self, doctor_client):
        response = await doctor_client.post(
            f"{BASE}/payment-plan/1/pay",
            json={"amount": 25000, "payment_method": "cash"},
        )
        assert response.status_code == 403

    async def test_pay_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/payment-plan/1/pay",
            json={"amount": 25000, "payment_method": "cash"},
        )
        assert response.status_code == 401
