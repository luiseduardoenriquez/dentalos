"""Addi BNPL financing service -- production implementation.

Integrates with the Addi Financing API to check patient eligibility,
submit financing applications, and query application status.

Security:
  - API key is read from settings, never logged or persisted outside memory
  - All httpx calls use explicit 30s timeouts
  - Webhook signatures verified with timing-safe HMAC-SHA256
  - Patient documents and amounts are NEVER logged in full
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.financing.base import FinancingProviderBase
from app.integrations.financing.schemas import (
    ApplicationResult,
    ApplicationStatusResult,
    EligibilityResult,
)

logger = logging.getLogger("dentalos.integrations.financing.addi")


class AddiService(FinancingProviderBase):
    """Production Addi BNPL financing service using Addi Financing API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        """Check if all required Addi credentials are set."""
        return bool(settings.addi_api_key and settings.addi_api_url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.addi_api_url,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Bearer {settings.addi_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def check_eligibility(
        self,
        *,
        patient_document: str,
        amount_cents: int,
    ) -> EligibilityResult:
        """Check patient eligibility via Addi API.

        Calls POST {addi_api_url}/eligibility. Converts amount from cents
        to COP (full pesos) as required by the Addi API.

        Args:
            patient_document: Patient's cedula or other document number.
            amount_cents: Requested amount in COP cents.

        Returns:
            EligibilityResult with eligibility, limits, and installment options.

        Raises:
            httpx.HTTPStatusError: On Addi API failure.
            RuntimeError: If Addi integration is not configured.
        """
        if not self.is_configured():
            raise RuntimeError("Addi integration is not configured")

        client = await self._get_client()

        payload: dict[str, Any] = {
            "document_number": patient_document,
            "amount": amount_cents // 100,  # Addi expects full COP
        }

        response = await client.post("/eligibility", json=payload)
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = EligibilityResult(
            eligible=data.get("eligible", False),
            max_amount_cents=(
                int(data["max_amount"]) * 100 if data.get("max_amount") is not None else None
            ),
            min_amount_cents=(
                int(data["min_amount"]) * 100 if data.get("min_amount") is not None else None
            ),
            available_installments=data.get("available_installments", []),
            reason=data.get("reason"),
        )

        logger.info(
            "Addi eligibility checked: eligible=%s document=%s...",
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
        """Submit a financing application to Addi.

        Calls POST {addi_api_url}/applications. Converts amount from cents
        to COP as required by the Addi API.

        Args:
            patient_document: Patient's cedula or other document number.
            amount_cents: Financing amount in COP cents.
            installments: Requested number of monthly installments.
            reference: Unique DentalOS reference for this application.
            callback_url: URL for Addi to post status update webhooks.

        Returns:
            ApplicationResult with provider reference, status, and redirect URL.

        Raises:
            httpx.HTTPStatusError: On Addi API failure.
            RuntimeError: If Addi integration is not configured.
        """
        if not self.is_configured():
            raise RuntimeError("Addi integration is not configured")

        client = await self._get_client()

        payload: dict[str, Any] = {
            "document_number": patient_document,
            "amount": amount_cents // 100,  # Addi expects full COP
            "installments": installments,
            "external_reference": reference,
            "callback_url": callback_url,
        }

        response = await client.post("/applications", json=payload)
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = ApplicationResult(
            provider_reference=data["application_id"],
            status=data.get("status", "pending"),
            redirect_url=data.get("redirect_url"),
        )

        logger.info(
            "Addi application created: ref=%s... status=%s",
            result.provider_reference[:8] if result.provider_reference else "unknown",
            result.status,
        )

        return result

    async def get_status(
        self,
        *,
        provider_reference: str,
    ) -> ApplicationStatusResult:
        """Query the current status of an Addi financing application.

        Calls GET {addi_api_url}/applications/{provider_reference}.

        Args:
            provider_reference: Addi-assigned application identifier.

        Returns:
            ApplicationStatusResult with current state and optional amounts.

        Raises:
            httpx.HTTPStatusError: On Addi API failure.
            RuntimeError: If Addi integration is not configured.
        """
        if not self.is_configured():
            raise RuntimeError("Addi integration is not configured")

        client = await self._get_client()

        response = await client.get(f"/applications/{provider_reference}")
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        approved_amount_cents: int | None = None
        if data.get("approved_amount") is not None:
            approved_amount_cents = int(data["approved_amount"]) * 100

        result = ApplicationStatusResult(
            provider_reference=provider_reference,
            status=data.get("status", "pending"),
            approved_amount_cents=approved_amount_cents,
            disbursed_at=data.get("disbursed_at"),
        )

        logger.info(
            "Addi application status queried: ref=%s... status=%s",
            provider_reference[:8],
            result.status,
        )

        return result

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature from Addi.

        Uses timing-safe comparison to prevent timing attacks.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Signature header value from Addi.

        Returns:
            True if the signature is valid.
        """
        if not settings.addi_api_key:
            logger.warning("Addi API key not configured for webhook verification")
            return False

        secret = settings.addi_api_key.encode("utf-8")
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed, signature)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton
addi_service = AddiService()
