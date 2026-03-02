"""Unit tests for the DaviplataServiceMock class.

Tests cover:
  - generate_qr_payment: returns a valid DaviplataQRResponse
  - get_payment_status (completed): payment_id starting with "mock_" → completed
  - get_payment_status (pending): payment_id NOT starting with "mock_" → pending
  - verify_webhook_signature (valid): mock always returns True
  - verify_webhook_signature (invalid): mock always returns True (dev mode)

Note: These tests exercise the mock adapter directly. The production adapter
requires live Daviplata credentials and is covered by integration/e2e tests.
"""

import hashlib
from datetime import UTC, datetime

import pytest

from app.integrations.daviplata.mock_service import DaviplataServiceMock


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_mock() -> DaviplataServiceMock:
    """Return a fresh DaviplataServiceMock instance."""
    return DaviplataServiceMock()


# ── generate_qr_payment ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateQrPayment:
    async def test_generate_qr_payment_returns_valid_response(self):
        """generate_qr_payment should return a DaviplataQRResponse with expected fields."""
        mock = _make_mock()

        result = await mock.generate_qr_payment(
            amount_cents=200_000,
            reference="abc123:some-ref",
            description="DentalOS Invoice INV-002",
        )

        assert result.payment_id.startswith("mock_")
        assert result.status == "pending"
        assert "mock.daviplata.local" in result.qr_code_url
        assert result.expires_at is not None

    async def test_generate_qr_payment_payment_id_is_deterministic(self):
        """Same reference always produces the same payment_id (SHA-256 derived)."""
        mock = _make_mock()
        reference = "tenant02:invoice-uuid"

        result_a = await mock.generate_qr_payment(
            amount_cents=100_000,
            reference=reference,
            description="Pago de prueba",
        )
        result_b = await mock.generate_qr_payment(
            amount_cents=300_000,  # different amount — must not affect ID
            reference=reference,
            description="Otro pago",
        )

        assert result_a.payment_id == result_b.payment_id

    async def test_generate_qr_payment_different_references_produce_different_ids(self):
        """Different references should produce different payment IDs."""
        mock = _make_mock()

        result_a = await mock.generate_qr_payment(
            amount_cents=100_000,
            reference="tenant02:invoice-aaa",
            description="Pago A",
        )
        result_b = await mock.generate_qr_payment(
            amount_cents=100_000,
            reference="tenant02:invoice-bbb",
            description="Pago B",
        )

        assert result_a.payment_id != result_b.payment_id

    async def test_generate_qr_payment_expires_at_is_future(self):
        """expires_at must be in the future (15 min from now)."""
        mock = _make_mock()

        result = await mock.generate_qr_payment(
            amount_cents=50_000,
            reference="t3:ref-xyz",
            description="Prueba expiración",
        )

        assert result.expires_at > datetime.now(UTC)

    async def test_generate_qr_payment_qr_url_contains_payment_id(self):
        """The qr_code_url should embed the payment_id."""
        mock = _make_mock()

        result = await mock.generate_qr_payment(
            amount_cents=80_000,
            reference="t4:ref-def",
            description="Prueba URL",
        )

        assert result.payment_id in result.qr_code_url


# ── get_payment_status ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetPaymentStatusCompleted:
    async def test_payment_id_starting_with_mock_is_completed(self):
        """payment_id starting with 'mock_' should yield status 'completed'."""
        mock = _make_mock()

        result = await mock.get_payment_status(payment_id="mock_abc123def456")

        assert result.status == "completed"

    async def test_completed_payment_has_completed_at_timestamp(self):
        """A completed payment should have a non-None completed_at."""
        mock = _make_mock()

        result = await mock.get_payment_status(payment_id="mock_abc123def456")

        assert result.completed_at is not None

    async def test_completed_payment_returns_correct_payment_id(self):
        """Returned payment_id must match the queried one."""
        mock = _make_mock()
        payment_id = "mock_ffffffffffffffff"

        result = await mock.get_payment_status(payment_id=payment_id)

        assert result.payment_id == payment_id


@pytest.mark.unit
class TestGetPaymentStatusPending:
    async def test_payment_id_not_starting_with_mock_is_pending(self):
        """payment_id NOT starting with 'mock_' should yield status 'pending'."""
        mock = _make_mock()

        result = await mock.get_payment_status(payment_id="live_abc123")

        assert result.status == "pending"

    async def test_pending_payment_has_no_completed_at(self):
        """A pending payment should have completed_at == None."""
        mock = _make_mock()

        result = await mock.get_payment_status(payment_id="pending_xyz789")

        assert result.completed_at is None

    async def test_pending_payment_has_positive_amount_cents(self):
        """amount_cents returned by the mock must be a positive integer."""
        mock = _make_mock()

        result = await mock.get_payment_status(payment_id="other_id")

        assert result.amount_cents > 0


# ── verify_webhook_signature ──────────────────────────────────────────────────


@pytest.mark.unit
class TestVerifyWebhookSignature:
    def test_verify_webhook_signature_valid_returns_true(self):
        """Mock always returns True regardless of payload/signature (dev mode)."""
        mock = _make_mock()

        payload = b'{"event_type": "payment.completed", "payment_id": "mock_abc"}'
        signature = hashlib.sha256(b"secret" + payload).hexdigest()

        result = mock.verify_webhook_signature(payload, signature)

        assert result is True

    def test_verify_webhook_signature_invalid_still_returns_true_in_mock(self):
        """In dev/mock mode, even an invalid signature should return True.

        This is by design: the mock never enforces HMAC so developers can
        fire test webhooks without computing real signatures.
        """
        mock = _make_mock()

        payload = b'{"event_type": "payment.completed"}'
        invalid_signature = "definitely-not-a-valid-hmac"

        result = mock.verify_webhook_signature(payload, invalid_signature)

        assert result is True

    def test_verify_webhook_signature_empty_payload_returns_true(self):
        """Even an empty payload should return True in mock mode."""
        mock = _make_mock()

        result = mock.verify_webhook_signature(b"", "any-signature")

        assert result is True
