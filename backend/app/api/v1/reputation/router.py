"""Staff-facing reputation management routes — VP-09.

Endpoint map:
  POST /reputation/surveys/send  — Send a satisfaction survey to a patient
  GET  /reputation/dashboard     — Aggregated reputation metrics
  GET  /reputation/feedback      — List private feedback (clinic_owner only)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission, require_role
from app.core.database import get_tenant_db
from app.schemas.reputation import (
    DashboardResponse,
    FeedbackListResponse,
    SurveyCreate,
    SurveyResponse,
)
from app.services.reputation_service import reputation_service

router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.post("/surveys/send", response_model=SurveyResponse, status_code=201)
async def send_survey(
    body: SurveyCreate,
    current_user: AuthenticatedUser = Depends(require_permission("reputation:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SurveyResponse:
    """Send a satisfaction survey to a patient after an appointment."""
    result = await reputation_service.send_survey(
        db=db,
        appointment_id=body.appointment_id,
        channel=body.channel,
        tenant_id=current_user.tenant.tenant_id,
    )
    return SurveyResponse(**result)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: AuthenticatedUser = Depends(require_permission("reputation:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DashboardResponse:
    """Get aggregated reputation dashboard metrics."""
    result = await reputation_service.get_dashboard(db=db)
    return DashboardResponse(**result)


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"]),
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> FeedbackListResponse:
    """List private feedback from patients (clinic_owner only).

    Shows survey responses where the patient gave a low score and was
    routed to private feedback instead of Google Reviews.
    """
    result = await reputation_service.get_feedback(
        db=db, page=page, page_size=page_size,
    )
    return FeedbackListResponse(**result)
