"""Intake form API routes — VP-03 (staff-facing).

Endpoint map:
  POST /intake/templates                   — Create template
  GET  /intake/templates                   — List templates
  PUT  /intake/templates/{template_id}     — Update template
  GET  /intake/submissions                 — List submissions
  POST /intake/submissions/{sub_id}/approve — Approve and auto-populate records
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.intake import (
    IntakeSubmissionResponse,
    IntakeTemplateCreate,
    IntakeTemplateResponse,
    IntakeTemplateUpdate,
)
from app.services.intake_service import intake_service

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/templates", response_model=IntakeTemplateResponse, status_code=201)
async def create_template(
    body: IntakeTemplateCreate,
    current_user: AuthenticatedUser = Depends(require_permission("intake:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> IntakeTemplateResponse:
    """Create a new intake form template."""
    fields_data = [f.model_dump() for f in body.fields]
    result = await intake_service.create_template(
        db=db,
        created_by=str(current_user.user_id),
        name=body.name,
        fields=fields_data,
        consent_template_ids=body.consent_template_ids,
        is_default=body.is_default,
    )
    return IntakeTemplateResponse(**result)


@router.get("/templates", response_model=list[IntakeTemplateResponse])
async def list_templates(
    include_inactive: bool = Query(default=False),
    current_user: AuthenticatedUser = Depends(require_permission("intake:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[IntakeTemplateResponse]:
    """List intake form templates."""
    results = await intake_service.list_templates(db=db, include_inactive=include_inactive)
    return [IntakeTemplateResponse(**r) for r in results]


@router.put("/templates/{template_id}", response_model=IntakeTemplateResponse)
async def update_template(
    template_id: str,
    body: IntakeTemplateUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("intake:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> IntakeTemplateResponse:
    """Update an intake form template."""
    update_data = body.model_dump(exclude_unset=True)
    if "fields" in update_data and update_data["fields"] is not None:
        update_data["fields"] = [
            f.model_dump() if hasattr(f, "model_dump") else f for f in body.fields
        ]
    result = await intake_service.update_template(
        db=db, template_id=template_id, **update_data,
    )
    return IntakeTemplateResponse(**result)


@router.get("/submissions")
async def list_submissions(
    status: str | None = Query(
        default=None, pattern=r"^(pending|reviewed|approved|rejected)$"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("intake:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """List intake form submissions."""
    return await intake_service.list_submissions(
        db=db, status=status, page=page, page_size=page_size,
    )


@router.post("/submissions/{submission_id}/approve", response_model=IntakeSubmissionResponse)
async def approve_submission(
    submission_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("intake:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> IntakeSubmissionResponse:
    """Approve a submission and auto-populate patient records."""
    result = await intake_service.approve_submission(
        db=db, submission_id=submission_id, reviewed_by=str(current_user.user_id),
    )
    return IntakeSubmissionResponse(**result)
