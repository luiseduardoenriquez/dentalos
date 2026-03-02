"""Abstract base for ADRES / BDUA verification services — INT-ADRES."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.adres.schemas import ADRESVerificationResponse


class ADRESServiceBase(ABC):
    """Contract that all ADRES service implementations must satisfy.

    Implementations:
        ADRESService      — production, calls the real ADRES BDUA API.
        ADRESServiceMock  — development/testing, returns deterministic fixtures.
    """

    @abstractmethod
    async def verify_affiliation(
        self,
        *,
        document_type: str,
        document_number: str,
    ) -> ADRESVerificationResponse:
        """Look up a patient's EPS affiliation in the ADRES BDUA registry.

        Args:
            document_type: Colombian document type code (CC, TI, CE, PA, RC, MS).
            document_number: The document number to query. PHI — never log this.

        Returns:
            ADRESVerificationResponse with affiliation details.

        Raises:
            httpx.HTTPStatusError: On non-2xx response from ADRES API.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the service has the credentials needed to make API calls."""
        ...
