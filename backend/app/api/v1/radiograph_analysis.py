"""AI Radiograph Analysis API routes (AI-01).

Endpoints:
  POST   /patients/{patient_id}/radiograph-analyses       → Create (trigger analysis)
  GET    /patients/{patient_id}/radiograph-analyses        → List (paginated)
  GET    /patients/{patient_id}/radiograph-analyses/{id}   → Get single
  PUT    /patients/{patient_id}/radiograph-analyses/{id}/review → Review findings
  DELETE /patients/{patient_id}/radiograph-analyses/{id}   → Soft delete
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_tenant_db, resolve_tenant
from app.core.error_codes import RadiographAnalysisErrors
from app.core.exceptions import DentalOSError
from app.core.queue import publish_message
from app.schemas.queue import QueueMessage
from app.schemas.radiograph_analysis import (
    RadiographAnalysisListResponse,
    RadiographAnalysisResponse,
    RadiographAnalyzeRequest,
    RadiographReviewRequest,
)
from app.services.radiograph_analysis_service import radiograph_analysis_service

router = APIRouter(
    prefix="/patients/{patient_id}/radiograph-analyses",
    tags=["radiograph-analysis"],
)


@router.post(
    "",
    response_model=RadiographAnalysisResponse,
    status_code=201,
)
async def create_radiograph_analysis(
    patient_id: uuid.UUID,
    body: RadiographAnalyzeRequest,
    current_user=Depends(get_current_user),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Trigger AI analysis of a dental radiograph.

    Creates the analysis record (status=processing) and publishes
    a job to the clinical queue for async processing.

    Requires: ai_radiograph add-on enabled.
    Roles: doctor, assistant, clinic_owner.
    """
    # Feature flag check
    features = tenant.get("features", {}) if isinstance(tenant, dict) else {}
    if not features.get("ai_radiograph"):
        raise DentalOSError(
            status_code=402,
            error=RadiographAnalysisErrors.ADDON_REQUIRED,
            message="El módulo de Análisis de Radiografías con IA requiere el add-on AI Radiograph.",
            details={"addon": "ai_radiograph", "price": "$20/doctor/mes"},
        )

    analysis = await radiograph_analysis_service.create_analysis(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.id,
        document_id=uuid.UUID(body.document_id),
        radiograph_type=body.radiograph_type,
        tenant_id=tenant.get("id", "") if isinstance(tenant, dict) else "",
    )

    # Publish async job to clinical queue
    tenant_id = tenant.get("id", "") if isinstance(tenant, dict) else ""
    await publish_message(
        "clinical",
        QueueMessage(
            tenant_id=tenant_id,
            job_type="radiograph.analyze",
            payload={
                "analysis_id": str(analysis.id),
                "document_id": str(analysis.document_id),
                "s3_key": f"{tenant_id}/{patient_id}/documents/{analysis.document_id}",
                "media_type": "image/jpeg",
                "radiograph_type": body.radiograph_type,
            },
            priority=7,
        ),
    )

    return radiograph_analysis_service._to_dict(analysis)


@router.get(
    "",
    response_model=RadiographAnalysisListResponse,
)
async def list_radiograph_analyses(
    patient_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List radiograph analyses for a patient (paginated)."""
    return await radiograph_analysis_service.list_analyses(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{analysis_id}",
    response_model=RadiographAnalysisResponse,
)
async def get_radiograph_analysis(
    patient_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a single radiograph analysis (supports polling while processing)."""
    return await radiograph_analysis_service.get_analysis(
        db=db,
        analysis_id=analysis_id,
        patient_id=patient_id,
    )


@router.put(
    "/{analysis_id}/review",
    response_model=RadiographAnalysisResponse,
)
async def review_radiograph_analysis(
    patient_id: uuid.UUID,
    analysis_id: uuid.UUID,
    body: RadiographReviewRequest,
    current_user=Depends(get_current_user),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Review radiograph analysis findings (accept/reject/modify each).

    Roles: doctor, clinic_owner only.
    """
    return await radiograph_analysis_service.review_analysis(
        db=db,
        analysis_id=analysis_id,
        patient_id=patient_id,
        review_items=[item.model_dump() for item in body.items],
        reviewer_notes=body.reviewer_notes,
    )


@router.delete(
    "/{analysis_id}",
    status_code=200,
)
async def delete_radiograph_analysis(
    patient_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Soft-delete a radiograph analysis."""
    await radiograph_analysis_service.delete_analysis(
        db=db,
        analysis_id=analysis_id,
        patient_id=patient_id,
    )
    return {"message": "Análisis eliminado correctamente."}
