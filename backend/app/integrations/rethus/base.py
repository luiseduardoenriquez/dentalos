"""Abstract base for RETHUS professional registry verification services — INT-RETHUS."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.rethus.schemas import RETHUSVerificationResponse


class RETHUSServiceBase(ABC):
    """Contract that all RETHUS service implementations must satisfy.

    Implementations:
        RETHUSService      — production, queries the datos.gov.co Socrata API.
        RETHUSServiceMock  — development/testing, returns deterministic fixtures.
    """

    @abstractmethod
    async def verify_professional(
        self,
        *,
        rethus_number: str,
    ) -> RETHUSVerificationResponse:
        """Look up a healthcare professional in the RETHUS registry.

        Args:
            rethus_number: The RETHUS registration number to query.

        Returns:
            RETHUSVerificationResponse with professional details.

        Raises:
            httpx.HTTPStatusError: On non-2xx response from datos.gov.co.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the service has the credentials needed to make API calls."""
        ...
