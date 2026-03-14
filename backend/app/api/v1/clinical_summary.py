"""AI Clinical Summary API route (AI-02).

Endpoint:
  GET /patients/{patient_id}/clinical-summary → Structured clinical briefing
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.compliance.deps import resolve_tenant
from app.core.database import get_tenant_db
from app.core.error_codes import AIClinicalSummaryErrors
from app.core.exceptions import DentalOSError
from app.schemas.clinical_summary import ClinicalSummaryResponse
from app.services.clinical_summary_service import clinical_summary_service

router = APIRouter(
    prefix="/patients/{patient_id}",
    tags=["clinical-summary"],
)


@router.get(
    "/clinical-summary",
    response_model=ClinicalSummaryResponse,
)
async def get_clinical_summary(
    patient_id: uuid.UUID,
    appointment_id: uuid.UUID | None = Query(None, description="Upcoming appointment for context"),
    force_refresh: bool = Query(False, description="Bypass cache (clinic_owner only)"),
    current_user=Depends(get_current_user),
    tenant=Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get AI-generated clinical summary for a patient.

    Returns a structured briefing with 8 sections: patient snapshot,
    today's context, active conditions, risk alerts, pending treatments,
    last visit summary, financial status, and action suggestions.

    Cached for 5 minutes. Pass force_refresh=true to regenerate.

    Requires: Pro+ plan with ai_clinical_summary feature enabled.
    Roles: doctor, assistant, clinic_owner.
    """
    # Feature flag check
    if not tenant.features.get("ai_clinical_summary"):
        raise DentalOSError(
            status_code=402,
            error=AIClinicalSummaryErrors.PLAN_REQUIRED,
            message="El Resumen Clínico con IA requiere el plan Pro o superior.",
            details={"required_plan": "pro"},
        )

    return await clinical_summary_service.generate_summary(
        db=db,
        patient_id=str(patient_id),
        doctor_id=str(current_user.user_id),
        tenant_id=tenant.tenant_id,
        tenant_features=tenant.features,
        force_refresh=force_refresh,
    )
