"""Mock RETHUS professional registry verification service for dev/testing — INT-RETHUS.

Returns deterministic, realistic-looking data based on the first character of
the RETHUS number.  This lets frontend and backend developers work without a
real datos.gov.co app token.

Deterministic mapping (first character of rethus_number):
  "1..."  → found=True, profession="Odontólogo", status="active"
  "2..."  → found=True, profession="Odontólogo", specialty="Endodoncia", status="active"
  other   → found=False
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.rethus.base import RETHUSServiceBase
from app.integrations.rethus.schemas import RETHUSVerificationResponse


class RETHUSServiceMock(RETHUSServiceBase):
    """Mock RETHUS service. Always configured; never makes HTTP calls."""

    def is_configured(self) -> bool:
        return True

    async def verify_professional(
        self,
        *,
        rethus_number: str,
    ) -> RETHUSVerificationResponse:
        """Return deterministic fixture data based on first character of rethus_number."""
        prefix = rethus_number.strip()[:1] if rethus_number.strip() else ""

        if prefix == "1":
            return RETHUSVerificationResponse(
                found=True,
                rethus_number=rethus_number,
                full_name="Doctor Ejemplo Uno",
                document_type="CC",
                profession="Odontólogo",
                specialty=None,
                institution="Universidad Nacional de Colombia",
                registration_date="2015-06-01",
                status="active",
                verification_date=datetime.now(UTC),
                raw_response={"mock": True, "bucket": "1x"},
            )

        if prefix == "2":
            return RETHUSVerificationResponse(
                found=True,
                rethus_number=rethus_number,
                full_name="Doctor Ejemplo Dos",
                document_type="CC",
                profession="Odontólogo",
                specialty="Endodoncia",
                institution="Pontificia Universidad Javeriana",
                registration_date="2012-03-15",
                status="active",
                verification_date=datetime.now(UTC),
                raw_response={"mock": True, "bucket": "2x"},
            )

        # All other prefixes → not found
        return RETHUSVerificationResponse(
            found=False,
            rethus_number=rethus_number,
            verification_date=datetime.now(UTC),
            raw_response={"mock": True, "bucket": "not_found"},
        )


# Module-level singleton
rethus_mock_service = RETHUSServiceMock()
