"""Integration tests for QR Payment generation (VP-05 / Sprint 23-24).

Endpoint:
  POST /api/v1/billing/invoices/{invoice_id}/payment-qr

Requires: billing:write permission (clinic_owner and receptionist have this).
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

INVOICE_ID = str(uuid.uuid4())
BASE = f"/api/v1/billing/invoices/{INVOICE_ID}/payment-qr"

_QR_RESPONSE = {
    "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA",
    "payment_id": "NEQ-2026-TESTPAYID",
    "provider": "nequi",
    "amount_cents": 12000000,
    "expires_at": "2026-03-02T15:30:00+00:00",
    "invoice_id": INVOICE_ID,
}


# ─── Success ─────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGeneratePaymentQRSuccess:
    async def test_generate_nequi_qr_success(self, authenticated_client):
        """POST with provider=nequi returns 200 with QR data."""
        with patch(
            "app.services.payment_qr_service.payment_qr_service.generate_payment_qr",
            new_callable=AsyncMock,
            return_value=_QR_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE,
                json={"provider": "nequi"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "qr_code_base64" in data
        assert "payment_id" in data
        assert "expires_at" in data
        assert data["provider"] == "nequi"

    async def test_generate_daviplata_qr_success(self, authenticated_client):
        """POST with provider=daviplata returns 200 with QR data."""
        daviplata_response = {**_QR_RESPONSE, "provider": "daviplata"}

        with patch(
            "app.services.payment_qr_service.payment_qr_service.generate_payment_qr",
            new_callable=AsyncMock,
            return_value=daviplata_response,
        ):
            response = await authenticated_client.post(
                BASE,
                json={"provider": "daviplata"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "daviplata"

    async def test_generate_qr_for_nonexistent_invoice(self, authenticated_client):
        """POST for an invoice that does not exist returns 404 or 500 from service."""
        other_id = str(uuid.uuid4())
        url = f"/api/v1/billing/invoices/{other_id}/payment-qr"

        with patch(
            "app.services.payment_qr_service.payment_qr_service.generate_payment_qr",
            new_callable=AsyncMock,
            side_effect=Exception("Invoice not found"),
        ):
            response = await authenticated_client.post(
                url,
                json={"provider": "nequi"},
            )

        assert response.status_code in (404, 500)


# ─── Validation errors ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGeneratePaymentQRInvalidProvider:
    async def test_unknown_provider_returns_422(self, authenticated_client):
        """POST with an unsupported provider returns 422 (Pydantic pattern validation)."""
        response = await authenticated_client.post(
            BASE,
            json={"provider": "paypal"},
        )
        assert response.status_code == 422

    async def test_missing_provider_field_returns_422(self, authenticated_client):
        """POST with an empty body (missing required provider field) returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={},
        )
        assert response.status_code == 422

    async def test_empty_provider_string_returns_422(self, authenticated_client):
        """POST with provider='' fails pattern validation."""
        response = await authenticated_client.post(
            BASE,
            json={"provider": ""},
        )
        assert response.status_code == 422

    async def test_invalid_invoice_id_format_returns_422(self, authenticated_client):
        """A non-UUID invoice_id in the path causes FastAPI 422."""
        response = await authenticated_client.post(
            "/api/v1/billing/invoices/not-a-uuid/payment-qr",
            json={"provider": "nequi"},
        )
        assert response.status_code == 422


# ─── Authorization ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGeneratePaymentQRUnauthorized:
    async def test_no_auth_returns_401(self, async_client):
        """Request without JWT is rejected with 401."""
        response = await async_client.post(
            BASE,
            json={"provider": "nequi"},
        )
        assert response.status_code == 401

    async def test_doctor_without_billing_write_returns_403(self, doctor_client):
        """Doctor role lacks billing:write, should receive 403."""
        response = await doctor_client.post(
            BASE,
            json={"provider": "nequi"},
        )
        assert response.status_code == 403
