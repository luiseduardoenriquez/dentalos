"""Prescription API routes — PR-01 through PR-04.

Endpoint map:
  POST /patients/{patient_id}/prescriptions                        — Create prescription
  GET  /patients/{patient_id}/prescriptions                        — List prescriptions
  GET  /patients/{patient_id}/prescriptions/{prescription_id}      — Get prescription detail
  GET  /patients/{patient_id}/prescriptions/{prescription_id}/pdf  — Generate PDF
"""

import io

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionListResponse,
    PrescriptionResponse,
)
from app.services.prescription_service import prescription_service

router = APIRouter(prefix="/patients/{patient_id}/prescriptions", tags=["prescriptions"])


@router.post("", response_model=PrescriptionResponse, status_code=201)
async def create_prescription(
    patient_id: str,
    body: PrescriptionCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("prescriptions:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PrescriptionResponse:
    """Create a new prescription for a patient."""
    medications = [med.model_dump() for med in body.medications]

    result = await prescription_service.create_prescription(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        medications=medications,
        diagnosis_id=body.diagnosis_id,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="prescription",
        resource_id=result["id"],
    )

    return PrescriptionResponse(**result)


@router.get("", response_model=PrescriptionListResponse)
async def list_prescriptions(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("prescriptions:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PrescriptionListResponse:
    """List prescriptions for a patient (paginated)."""
    result = await prescription_service.list_prescriptions(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return PrescriptionListResponse(**result)


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    patient_id: str,
    prescription_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("prescriptions:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PrescriptionResponse:
    """Get prescription detail."""
    result = await prescription_service.get_prescription(
        db=db,
        patient_id=patient_id,
        prescription_id=prescription_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="PRESCRIPTION_not_found",
            resource_name="Prescription",
        )
    return PrescriptionResponse(**result)


@router.get("/{prescription_id}/pdf")
async def get_prescription_pdf(
    patient_id: str,
    prescription_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("prescriptions:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> StreamingResponse:
    """Generate and return a PDF for a prescription."""
    pdf_bytes = await prescription_service.generate_pdf(
        db=db,
        prescription_id=prescription_id,
        patient_id=patient_id,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=prescripcion_{prescription_id}.pdf"
        },
    )
