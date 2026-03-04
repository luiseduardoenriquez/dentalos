"""Production EPS claims submission service -- VP-19 / Sprint 31-32.

Calls the external EPS claims REST API using httpx with Bearer token
authentication.  Uses a lazily-initialized persistent async client so
the singleton can be imported at module level without requiring the
event loop to already be running.

Security:
  - eps_claims_api_key is NEVER logged.
  - patient_document_number (PHI) inside claim_data is NEVER logged.
  - All HTTP calls have a 30 s timeout for submission, 15 s for status queries.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.eps_claims.base import EPSClaimsServiceBase
from app.integrations.eps_claims.schemas import (
    EPSClaimStatusResponse,
    EPSClaimSubmitRequest,
    EPSClaimSubmitResponse,
)

logger = logging.getLogger("dentalos.integrations.eps_claims")

_SUBMIT_PATH = "/v1/claims"
_STATUS_PATH = "/v1/claims/{claim_id}/status"


class EPSClaimsService(EPSClaimsServiceBase):
    """Production EPS claims API client.

    Uses a lazily-initialized httpx.AsyncClient so the service can be
    instantiated at module load time without requiring the event loop.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return (or lazily create) the shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.eps_claims_api_url,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Bearer {settings.eps_claims_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    def is_configured(self) -> bool:
        """Return True if both api_url and api_key are configured."""
        return bool(settings.eps_claims_api_url and settings.eps_claims_api_key)

    async def submit_claim(self, *, claim_data: dict[str, Any]) -> EPSClaimSubmitResponse:
        """Submit a new claim to the EPS provider.

        Args:
            claim_data: Dict matching EPSClaimSubmitRequest schema.
                        Contains PHI (patient_document_number) — never log.

        Returns:
            EPSClaimSubmitResponse with external_claim_id and initial status.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP response.
            httpx.TimeoutException: If EPS API does not respond within 30 s.
        """
        # Validate via Pydantic before sending
        request = EPSClaimSubmitRequest(**claim_data)

        logger.info(
            "EPS claim submission: eps_code=%s claim_type=%s",
            request.eps_code,
            request.claim_type,
            # NOTE: patient_document_number intentionally omitted from all logs.
        )

        client = await self._get_client()
        response = await client.post(
            _SUBMIT_PATH,
            json=request.model_dump(),
        )
        response.raise_for_status()

        raw: dict[str, Any] = response.json()
        result = EPSClaimSubmitResponse(
            external_claim_id=raw.get("external_claim_id") or raw.get("claim_id", ""),
            status=raw.get("status", "submitted"),
            message=raw.get("message"),
        )

        logger.info(
            "EPS claim submitted: external_id=%s... status=%s",
            result.external_claim_id[:8],
            result.status,
        )

        return result

    async def get_claim_status(
        self, *, external_claim_id: str
    ) -> EPSClaimStatusResponse:
        """Query the current status of a previously submitted claim.

        Args:
            external_claim_id: EPS-assigned claim identifier.

        Returns:
            EPSClaimStatusResponse with current status and optional paid amount.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP response.
            httpx.TimeoutException: If EPS API does not respond within 15 s.
        """
        logger.info(
            "EPS claim status query: external_id=%s...",
            external_claim_id[:8],
        )

        client = await self._get_client()
        # Override timeout for status queries (lighter call)
        response = await client.get(
            _STATUS_PATH.format(claim_id=external_claim_id),
            timeout=15.0,
        )
        response.raise_for_status()

        raw: dict[str, Any] = response.json()
        result = EPSClaimStatusResponse(
            external_claim_id=external_claim_id,
            status=raw.get("status", "submitted"),
            paid_amount_cents=raw.get("paid_amount_cents"),
            error_message=raw.get("error_message") or raw.get("error"),
        )

        logger.info(
            "EPS claim status result: external_id=%s... status=%s",
            external_claim_id[:8],
            result.status,
        )

        return result

    async def close(self) -> None:
        """Close the underlying HTTP client (call on application shutdown)."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton — import this in services and route handlers.
eps_claims_service = EPSClaimsService()
