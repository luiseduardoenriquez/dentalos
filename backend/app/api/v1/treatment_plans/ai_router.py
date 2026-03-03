"""AI treatment suggestion API routes (VP-13).

Endpoint map (top-level, not patient-scoped):
  POST   /treatment-plans/ai-suggest            -- Generate AI suggestions
  GET    /treatment-plans/ai-suggest/{id}        -- Get suggestion detail
  POST   /treatment-plans/ai-suggest/{id}/review -- Review suggestions
  POST   /treatment-plans/ai-suggest/{id}/create-plan -- Create plan from accepted
  GET    /treatment-plans/ai-usage               -- Token usage stats
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.ai_treatment import (
    AITreatmentPlanCreatedResponse,
    AITreatmentReviewRequest,
    AITreatmentSuggestRequest,
    AITreatmentSuggestResponse,
    AITreatmentUsageResponse,
)
from app.services.ai_treatment_service import ai_treatment_service

router = APIRouter(prefix="/treatment-plans", tags=["ai-treatment"])


@router.post("/ai-suggest", response_model=AITreatmentSuggestResponse, status_code=201)
async def generate_ai_suggestions(
    body: AITreatmentSuggestRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("ai_treatment:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AITreatmentSuggestResponse:
    """Generate AI-powered treatment suggestions for a patient.

    Requires the ai_treatment_advisor add-on to be active on the tenant.
    Only available to doctors and clinic owners.
    """
    result = await ai_treatment_service.generate_suggestions(
        db=db,
        patient_id=body.patient_id,
        doctor_id=current_user.user_id,
        tenant_features=current_user.tenant.features,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="ai_treatment_suggestion",
        resource_id=result["id"],
    )

    return AITreatmentSuggestResponse(**result)


@router.get("/ai-suggest/{suggestion_id}", response_model=AITreatmentSuggestResponse)
async def get_ai_suggestion(
    suggestion_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("ai_treatment:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AITreatmentSuggestResponse:
    """Get a specific AI treatment suggestion by ID."""
    result = await ai_treatment_service.get_suggestion(
        db=db,
        suggestion_id=suggestion_id,
    )
    return AITreatmentSuggestResponse(**result)


@router.post(
    "/ai-suggest/{suggestion_id}/review",
    response_model=AITreatmentSuggestResponse,
)
async def review_ai_suggestions(
    suggestion_id: str,
    body: AITreatmentReviewRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("ai_treatment:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AITreatmentSuggestResponse:
    """Review AI treatment suggestions (accept, modify, or reject each item)."""
    review_items = [item.model_dump() for item in body.items]

    result = await ai_treatment_service.review_suggestion(
        db=db,
        suggestion_id=suggestion_id,
        review_items=review_items,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="review",
        resource_type="ai_treatment_suggestion",
        resource_id=suggestion_id,
    )

    return AITreatmentSuggestResponse(**result)


@router.post(
    "/ai-suggest/{suggestion_id}/create-plan",
    response_model=AITreatmentPlanCreatedResponse,
    status_code=201,
)
async def create_plan_from_ai_suggestions(
    suggestion_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("ai_treatment:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AITreatmentPlanCreatedResponse:
    """Convert accepted AI suggestions into a treatment plan.

    The suggestion must be in 'reviewed' status with at least one
    accepted item. Requires both ai_treatment:write and
    treatment_plans:write permissions (doctor or clinic_owner).
    """
    # Double-check treatment plan write permission explicitly
    if "treatment_plans:write" not in current_user.permissions:
        from app.core.exceptions import AuthError

        raise AuthError(
            error="AUTH_insufficient_permission",
            message="Se requiere permiso treatment_plans:write.",
            status_code=403,
        )

    # We need the patient_id from the suggestion to pass to the plan service.
    # Fetch suggestion first to get the patient_id.
    suggestion = await ai_treatment_service.get_suggestion(
        db=db,
        suggestion_id=suggestion_id,
    )

    result = await ai_treatment_service.create_plan_from_suggestions(
        db=db,
        suggestion_id=suggestion_id,
        patient_id=suggestion["patient_id"],
        doctor_id=current_user.user_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="apply",
        resource_type="ai_treatment_suggestion",
        resource_id=suggestion_id,
        changes={"treatment_plan_id": result["treatment_plan_id"]},
    )

    return AITreatmentPlanCreatedResponse(**result)


@router.get("/ai-usage", response_model=AITreatmentUsageResponse)
async def get_ai_usage_stats(
    date_from: str = Query(..., description="ISO 8601 start date (e.g. 2026-03-01)"),
    date_to: str = Query(..., description="ISO 8601 end date (e.g. 2026-03-31)"),
    current_user: AuthenticatedUser = Depends(
        require_permission("ai_treatment:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AITreatmentUsageResponse:
    """Get AI treatment token usage statistics for the current doctor."""
    result = await ai_treatment_service.get_usage_stats(
        db=db,
        doctor_id=current_user.user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return AITreatmentUsageResponse(**result)
