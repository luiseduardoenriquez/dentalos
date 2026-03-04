"""Mock Sistecrédito financing service for local development and testing.

Returns deterministic fake data so that the financing flow can be exercised
end-to-end without real Sistecrédito credentials. Automatically selected
when Sistecrédito env vars are empty.

Security:
  - verify_webhook() always returns True in dev mode
  - No real API calls are made
"""

from __future__ import annotations

import logging
import uuid

from app.integrations.financing.base import FinancingProviderBase
from app.integrations.financing.schemas import (
    ApplicationResult,
    ApplicationStatusResult,
    EligibilityResult,
)

logger = logging.getLogger("dentalos.integrations.financing.sistecredito.mock")

# Sistecrédito financing thresholds (in COP cents)
_MIN_AMOUNT_CENTS = 100_000  # COP 1,000
_MAX_AMOUNT_CENTS = 50_000_000  # COP 500,000

# Standard installment options offered by Sistecrédito in Colombia
_AVAILABLE_INSTALLMENTS = [6, 12, 18, 24, 36]


class SistecreditoMockService(FinancingProviderBase):
    """Fake Sistecrédito service for development environments."""

    def is_configured(self) -> bool:
        """Mock is always considered configured."""
        return True

    async def check_eligibility(
        self,
        *,
        patient_document: str,
        amount_cents: int,
    ) -> EligibilityResult:
        """Return mock eligibility result.

        Always eligible for amounts between 100,000 and 50,000,000 COP cents
        (COP 1,000 – COP 500,000). Returns not eligible with a reason if the
        amount is outside the mock range.

        Args:
            patient_document: Patient document number (used only for logging).
            amount_cents: Requested financing amount in COP cents.

        Returns:
            EligibilityResult with mock data.
        """
        in_range = _MIN_AMOUNT_CENTS <= amount_cents <= _MAX_AMOUNT_CENTS

        if in_range:
            result = EligibilityResult(
                eligible=True,
                max_amount_cents=_MAX_AMOUNT_CENTS,
                min_amount_cents=_MIN_AMOUNT_CENTS,
                available_installments=_AVAILABLE_INSTALLMENTS,
                reason=None,
            )
        else:
            result = EligibilityResult(
                eligible=False,
                max_amount_cents=_MAX_AMOUNT_CENTS,
                min_amount_cents=_MIN_AMOUNT_CENTS,
                available_installments=[],
                reason="Monto fuera del rango permitido por Sistecrédito.",
            )

        logger.info(
            "Mock Sistecrédito eligibility: eligible=%s document=%s...",
            result.eligible,
            patient_document[:4] if patient_document else "unknown",
        )

        return result

    async def create_application(
        self,
        *,
        patient_document: str,
        amount_cents: int,
        installments: int,
        reference: str,
        callback_url: str,
    ) -> ApplicationResult:
        """Return a fake credit application response.

        The provider_reference is a UUID4 string prefixed with "sc_mock_"
        to make it easy to identify in test scenarios.

        Args:
            patient_document: Patient document number (unused in mock).
            amount_cents: Financing amount in COP cents (unused in mock).
            installments: Number of installments (unused in mock).
            reference: DentalOS financing reference.
            callback_url: Callback URL (unused in mock).

        Returns:
            ApplicationResult with mock data.
        """
        provider_reference = f"sc_mock_{uuid.uuid4().hex[:16]}"

        result = ApplicationResult(
            provider_reference=provider_reference,
            status="pending",
            redirect_url=f"https://mock.sistecredito.com.co/credito/{provider_reference}",
        )

        logger.info(
            "Mock Sistecrédito application created: ref=%s...",
            provider_reference[:12],
        )

        return result

    async def get_status(
        self,
        *,
        provider_reference: str,
    ) -> ApplicationStatusResult:
        """Return mock application status.

        References starting with "sc_mock_" are reported as "approved".
        All other references are reported as "pending". This allows testing
        both success and in-progress flows.

        Args:
            provider_reference: Application identifier to query.

        Returns:
            ApplicationStatusResult with mock data.
        """
        from datetime import UTC, datetime

        is_approved = provider_reference.startswith("sc_mock_")
        status = "approved" if is_approved else "pending"

        result = ApplicationStatusResult(
            provider_reference=provider_reference,
            status=status,
            approved_amount_cents=3_000_000 if is_approved else None,  # COP 30,000 mock amount
            disbursed_at=datetime.now(UTC) if is_approved else None,
        )

        logger.info(
            "Mock Sistecrédito status queried: ref=%s... status=%s",
            provider_reference[:12],
            result.status,
        )

        return result

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Always returns True in mock mode.

        Args:
            payload: Raw request body (ignored).
            signature: Signature header value (ignored).

        Returns:
            True always.
        """
        return True


# Module-level singleton
sistecredito_mock_service = SistecreditoMockService()
