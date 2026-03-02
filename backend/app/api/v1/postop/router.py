"""Post-operative instruction endpoints — VP-20.

Endpoint map:
  GET  /postop/templates                     — List templates (optionally filtered)
  POST /postop/templates                     — Create template (clinic_owner)
  PUT  /postop/templates/{template_id}       — Update template (clinic_owner)
  GET  /postop/templates/{template_id}       — Get single template
  POST /postop/send/{patient_id}             — Send instructions to patient
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.postop import (
    PostopSendRequest,
    PostopSendResponse,
    PostopTemplateCreate,
    PostopTemplateListResponse,
    PostopTemplateResponse,
    PostopTemplateUpdate,
)
from app.services.postop_service import postop_service

router = APIRouter(prefix="/postop", tags=["postop"])


@router.get("/templates", response_model=PostopTemplateListResponse)
async def list_templates(
    procedure_type: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("postop:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """List post-op instruction templates, optionally filtered by procedure_type."""
    return await postop_service.list_templates(db=db, procedure_type=procedure_type)


@router.post("/templates", response_model=PostopTemplateResponse, status_code=201)
async def create_template(
    body: PostopTemplateCreate,
    current_user: AuthenticatedUser = Depends(require_permission("postop:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Create a new post-op instruction template. clinic_owner only."""
    return await postop_service.create_template(
        db=db,
        procedure_type=body.procedure_type,
        title=body.title,
        instruction_content=body.instruction_content,
        channel_preference=body.channel_preference,
        is_default=body.is_default,
    )


@router.get("/templates/{template_id}", response_model=PostopTemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: AuthenticatedUser = Depends(require_permission("postop:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get a single post-op instruction template by id."""
    return await postop_service.get_template(db=db, template_id=template_id)


@router.put("/templates/{template_id}", response_model=PostopTemplateResponse)
async def update_template(
    template_id: UUID,
    body: PostopTemplateUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("postop:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Update a post-op instruction template. clinic_owner only."""
    return await postop_service.update_template(
        db=db,
        template_id=template_id,
        **body.model_dump(exclude_unset=True),
    )


@router.post("/send/{patient_id}", response_model=PostopSendResponse)
async def send_postop_instructions(
    patient_id: UUID,
    body: PostopSendRequest,
    current_user: AuthenticatedUser = Depends(require_permission("postop:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Send post-op instructions to a patient. doctor/assistant."""
    template_uuid = UUID(body.template_id) if body.template_id else None
    return await postop_service.send_instructions(
        db=db,
        patient_id=patient_id,
        procedure_type=body.procedure_type,
        template_id=template_uuid,
        tenant_id=current_user.tenant.tenant_id,
    )
