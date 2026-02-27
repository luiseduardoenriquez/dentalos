"""Evolution templates API routes — CR-15, CR-16.

Endpoint map:
  GET  /evolution-templates — CR-15: List templates (optionally by procedure type)
  POST /evolution-templates — CR-16: Create a custom template

Evolution templates define reusable step-by-step clinical procedure flows.
Built-in templates (is_builtin=True) are seeded at startup and cannot be
modified via this API — only tenant-created templates are mutable.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_tenant_db
from app.schemas.evolution_template import (
    EvolutionTemplateCreate,
    EvolutionTemplateListItem,
    EvolutionTemplateListResponse,
    EvolutionTemplateResponse,
)
from app.services.evolution_template_service import evolution_template_service

router = APIRouter(prefix="/evolution-templates", tags=["evolution-templates"])


# ─── CR-15: List evolution templates ─────────────────────────────────────────


@router.get("", response_model=EvolutionTemplateListResponse)
async def list_evolution_templates(
    procedure_type: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> EvolutionTemplateListResponse:
    """Return all evolution templates available to the current tenant.

    Includes both built-in templates (seeded at startup) and any custom
    templates created by the clinic. Optionally filtered by procedure type.
    No audit event is emitted (read-only).
    """
    result = await evolution_template_service.list_templates(
        db=db,
        procedure_type=procedure_type,
    )
    return EvolutionTemplateListResponse(
        items=[EvolutionTemplateListItem(**t) for t in result["items"]],
        total=result["total"],
    )


# ─── CR-16: Create evolution template ────────────────────────────────────────


@router.post("", response_model=EvolutionTemplateResponse, status_code=201)
async def create_evolution_template(
    body: EvolutionTemplateCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("clinical_records:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> EvolutionTemplateResponse:
    """Create a custom evolution template for the current tenant.

    Templates must contain at least one ordered step. Variables define
    placeholder slots that clinicians fill in when applying the template
    to a clinical record. Created templates are immediately available to
    all staff in the tenant.
    """
    result = await evolution_template_service.create_template(
        db=db,
        name=body.name,
        procedure_type=body.procedure_type,
        cups_code=body.cups_code,
        complexity=body.complexity,
        steps=[s.model_dump() for s in body.steps],
        variables=[v.model_dump() for v in body.variables] if body.variables else None,
    )
    return EvolutionTemplateResponse(**result)
