"""Sistecrédito financing service -- production implementation.

Integrates with the Sistecrédito API to check patient eligibility (preaprobación),
submit credit applications, and query application status.

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

logger = logging.getLogger("dentalos.integrations.financing.sistecredito")


class SistecreditoService(FinancingProviderBase):
    """Production Sistecrédito financing service using Sistecrédito API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        """Check if all required Sistecrédito credentials are set."""
        return bool(settings.sistecredito_api_key and settings.sistecredito_api_url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.sistecredito_api_url,
                timeout=httpx.Timeout(30.0),
                headers={
                    "x-api-key": settings.sistecredito_api_key,
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
        """Check patient eligibility via Sistecrédito preaprobación endpoint.

        Calls POST {sistecredito_api_url}/preaprobacion. Converts amount from
        cents to COP as required by the Sistecrédito API.

        Args:
            patient_document: Patient's cedula or other document number.
            amount_cents: Requested amount in COP cents.

        Returns:
            EligibilityResult with eligibility, limits, and installment options.

        Raises:
            httpx.HTTPStatusError: On Sistecrédito API failure.
            RuntimeError: If Sistecrédito integration is not configured.
        """
        if not self.is_configured():
            raise RuntimeError("Sistecrédito integration is not configured")

        client = await self._get_client()

        payload: dict[str, Any] = {
            "numero_documento": patient_document,
            "valor_solicitado": amount_cents // 100,  # Sistecrédito expects full COP
        }

        response = await client.post("/preaprobacion", json=payload)
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = EligibilityResult(
            eligible=data.get("preaprobado", False),
            max_amount_cents=(
                int(data["cupo_maximo"]) * 100
                if data.get("cupo_maximo") is not None
                else None
            ),
            min_amount_cents=(
                int(data["cupo_minimo"]) * 100
                if data.get("cupo_minimo") is not None
                else None
            ),
            available_installments=data.get("plazos_disponibles", []),
            reason=data.get("motivo_rechazo"),
        )

        logger.info(
            "Sistecrédito eligibility checked: eligible=%s document=%s...",
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
        """Submit a credit application to Sistecrédito.

        Calls POST {sistecredito_api_url}/credito. Converts amount from cents
        to COP as required by the Sistecrédito API.

        Args:
            patient_document: Patient's cedula or other document number.
            amount_cents: Financing amount in COP cents.
            installments: Requested number of monthly installments.
            reference: Unique DentalOS reference for this application.
            callback_url: URL for Sistecrédito to post status update webhooks.

        Returns:
            ApplicationResult with provider reference, status, and redirect URL.

        Raises:
            httpx.HTTPStatusError: On Sistecrédito API failure.
            RuntimeError: If Sistecrédito integration is not configured.
        """
        if not self.is_configured():
            raise RuntimeError("Sistecrédito integration is not configured")

        client = await self._get_client()

        payload: dict[str, Any] = {
            "numero_documento": patient_document,
            "valor_credito": amount_cents // 100,  # Sistecrédito expects full COP
            "numero_cuotas": installments,
            "referencia_externa": reference,
            "url_callback": callback_url,
        }

        response = await client.post("/credito", json=payload)
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = ApplicationResult(
            provider_reference=data["id_credito"],
            status=data.get("estado", "pending"),
            redirect_url=data.get("url_firma"),
        )

        logger.info(
            "Sistecrédito application created: ref=%s... status=%s",
            result.provider_reference[:8] if result.provider_reference else "unknown",
            result.status,
        )

        return result

    async def get_status(
        self,
        *,
        provider_reference: str,
    ) -> ApplicationStatusResult:
        """Query the current status of a Sistecrédito credit application.

        Calls GET {sistecredito_api_url}/credito/{provider_reference}.

        Args:
            provider_reference: Sistecrédito-assigned application identifier.

        Returns:
            ApplicationStatusResult with current state and optional amounts.

        Raises:
            httpx.HTTPStatusError: On Sistecrédito API failure.
            RuntimeError: If Sistecrédito integration is not configured.
        """
        if not self.is_configured():
            raise RuntimeError("Sistecrédito integration is not configured")

        client = await self._get_client()

        response = await client.get(f"/credito/{provider_reference}")
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        approved_amount_cents: int | None = None
        if data.get("valor_aprobado") is not None:
            approved_amount_cents = int(data["valor_aprobado"]) * 100

        result = ApplicationStatusResult(
            provider_reference=provider_reference,
            status=data.get("estado", "pending"),
            approved_amount_cents=approved_amount_cents,
            disbursed_at=data.get("fecha_desembolso"),
        )

        logger.info(
            "Sistecrédito application status queried: ref=%s... status=%s",
            provider_reference[:8],
            result.status,
        )

        return result

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature from Sistecrédito.

        Uses timing-safe comparison to prevent timing attacks.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Signature header value from Sistecrédito.

        Returns:
            True if the signature is valid.
        """
        if not settings.sistecredito_api_key:
            logger.warning("Sistecrédito API key not configured for webhook verification")
            return False

        secret = settings.sistecredito_api_key.encode("utf-8")
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed, signature)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton
sistecredito_service = SistecreditoService()
