"""Patient portal loyalty points endpoint.

Endpoint map:
  GET /portal/loyalty -- Get the patient's loyalty balance and recent transactions
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.database import get_tenant_db
from app.schemas.loyalty import PortalLoyaltyResponse
from app.services.loyalty_service import loyalty_service

router = APIRouter(prefix="/portal", tags=["portal-loyalty"])


@router.get("/loyalty", response_model=PortalLoyaltyResponse)
async def get_my_loyalty(
    limit: int = Query(default=20, ge=1, le=50),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get loyalty balance and recent transactions for the current patient."""
    return await loyalty_service.get_portal_loyalty(
        db=db,
        patient_id=uuid.UUID(portal_user.patient_id),
        limit=limit,
    )
