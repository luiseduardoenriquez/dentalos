"""Public intake form submission — VP-03.

No authentication required. Uses tenant slug for resolution.

Endpoint:
  POST /public/{slug}/intake — Submit an intake form
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.core.tenant import validate_schema_name
from app.models.public.tenant import Tenant
from app.schemas.intake import IntakeSubmissionCreate, IntakeSubmissionResponse

logger = logging.getLogger("dentalos.public_intake")

router = APIRouter(prefix="/public", tags=["public-intake"])


async def resolve_tenant_by_slug(slug: str, db: AsyncSession) -> Tenant:
    """Resolve an active tenant from a URL slug.

    Queries public.tenants and returns the Tenant ORM object.

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


@router.post("/{slug}/intake", response_model=IntakeSubmissionResponse, status_code=201)
async def submit_public_intake(
    slug: str,
    body: IntakeSubmissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IntakeSubmissionResponse:
    """Submit an intake form from a public link (no auth required).

    Flow:
      1. Rate limit (10 per hour per IP).
      2. Resolve tenant by slug.
      3. Validate schema name.
      4. Switch to tenant schema.
      5. Create submission via intake_service.
      6. Return submission confirmation.
    """
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(f"rl:public_intake:{ip}", limit=10, window_seconds=3600)

    tenant = await resolve_tenant_by_slug(slug, db)

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

    from app.services.intake_service import intake_service

    result = await intake_service.create_submission(
        db=db,
        template_id=body.template_id,
        data=body.data,
        appointment_id=body.appointment_id,
    )
    return IntakeSubmissionResponse(**result)
