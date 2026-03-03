"""Schedule Intelligence API routes — VP-10.

Endpoint map:
  GET /analytics/schedule-intelligence  — Combined no-show risk, gaps, utilization
  GET /analytics/suggested-fills        — Paginated fill suggestions for gaps

Both endpoints require ``schedule_intelligence:read`` permission.
"""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.cache import get_cached, set_cached
from app.core.database import get_tenant_db
from app.schemas.schedule_intelligence import (
    IntelligenceResponse,
    SuggestedFillsResponse,
)
from app.services.schedule_intelligence_service import schedule_intelligence_service

logger = logging.getLogger("dentalos.schedule_intelligence")

router = APIRouter(prefix="/analytics", tags=["analytics", "schedule-intelligence"])

# Cache TTL for intelligence results (seconds).
_INTELLIGENCE_CACHE_TTL = 60


# ── GET /analytics/schedule-intelligence ─────────────────────────────────────


@router.get(
    "/schedule-intelligence",
    response_model=IntelligenceResponse,
    summary="Schedule intelligence for a target date",
)
async def get_schedule_intelligence(
    target_date: date = Query(
        default=None,
        alias="date",
        description="Target date (defaults to today).",
    ),
    doctor_id: UUID | None = Query(
        default=None,
        description="Filter to a specific doctor.",
    ),
    current_user: AuthenticatedUser = Depends(
        require_permission("schedule_intelligence:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> IntelligenceResponse:
    """Aggregated schedule intelligence: no-show risks, gaps, and utilization.

    Combines three parallel queries into a single response. Results are
    cached for 60 seconds per tenant+date+doctor combination.
    """
    if target_date is None:
        target_date = date.today()

    tenant_id = current_user.tenant.tenant_id

    # Try cache first
    cache_key = (
        f"dentalos:{tenant_id}:analytics:schedule_intelligence:"
        f"{target_date.isoformat()}:{doctor_id or 'all'}"
    )
    cached = await get_cached(cache_key)
    if cached is not None:
        return IntelligenceResponse(**cached)

    result = await schedule_intelligence_service.get_intelligence(
        db=db,
        target_date=target_date,
        doctor_id=doctor_id,
    )

    # Cache the result (60s TTL)
    await set_cached(cache_key, result, ttl_seconds=_INTELLIGENCE_CACHE_TTL)

    logger.info(
        "schedule_intelligence served: tenant=%s date=%s doctor=%s",
        tenant_id[:8],
        target_date.isoformat(),
        str(doctor_id)[:8] if doctor_id else "all",
    )

    return IntelligenceResponse(**result)


# ── GET /analytics/suggested-fills ───────────────────────────────────────────


@router.get(
    "/suggested-fills",
    response_model=SuggestedFillsResponse,
    summary="Paginated fill suggestions for schedule gaps",
)
async def get_suggested_fills(
    target_date: date = Query(
        default=None,
        alias="date",
        description="Target date (defaults to today).",
    ),
    doctor_id: UUID | None = Query(
        default=None,
        description="Filter to a specific doctor.",
    ),
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page."
    ),
    current_user: AuthenticatedUser = Depends(
        require_permission("schedule_intelligence:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> SuggestedFillsResponse:
    """Paginated list of suggested patients to fill schedule gaps.

    Combines gap analysis with waitlist, recall, and pending treatment plan
    data to suggest optimal fill candidates with contact information.
    """
    if target_date is None:
        target_date = date.today()

    result = await schedule_intelligence_service.suggest_fills(
        db=db,
        target_date=target_date,
        doctor_id=doctor_id,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "suggested_fills served: tenant=%s date=%s total=%d",
        current_user.tenant.tenant_id[:8],
        target_date.isoformat(),
        result["total"],
    )

    return SuggestedFillsResponse(**result)
