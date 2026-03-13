"""Marketing API routes — VP-17 Email Marketing Campaigns.

Endpoint map (all JWT-protected):
  POST   /marketing/campaigns                        — Create campaign
  GET    /marketing/campaigns                        — List campaigns (paginated)
  GET    /marketing/campaigns/{id}                   — Get single campaign
  PUT    /marketing/campaigns/{id}                   — Update draft campaign
  POST   /marketing/campaigns/{id}/send              — Dispatch campaign → 202
  POST   /marketing/campaigns/{id}/schedule          — Schedule campaign
  DELETE /marketing/campaigns/{id}                   — Soft-delete / cancel
  GET    /marketing/campaigns/{id}/stats             — Engagement stats
  GET    /marketing/campaigns/{id}/recipients        — Paginated recipient list
  GET    /marketing/templates                        — Built-in template catalogue

All write endpoints require the 'marketing:write' permission (clinic_owner).
All read endpoints require 'marketing:read'.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.exceptions import DentalOSError
from app.schemas.email_campaign import (
    CampaignListResponse,
    CampaignRecipientListResponse,
    CampaignRecipientResponse,
    CampaignStatsResponse,
    EmailCampaignCreate,
    EmailCampaignResponse,
    EmailCampaignUpdate,
    EmailTemplateResponse,
    ScheduleRequest,
)
from app.services.email_campaign_service import email_campaign_service

router = APIRouter(prefix="/marketing", tags=["marketing"])


# ── Create campaign ───────────────────────────────────────────────────────────


@router.post(
    "/campaigns",
    response_model=EmailCampaignResponse,
    status_code=201,
    summary="Crear campaña de email",
)
async def create_campaign(
    body: EmailCampaignCreate,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmailCampaignResponse:
    """Create a new email marketing campaign in draft status."""
    data = body.model_dump()
    result = await email_campaign_service.create_campaign(
        db=db,
        data=data,
        created_by=uuid.UUID(str(current_user.user_id)),
    )
    return EmailCampaignResponse(**result)


# ── List campaigns ────────────────────────────────────────────────────────────


@router.get(
    "/campaigns",
    response_model=CampaignListResponse,
    summary="Listar campañas de email",
)
async def list_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("marketing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CampaignListResponse:
    """Return a paginated list of all active email campaigns."""
    result = await email_campaign_service.list_campaigns(
        db=db, page=page, page_size=page_size
    )
    return CampaignListResponse(
        items=[EmailCampaignResponse(**c) for c in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ── Get single campaign ───────────────────────────────────────────────────────


@router.get(
    "/campaigns/{campaign_id}",
    response_model=EmailCampaignResponse,
    summary="Obtener campaña de email",
)
async def get_campaign(
    campaign_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmailCampaignResponse:
    """Fetch a single campaign by ID."""
    result = await email_campaign_service.get_campaign(db=db, campaign_id=campaign_id)
    if result is None:
        from app.core.error_codes import MarketingErrors

        raise DentalOSError(
            error=MarketingErrors.CAMPAIGN_NOT_FOUND,
            message="Campaña de email no encontrada.",
            status_code=404,
            details={"campaign_id": str(campaign_id)},
        )
    return EmailCampaignResponse(**result)


# ── Update draft campaign ─────────────────────────────────────────────────────


@router.put(
    "/campaigns/{campaign_id}",
    response_model=EmailCampaignResponse,
    summary="Actualizar campaña en borrador",
)
async def update_campaign(
    campaign_id: uuid.UUID,
    body: EmailCampaignUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmailCampaignResponse:
    """Update name, subject, template HTML, or segment filters on a draft campaign."""
    result = await email_campaign_service.update_campaign(
        db=db,
        campaign_id=campaign_id,
        data=body.model_dump(exclude_unset=True),
    )
    return EmailCampaignResponse(**result)


# ── Send campaign ─────────────────────────────────────────────────────────────


@router.post(
    "/campaigns/{campaign_id}/send",
    status_code=202,
    summary="Enviar campaña de email",
)
async def send_campaign(
    campaign_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> JSONResponse:
    """Dispatch a draft or scheduled campaign.

    Identifies recipients, bulk-inserts them, advances status to 'sending',
    and enqueues the batch email job. Returns 202 Accepted.
    """
    result = await email_campaign_service.send_campaign(
        db=db,
        campaign_id=campaign_id,
        tenant_id=str(current_user.tenant.tenant_id),
    )
    return JSONResponse(
        status_code=202,
        content={
            "campaign_id": str(result["campaign_id"]),
            "status": result["status"],
            "recipient_count": result["recipient_count"],
            "queued": result["queued"],
            "message": (
                f"Campaña puesta en cola para envío a "
                f"{result['recipient_count']} destinatario(s)."
            ),
        },
    )


# ── Schedule campaign ─────────────────────────────────────────────────────────


@router.post(
    "/campaigns/{campaign_id}/schedule",
    response_model=EmailCampaignResponse,
    summary="Programar campaña para envío futuro",
)
async def schedule_campaign(
    campaign_id: uuid.UUID,
    body: ScheduleRequest,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmailCampaignResponse:
    """Schedule a draft campaign to be dispatched at a future UTC datetime."""
    result = await email_campaign_service.schedule_campaign(
        db=db,
        campaign_id=campaign_id,
        scheduled_at=body.scheduled_at,
    )
    return EmailCampaignResponse(**result)


# ── Delete / cancel campaign ──────────────────────────────────────────────────


@router.delete(
    "/campaigns/{campaign_id}",
    response_model=EmailCampaignResponse,
    summary="Eliminar o cancelar campaña",
)
async def delete_campaign(
    campaign_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmailCampaignResponse:
    """Soft-delete a draft campaign or cancel a scheduled one."""
    result = await email_campaign_service.delete_campaign(
        db=db, campaign_id=campaign_id
    )
    return EmailCampaignResponse(**result)


# ── Campaign stats ────────────────────────────────────────────────────────────


@router.get(
    "/campaigns/{campaign_id}/stats",
    response_model=CampaignStatsResponse,
    summary="Estadísticas de engagement de la campaña",
)
async def get_campaign_stats(
    campaign_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("marketing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CampaignStatsResponse:
    """Return aggregated open/click/bounce/unsubscribe stats for a campaign."""
    result = await email_campaign_service.get_campaign_stats(
        db=db, campaign_id=campaign_id
    )
    return CampaignStatsResponse(**result)


# ── Campaign recipients ───────────────────────────────────────────────────────


@router.get(
    "/campaigns/{campaign_id}/recipients",
    response_model=CampaignRecipientListResponse,
    summary="Destinatarios de la campaña",
)
async def get_campaign_recipients(
    campaign_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(require_permission("marketing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CampaignRecipientListResponse:
    """Return a paginated list of recipients with their delivery status."""
    result = await email_campaign_service.get_campaign_recipients(
        db=db, campaign_id=campaign_id, page=page, page_size=page_size
    )
    return CampaignRecipientListResponse(
        items=[CampaignRecipientResponse(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ── Templates ─────────────────────────────────────────────────────────────────


@router.get(
    "/templates",
    response_model=list[EmailTemplateResponse],
    summary="Plantillas de email disponibles",
)
async def list_templates(
    current_user: AuthenticatedUser = Depends(require_permission("marketing:read")),
) -> list[EmailTemplateResponse]:
    """Return the built-in catalogue of Spanish marketing email templates."""
    templates = email_campaign_service.get_templates()
    return [EmailTemplateResponse(**t) for t in templates]
