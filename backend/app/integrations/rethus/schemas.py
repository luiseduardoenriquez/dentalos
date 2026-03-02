"""RETHUS professional registry verification schemas — INT-RETHUS."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RETHUSVerificationResponse(BaseModel):
    """Result of a professional registry lookup against the RETHUS / datos.gov.co dataset.

    Used to verify that a healthcare professional (doctor, hygienist, etc.)
    holds a valid, active registration with the Colombian Ministry of Health.
    """

    found: bool = Field(
        ...,
        description="True if the RETHUS number was found in the dataset.",
    )

    rethus_number: str = Field(
        ...,
        description="The RETHUS registration number used for the query.",
    )

    # PHI — full names and document numbers are never logged.
    full_name: str | None = Field(
        None,
        description="Full name of the registered professional. PHI — handle with care.",
    )
    document_type: str | None = Field(
        None,
        description="Document type on record (CC, CE, PA, etc.).",
    )

    profession: str | None = Field(
        None,
        description='Healthcare profession title, e.g. "Odontólogo".',
    )
    specialty: str | None = Field(
        None,
        description='Specialty title if applicable, e.g. "Endodoncia".',
    )
    institution: str | None = Field(
        None,
        description="Name of the graduating / awarding institution.",
    )
    registration_date: str | None = Field(
        None,
        description="Date the RETHUS registration was issued (ISO 8601 string from API).",
    )

    status: str | None = Field(
        None,
        description="Registration status. One of: active, inactive, suspended.",
    )

    verification_date: datetime = Field(
        ...,
        description="UTC timestamp of when the verification was performed.",
    )

    # Full Socrata record kept for audit — NOT exposed in public APIs.
    raw_response: dict[str, Any] | None = Field(
        default=None,
        description="Raw JSON record from datos.gov.co, stored for audit. Internal only.",
    )
