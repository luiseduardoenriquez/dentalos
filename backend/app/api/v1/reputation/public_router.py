"""Public survey response endpoint — VP-09 Reputation Management.

No authentication required. Uses tenant slug for resolution and
survey token for authorization.

Endpoint:
  POST /public/{slug}/survey/{token} — Submit a survey response
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.core.tenant import validate_schema_name
from app.models.public.tenant import Tenant
from app.schemas.reputation import SurveyPublicResponse

logger = logging.getLogger("dentalos.public_reputation")

router = APIRouter(prefix="/public", tags=["public-reputation"])


async def _resolve_tenant_by_slug(slug: str, db: AsyncSession) -> Tenant:
    """Resolve an active tenant from a URL slug.

    Queries public.tenants and returns the Tenant ORM object.

    Raises:
        HTTPException (404) -- slug does not exist or tenant is not active.
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


@router.post("/{slug}/survey/{token}")
async def submit_survey_response(
    slug: str,
    token: str,
    body: SurveyPublicResponse,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a satisfaction survey response (public, no auth required).

    Flow:
      1. Rate limit (20 per hour per IP).
      2. Resolve tenant by slug.
      3. Validate schema name.
      4. Switch to tenant schema.
      5. Record response via reputation_service.
      6. Return routing info (google_review or private_feedback).
    """
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(f"rl:public_survey:{ip}", limit=20, window_seconds=3600)

    tenant = await _resolve_tenant_by_slug(slug, db)

    schema = tenant.schema_name
    if not validate_schema_name(schema):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TENANT_invalid_schema",
                "message": "Internal configuration error.",
                "details": {},
            },
        )

    await db.execute(text(f"SET search_path TO {schema}, public"))

    # Extract tenant settings for routing configuration
    tenant_settings = tenant.settings or {}

    from app.services.reputation_service import reputation_service

    result = await reputation_service.record_response(
        db=db,
        token=token,
        score=body.score,
        feedback_text=body.feedback_text,
        tenant_settings=tenant_settings,
    )

    return result
