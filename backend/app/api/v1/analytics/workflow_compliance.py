"""GAP-15: AI Workflow Compliance Monitor API router.

Single read-only endpoint that runs compliance checks and returns
detected workflow gaps. Plan-gated to Pro+ plans.

Endpoint:
    GET /analytics/workflow-compliance   — analytics:read (doctor, clinic_owner)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.error_codes import WorkflowComplianceErrors
from app.schemas.workflow_compliance import WorkflowComplianceResponse
from app.services.workflow_compliance_service import workflow_compliance_service

logger = logging.getLogger("dentalos.analytics.workflow_compliance")

router = APIRouter(prefix="/analytics", tags=["analytics"])

_PRO_PLANS = {"pro", "clinica", "enterprise"}


@router.get(
    "/workflow-compliance",
    response_model=WorkflowComplianceResponse,
    status_code=200,
    summary="Monitor de cumplimiento de flujos de trabajo",
    description=(
        "Ejecuta 7 verificaciones concurrentes contra el esquema del "
        "tenant para detectar flujos clinicos/administrativos incompletos."
    ),
)
async def get_workflow_compliance(
    lookback_days: int = Query(30, ge=1, le=365),
    enable_ai: bool = Query(False),
    current_user: AuthenticatedUser = Depends(
        require_permission("analytics:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> WorkflowComplianceResponse:
    """Return a compliance snapshot for the current tenant.

    Requires Pro+ plan. Read-only, no side effects.
    """
    if current_user.tenant.plan_name not in _PRO_PLANS:
        raise HTTPException(
            status_code=403,
            detail={
                "error": WorkflowComplianceErrors.PLAN_REQUIRED,
                "message": "El monitor de cumplimiento requiere plan Pro o superior.",
                "details": {"current_plan": current_user.tenant.plan_name},
            },
        )

    result = await workflow_compliance_service.get_compliance_snapshot(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        lookback_days=lookback_days,
        enable_ai=enable_ai,
        tenant_features=current_user.tenant.features,
    )

    return result
