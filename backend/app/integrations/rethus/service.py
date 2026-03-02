"""RETHUS professional registry verification service — INT-RETHUS.

Queries the RETHUS dataset published on datos.gov.co via the Socrata Open
Data API (SODA).  Used to confirm that a doctor or other healthcare
professional holds a valid, active registration with the Colombian Ministry
of Health before allowing them to sign clinical documents.

Dataset: "sues-anis" on datos.gov.co
API docs: https://dev.socrata.com/docs/queries/

Security:
  - full_name and document_number (PHI) are NEVER written to logs.
  - rethus_app_token is never logged.
  - raw_response is stored for audit but must NOT be returned in public APIs.
  - All HTTP calls use a 30 s timeout to avoid blocking request threads.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.rethus.base import RETHUSServiceBase
from app.integrations.rethus.schemas import RETHUSVerificationResponse

logger = logging.getLogger("dentalos.integrations.rethus")

# Socrata dataset ID for the RETHUS registry on datos.gov.co.
# Actual dataset slug; replace if datos.gov.co migrates the resource.
_DATASET_ID = "sues-anis"

# Map Socrata "estado" values to our canonical status strings.
_STATUS_MAP: dict[str, str] = {
    "ACTIVO": "active",
    "INACTIVO": "inactive",
    "SUSPENDIDO": "suspended",
    "active": "active",
    "inactive": "inactive",
    "suspended": "suspended",
}


class RETHUSService(RETHUSServiceBase):
    """Production RETHUS verification service via datos.gov.co Socrata API.

    Uses a lazily-initialized httpx.AsyncClient so the service can be
    instantiated at module load time without requiring the event loop.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Accept": "application/json",
            }
            if settings.rethus_app_token:
                # Socrata uses $$app_token as a query-string-style header name.
                headers["$$app_token"] = settings.rethus_app_token

            self._client = httpx.AsyncClient(
                base_url=settings.rethus_api_url,
                timeout=httpx.Timeout(30.0),
                headers=headers,
            )
        return self._client

    def is_configured(self) -> bool:
        """Return True if rethus_app_token is set."""
        return bool(settings.rethus_app_token)

    async def verify_professional(
        self,
        *,
        rethus_number: str,
    ) -> RETHUSVerificationResponse:
        """Query datos.gov.co for a professional's RETHUS registration.

        Socrata returns an array of matching records (usually 0 or 1).
        We take the first match.

        Args:
            rethus_number: RETHUS registration number to look up.

        Returns:
            RETHUSVerificationResponse populated from the Socrata record.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP responses.
            httpx.TimeoutException: If datos.gov.co does not respond within 30 s.
        """
        if not self.is_configured():
            logger.warning(
                "RETHUS integration not configured — returning not-found result. "
                "Set rethus_app_token in environment to enable."
            )
            return RETHUSVerificationResponse(
                found=False,
                rethus_number=rethus_number,
                verification_date=datetime.now(UTC),
            )

        # rethus_number is a registry code, not PHI — safe to log.
        logger.info("RETHUS lookup: rethus_number=%s", rethus_number)

        client = await self._get_client()
        response = await client.get(
            f"/{_DATASET_ID}.json",
            params={"rethus": rethus_number},
        )
        response.raise_for_status()

        records: list[dict[str, Any]] = response.json()

        if not records:
            logger.info("RETHUS lookup: rethus_number=%s found=False", rethus_number)
            return RETHUSVerificationResponse(
                found=False,
                rethus_number=rethus_number,
                verification_date=datetime.now(UTC),
            )

        # Use the first (and normally only) matching record.
        raw: dict[str, Any] = records[0]

        status_raw: str | None = raw.get("estado") or raw.get("status")

        result = RETHUSVerificationResponse(
            found=True,
            rethus_number=rethus_number,
            # PHI fields — never log these values
            full_name=raw.get("nombre_completo") or raw.get("full_name"),
            document_type=raw.get("tipo_documento") or raw.get("document_type"),
            profession=raw.get("profesion") or raw.get("profession"),
            specialty=raw.get("especialidad") or raw.get("specialty"),
            institution=raw.get("institucion") or raw.get("institution"),
            registration_date=raw.get("fecha_registro") or raw.get("registration_date"),
            status=_STATUS_MAP.get(status_raw or "", status_raw),
            verification_date=datetime.now(UTC),
            raw_response=raw,
        )

        # Log only non-PHI fields
        logger.info(
            "RETHUS verification complete: rethus_number=%s found=True status=%s",
            rethus_number,
            result.status,
        )

        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton — import this in services and route handlers.
rethus_service = RETHUSService()
