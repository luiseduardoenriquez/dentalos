"""ADRES / BDUA verification schemas — INT-ADRES."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ADRESVerificationResponse(BaseModel):
    """Result of an EPS affiliation lookup against the ADRES BDUA registry.

    Security note: document_number is NOT logged at any point.
    It is stored only in encrypted form once persisted to the tenant DB.
    """

    found: bool = Field(..., description="True if the document was found in BDUA.")

    document_type: str = Field(
        ...,
        description="Document type code used for the query (e.g. CC, TI, CE, PA).",
    )
    # PHI — never logged, stored encrypted
    document_number: str = Field(
        ...,
        description="Document number used for the query. PHI — handle with care.",
    )

    eps_name: str | None = Field(
        None,
        description="Name of the affiliated EPS/health insurer.",
    )
    eps_code: str | None = Field(
        None,
        description="Official EPS code as registered with ADRES.",
    )

    affiliation_status: str | None = Field(
        None,
        description=(
            "Current affiliation status. "
            "One of: activo, inactivo, suspendido, retirado, no_afiliado."
        ),
    )
    regime: str | None = Field(
        None,
        description=(
            "Healthcare regime. "
            "One of: contributivo, subsidiado, vinculado, excepcion."
        ),
    )
    copay_category: str | None = Field(
        None,
        description="Copay (cuota moderadora) category: A, B, C, or None.",
    )

    verification_date: datetime = Field(
        ...,
        description="UTC timestamp of when the verification was performed.",
    )

    # Full ADRES API response kept for audit trail — NOT exposed in public APIs
    raw_response: dict[str, Any] | None = Field(
        default=None,
        description="Raw JSON response from ADRES API, stored for audit. Internal only.",
    )
