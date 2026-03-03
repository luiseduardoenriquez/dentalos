"""Staff-facing loyalty points endpoints.

Endpoint map:
  POST /loyalty/redeem      -- Redeem points for a patient (loyalty:write)
  GET  /loyalty/leaderboard -- Top patients by points balance (loyalty:read)
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.loyalty import (
    LeaderboardResponse,
    RedeemRequest,
    RedeemResponse,
)
from app.services.loyalty_service import loyalty_service

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.post("/redeem", response_model=RedeemResponse)
async def redeem_points(
    body: RedeemRequest,
    current_user: AuthenticatedUser = Depends(require_permission("loyalty:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Redeem loyalty points for a patient. Requires loyalty:write permission."""
    result = await loyalty_service.redeem_points(
        db=db,
        patient_id=uuid.UUID(body.patient_id),
        points=body.points,
        reason=body.reason,
        performed_by=uuid.UUID(current_user.user_id),
    )
    return result


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(require_permission("loyalty:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get the loyalty points leaderboard. Requires loyalty:read permission."""
    return await loyalty_service.get_leaderboard(db=db, limit=limit)
