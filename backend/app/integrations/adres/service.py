"""ADRES / BDUA EPS affiliation verification service — INT-ADRES.

Calls the ADRES BDUA REST API to verify a patient's health insurance
affiliation status. This is a read-only lookup used during patient intake
and for generating RIPS reports.

Security:
  - document_number (PHI) is NEVER written to logs at any log level.
  - adres_api_key is never logged.
  - raw_response is stored for audit but must NOT be returned in public APIs.
  - All HTTP calls use a 30 s timeout to avoid blocking request threads.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.adres.base import ADRESServiceBase
from app.integrations.adres.schemas import ADRESVerificationResponse

logger = logging.getLogger("dentalos.integrations.adres")

# ADRES BDUA verification endpoint path.
# Full URL: {adres_api_url}/v1/afiliados/verificar
_VERIFY_PATH = "/v1/afiliados/verificar"

# Map ADRES API status codes to our canonical values.
_STATUS_MAP: dict[str, str] = {
    "A": "activo",
    "I": "inactivo",
    "S": "suspendido",
    "R": "retirado",
    "N": "no_afiliado",
    # Pass through already-canonical values unchanged
    "activo": "activo",
    "inactivo": "inactivo",
    "suspendido": "suspendido",
    "retirado": "retirado",
    "no_afiliado": "no_afiliado",
}

_REGIME_MAP: dict[str, str] = {
    "C": "contributivo",
    "S": "subsidiado",
    "V": "vinculado",
    "E": "excepcion",
    "contributivo": "contributivo",
    "subsidiado": "subsidiado",
    "vinculado": "vinculado",
    "excepcion": "excepcion",
}


class ADRESService(ADRESServiceBase):
    """Production ADRES BDUA verification service.

    Uses a lazily-initialized httpx.AsyncClient so the service can be
    instantiated at module load time without requiring the event loop.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.adres_api_url,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Bearer {settings.adres_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    def is_configured(self) -> bool:
        """Return True if adres_api_key is set."""
        return bool(settings.adres_api_key)

    async def verify_affiliation(
        self,
        *,
        document_type: str,
        document_number: str,
    ) -> ADRESVerificationResponse:
        """Query ADRES BDUA for a patient's EPS affiliation.

        Args:
            document_type: Colombian document type (CC, TI, CE, PA, RC, MS).
            document_number: The document number to look up. PHI — never logged.

        Returns:
            ADRESVerificationResponse populated from the ADRES API response.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP responses.
            httpx.TimeoutException: If ADRES API does not respond within 30 s.
        """
        if not self.is_configured():
            logger.warning(
                "ADRES integration not configured — returning not-found result. "
                "Set adres_api_key in environment to enable."
            )
            return ADRESVerificationResponse(
                found=False,
                document_type=document_type,
                document_number=document_number,
                affiliation_status="no_afiliado",
                verification_date=datetime.now(UTC),
            )

        # NOTE: document_number intentionally omitted from all log calls below.
        logger.info(
            "ADRES affiliation lookup: document_type=%s",
            document_type,
        )

        client = await self._get_client()
        response = await client.post(
            _VERIFY_PATH,
            json={
                "tipo_documento": document_type,
                "numero_documento": document_number,
            },
        )
        response.raise_for_status()

        raw: dict[str, Any] = response.json()

        # Determine whether a record was found.  ADRES returns an explicit
        # "encontrado" flag; fall back to checking for eps data presence.
        found: bool = raw.get("encontrado", bool(raw.get("eps_codigo")))

        affiliation_status_raw = raw.get("estado_afiliacion") or raw.get("status")
        regime_raw = raw.get("regimen") or raw.get("regime")

        result = ADRESVerificationResponse(
            found=found,
            document_type=document_type,
            document_number=document_number,
            eps_name=raw.get("eps_nombre") or raw.get("eps_name"),
            eps_code=raw.get("eps_codigo") or raw.get("eps_code"),
            affiliation_status=_STATUS_MAP.get(affiliation_status_raw or "", affiliation_status_raw),
            regime=_REGIME_MAP.get(regime_raw or "", regime_raw),
            copay_category=raw.get("categoria_copago") or raw.get("copay_category"),
            verification_date=datetime.now(UTC),
            raw_response=raw,
        )

        logger.info(
            "ADRES verification complete: found=%s status=%s",
            result.found,
            result.affiliation_status,
        )

        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton — import this in services and route handlers.
adres_service = ADRESService()
