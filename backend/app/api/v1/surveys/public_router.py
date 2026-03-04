"""Public NPS/CSAT survey endpoints — VP-21.

No authentication required. Uses tenant slug for resolution and
survey token for authorization.

Endpoint map:
  GET  /public/{slug}/nps-survey/{token} — Return survey info for the patient
  POST /public/{slug}/nps-survey/{token} — Submit the NPS/CSAT response
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.core.tenant import validate_schema_name
from app.models.public.tenant import Tenant
from app.schemas.nps_survey import NPSSurveyPublicInfo, NPSSurveySubmission

logger = logging.getLogger("dentalos.public_nps_survey")

router = APIRouter(prefix="/public", tags=["surveys-public"])


# ── Internal Helpers ─────────────────────────────────────────────────────────


async def _resolve_tenant_by_slug(slug: str, db: AsyncSession) -> Tenant:
    """Resolve an active tenant from a URL slug.

    Raises:
        HTTPException (404) — slug does not exist or tenant is not active.
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == slug,
            Tenant.status == "active",
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TENANT_not_found",
                "message": "No se encontro una clinica activa con ese enlace.",
                "details": {},
            },
        )
    return tenant


def _assert_valid_schema(schema: str) -> None:
    """Raise 500 if the resolved tenant schema name is invalid."""
    if not validate_schema_name(schema):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TENANT_invalid_schema",
                "message": "Internal configuration error.",
                "details": {},
            },
        )


# ── GET /public/{slug}/nps-survey/{token} ────────────────────────────────────


@router.get(
    "/{slug}/nps-survey/{token}",
    response_model=NPSSurveyPublicInfo,
    summary="Get NPS survey info for the patient",
)
async def get_nps_survey_info(
    slug: str,
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> NPSSurveyPublicInfo:
    """Return survey metadata so the patient can see doctor + clinic name.

    - 200 with already_responded=True if survey was already filled.
    - 404 if token does not exist.
    - 400 if token is invalid (no matching survey).
    """
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(f"rl:public_nps_info:{ip}", limit=60, window_seconds=3600)

    tenant = await _resolve_tenant_by_slug(slug, db)
    _assert_valid_schema(tenant.schema_name)

    await db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))

    from app.services.nps_survey_service import nps_survey_service

    survey = await nps_survey_service.get_survey_by_token(db=db, token=token)
    if survey is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SURVEY_not_found",
                "message": "Encuesta no encontrada.",
                "details": {},
            },
        )

    # Load doctor name from users table
    from sqlalchemy import select as sa_select
    from app.models.tenant.user import User

    doctor_name = "Médico"
    if survey.doctor_id is not None:
        doc_result = await db.execute(
            sa_select(User.name).where(User.id == survey.doctor_id)
        )
        doctor_name = doc_result.scalar_one_or_none() or "Médico"

    already_responded = survey.responded_at is not None

    logger.info(
        "NPS survey info fetched: survey_id=%s already_responded=%s",
        str(survey.id)[:8],
        already_responded,
    )

    return NPSSurveyPublicInfo(
        doctor_name=doctor_name,
        clinic_name=tenant.name,
        already_responded=already_responded,
    )


# ── POST /public/{slug}/nps-survey/{token} ───────────────────────────────────


@router.post(
    "/{slug}/nps-survey/{token}",
    summary="Submit an NPS/CSAT survey response",
)
async def submit_nps_survey(
    slug: str,
    token: str,
    body: NPSSurveySubmission,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a patient's NPS and optional CSAT response (no auth required).

    Flow:
      1. Rate limit (20 per hour per IP).
      2. Resolve tenant by slug.
      3. Validate schema name.
      4. Switch to tenant schema.
      5. Submit response via nps_survey_service.
      6. Return thank-you message.

    Errors:
      - 404 if token not found.
      - 409 if already responded.
      - 422 if score is out of valid range.
    """
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(f"rl:public_nps_submit:{ip}", limit=20, window_seconds=3600)

    tenant = await _resolve_tenant_by_slug(slug, db)
    _assert_valid_schema(tenant.schema_name)

    await db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))

    from app.services.nps_survey_service import nps_survey_service

    await nps_survey_service.submit_response(
        db=db,
        token=token,
        nps_score=body.nps_score,
        csat_score=body.csat_score,
        comments=body.comments,
    )

    logger.info(
        "NPS survey submitted: tenant=%s nps_score=%d",
        slug,
        body.nps_score,
    )

    return {
        "message": "Gracias por tu opinion. Tu respuesta ha sido registrada.",
    }
