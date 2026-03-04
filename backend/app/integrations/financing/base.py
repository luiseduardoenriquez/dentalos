"""Abstract base class for patient financing provider integrations.

Defines the contract that both the production service and mock service
must implement. This enables seamless swapping between real and fake
financing backends via dependency injection or feature flags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.financing.schemas import (
    ApplicationResult,
    ApplicationStatusResult,
    EligibilityResult,
)


class FinancingProviderBase(ABC):
    """Contract for patient financing provider operations."""

    @abstractmethod
    async def check_eligibility(
        self,
        *,
        patient_document: str,
        amount_cents: int,
    ) -> EligibilityResult:
        """Check if a patient is eligible for financing a given amount.

        Args:
            patient_document: Patient's national document number (e.g. cedula).
            amount_cents: Requested financing amount in COP cents.

        Returns:
            EligibilityResult with eligibility flag, limits, and installment options.
        """
        ...

    @abstractmethod
    async def create_application(
        self,
        *,
        patient_document: str,
        amount_cents: int,
        installments: int,
        reference: str,
        callback_url: str,
    ) -> ApplicationResult:
        """Submit a new financing application with the provider.

        Args:
            patient_document: Patient's national document number.
            amount_cents: Financing amount in COP cents.
            installments: Requested number of monthly installments.
            reference: Unique DentalOS financing reference (e.g. application UUID).
            callback_url: URL the provider calls on status changes.

        Returns:
            ApplicationResult with provider reference, status, and redirect URL.
        """
        ...

    @abstractmethod
    async def get_status(
        self,
        *,
        provider_reference: str,
    ) -> ApplicationStatusResult:
        """Query the current status of a financing application.

        Args:
            provider_reference: The provider-assigned application identifier.

        Returns:
            ApplicationStatusResult with current state and optional approved amount.
        """
        ...

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA256 signature on a provider webhook request.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Signature header value from the provider.

        Returns:
            True if the signature is valid and timing-safe comparison passes.
        """
        ...
