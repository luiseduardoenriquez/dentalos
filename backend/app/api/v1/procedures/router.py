"""Procedure API routes — CR-12, CR-13, CR-14.

Endpoint map:
  POST /patients/{patient_id}/procedures                — Record procedure
  GET  /patients/{patient_id}/procedures                — List procedures
  GET  /patients/{patient_id}/procedures/{procedure_id} — Get procedure detail
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureListResponse,
    ProcedureResponse,
)
from app.services.procedure_service import procedure_service

router = APIRouter(prefix="/patients/{patient_id}/procedures", tags=["procedures"])


@router.post("", response_model=ProcedureResponse, status_code=201)
async def create_procedure(
    patient_id: str,
    body: ProcedureCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("procedures:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProcedureResponse:
    """Record a new clinical procedure."""
    materials = None
    if body.materials_used:
        materials = [m.model_dump() for m in body.materials_used]

    result = await procedure_service.create_procedure(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        cups_code=body.cups_code,
        cups_description=body.cups_description,
        tooth_number=body.tooth_number,
        zones=body.zones,
        materials_used=materials,
        duration_minutes=body.duration_minutes,
        notes=body.notes,
        treatment_plan_item_id=body.treatment_plan_item_id,
        clinical_record_id=body.clinical_record_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="procedure",
        resource_id=result["id"],
    )

    return ProcedureResponse(**result)


@router.get("", response_model=ProcedureListResponse)
async def list_procedures(
    patient_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("procedures:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProcedureListResponse:
    """List procedures for a patient (cursor-paginated)."""
    result = await procedure_service.list_procedures(
        db=db,
        patient_id=patient_id,
        cursor=cursor,
        limit=limit,
    )
    return ProcedureListResponse(
        items=[ProcedureResponse(**p) for p in result["items"]],
        next_cursor=result["next_cursor"],
        has_more=result["has_more"],
    )


@router.get("/{procedure_id}", response_model=ProcedureResponse)
async def get_procedure(
    patient_id: str,
    procedure_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("procedures:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProcedureResponse:
    """Get procedure detail by ID."""
    result = await procedure_service.get_procedure(
        db=db,
        patient_id=patient_id,
        procedure_id=procedure_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="PROCEDURE_not_found",
            resource_name="Procedure",
        )
    return ProcedureResponse(**result)
