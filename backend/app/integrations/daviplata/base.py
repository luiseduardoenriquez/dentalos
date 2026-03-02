"""Abstract base class for the Daviplata payment service.

Defines the contract that both the production service and mock service
must implement. This enables seamless swapping between real and fake
Daviplata backends via dependency injection or feature flags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.daviplata.schemas import (
    DaviplataPaymentStatus,
    DaviplataQRResponse,
)


class DaviplataServiceBase(ABC):
    """Contract for Daviplata QR payment operations."""

    @abstractmethod
    async def generate_qr_payment(
        self,
        *,
        amount_cents: int,
        reference: str,
        description: str,
    ) -> DaviplataQRResponse:
        """Generate a Daviplata QR code for payment collection.

        Args:
            amount_cents: Payment amount in Colombian pesos * 100.
            reference: Unique DentalOS payment reference (e.g. invoice ID).
            description: Human-readable payment description (no PHI).

        Returns:
            DaviplataQRResponse with QR URL, payment ID, and expiry.
        """
        ...

    @abstractmethod
    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> DaviplataPaymentStatus:
        """Query the current status of a Daviplata payment.

        Args:
            payment_id: Daviplata-assigned payment identifier.

        Returns:
            DaviplataPaymentStatus with current state and details.
        """
        ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA256 signature on a Daviplata webhook request.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Value of the X-Daviplata-Signature header.

        Returns:
            True if the signature is valid and timing-safe comparison passes.
        """
        ...
