"""Integration tests for Webhook endpoints (INT-01, INT-02).

Endpoints:
  GET  /api/v1/webhooks/whatsapp            — Meta verification challenge
  POST /api/v1/webhooks/whatsapp            — WhatsApp delivery status
  POST /api/v1/webhooks/twilio/status       — Twilio SMS delivery status

These endpoints use provider-specific signature verification, NOT JWT auth.
"""

import hashlib
import hmac
import json

import pytest


# ─── WhatsApp Webhook (INT-01) ───────────────────────────────────────────────


@pytest.mark.integration
class TestWhatsAppVerify:
    async def test_verify_missing_params(self, async_client):
        response = await async_client.get("/api/v1/webhooks/whatsapp")
        assert response.status_code == 422

    async def test_verify_invalid_mode(self, async_client):
        response = await async_client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "test-token",
                "hub.challenge": "challenge123",
            },
        )
        assert response.status_code in (403, 500)

    async def test_verify_wrong_token(self, async_client):
        response = await async_client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge123",
            },
        )
        assert response.status_code in (403, 500)


@pytest.mark.integration
class TestWhatsAppReceive:
    async def test_receive_missing_signature(self, async_client):
        response = await async_client.post(
            "/api/v1/webhooks/whatsapp",
            json={"entry": []},
        )
        assert response.status_code == 422

    async def test_receive_invalid_signature(self, async_client):
        response = await async_client.post(
            "/api/v1/webhooks/whatsapp",
            json={"entry": []},
            headers={"X-Hub-Signature-256": "sha256=invalid"},
        )
        assert response.status_code in (403, 500)

    async def test_receive_malformed_signature(self, async_client):
        response = await async_client.post(
            "/api/v1/webhooks/whatsapp",
            json={"entry": []},
            headers={"X-Hub-Signature-256": "not-sha256-prefixed"},
        )
        assert response.status_code in (403, 500)


# ─── Twilio SMS Webhook (INT-02) ─────────────────────────────────────────────


@pytest.mark.integration
class TestTwilioStatusCallback:
    async def test_status_missing_signature(self, async_client):
        response = await async_client.post(
            "/api/v1/webhooks/twilio/status",
            data={"MessageSid": "SM123", "MessageStatus": "delivered"},
        )
        assert response.status_code == 422

    async def test_status_invalid_signature(self, async_client):
        response = await async_client.post(
            "/api/v1/webhooks/twilio/status",
            data={"MessageSid": "SM123", "MessageStatus": "delivered"},
            headers={"X-Twilio-Signature": "invalid-signature"},
        )
        assert response.status_code in (403, 500)
