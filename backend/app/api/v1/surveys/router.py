"""Staff-facing NPS/CSAT survey routes — VP-21.

Endpoint map:
  GET  /analytics/nps              — NPS dashboard (promoters/passives/detractors + trend)
  GET  /analytics/nps/by-doctor    — NPS breakdown per doctor
  POST /surveys/send               — Send a new NPS survey to a patient
  GET  /surveys                    — Paginated list of survey responses
"""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.nps_survey import (
    NPSByDoctorResponse,
    NPSDashboardResponse,
    NPSSurveyListResponse,
    NPSSurveyResponse,
    NPSSurveySendRequest,
)
from app.services.nps_survey_service import nps_survey_service

logger = logging.getLogger("dentalos.surveys")

router = APIRouter(tags=["surveys"])


# ── GET /analytics/nps ────────────────────────────────────────────────────────


@router.get(
    "/analytics/nps",
    response_model=NPSDashboardResponse,
    summary="NPS/CSAT dashboard",
)
async def get_nps_dashboard(
    start_date: date | None = Query(
        default=None,
        alias="start_date",
        description="Filter responses from this date (inclusive).",
    ),
    end_date: date | None = Query(
        default=None,
        alias="end_date",
        description="Filter responses up to this date (inclusive).",
    ),
    current_user: AuthenticatedUser = Depends(require_permission("surveys:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> NPSDashboardResponse:
    """Aggregated NPS dashboard: promoters, passives, detractors, score, and monthly trend.

    Promoters = NPS 9-10. Passives = 7-8. Detractors = 0-6.
    NPS score = (promoters% - detractors%) of total responded.
    """
    result = await nps_survey_service.get_nps_dashboard(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(
        "nps_dashboard served: tenant=%s total=%d",
        current_user.tenant.tenant_id[:8],
        result["total_responses"],
    )
    return NPSDashboardResponse(**result)


# ── GET /analytics/nps/by-doctor ─────────────────────────────────────────────


@router.get(
    "/analytics/nps/by-doctor",
    response_model=NPSByDoctorResponse,
    summary="NPS breakdown per doctor",
)
async def get_nps_by_doctor(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("surveys:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> NPSByDoctorResponse:
    """Per-doctor NPS breakdown — promoters, passives, detractors, and NPS score.

    Only doctors with at least one responded survey are included.
    """
    result = await nps_survey_service.get_nps_by_doctor(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(
        "nps_by_doctor served: tenant=%s doctors=%d",
        current_user.tenant.tenant_id[:8],
        len(result["items"]),
    )
    return NPSByDoctorResponse(**result)


# ── POST /surveys/send ────────────────────────────────────────────────────────


@router.post(
    "/surveys/send",
    response_model=NPSSurveyResponse,
    status_code=201,
    summary="Send an NPS survey to a patient",
)
async def send_nps_survey(
    body: NPSSurveySendRequest,
    current_user: AuthenticatedUser = Depends(require_permission("surveys:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> NPSSurveyResponse:
    """Create and dispatch an NPS/CSAT survey for a patient.

    Returns the survey record (including the token) so the caller
    can trigger a notification via the queue if needed.
    """
    result = await nps_survey_service.send_survey(
        db=db,
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        appointment_id=body.appointment_id,
        channel=body.channel,
    )
    logger.info(
        "NPS survey sent: tenant=%s channel=%s",
        current_user.tenant.tenant_id[:8],
        body.channel,
    )
    return NPSSurveyResponse(**result)


# ── GET /surveys ──────────────────────────────────────────────────────────────


@router.get(
    "/surveys",
    response_model=NPSSurveyListResponse,
    summary="List NPS survey responses",
)
async def list_nps_surveys(
    doctor_id: UUID | None = Query(
        default=None,
        description="Filter surveys by doctor.",
    ),
    responded: bool | None = Query(
        default=None,
        description="True = only responded, False = only pending, omit = all.",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("surveys:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> NPSSurveyListResponse:
    """Paginated list of NPS survey records.

    Optional filters: ?doctor_id=<uuid> and/or ?responded=true|false.
    """
    result = await nps_survey_service.list_surveys(
        db=db,
        doctor_id=doctor_id,
        responded=responded,
        page=page,
        page_size=page_size,
    )
    return NPSSurveyListResponse(**result)
