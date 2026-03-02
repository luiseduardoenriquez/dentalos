"""Integration tests for the Nequi payment webhook (GAP-01 / Sprint 25-26).

Endpoint:
  POST /api/v1/webhooks/nequi -- Payment status notifications

Security model: provider HMAC-SHA256 signature via X-Nequi-Signature header.
NO JWT auth -- these are server-to-server callbacks from Nequi.

The endpoint returns 200 on valid signature, 403 on invalid/missing signature,
and 400 on an unparseable payload (after a valid signature).
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

WEBHOOK_URL = "/api/v1/webhooks/nequi"

_VALID_PAYLOAD = {
    "event_type": "payment.completed",
    "payment_id": "NEQ-2026-ABCD1234",
    "amount_cents": 15000000,
    "reference": "tn_abc123:invoice-uuid",
    "status": "completed",
    "timestamp": datetime.now(timezone.utc).isoformat(),
}


def _make_signature(body: bytes, secret: str) -> str:
    """Compute the expected HMAC-SHA256 signature for the given body and secret."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ─── Valid signature ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNequiWebhookValidSignature:
    async def test_valid_signature_returns_200(self, async_client):
        """A correctly signed payload with a valid status is accepted (200 ok)."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        secret = "test-nequi-secret"
        sig = _make_signature(body, secret)

        with (
            patch(
                "app.integrations.nequi.service.nequi_service.verify_webhook_signature",
                return_value=True,
            ),
            patch(
                "app.integrations.nequi.webhook_router.publish_message",
                new_callable=AsyncMock,
            ),
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Nequi-Signature": sig,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    async def test_pending_status_accepted_no_queue(self, async_client):
        """A pending payment is accepted (200) but nothing is enqueued."""
        payload = {**_VALID_PAYLOAD, "status": "pending"}
        body = json.dumps(payload).encode()

        with (
            patch(
                "app.integrations.nequi.service.nequi_service.verify_webhook_signature",
                return_value=True,
            ),
            patch(
                "app.integrations.nequi.webhook_router.publish_message",
                new_callable=AsyncMock,
            ) as mock_publish,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Nequi-Signature": "valid",
                },
            )

        assert response.status_code == 200
        mock_publish.assert_not_called()


# ─── Invalid signature ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNequiWebhookInvalidSignature:
    async def test_invalid_signature_returns_403(self, async_client):
        """A tampered or incorrect HMAC signature is rejected with 403."""
        body = json.dumps(_VALID_PAYLOAD).encode()

        with patch(
            "app.integrations.nequi.service.nequi_service.verify_webhook_signature",
            return_value=False,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Nequi-Signature": "sha256=incorrectsignature",
                },
            )

        assert response.status_code == 403

    async def test_wrong_secret_returns_403(self, async_client):
        """A payload signed with the wrong secret is rejected with 403."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        wrong_sig = _make_signature(body, "wrong-secret")

        with patch(
            "app.integrations.nequi.service.nequi_service.verify_webhook_signature",
            return_value=False,
        ):
            response = await async_client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Nequi-Signature": wrong_sig,
                },
            )

        assert response.status_code == 403


# ─── Missing signature ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNequiWebhookMissingSignature:
    async def test_missing_header_returns_422(self, async_client):
        """Omitting the X-Nequi-Signature header causes FastAPI 422 (required header)."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        response = await async_client.post(
            WEBHOOK_URL,
            content=body,
            headers={"Content-Type": "application/json"},
        )
        # FastAPI treats a missing required Header(...) as 422 Unprocessable Entity
        assert response.status_code == 422

    async def test_empty_signature_header_returns_422(self, async_client):
        """An empty X-Nequi-Signature header is treated as missing by FastAPI."""
        body = json.dumps(_VALID_PAYLOAD).encode()
        response = await async_client.post(
            WEBHOOK_URL,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Nequi-Signature": "",
            },
        )
        assert response.status_code in (422, 403)
