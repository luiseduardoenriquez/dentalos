"""Abstract base class for the Mercado Pago payment service.

Defines the contract that both the production service and mock service
must implement. This pattern enables seamless swapping between real and fake
Mercado Pago backends via dependency injection or environment-based selection.

Two core flows are supported:
  1. One-time checkout preference  — invoice payment via redirect
  2. Recurring subscription (preapproval) — patient membership billing

Webhook verification is also part of the contract to ensure both
implementations validate IPN signatures consistently.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.payments.mercadopago_schemas import (
    PaymentStatusResult,
    PreferenceResult,
    SubscriptionResult,
)


class MercadoPagoServiceBase(ABC):
    """Contract for Mercado Pago checkout and subscription operations."""

    # ------------------------------------------------------------------
    # Checkout preference (one-time payment)
    # ------------------------------------------------------------------

    @abstractmethod
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

        Generates a preference object on the MP API which includes a hosted
        checkout URL (init_point) the patient can be redirected to.

        The ``external_reference`` stored in the preference is set to
        ``{tenant_id}:{invoice_id}`` so that incoming IPN notifications can
        be routed back to the correct tenant and invoice without any
        database lookups on an unauthenticated path.

        Args:
            tenant_id: DentalOS tenant identifier (used in external_reference).
            invoice_id: UUID of the invoice being paid.
            amount_cents: Payment amount in cents (COP or configured currency).
            description: Human-readable description shown on MP checkout (no PHI).
            payer_email: Patient's email address for MP pre-fill — NEVER logged.
            callback_url: URL MP redirects to after payment completion.

        Returns:
            PreferenceResult with the preference ID and checkout URLs.

        Raises:
            httpx.HTTPStatusError: On Mercado Pago API failure.
            RuntimeError: If the service is not configured.
        """
        ...

    # ------------------------------------------------------------------
    # Recurring subscription (preapproval)
    # ------------------------------------------------------------------

    @abstractmethod
    async def create_subscription(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        payer_email: str,
        amount_cents: int,
        frequency_months: int,
    ) -> SubscriptionResult:
        """Create a Mercado Pago recurring subscription (preapproval).

        Uses MP's /preapproval API to set up automatic recurring charges for
        a patient's clinic membership plan. The patient must authorize the
        subscription via the returned init_point URL before charges begin.

        Args:
            tenant_id: DentalOS tenant identifier.
            plan_id: UUID of the DentalOS membership plan.
            payer_email: Patient's email address — NEVER logged.
            amount_cents: Recurring charge amount in cents.
            frequency_months: Billing interval in months (1 = monthly, 12 = annual).

        Returns:
            SubscriptionResult with subscription ID, initial status, and init URL.

        Raises:
            httpx.HTTPStatusError: On Mercado Pago API failure.
            RuntimeError: If the service is not configured.
        """
        ...

    # ------------------------------------------------------------------
    # Payment status lookup
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> PaymentStatusResult:
        """Fetch the current status of a Mercado Pago payment.

        Used by the webhook handler to retrieve full payment details after
        receiving an IPN notification that only contains the payment ID.

        Args:
            payment_id: Mercado Pago-assigned payment identifier.

        Returns:
            PaymentStatusResult with status, status_detail, and amount.

        Raises:
            httpx.HTTPStatusError: On Mercado Pago API failure.
            RuntimeError: If the service is not configured.
        """
        ...

    # ------------------------------------------------------------------
    # Webhook signature verification
    # ------------------------------------------------------------------

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA256 signature on a Mercado Pago IPN request.

        Mercado Pago signs webhook payloads with the configured webhook secret
        using HMAC-SHA256 and sends the hex digest in the
        ``x-signature`` header (format: ``ts=<timestamp>,v1=<hex_digest>``).

        This method must use a timing-safe comparison to prevent timing attacks.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Value of the ``x-signature`` header from Mercado Pago.

        Returns:
            True if the signature is valid and the webhook secret is configured.
            False if the signature is invalid or the secret is not set.
        """
        ...
