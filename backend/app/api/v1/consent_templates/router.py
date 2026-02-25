"""Consent template API routes — IC-01, IC-02, IC-03.

Endpoint map:
  GET  /consent-templates              — List templates (public + tenant)
  POST /consent-templates              — Create tenant template
  GET  /consent-templates/{template_id} — Get template detail
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.consent import (
    ConsentTemplateCreate,
    ConsentTemplateListResponse,
    ConsentTemplateResponse,
)
from app.services.consent_service import consent_service

router = APIRouter(prefix="/consent-templates", tags=["consent-templates"])


@router.get("", response_model=ConsentTemplateListResponse)
async def list_consent_templates(
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentTemplateListResponse:
    """List all consent templates (public builtin + tenant custom)."""
    result = await consent_service.list_templates(db=db)
    return ConsentTemplateListResponse(
        items=[ConsentTemplateResponse(**t) for t in result["items"]],
        total=result["total"],
    )


@router.post("", response_model=ConsentTemplateResponse, status_code=201)
async def create_consent_template(
    body: ConsentTemplateCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentTemplateResponse:
    """Create a new tenant consent template."""
    result = await consent_service.create_template(
        db=db,
        name=body.name,
        category=body.category,
        content=body.content,
        description=body.description,
        signature_positions=body.signature_positions,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="consent_template",
        resource_id=result["id"],
    )

    return ConsentTemplateResponse(**result)


@router.get("/{template_id}", response_model=ConsentTemplateResponse)
async def get_consent_template(
    template_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentTemplateResponse:
    """Get consent template detail."""
    result = await consent_service.get_template(
        db=db, template_id=template_id
    )
    if result is None:
        raise ResourceNotFoundError(
            error="CONSENT_template_not_found",
            resource_name="ConsentTemplate",
        )
    return ConsentTemplateResponse(**result)
