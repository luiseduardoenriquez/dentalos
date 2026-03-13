"""Recall campaign API routes — VP-02.

Endpoint map:
  POST /recall/campaigns                        — Create campaign
  GET  /recall/campaigns                        — List campaigns with stats
  PUT  /recall/campaigns/{campaign_id}          — Update campaign
  POST /recall/campaigns/{campaign_id}/activate — Activate campaign
  POST /recall/campaigns/{campaign_id}/pause    — Pause campaign
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.recall import (
    RecallCampaignCreate,
    RecallCampaignResponse,
    RecallCampaignUpdate,
)
from app.services.recall_service import recall_service

router = APIRouter(prefix="/recall", tags=["recall"])


@router.post("/campaigns", response_model=RecallCampaignResponse, status_code=201)
async def create_campaign(
    body: RecallCampaignCreate,
    current_user: AuthenticatedUser = Depends(require_permission("recall:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecallCampaignResponse:
    """Create a new recall campaign."""
    data = body.model_dump()
    if data.get("schedule"):
        data["schedule"] = [
            s.model_dump() if hasattr(s, "model_dump") else s for s in body.schedule
        ]
    result = await recall_service.create_campaign(
        db=db, created_by=str(current_user.user_id), **data,
    )
    return RecallCampaignResponse(**result)


@router.get("/campaigns")
async def list_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("recall:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """List recall campaigns with aggregated stats."""
    return await recall_service.list_campaigns(db=db, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}", response_model=RecallCampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("recall:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecallCampaignResponse:
    """Get a single recall campaign by ID."""
    result = await recall_service.get_campaign(db=db, campaign_id=campaign_id)
    return RecallCampaignResponse(**result)


@router.put("/campaigns/{campaign_id}", response_model=RecallCampaignResponse)
async def update_campaign(
    campaign_id: str,
    body: RecallCampaignUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("recall:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecallCampaignResponse:
    """Update a recall campaign."""
    update_data = body.model_dump(exclude_unset=True)
    if "schedule" in update_data and update_data["schedule"] is not None:
        update_data["schedule"] = [
            s.model_dump() if hasattr(s, "model_dump") else s for s in body.schedule
        ]
    result = await recall_service.update_campaign(
        db=db, campaign_id=campaign_id, **update_data,
    )
    return RecallCampaignResponse(**result)


@router.post("/campaigns/{campaign_id}/activate", response_model=RecallCampaignResponse)
async def activate_campaign(
    campaign_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("recall:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecallCampaignResponse:
    """Activate a draft or paused campaign."""
    result = await recall_service.activate_campaign(db=db, campaign_id=campaign_id)
    return RecallCampaignResponse(**result)


@router.post("/campaigns/{campaign_id}/pause", response_model=RecallCampaignResponse)
async def pause_campaign(
    campaign_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("recall:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecallCampaignResponse:
    """Pause an active campaign."""
    result = await recall_service.pause_campaign(db=db, campaign_id=campaign_id)
    return RecallCampaignResponse(**result)
