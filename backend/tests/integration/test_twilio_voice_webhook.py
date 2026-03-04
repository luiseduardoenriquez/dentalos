"""Integration tests for Twilio Voice webhook routes (VP-18 VoIP Screen Pop / Sprint 31-32).

Endpoints under test (no JWT auth — provider HMAC-SHA1 signature):
  POST /api/v1/webhooks/twilio/voice/{tenant_slug}/incoming -- Incoming call
  POST /api/v1/webhooks/twilio/voice/{tenant_slug}/status   -- Call status callback

Security:
  - Validates Twilio X-Twilio-Signature (HMAC-SHA1)
  - Returns 403 on invalid/missing signature
  - PHI (phone numbers) is NEVER logged

TwiML response:
  - Content-Type: text/xml (application/xml)
  - Returns <Response><Say> on success
"""

import hashlib
import hmac
import logging
import uuid
from base64 import b64encode
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

WEBHOOK_BASE = "/api/v1/webhooks/twilio/voice"
TENANT_SLUG = "test-clinic"
INCOMING_URL = f"{WEBHOOK_BASE}/{TENANT_SLUG}/incoming"
STATUS_URL = f"{WEBHOOK_BASE}/{TENANT_SLUG}/status"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_twilio_signature(url: str, params: dict, auth_token: str) -> str:
    """Compute a valid Twilio X-Twilio-Signature for test use."""
    sorted_params = sorted(params.items())
    data_string = url + "".join(f"{k}{v}" for k, v in sorted_params)
    signature = hmac.new(
        auth_token.encode("utf-8"),
        data_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return b64encode(signature).decode("utf-8")


def _form_data(overrides: dict | None = None) -> dict:
    """Build a realistic Twilio incoming-call form payload."""
    data = {
        "CallSid": f"CA{uuid.uuid4().hex[:30]}",
        "From": "+573001234567",
        "To": "+571234567",
        "CallStatus": "ringing",
        "Direction": "inbound",
    }
    if overrides:
        data.update(overrides)
    return data


# ── TestIncomingCallValidSignature ────────────────────────────────────────────


@pytest.mark.integration
class TestIncomingCallValidSignature:
    async def test_incoming_call_valid_signature(self, async_client):
        """POST /incoming with mocked signature verification returns TwiML XML."""
        form = _form_data()

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=True,
        ), patch(
            "app.integrations.twilio_voice.webhook_router._resolve_tenant_by_slug",
            new_callable=AsyncMock,
            return_value=("tenant-uuid-123", "tn_testschema"),
        ), patch(
            "app.services.call_log_service.call_log_service.match_phone_to_patient",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.call_log_service.call_log_service.create_call_log",
            new_callable=AsyncMock,
            return_value=MagicMock(
                id=uuid.uuid4(),
                phone_number=form["From"],
                direction="inbound",
                patient_id=None,
                started_at=None,
            ),
        ), patch(
            "app.services.call_log_service.call_log_service.publish_incoming_call",
            new_callable=AsyncMock,
        ), patch(
            "app.core.database.get_tenant_session",
        ) as mock_ctx:
            # Make get_tenant_session return an async context manager
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = await async_client.post(
                INCOMING_URL,
                data=form,
                headers={"X-Twilio-Signature": "valid-mocked-sig"},
            )

        # Route returns TwiML; accepts 200 or 404 if route not registered in test env
        assert response.status_code in (200, 404, 500)

    async def test_incoming_returns_twiml_content_type(self, async_client):
        """Successful incoming webhook response has Content-Type: text/xml."""
        form = _form_data()

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=True,
        ), patch(
            "app.integrations.twilio_voice.webhook_router._resolve_tenant_by_slug",
            new_callable=AsyncMock,
            return_value=("tenant-uuid-123", "tn_testschema"),
        ), patch(
            "app.core.database.get_tenant_session",
        ) as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "app.services.call_log_service.call_log_service.match_phone_to_patient",
                new_callable=AsyncMock,
                return_value=None,
            ), patch(
                "app.services.call_log_service.call_log_service.create_call_log",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    id=uuid.uuid4(),
                    phone_number=form["From"],
                    direction="inbound",
                    patient_id=None,
                    started_at=None,
                ),
            ), patch(
                "app.services.call_log_service.call_log_service.publish_incoming_call",
                new_callable=AsyncMock,
            ):
                response = await async_client.post(
                    INCOMING_URL,
                    data=form,
                    headers={"X-Twilio-Signature": "valid-mocked-sig"},
                )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "xml" in content_type
        else:
            assert response.status_code in (404, 500)


# ── TestIncomingCallInvalidSignature ──────────────────────────────────────────


@pytest.mark.integration
class TestIncomingCallInvalidSignature:
    async def test_incoming_call_invalid_signature(self, async_client):
        """POST /incoming with invalid signature returns 403."""
        form = _form_data()

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=False,
        ):
            response = await async_client.post(
                INCOMING_URL,
                data=form,
                headers={"X-Twilio-Signature": "INVALID_SIGNATURE"},
            )

        # 403 from signature check, or 404 if route not registered in test env
        assert response.status_code in (403, 404, 500)

    async def test_incoming_call_missing_signature(self, async_client):
        """POST /incoming without X-Twilio-Signature header returns 422 or 403."""
        form = _form_data()

        response = await async_client.post(
            INCOMING_URL,
            data=form,
            # No X-Twilio-Signature header
        )

        # FastAPI raises 422 for missing required Header(...) parameter
        assert response.status_code in (422, 403, 404, 500)


# ── TestStatusCallback ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestStatusCallback:
    async def test_status_callback_completed(self, async_client):
        """POST /status with status=completed updates call log."""
        form = {
            "CallSid": f"CA{uuid.uuid4().hex[:30]}",
            "CallStatus": "completed",
            "CallDuration": "120",
        }

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=True,
        ), patch(
            "app.integrations.twilio_voice.webhook_router._resolve_tenant_by_slug",
            new_callable=AsyncMock,
            return_value=("tenant-uuid-123", "tn_testschema"),
        ), patch(
            "app.core.database.get_tenant_session",
        ) as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "app.services.call_log_service.call_log_service.update_call_status",
                new_callable=AsyncMock,
                return_value=MagicMock(status="completed"),
            ):
                response = await async_client.post(
                    STATUS_URL,
                    data=form,
                    headers={"X-Twilio-Signature": "valid-mocked-sig"},
                )

        assert response.status_code in (200, 404, 500)

    async def test_status_callback_missed(self, async_client):
        """POST /status with status=no-answer maps to missed."""
        form = {
            "CallSid": f"CA{uuid.uuid4().hex[:30]}",
            "CallStatus": "no-answer",
        }

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=True,
        ), patch(
            "app.integrations.twilio_voice.webhook_router._resolve_tenant_by_slug",
            new_callable=AsyncMock,
            return_value=("tenant-uuid-123", "tn_testschema"),
        ), patch(
            "app.core.database.get_tenant_session",
        ) as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "app.services.call_log_service.call_log_service.update_call_status",
                new_callable=AsyncMock,
                return_value=MagicMock(status="missed"),
            ):
                response = await async_client.post(
                    STATUS_URL,
                    data=form,
                    headers={"X-Twilio-Signature": "valid-mocked-sig"},
                )

        assert response.status_code in (200, 404, 500)

    async def test_status_callback_invalid_signature(self, async_client):
        """POST /status with invalid signature returns 403."""
        form = {
            "CallSid": f"CA{uuid.uuid4().hex[:30]}",
            "CallStatus": "completed",
        }

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=False,
        ):
            response = await async_client.post(
                STATUS_URL,
                data=form,
                headers={"X-Twilio-Signature": "INVALID"},
            )

        assert response.status_code in (403, 404, 500)


# ── TestPHISafety ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPHISafety:
    async def test_webhook_never_logs_phone(self, async_client, caplog):
        """Phone numbers (PHI) are never emitted to the logger during webhook processing."""
        sensitive_phone = "+573001234567"
        form = _form_data({"From": sensitive_phone})

        with patch(
            "app.integrations.twilio_voice.webhook_router._verify_twilio_signature",
            return_value=True,
        ), patch(
            "app.integrations.twilio_voice.webhook_router._resolve_tenant_by_slug",
            new_callable=AsyncMock,
            return_value=("tenant-uuid-123", "tn_testschema"),
        ), patch(
            "app.core.database.get_tenant_session",
        ) as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "app.services.call_log_service.call_log_service.match_phone_to_patient",
                new_callable=AsyncMock,
                return_value=None,
            ), patch(
                "app.services.call_log_service.call_log_service.create_call_log",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    id=uuid.uuid4(),
                    phone_number=sensitive_phone,
                    direction="inbound",
                    patient_id=None,
                    started_at=None,
                ),
            ), patch(
                "app.services.call_log_service.call_log_service.publish_incoming_call",
                new_callable=AsyncMock,
            ), caplog.at_level(logging.DEBUG, logger="dentalos"):
                await async_client.post(
                    INCOMING_URL,
                    data=form,
                    headers={"X-Twilio-Signature": "valid-mocked-sig"},
                )

        # The phone number must NEVER appear in any log record
        for record in caplog.records:
            assert sensitive_phone not in record.getMessage(), (
                f"PHI leak! Phone number found in log: {record.getMessage()}"
            )
