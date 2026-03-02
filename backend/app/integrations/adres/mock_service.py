"""Mock ADRES / BDUA verification service for development and testing — INT-ADRES.

Returns deterministic, realistic-looking Colombian EPS data based on the
last digit of the document number.  This lets frontend and backend developers
work without a real ADRES API key.

Deterministic mapping (last digit of document_number):
  0-5  → activo, contributivo, EPS Sura (code: EPS010)
  6-7  → activo, subsidiado, EPS Capital Salud (code: EPSC09)
  8    → inactivo (last known EPS: EPS Sura)
  9    → no_afiliado (no EPS data)
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.adres.base import ADRESServiceBase
from app.integrations.adres.schemas import ADRESVerificationResponse

# Fixture data keyed by the bucket a document falls into.
# Bucket is determined by _get_bucket() below.
_FIXTURES: dict[str, dict] = {
    "activo_contributivo": {
        "found": True,
        "eps_name": "EPS Sura",
        "eps_code": "EPS010",
        "affiliation_status": "activo",
        "regime": "contributivo",
        "copay_category": "B",
    },
    "activo_subsidiado": {
        "found": True,
        "eps_name": "Capital Salud EPS-S",
        "eps_code": "EPSC09",
        "affiliation_status": "activo",
        "regime": "subsidiado",
        "copay_category": "A",
    },
    "inactivo": {
        "found": True,
        "eps_name": "EPS Sura",
        "eps_code": "EPS010",
        "affiliation_status": "inactivo",
        "regime": "contributivo",
        "copay_category": None,
    },
    "no_afiliado": {
        "found": False,
        "eps_name": None,
        "eps_code": None,
        "affiliation_status": "no_afiliado",
        "regime": None,
        "copay_category": None,
    },
}


def _get_bucket(document_number: str) -> str:
    """Derive fixture bucket from the last digit of the document number."""
    last_digit_char = document_number.strip()[-1] if document_number.strip() else "0"
    # Non-numeric suffix → treat as digit 0 (activo contributivo)
    last_digit = int(last_digit_char) if last_digit_char.isdigit() else 0

    if 0 <= last_digit <= 5:
        return "activo_contributivo"
    if last_digit in (6, 7):
        return "activo_subsidiado"
    if last_digit == 8:
        return "inactivo"
    # digit 9
    return "no_afiliado"


class ADRESServiceMock(ADRESServiceBase):
    """Mock ADRES service. Always configured; never makes HTTP calls."""

    def is_configured(self) -> bool:
        return True

    async def verify_affiliation(
        self,
        *,
        document_type: str,
        document_number: str,
    ) -> ADRESVerificationResponse:
        """Return deterministic fixture data based on last digit of document_number."""
        bucket = _get_bucket(document_number)
        fixture = _FIXTURES[bucket]

        return ADRESVerificationResponse(
            found=fixture["found"],
            document_type=document_type,
            document_number=document_number,
            eps_name=fixture["eps_name"],
            eps_code=fixture["eps_code"],
            affiliation_status=fixture["affiliation_status"],
            regime=fixture["regime"],
            copay_category=fixture["copay_category"],
            verification_date=datetime.now(UTC),
            raw_response={"mock": True, "bucket": bucket},
        )


# Module-level singleton
adres_mock_service = ADRESServiceMock()
