"""Diagnosis API routes — CR-07, CR-08, CR-09.

Endpoint map:
  POST /patients/{patient_id}/diagnoses                — Create diagnosis
  GET  /patients/{patient_id}/diagnoses                — List diagnoses
  PUT  /patients/{patient_id}/diagnoses/{diagnosis_id} — Update/resolve diagnosis
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.diagnosis import (
    DiagnosisCreate,
    DiagnosisListResponse,
    DiagnosisResponse,
    DiagnosisUpdate,
)
from app.services.diagnosis_service import diagnosis_service

router = APIRouter(prefix="/patients/{patient_id}/diagnoses", tags=["diagnoses"])


@router.post("", response_model=DiagnosisResponse, status_code=201)
async def create_diagnosis(
    patient_id: str,
    body: DiagnosisCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("diagnoses:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> DiagnosisResponse:
    """Create a new diagnosis for a patient."""
    result = await diagnosis_service.create_diagnosis(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        cie10_code=body.cie10_code,
        cie10_description=body.cie10_description,
        severity=body.severity,
        tooth_number=body.tooth_number,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="diagnosis",
        resource_id=result["id"],
    )

    return DiagnosisResponse(**result)


@router.get("", response_model=DiagnosisListResponse)
async def list_diagnoses(
    patient_id: str,
    status: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(
        require_permission("diagnoses:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> DiagnosisListResponse:
    """List all diagnoses for a patient."""
    result = await diagnosis_service.list_diagnoses(
        db=db,
        patient_id=patient_id,
        status_filter=status,
    )
    return DiagnosisListResponse(
        items=[DiagnosisResponse(**d) for d in result["items"]],
        total=result["total"],
    )


@router.put("/{diagnosis_id}", response_model=DiagnosisResponse)
async def update_diagnosis(
    patient_id: str,
    diagnosis_id: str,
    body: DiagnosisUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("diagnoses:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> DiagnosisResponse:
    """Update or resolve an existing diagnosis."""
    result = await diagnosis_service.update_diagnosis(
        db=db,
        patient_id=patient_id,
        diagnosis_id=diagnosis_id,
        user_id=current_user.user_id,
        severity=body.severity,
        notes=body.notes,
        status=body.status,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="diagnosis",
        resource_id=diagnosis_id,
    )

    return DiagnosisResponse(**result)
