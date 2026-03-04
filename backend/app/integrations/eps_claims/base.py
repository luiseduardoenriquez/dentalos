"""Abstract base for EPS claims submission services -- VP-19 / Sprint 31-32.

Defines the contract that both the production EPS claims API client and the
development mock must satisfy.  Callers always program to this interface so
that switching from mock to production requires only a one-line change in the
service layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.eps_claims.schemas import (
    EPSClaimStatusResponse,
    EPSClaimSubmitRequest,
    EPSClaimSubmitResponse,
)


class EPSClaimsServiceBase(ABC):
    """Contract for EPS claims submission implementations.

    Implementations:
        EPSClaimsService      — production, calls the real EPS claims REST API.
        EPSClaimsMockService  — development/testing, returns deterministic fixtures.
    """

    @abstractmethod
    async def submit_claim(
        self, *, claim_data: dict
    ) -> EPSClaimSubmitResponse:
        """Submit a new claim to the EPS provider.

        Args:
            claim_data: Claim payload dict. Will be coerced to EPSClaimSubmitRequest
                        internally by each implementation.

        Returns:
            EPSClaimSubmitResponse with the external claim ID and initial status.

        Raises:
            httpx.HTTPStatusError: On non-2xx response from the EPS API.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        ...

    @abstractmethod
    async def get_claim_status(
        self, *, external_claim_id: str
    ) -> EPSClaimStatusResponse:
        """Query the current status of a previously submitted claim.

        Args:
            external_claim_id: Identifier assigned by the EPS system at submission.

        Returns:
            EPSClaimStatusResponse with current status and optional paid amount.

        Raises:
            httpx.HTTPStatusError: On non-2xx response from the EPS API.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the service has all credentials needed to make API calls."""
        ...
