"""Mercado Pago payment gateway — production implementation (INT-07).

Integrates with the Mercado Pago Checkout API to:
  - Create one-time checkout preferences (invoice payments)
  - Create recurring subscriptions via the Preapproval API
  - Query payment status for IPN reconciliation
  - Verify HMAC-SHA256 webhook signatures

API reference:
  https://www.mercadopago.com/developers/en/reference

Security:
  - Access token is read from settings and sent as Bearer header — never logged
  - Payer email is PHI — never logged in any method
  - Webhook signatures use timing-safe HMAC-SHA256 comparison
  - All HTTP calls use explicit 30-second timeouts
  - external_reference encodes tenant_id:invoice_id for IPN routing without DB lookups
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.payments.mercadopago_base import MercadoPagoServiceBase
from app.integrations.payments.mercadopago_schemas import (
    PaymentStatusResult,
    PreferenceResult,
    SubscriptionResult,
)

logger = logging.getLogger("dentalos.integrations.mercadopago")

_MP_BASE_URL = "https://api.mercadopago.com"

# API path constants
_PREFERENCES_PATH = "/checkout/preferences"
_PREAPPROVAL_PATH = "/preapproval"
_PAYMENTS_PATH = "/v1/payments"

# Mercado Pago x-signature header format: "ts=<epoch>,v1=<hex_digest>"
# We accept either the full "v1=<hex>" compound format or a bare hex digest
# for forward-compatibility with simpler test environments.
_SIGNATURE_V1_PREFIX = "v1="


class MercadoPagoService(MercadoPagoServiceBase):
    """Production Mercado Pago integration using the Checkout and Preapproval APIs.

    A lazily-initialized httpx.AsyncClient is shared across requests to
    benefit from HTTP/1.1 keep-alive connection pooling. The client is
    closed via ``close()`` during application shutdown.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True when a Mercado Pago access token is configured."""
        return bool(settings.mercadopago_access_token)

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_MP_BASE_URL,
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    def _auth_headers(self) -> dict[str, str]:
        """Build the authorization headers required by all MP API calls."""
        return {
            "Authorization": f"Bearer {settings.mercadopago_access_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Checkout preference (one-time payment)
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
        """Create a Mercado Pago checkout preference for a one-time payment.

        The external_reference is set to ``{tenant_id}:{invoice_id}`` so that
        IPN webhook handlers can identify the invoice without requiring
        authentication or an extra DB lookup on the inbound path.

        MP expects the unit_price in the full currency unit (not cents), so
        we convert by dividing by 100.

        Args:
            tenant_id: DentalOS tenant identifier.
            invoice_id: UUID of the invoice being paid.
            amount_cents: Payment amount in cents.
            description: Short description shown on the MP checkout page (no PHI).
            payer_email: Payer email pre-filled in MP checkout — PHI, never logged.
            callback_url: MP redirects here after payment completion/failure.

        Returns:
            PreferenceResult with preference_id, init_point, sandbox_init_point.

        Raises:
            RuntimeError: If the service is not configured.
            httpx.HTTPStatusError: On Mercado Pago API error (non-2xx response).
        """
        if not self.is_configured():
            raise RuntimeError(
                "Mercado Pago is not configured. "
                "Set MERCADOPAGO_ACCESS_TOKEN in the environment."
            )

        # Convert cents to full units (MP does not accept fractional amounts
        # for ARS/COP; we pass as float to allow future multi-currency support)
        unit_price = amount_cents / 100.0

        # external_reference encodes routing information for IPN callbacks
        external_reference = f"{tenant_id}:{invoice_id}"

        body: dict[str, Any] = {
            "items": [
                {
                    "title": description,
                    "quantity": 1,
                    "unit_price": unit_price,
                    "currency_id": "COP",
                }
            ],
            "payer": {
                "email": payer_email,
            },
            "external_reference": external_reference,
            "back_urls": {
                "success": callback_url,
                "failure": callback_url,
                "pending": callback_url,
            },
            "auto_return": "approved",
            # IPN notifications are handled by our webhook endpoint
            "notification_url": f"{settings.frontend_url}/api/v1/webhooks/mercadopago/ipn",
        }

        client = await self._get_client()
        response = await client.post(
            _PREFERENCES_PATH,
            json=body,
            headers=self._auth_headers(),
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = PreferenceResult(
            preference_id=data["id"],
            init_point=data["init_point"],
            sandbox_init_point=data.get("sandbox_init_point", data["init_point"]),
        )

        # Log only the first 8 chars of preference_id — no amounts, no emails
        logger.info(
            "MP preference created: preference_id=%s...",
            result.preference_id[:8] if result.preference_id else "unknown",
        )

        return result

    # ------------------------------------------------------------------
    # Recurring subscription (preapproval)
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
        """Create a Mercado Pago recurring subscription via the Preapproval API.

        Uses the /preapproval endpoint (not the legacy /checkout/preferences)
        to create a subscription that charges the payer on a recurring basis.
        The payer must authorize the subscription at the returned init_point.

        Frequency is expressed in months. MP requires ``frequency_type="months"``
        and ``frequency`` as the integer interval.

        Args:
            tenant_id: DentalOS tenant identifier (used in external_reference).
            plan_id: UUID of the DentalOS membership plan.
            payer_email: Patient's email — PHI, NEVER logged.
            amount_cents: Recurring charge in cents.
            frequency_months: Billing interval in months (1 = monthly, 12 = annual).

        Returns:
            SubscriptionResult with subscription_id, status, and init_point URL.

        Raises:
            RuntimeError: If the service is not configured.
            httpx.HTTPStatusError: On Mercado Pago API error.
        """
        if not self.is_configured():
            raise RuntimeError(
                "Mercado Pago is not configured. "
                "Set MERCADOPAGO_ACCESS_TOKEN in the environment."
            )

        transaction_amount = amount_cents / 100.0
        external_reference = f"{tenant_id}:{plan_id}"

        body: dict[str, Any] = {
            "reason": "DentalOS Membership",
            "external_reference": external_reference,
            "payer_email": payer_email,
            "auto_recurring": {
                "frequency": frequency_months,
                "frequency_type": "months",
                "transaction_amount": transaction_amount,
                "currency_id": "COP",
            },
            "back_url": settings.frontend_url,
            "status": "pending",
        }

        client = await self._get_client()
        response = await client.post(
            _PREAPPROVAL_PATH,
            json=body,
            headers=self._auth_headers(),
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = SubscriptionResult(
            subscription_id=data["id"],
            status=data.get("status", "pending"),
            init_point=data.get("init_point", ""),
        )

        logger.info(
            "MP subscription created: subscription_id=%s... status=%s",
            result.subscription_id[:8] if result.subscription_id else "unknown",
            result.status,
        )

        return result

    # ------------------------------------------------------------------
    # Payment status lookup
    # ------------------------------------------------------------------

    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> PaymentStatusResult:
        """Fetch full payment details for a given Mercado Pago payment ID.

        Called by the IPN webhook handler after receiving a notification.
        MP IPN only carries the resource ID, so we must fetch the full
        resource to learn the amount, status_detail, and external_reference.

        The payer email returned by MP is PHI — it is stored in the result
        schema but must NOT be logged by callers.

        Args:
            payment_id: MP payment identifier from the IPN data.id field.

        Returns:
            PaymentStatusResult with status, status_detail, amount_cents.

        Raises:
            RuntimeError: If the service is not configured.
            httpx.HTTPStatusError: On Mercado Pago API error (e.g. 404).
        """
        if not self.is_configured():
            raise RuntimeError(
                "Mercado Pago is not configured. "
                "Set MERCADOPAGO_ACCESS_TOKEN in the environment."
            )

        client = await self._get_client()
        response = await client.get(
            f"{_PAYMENTS_PATH}/{payment_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        # MP returns transaction_amount as a float; convert to cents
        transaction_amount = data.get("transaction_amount", 0.0)
        amount_cents = round(transaction_amount * 100)

        # payer is nested; email is PHI — extract but never log
        payer: dict[str, Any] = data.get("payer", {})
        payer_email: str | None = payer.get("email") or None

        result = PaymentStatusResult(
            payment_id=str(data.get("id", payment_id)),
            status=data.get("status", "unknown"),
            status_detail=data.get("status_detail", ""),
            amount_cents=amount_cents,
            payer_email=payer_email,
        )

        logger.info(
            "MP payment status fetched: payment_id=%s... status=%s status_detail=%s",
            str(payment_id)[:8],
            result.status,
            result.status_detail,
        )

        return result

    # ------------------------------------------------------------------
    # Webhook signature verification
    # ------------------------------------------------------------------

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA256 signature from a Mercado Pago IPN request.

        Mercado Pago sends the ``x-signature`` header in the compound format:
            ``ts=<epoch_milliseconds>,v1=<hex_digest>``

        We extract the hex digest portion (after ``v1=``) and compare it
        against an HMAC-SHA256 computed from the raw request body bytes
        and the configured ``mercadopago_webhook_secret``.

        Falls back gracefully to treating the whole ``signature`` string as a
        bare hex digest when the compound format is not detected — this covers
        simplified test environments and future format changes.

        Uses ``hmac.compare_digest`` to prevent timing-side-channel attacks.

        Args:
            payload: Raw HTTP request body bytes (before any JSON parsing).
            signature: Value of the ``x-signature`` header from Mercado Pago.

        Returns:
            True if the signature matches. False if the secret is not configured
            or the signature is invalid.
        """
        if not settings.mercadopago_webhook_secret:
            logger.warning(
                "MP webhook secret not configured — rejecting inbound webhook"
            )
            return False

        # Extract the v1 hex digest from the compound header value
        hex_digest = signature
        for part in signature.split(","):
            part = part.strip()
            if part.startswith(_SIGNATURE_V1_PREFIX):
                hex_digest = part[len(_SIGNATURE_V1_PREFIX):]
                break

        secret = settings.mercadopago_webhook_secret.encode("utf-8")
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

        is_valid = hmac.compare_digest(computed, hex_digest)

        if not is_valid:
            logger.warning("MP webhook signature verification failed")

        return is_valid

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client gracefully on shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# Module-level singleton — import and use this in routers and services
# ---------------------------------------------------------------------------
mercadopago_service = MercadoPagoService()
