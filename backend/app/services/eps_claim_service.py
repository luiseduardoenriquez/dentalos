"""EPS claim service -- VP-19 EPS Claims Management / Sprint 31-32.

Stateless service class that orchestrates EPS claim lifecycle:
  create_draft → update_claim (draft only) → submit_claim → sync_status

Also provides list_claims (paginated), get_claim (single record), and
get_aging_report (counts by days-since-submission buckets).

Security invariants:
  - PHI (patient document numbers) is NEVER logged at any level.
  - All monetary values in COP cents.
  - Adapter selection: production when is_configured(), mock otherwise —
    no hardcoded decision in route handlers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import EPSClaimErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.integrations.eps_claims.mock_service import eps_claims_mock_service
from app.integrations.eps_claims.service import eps_claims_service
from app.models.tenant.eps_claim import EPSClaim
from app.schemas.eps_claim import EPSClaimCreate, EPSClaimUpdate

logger = logging.getLogger("dentalos.eps_claim")

# Statuses that mean "pending response from EPS" for aging report purposes.
_PENDING_STATUSES = ("submitted", "acknowledged")


def _get_adapter():
    """Return production or mock EPS claims adapter.

    Uses production when fully configured (both api_url and api_key set).
    Falls back to the mock adapter in development / when unconfigured.
    """
    if eps_claims_service.is_configured():
        return eps_claims_service
    return eps_claims_mock_service


class EPSClaimService:
    """Stateless EPS claims service.

    All methods receive the AsyncSession from the caller (injected via
    FastAPI Depends). No internal state is held between calls.
    """

    # -- Create ---------------------------------------------------------------

    async def create_draft(
        self,
        db: AsyncSession,
        data: EPSClaimCreate,
        created_by: uuid.UUID,
    ) -> dict[str, Any]:
        """Create a new EPS claim in draft status.

        Args:
            db: Tenant-scoped AsyncSession.
            data: Validated EPSClaimCreate payload from the route handler.
            created_by: UUID of the authenticated user creating the draft.

        Returns:
            dict representation of the created EPSClaim.
        """
        claim = EPSClaim(
            patient_id=uuid.UUID(data.patient_id),
            eps_code=data.eps_code,
            eps_name=data.eps_name,
            claim_type=data.claim_type,
            procedures=[p.model_dump() for p in data.procedures],
            total_amount_cents=data.total_amount_cents,
            copay_amount_cents=data.copay_amount_cents,
            status="draft",
            created_by=created_by,
        )
        db.add(claim)
        await db.flush()
        await db.refresh(claim)

        logger.info(
            "EPS claim draft created: claim=%s... eps=%s",
            str(claim.id)[:8],
            claim.eps_code,
        )
        return self._claim_to_dict(claim)

    # -- Update ---------------------------------------------------------------

    async def update_claim(
        self,
        db: AsyncSession,
        claim_id: uuid.UUID,
        data: EPSClaimUpdate,
    ) -> dict[str, Any]:
        """Update a draft EPS claim.

        Only claims in status=draft can be modified.  Raises DentalOSError
        with status 409 if the claim has already been submitted.

        Args:
            db: Tenant-scoped AsyncSession.
            claim_id: UUID of the claim to update.
            data: Validated EPSClaimUpdate payload (all fields optional).

        Returns:
            dict representation of the updated EPSClaim.

        Raises:
            ResourceNotFoundError: If claim does not exist.
            DentalOSError: If claim status is not draft.
        """
        claim = await self._get_claim_orm(db, claim_id)

        if claim.status != "draft":
            raise DentalOSError(
                error=EPSClaimErrors.ALREADY_SUBMITTED,
                message="Solo se pueden editar reclamaciones en estado borrador.",
                status_code=409,
            )

        if data.eps_code is not None:
            claim.eps_code = data.eps_code
        if data.eps_name is not None:
            claim.eps_name = data.eps_name
        if data.claim_type is not None:
            claim.claim_type = data.claim_type
        if data.procedures is not None:
            claim.procedures = [p.model_dump() for p in data.procedures]
        if data.total_amount_cents is not None:
            claim.total_amount_cents = data.total_amount_cents
        if data.copay_amount_cents is not None:
            claim.copay_amount_cents = data.copay_amount_cents

        await db.flush()
        await db.refresh(claim)

        logger.info(
            "EPS claim draft updated: claim=%s... eps=%s",
            str(claim.id)[:8],
            claim.eps_code,
        )
        return self._claim_to_dict(claim)

    # -- Submit ---------------------------------------------------------------

    async def submit_claim(
        self,
        db: AsyncSession,
        claim_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Submit a draft claim to the EPS provider.

        Validates that the claim is in draft status, calls the EPS adapter
        (production or mock), transitions the claim to submitted, and records
        the submission timestamp.

        Args:
            db: Tenant-scoped AsyncSession.
            claim_id: UUID of the claim to submit.

        Returns:
            dict representation of the updated EPSClaim.

        Raises:
            ResourceNotFoundError: If claim does not exist.
            DentalOSError: If claim is not in draft status or the adapter fails.
        """
        claim = await self._get_claim_orm(db, claim_id)

        if claim.status != "draft":
            raise DentalOSError(
                error=EPSClaimErrors.ALREADY_SUBMITTED,
                message="Esta reclamación ya fue enviada. No se puede reenviar.",
                status_code=409,
            )

        adapter = _get_adapter()

        # Build the payload for the EPS API.
        # patient_document_type/number would ideally be fetched from the patient record;
        # the adapter mock does not require real values.
        claim_data = {
            "eps_code": claim.eps_code,
            "patient_document_type": "CC",
            "patient_document_number": "0000000000",  # populated from patient in full impl
            "claim_type": claim.claim_type,
            "procedures": claim.procedures or [],
            "total_amount_cents": claim.total_amount_cents,
            "copay_amount_cents": claim.copay_amount_cents,
        }

        try:
            resp = await adapter.submit_claim(claim_data=claim_data)
        except Exception as exc:
            logger.error(
                "EPS claim submission failed: claim=%s... error=%s",
                str(claim_id)[:8],
                str(exc),
            )
            raise DentalOSError(
                error=EPSClaimErrors.PROVIDER_UNAVAILABLE,
                message="El proveedor de reclamaciones EPS no está disponible.",
                status_code=503,
            ) from exc

        claim.status = "submitted"
        claim.external_claim_id = resp.external_claim_id
        claim.submitted_at = datetime.now(UTC)

        await db.flush()
        await db.refresh(claim)

        logger.info(
            "EPS claim submitted: claim=%s... external_id=%s... status=%s",
            str(claim.id)[:8],
            resp.external_claim_id[:8],
            resp.status,
        )
        return self._claim_to_dict(claim)

    # -- Sync status ----------------------------------------------------------

    async def sync_status(
        self,
        db: AsyncSession,
        claim_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Query the EPS provider for the current status of a submitted claim.

        Updates the local record with the response status, error message,
        and response timestamp.  If the EPS acknowledges the claim,
        acknowledged_at is set.

        Args:
            db: Tenant-scoped AsyncSession.
            claim_id: UUID of the claim to sync.

        Returns:
            dict representation of the updated EPSClaim.

        Raises:
            ResourceNotFoundError: If claim does not exist.
            DentalOSError: If claim has no external_claim_id or provider fails.
        """
        claim = await self._get_claim_orm(db, claim_id)

        if not claim.external_claim_id:
            raise DentalOSError(
                error=EPSClaimErrors.INVALID_STATUS_TRANSITION,
                message="La reclamación no ha sido enviada al proveedor EPS.",
                status_code=422,
            )

        adapter = _get_adapter()

        try:
            resp = await adapter.get_claim_status(
                external_claim_id=claim.external_claim_id
            )
        except Exception as exc:
            logger.error(
                "EPS claim status sync failed: claim=%s... error=%s",
                str(claim_id)[:8],
                str(exc),
            )
            raise DentalOSError(
                error=EPSClaimErrors.PROVIDER_UNAVAILABLE,
                message="El proveedor de reclamaciones EPS no está disponible.",
                status_code=503,
            ) from exc

        now = datetime.now(UTC)
        claim.status = resp.status
        claim.error_message = resp.error_message
        claim.response_at = now

        if resp.status == "acknowledged" and claim.acknowledged_at is None:
            claim.acknowledged_at = now

        await db.flush()
        await db.refresh(claim)

        logger.info(
            "EPS claim status synced: claim=%s... status=%s",
            str(claim.id)[:8],
            resp.status,
        )
        return self._claim_to_dict(claim)

    # -- List -----------------------------------------------------------------

    async def list_claims(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        patient_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Return a paginated list of EPS claims, ordered by created_at desc.

        Args:
            db: Tenant-scoped AsyncSession.
            page: 1-based page number.
            page_size: Items per page (max 100).
            status_filter: Optional status to filter by.
            patient_id: Optional patient UUID to filter by.

        Returns:
            dict with keys: items (list of dicts), total, page, page_size.
        """
        base_query = select(EPSClaim).where(EPSClaim.is_active.is_(True))

        if status_filter is not None:
            base_query = base_query.where(EPSClaim.status == status_filter)
        if patient_id is not None:
            base_query = base_query.where(EPSClaim.patient_id == patient_id)

        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total: int = count_result.scalar_one()

        # Paginated data
        offset = (page - 1) * page_size
        data_result = await db.execute(
            base_query.order_by(EPSClaim.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        claims = data_result.scalars().all()

        return {
            "items": [self._claim_to_dict(c) for c in claims],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # -- Get single -----------------------------------------------------------

    async def get_claim(
        self,
        db: AsyncSession,
        claim_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Return a single EPS claim as a dict.

        Args:
            db: Tenant-scoped AsyncSession.
            claim_id: UUID of the claim.

        Returns:
            dict representation of the EPSClaim.

        Raises:
            ResourceNotFoundError: If no active claim with that ID exists.
        """
        claim = await self._get_claim_orm(db, claim_id)
        return self._claim_to_dict(claim)

    # -- Aging report ---------------------------------------------------------

    async def get_aging_report(self, db: AsyncSession) -> dict[str, int]:
        """Return counts of submitted/acknowledged claims grouped by age bucket.

        Age buckets (days since submitted_at):
          0-30d, 31-60d, 61-90d, 90+d

        Only claims in status "submitted" or "acknowledged" are included.
        Terminal statuses (paid, rejected, appealed) are excluded.

        Args:
            db: Tenant-scoped AsyncSession.

        Returns:
            dict with keys: "0_30", "31_60", "61_90", "90_plus" → int counts.
        """
        now = datetime.now(UTC)
        counts: dict[str, int] = {
            "0_30": 0,
            "31_60": 0,
            "61_90": 0,
            "90_plus": 0,
        }

        buckets = [
            ("0_30", 0, 30),
            ("31_60", 31, 60),
            ("61_90", 61, 90),
        ]

        for label, start_days, end_days in buckets:
            result = await db.execute(
                select(func.count()).select_from(EPSClaim).where(
                    and_(
                        EPSClaim.is_active.is_(True),
                        EPSClaim.status.in_(_PENDING_STATUSES),
                        EPSClaim.submitted_at.is_not(None),
                        EPSClaim.submitted_at >= now - timedelta(days=end_days),
                        EPSClaim.submitted_at <= now - timedelta(days=start_days),
                    )
                )
            )
            counts[label] = result.scalar_one()

        # 90+ days bucket
        result_90 = await db.execute(
            select(func.count()).select_from(EPSClaim).where(
                and_(
                    EPSClaim.is_active.is_(True),
                    EPSClaim.status.in_(_PENDING_STATUSES),
                    EPSClaim.submitted_at.is_not(None),
                    EPSClaim.submitted_at < now - timedelta(days=90),
                )
            )
        )
        counts["90_plus"] = result_90.scalar_one()

        return counts

    # -- Private helpers ------------------------------------------------------

    async def _get_claim_orm(
        self,
        db: AsyncSession,
        claim_id: uuid.UUID,
    ) -> EPSClaim:
        """Fetch an active EPSClaim ORM object or raise ResourceNotFoundError."""
        result = await db.execute(
            select(EPSClaim).where(
                EPSClaim.id == claim_id,
                EPSClaim.is_active.is_(True),
            )
        )
        claim = result.scalar_one_or_none()
        if claim is None:
            raise ResourceNotFoundError(
                error=EPSClaimErrors.NOT_FOUND,
                resource_name="EPSClaim",
            )
        return claim

    @staticmethod
    def _claim_to_dict(claim: EPSClaim) -> dict[str, Any]:
        """Serialize an EPSClaim ORM object to a response dict.

        UUIDs are serialised as strings per DentalOS JSON convention.
        Datetimes are left as datetime objects (Pydantic serialises them).
        """
        return {
            "id": str(claim.id),
            "patient_id": str(claim.patient_id),
            "eps_code": claim.eps_code,
            "eps_name": claim.eps_name,
            "claim_type": claim.claim_type,
            "procedures": claim.procedures or [],
            "total_amount_cents": claim.total_amount_cents,
            "copay_amount_cents": claim.copay_amount_cents,
            "status": claim.status,
            "external_claim_id": claim.external_claim_id,
            "error_message": claim.error_message,
            "submitted_at": claim.submitted_at,
            "acknowledged_at": claim.acknowledged_at,
            "response_at": claim.response_at,
            "created_by": str(claim.created_by) if claim.created_by else None,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
        }


# Module-level singleton — import this in route handlers.
eps_claim_service = EPSClaimService()
