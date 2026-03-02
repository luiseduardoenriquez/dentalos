"""Integration tests for the Daviplata payment webhook (GAP-01 / Sprint 25-26).

Endpoint:
  POST /api/v1/webhooks/daviplata -- Payment status notifications

Security model: provider HMAC-SHA256 signature via X-Daviplata-Signature header.
NO JWT auth -- these are server-to-server callbacks from Daviplata.

Mirrors the Nequi webhook test structure exactly; Daviplata uses an identical
signature scheme with a different header name and secret config key.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

WEBHOOK_URL = "/api/v1/webhooks/daviplata"

_VALID_PAYLOAD = {
    "event_type": "payment.completed",
    "payment_id": "DVP-2026-EFGH5678",
    "amount_cents": 8000000,
    "reference": "tn_xyz789:invoice-uuid",
    "status": "completed",
    "timestamp": datetime.now(timezone.utc).isoformat(),
}


def _make_signature(body: bytes, secret: str) -> str:
    """Compute the expected HMAC-SHA256 signature for the given body and secret."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ─── Valid signature ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDaviplataWebhookValidSignature:
    async def test_valid_signature_returns_200(self, async_client):
        """A correctly signed payload with a completed status is accepted (200 ok)."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        secret = "test-daviplata-secret"
        sig = _make_signature(body, secret)

        with (
            patch(
                "app.integrations.daviplata.service.daviplata_service.verify_webhook_signature",
                return_value=True,
            ),
            patch(
                "app.integrations.daviplata.webhook_router.publish_message",
                new_callable=AsyncMock,
            ),
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Daviplata-Signature": sig,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    async def test_expired_status_accepted_no_queue(self, async_client):
        """An expired payment is acknowledged (200) but not enqueued for reconciliation."""
        payload = {**_VALID_PAYLOAD, "status": "expired"}
        body = json.dumps(payload).encode()

        with (
            patch(
                "app.integrations.daviplata.service.daviplata_service.verify_webhook_signature",
                return_value=True,
            ),
            patch(
                "app.integrations.daviplata.webhook_router.publish_message",
                new_callable=AsyncMock,
            ) as mock_publish,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Daviplata-Signature": "valid",
                },
            )

        assert response.status_code == 200
        mock_publish.assert_not_called()

    async def test_completed_status_enqueues_reconciliation(self, async_client):
        """A completed payment is enqueued for reconciliation."""
        body = json.dumps(_VALID_PAYLOAD).encode()

        with (
            patch(
                "app.integrations.daviplata.service.daviplata_service.verify_webhook_signature",
                return_value=True,
            ),
            patch(
                "app.integrations.daviplata.webhook_router.publish_message",
                new_callable=AsyncMock,
            ) as mock_publish,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Daviplata-Signature": "valid",
                },
            )

        assert response.status_code == 200
        mock_publish.assert_called_once()


# ─── Invalid signature ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDaviplataWebhookInvalidSignature:
    async def test_invalid_signature_returns_403(self, async_client):
        """A tampered or incorrect HMAC signature is rejected with 403."""
        body = json.dumps(_VALID_PAYLOAD).encode()

        with patch(
            "app.integrations.daviplata.service.daviplata_service.verify_webhook_signature",
            return_value=False,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Daviplata-Signature": "sha256=badsignature",
                },
            )

        assert response.status_code == 403

    async def test_wrong_secret_rejected(self, async_client):
        """A payload signed with the wrong secret is rejected."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        wrong_sig = _make_signature(body, "wrong-secret")

        with patch(
            "app.integrations.daviplata.service.daviplata_service.verify_webhook_signature",
            return_value=False,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Daviplata-Signature": wrong_sig,
                },
            )

        assert response.status_code == 403


# ─── Missing signature ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDaviplataWebhookMissingSignature:
    async def test_missing_header_returns_422(self, async_client):
        """Omitting the X-Daviplata-Signature header causes FastAPI 422."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        response = await async_client.post(
            WEBHOOK_URL,
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    async def test_empty_signature_rejected(self, async_client):
        """An empty X-Daviplata-Signature header is treated as missing by FastAPI."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        response = await async_client.post(
            WEBHOOK_URL,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Daviplata-Signature": "",
            },
        )
        assert response.status_code in (422, 403)
