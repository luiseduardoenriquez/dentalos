"""Mock Mercado Pago service for local development and automated testing.

Returns deterministic fake data so that payment flows can be exercised
end-to-end without real MP credentials or network calls. This service is
automatically selected when ``MERCADOPAGO_ACCESS_TOKEN`` is empty.

Payment IDs are derived from the input arguments via SHA-256 to ensure
idempotency: the same inputs always produce the same mock ID. This is
useful for integration tests that need to re-query a payment by ID.

Security:
  - No real API calls are made.
  - verify_webhook() always returns True in mock mode.
  - Payer emails are accepted but never stored or logged.
"""

from __future__ import annotations

import hashlib
import logging

from app.integrations.payments.mercadopago_base import MercadoPagoServiceBase
from app.integrations.payments.mercadopago_schemas import (
    PaymentStatusResult,
    PreferenceResult,
    SubscriptionResult,
)

logger = logging.getLogger("dentalos.integrations.mercadopago.mock")

_SANDBOX_CHECKOUT_URL = "https://sandbox.mercadopago.com/checkout/test"


def _deterministic_id(seed: str, prefix: str = "mock") -> str:
    """Return a deterministic fake ID derived from ``seed`` via SHA-256.

    The first 16 hex characters of the hash are used to keep IDs short
    while still being unique per seed value.

    Args:
        seed: Arbitrary string used as hash input.
        prefix: Prepended to the hex fragment for readability.

    Returns:
        A string of the form ``{prefix}_{16-hex-chars}``.
    """
    hex_fragment = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{hex_fragment}"


class MercadoPagoMockService(MercadoPagoServiceBase):
    """Fake Mercado Pago service for development and test environments.

    All methods return plausible-looking fake data without making HTTP calls.
    This allows UI flows, background workers, and integration tests to run
    against a predictable, offline implementation of the MP contract.
    """

    def is_configured(self) -> bool:
        """Mock is always considered configured — no credentials required."""
        return True

    # ------------------------------------------------------------------
    # Checkout preference
    # ------------------------------------------------------------------

    async def create_preference(
        self,
        *,
        tenant_id: str,
        invoice_id: str,
        amount_cents: int,
        description: str,
        payer_email: str,
        callback_url: str,
    ) -> PreferenceResult:
        """Return a fake checkout preference.

        The preference_id is deterministic based on tenant_id + invoice_id
        so that the same invoice always yields the same mock preference.
        payer_email is accepted but not stored or logged.

        Args:
            tenant_id: DentalOS tenant identifier.
            invoice_id: UUID of the invoice being paid.
            amount_cents: Payment amount in cents (unused in mock).
            description: Payment description (unused in mock).
            payer_email: Patient email — accepted, never logged.
            callback_url: Redirect URL after payment (unused in mock).

        Returns:
            PreferenceResult with mock preference_id and sandbox init_point.
        """
        seed = f"{tenant_id}:{invoice_id}"
        preference_id = _deterministic_id(seed, prefix="pref")

        result = PreferenceResult(
            preference_id=preference_id,
            init_point=f"{_SANDBOX_CHECKOUT_URL}/{preference_id}",
            sandbox_init_point=f"{_SANDBOX_CHECKOUT_URL}/{preference_id}",
        )

        logger.info(
            "Mock MP preference created: preference_id=%s...",
            preference_id[:8],
        )

        return result

    # ------------------------------------------------------------------
    # Recurring subscription
    # ------------------------------------------------------------------

    async def create_subscription(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        payer_email: str,
        amount_cents: int,
        frequency_months: int,
    ) -> SubscriptionResult:
        """Return a fake subscription (preapproval) result.

        The subscription always starts as 'authorized' in the mock so that
        test flows can proceed past the authorization gate without user
        interaction. payer_email is accepted but not stored or logged.

        Args:
            tenant_id: DentalOS tenant identifier.
            plan_id: UUID of the DentalOS membership plan.
            payer_email: Patient email — accepted, never logged.
            amount_cents: Recurring charge in cents (unused in mock).
            frequency_months: Billing interval in months (unused in mock).

        Returns:
            SubscriptionResult with mock subscription_id, status='authorized'.
        """
        seed = f"{tenant_id}:{plan_id}"
        subscription_id = _deterministic_id(seed, prefix="sub")

        result = SubscriptionResult(
            subscription_id=subscription_id,
            status="authorized",
            init_point=f"{_SANDBOX_CHECKOUT_URL}/subscription/{subscription_id}",
        )

        logger.info(
            "Mock MP subscription created: subscription_id=%s... status=%s",
            subscription_id[:8],
            result.status,
        )

        return result

    # ------------------------------------------------------------------
    # Payment status
    # ------------------------------------------------------------------

    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> PaymentStatusResult:
        """Return a mock payment status.

        Payments whose ID starts with ``mock_`` are reported as ``approved``.
        All other IDs (e.g. raw numeric strings from tests) are reported as
        ``pending``. This lets tests exercise both success and in-progress flows
        by choosing IDs appropriately.

        Args:
            payment_id: MP payment identifier to query.

        Returns:
            PaymentStatusResult with fake status and a fixed amount.
        """
        is_approved = payment_id.startswith("mock_")
        status = "approved" if is_approved else "pending"
        status_detail = "accredited" if is_approved else "pending_contingency"

        result = PaymentStatusResult(
            payment_id=payment_id,
            status=status,
            status_detail=status_detail,
            amount_cents=50_000_00,  # 50,000 COP in cents
            payer_email=None,  # Never return PHI from mock
        )

        logger.info(
            "Mock MP payment status queried: payment_id=%s... status=%s",
            str(payment_id)[:8],
            status,
        )

        return result

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Always return True in mock mode.

        In development environments there is no real MP webhook secret, so
        signature verification is bypassed entirely. This must NEVER be used
        in production.

        Args:
            payload: Raw request body bytes (ignored).
            signature: Signature header value (ignored).

        Returns:
            True always.
        """
        return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
mercadopago_mock_service = MercadoPagoMockService()
