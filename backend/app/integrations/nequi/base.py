"""Abstract base class for the Nequi payment service.

Defines the contract that both the production service and mock service
must implement. This enables seamless swapping between real and fake
Nequi backends via dependency injection or feature flags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.nequi.schemas import NequiPaymentStatus, NequiQRResponse


class NequiServiceBase(ABC):
    """Contract for Nequi QR payment operations."""

    @abstractmethod
    async def generate_qr_payment(
        self,
        *,
        amount_cents: int,
        reference: str,
        description: str,
    ) -> NequiQRResponse:
        """Generate a Nequi QR code for push payment collection.

        Args:
            amount_cents: Payment amount in Colombian pesos * 100.
            reference: Unique DentalOS payment reference (e.g. invoice ID).
            description: Human-readable payment description (no PHI).

        Returns:
            NequiQRResponse with QR URL, payment ID, and expiry.
        """
        ...

    @abstractmethod
    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> NequiPaymentStatus:
        """Query the current status of a Nequi payment.

        Args:
            payment_id: Nequi-assigned payment identifier.

        Returns:
            NequiPaymentStatus with current state and details.
        """
        ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA256 signature on a Nequi webhook request.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Value of the X-Nequi-Signature header.

        Returns:
            True if the signature is valid and timing-safe comparison passes.
        """
        ...
