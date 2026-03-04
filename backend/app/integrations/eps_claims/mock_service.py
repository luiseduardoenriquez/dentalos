"""Mock EPS claims service for development and testing -- VP-19 / Sprint 31-32.

Returns deterministic, realistic-looking results so that frontend and backend
developers can work without a real EPS API key.

Deterministic mapping — submit_claim (based on last digit of eps_code):
  even digit (0,2,4,6,8) → status "acknowledged"
  odd digit  (1,3,5,7,9) → status "submitted"

Deterministic mapping — get_claim_status (based on last digit of external_claim_id):
  0-3 → acknowledged
  4-6 → paid (150,000 COP cents)
  7-8 → submitted (still pending)
  9   → rejected
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.integrations.eps_claims.base import EPSClaimsServiceBase
from app.integrations.eps_claims.schemas import (
    EPSClaimStatusResponse,
    EPSClaimSubmitResponse,
)


def _last_digit(value: str) -> int:
    """Extract last numeric-equivalent digit from a string.

    Strips the string, takes the last character, and returns its integer value
    modulo 10.  For non-numeric suffixes the SHA-256 hash byte is used instead,
    ensuring the result is always deterministic and in [0, 9].
    """
    stripped = value.strip()
    if not stripped:
        return 0
    last_char = stripped[-1]
    if last_char.isdigit():
        return int(last_char)
    # Non-numeric: derive from SHA-256 for consistent determinism
    return int(hashlib.sha256(stripped.encode()).hexdigest()[-1], 16) % 10


def _derive_mock_claim_id(eps_code: str) -> str:
    """Build a deterministic mock claim ID from the EPS code."""
    digest = hashlib.sha256(eps_code.encode()).hexdigest()[:8].upper()
    return f"MOCK-EPS-{digest}"


class EPSClaimsMockService(EPSClaimsServiceBase):
    """Mock EPS claims service. Always configured; never makes HTTP calls."""

    def is_configured(self) -> bool:
        return True

    async def submit_claim(self, *, claim_data: dict[str, Any]) -> EPSClaimSubmitResponse:
        """Return a deterministic result based on the last digit of eps_code.

        Even digit → acknowledged; odd digit → submitted.
        The external_claim_id is derived deterministically from eps_code so
        that repeated calls with the same eps_code return the same claim ID.
        """
        eps_code: str = claim_data.get("eps_code", "0")
        digit = _last_digit(eps_code)
        status = "acknowledged" if digit % 2 == 0 else "submitted"
        external_claim_id = _derive_mock_claim_id(eps_code)

        return EPSClaimSubmitResponse(
            external_claim_id=external_claim_id,
            status=status,
            message=f"Reclamación recibida correctamente (mock). Estado inicial: {status}.",
        )

    async def get_claim_status(
        self, *, external_claim_id: str
    ) -> EPSClaimStatusResponse:
        """Return a deterministic status based on last digit of external_claim_id.

        Bucket mapping:
          0-3 → acknowledged
          4-6 → paid (150,000 COP cents reimbursed)
          7-8 → submitted (still pending at EPS)
          9   → rejected (procedure not covered)
        """
        digit = _last_digit(external_claim_id)

        if digit <= 3:
            return EPSClaimStatusResponse(
                external_claim_id=external_claim_id,
                status="acknowledged",
            )
        if digit <= 6:
            return EPSClaimStatusResponse(
                external_claim_id=external_claim_id,
                status="paid",
                paid_amount_cents=150_000,
            )
        if digit <= 8:
            return EPSClaimStatusResponse(
                external_claim_id=external_claim_id,
                status="submitted",
            )
        # digit == 9
        return EPSClaimStatusResponse(
            external_claim_id=external_claim_id,
            status="rejected",
            error_message="Procedimiento no cubierto por el plan de beneficios.",
        )


# Module-level singleton — import this in service layer when mock is selected.
eps_claims_mock_service = EPSClaimsMockService()
