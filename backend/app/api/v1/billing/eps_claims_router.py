"""EPS claims API routes -- VP-19 EPS Claims Management / Sprint 31-32.

Endpoint map:
  POST /billing/eps-claims                       -- Create draft claim (201)
  GET  /billing/eps-claims                       -- List claims, paginated (200)
  GET  /billing/eps-claims/aging                 -- Aging report (200)
  GET  /billing/eps-claims/{claim_id}            -- Get claim detail (200)
  PUT  /billing/eps-claims/{claim_id}            -- Update draft claim (200)
  POST /billing/eps-claims/{claim_id}/submit     -- Submit to EPS (200)
  POST /billing/eps-claims/{claim_id}/sync-status -- Sync status from EPS (200)

IMPORTANT: GET /aging is defined BEFORE GET /{claim_id} so that FastAPI does
not interpret the literal string "aging" as a claim_id path parameter.

Security:
  - eps_claims:read  — read-only operations (list, get, aging)
  - eps_claims:write — mutating operations (create, update, submit, sync-status)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.eps_claim import (
    EPSClaimCreate,
    EPSClaimListResponse,
    EPSClaimResponse,
    EPSClaimUpdate,
)
from app.services.eps_claim_service import eps_claim_service

logger = logging.getLogger("dentalos.api.eps_claims")

router = APIRouter(prefix="/billing/eps-claims", tags=["eps-claims"])


# ─── POST /billing/eps-claims ─────────────────────────────────────────────────


@router.post("", response_model=EPSClaimResponse, status_code=201)
async def create_eps_claim(
    body: EPSClaimCreate,
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EPSClaimResponse:
    """Create a new EPS claim in draft status.

    The claim is created with status=draft and is not yet sent to the EPS
    provider.  Use the /submit action to transmit it.

    Requires ``eps_claims:write`` permission.
    """
    result = await eps_claim_service.create_draft(
        db,
        data=body,
        created_by=uuid.UUID(current_user.user_id),
    )
    return EPSClaimResponse(**result)


# ─── GET /billing/eps-claims ──────────────────────────────────────────────────


@router.get("", response_model=EPSClaimListResponse)
async def list_eps_claims(
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(
        default=None,
        description="Filter by status: draft|submitted|acknowledged|paid|rejected|appealed",
    ),
    patient_id: uuid.UUID | None = Query(
        default=None, description="Filter by patient UUID"
    ),
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EPSClaimListResponse:
    """Return a paginated list of EPS claims.

    Optionally filtered by status and/or patient.  Results are ordered by
    created_at descending.  Requires ``eps_claims:read`` permission.
    """
    result = await eps_claim_service.list_claims(
        db,
        page=page,
        page_size=page_size,
        status_filter=status,
        patient_id=patient_id,
    )
    return EPSClaimListResponse(
        items=[EPSClaimResponse(**c) for c in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── GET /billing/eps-claims/aging ────────────────────────────────────────────
# IMPORTANT: This route MUST be defined before GET /{claim_id} so that FastAPI
# does not mistakenly try to parse "aging" as a UUID claim_id.


@router.get("/aging", response_model=dict[str, int])
async def get_aging_report(
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict[str, int]:
    """Return claim aging counts grouped by days since submission.

    Only claims in status "submitted" or "acknowledged" are counted.
    Terminal statuses (paid, rejected, appealed) are excluded.

    Response keys:
      - ``0_30``   — 0 to 30 days since submitted_at
      - ``31_60``  — 31 to 60 days
      - ``61_90``  — 61 to 90 days
      - ``90_plus`` — more than 90 days

    Requires ``eps_claims:read`` permission.
    """
    return await eps_claim_service.get_aging_report(db)


# ─── GET /billing/eps-claims/{claim_id} ───────────────────────────────────────


@router.get("/{claim_id}", response_model=EPSClaimResponse)
async def get_eps_claim(
    claim_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EPSClaimResponse:
    """Return a single EPS claim by ID.

    Returns 404 if the claim does not exist or has been soft-deleted.
    Requires ``eps_claims:read`` permission.
    """
    result = await eps_claim_service.get_claim(db, claim_id)
    return EPSClaimResponse(**result)


# ─── PUT /billing/eps-claims/{claim_id} ───────────────────────────────────────


@router.put("/{claim_id}", response_model=EPSClaimResponse)
async def update_eps_claim(
    claim_id: uuid.UUID,
    body: EPSClaimUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EPSClaimResponse:
    """Update a draft EPS claim.

    All body fields are optional — only the provided fields are updated.
    Returns 409 if the claim is not in draft status.
    Requires ``eps_claims:write`` permission.
    """
    result = await eps_claim_service.update_claim(db, claim_id, data=body)
    return EPSClaimResponse(**result)


# ─── POST /billing/eps-claims/{claim_id}/submit ───────────────────────────────


@router.post("/{claim_id}/submit", response_model=EPSClaimResponse)
async def submit_eps_claim(
    claim_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EPSClaimResponse:
    """Submit a draft claim to the EPS provider.

    Transitions the claim from status=draft to status=submitted and records
    the external_claim_id assigned by the EPS system.  Returns 409 if the
    claim has already been submitted.  Returns 503 if the EPS adapter is
    unreachable.

    Requires ``eps_claims:write`` permission.
    """
    result = await eps_claim_service.submit_claim(db, claim_id)
    return EPSClaimResponse(**result)


# ─── POST /billing/eps-claims/{claim_id}/sync-status ─────────────────────────


@router.post("/{claim_id}/sync-status", response_model=EPSClaimResponse)
async def sync_eps_claim_status(
    claim_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("eps_claims:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EPSClaimResponse:
    """Query the EPS provider for the latest status of a submitted claim.

    Updates local status, error_message, and response_at.  If the EPS has
    acknowledged the claim, acknowledged_at is also set.  Returns 422 if the
    claim has not been submitted yet (no external_claim_id).  Returns 503 if
    the EPS adapter is unreachable.

    Requires ``eps_claims:write`` permission.
    """
    result = await eps_claim_service.sync_status(db, claim_id)
    return EPSClaimResponse(**result)
