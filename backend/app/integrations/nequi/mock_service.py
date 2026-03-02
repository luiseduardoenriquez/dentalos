"""Mock Nequi service for local development and testing.

Returns deterministic fake data so that the payment flow can be exercised
end-to-end without real Nequi credentials. Automatically selected when
Nequi env vars are empty.

Security:
  - verify_webhook_signature() always returns True in dev mode
  - No real API calls are made
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from app.integrations.nequi.base import NequiServiceBase
from app.integrations.nequi.schemas import NequiPaymentStatus, NequiQRResponse

logger = logging.getLogger("dentalos.integrations.nequi.mock")


class NequiServiceMock(NequiServiceBase):
    """Fake Nequi service for development environments."""

    def is_configured(self) -> bool:
        """Mock is always considered configured."""
        return True

    async def generate_qr_payment(
        self,
        *,
        amount_cents: int,
        reference: str,
        description: str,
    ) -> NequiQRResponse:
        """Return a fake QR payment response.

        The payment_id is deterministic, derived from the reference using
        SHA-256 so that the same reference always produces the same mock
        payment_id (useful for idempotency testing).

        Args:
            amount_cents: Payment amount in COP cents.
            reference: DentalOS payment reference.
            description: Payment description (unused in mock).

        Returns:
            NequiQRResponse with mock data.
        """
        # Deterministic mock payment ID based on reference
        reference_hash = hashlib.sha256(reference.encode("utf-8")).hexdigest()[:16]
        payment_id = f"mock_{reference_hash}"

        result = NequiQRResponse(
            qr_code_url=f"https://mock.nequi.local/qr/{payment_id}",
            payment_id=payment_id,
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

        logger.info(
            "Mock Nequi QR generated: payment_id=%s...",
            payment_id[:8],
        )

        return result

    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> NequiPaymentStatus:
        """Return mock payment status.

        Payment IDs starting with "mock_" are reported as "completed".
        All other IDs are reported as "pending". This allows testing
        both success and in-progress flows.

        Args:
            payment_id: Payment identifier to query.

        Returns:
            NequiPaymentStatus with mock data.
        """
        is_completed = payment_id.startswith("mock_")
        status = "completed" if is_completed else "pending"

        result = NequiPaymentStatus(
            payment_id=payment_id,
            status=status,
            amount_cents=100_00,  # Default 100 COP in cents
            reference="mock_reference",
            completed_at=datetime.now(UTC) if is_completed else None,
        )

        logger.info(
            "Mock Nequi status queried: payment_id=%s... status=%s",
            payment_id[:8],
            status,
        )

        return result

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Always returns True in mock mode.

        Args:
            payload: Raw request body (ignored).
            signature: Signature header value (ignored).

        Returns:
            True always.
        """
        return True

    async def close(self) -> None:
        """No-op for mock service."""


# Module-level singleton
nequi_service_mock = NequiServiceMock()
