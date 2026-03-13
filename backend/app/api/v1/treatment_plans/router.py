"""Treatment plan API routes — TP-01 through TP-10.

Endpoint map (all scoped to /patients/{patient_id}/treatment-plans):
  POST   /                        — Create plan
  GET    /                        — List plans
  GET    /{plan_id}               — Get plan detail
  PUT    /{plan_id}               — Update plan metadata
  POST   /{plan_id}/items         — Add item to plan
  PUT    /{plan_id}/items/{item_id} — Update item
  POST   /{plan_id}/items/{item_id}/complete — Complete item
  POST   /{plan_id}/approve       — Approve plan (signature)
  POST   /{plan_id}/cancel        — Cancel plan
  GET    /{plan_id}/pdf           — Generate PDF
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.treatment_plan import (
    ApprovalRequest,
    TreatmentPlanCreate,
    TreatmentPlanItemCreate,
    TreatmentPlanItemUpdate,
    TreatmentPlanListResponse,
    TreatmentPlanResponse,
    TreatmentPlanUpdate,
)
from app.services.treatment_plan_service import treatment_plan_service

router = APIRouter(
    prefix="/patients/{patient_id}/treatment-plans",
    tags=["treatment-plans"],
)


@router.post("", response_model=TreatmentPlanResponse, status_code=201)
async def create_treatment_plan(
    patient_id: str,
    body: TreatmentPlanCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Create a new treatment plan."""
    items = None
    if body.items:
        items = [i.model_dump() for i in body.items]

    result = await treatment_plan_service.create_plan(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        name=body.name,
        description=body.description,
        items=items,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="treatment_plan",
        resource_id=result["id"],
    )

    return TreatmentPlanResponse(**result)


@router.get("", response_model=TreatmentPlanListResponse)
async def list_treatment_plans(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanListResponse:
    """List treatment plans for a patient."""
    result = await treatment_plan_service.list_plans(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )
    return TreatmentPlanListResponse(**result)


@router.get("/{plan_id}", response_model=TreatmentPlanResponse)
async def get_treatment_plan(
    patient_id: str,
    plan_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Get treatment plan detail."""
    result = await treatment_plan_service.get_plan(
        db=db, patient_id=patient_id, plan_id=plan_id
    )
    if result is None:
        raise ResourceNotFoundError(
            error="TREATMENT_PLAN_not_found",
            resource_name="TreatmentPlan",
        )
    return TreatmentPlanResponse(**result)


@router.put("/{plan_id}", response_model=TreatmentPlanResponse)
async def update_treatment_plan(
    patient_id: str,
    plan_id: str,
    body: TreatmentPlanUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Update treatment plan metadata."""
    result = await treatment_plan_service.update_plan(
        db=db,
        patient_id=patient_id,
        plan_id=plan_id,
        name=body.name,
        description=body.description,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="treatment_plan",
        resource_id=plan_id,
    )

    return TreatmentPlanResponse(**result)


@router.post("/{plan_id}/items", response_model=TreatmentPlanResponse, status_code=201)
async def add_plan_item(
    patient_id: str,
    plan_id: str,
    body: TreatmentPlanItemCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Add an item to a treatment plan."""
    result = await treatment_plan_service.add_item(
        db=db,
        patient_id=patient_id,
        plan_id=plan_id,
        cups_code=body.cups_code,
        cups_description=body.cups_description,
        tooth_number=body.tooth_number,
        estimated_cost=body.estimated_cost,
        priority_order=body.priority_order,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="treatment_plan_item",
        resource_id=plan_id,
    )

    return TreatmentPlanResponse(**result)


@router.put("/{plan_id}/items/{item_id}", response_model=TreatmentPlanResponse)
async def update_plan_item(
    patient_id: str,
    plan_id: str,
    item_id: str,
    body: TreatmentPlanItemUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Update a plan item."""
    result = await treatment_plan_service.update_item(
        db=db,
        patient_id=patient_id,
        plan_id=plan_id,
        item_id=item_id,
        estimated_cost=body.estimated_cost,
        priority_order=body.priority_order,
        notes=body.notes,
        status=body.status,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="treatment_plan_item",
        resource_id=item_id,
    )

    return TreatmentPlanResponse(**result)


@router.post("/{plan_id}/approve", response_model=TreatmentPlanResponse)
async def approve_treatment_plan(
    patient_id: str,
    plan_id: str,
    body: ApprovalRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Approve a treatment plan with a digital signature."""
    result = await treatment_plan_service.approve_plan(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        patient_id=patient_id,
        plan_id=plan_id,
        signer_id=current_user.user_id,
        signature_image_b64=body.signature_image,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="approve",
        resource_type="treatment_plan",
        resource_id=plan_id,
    )

    return TreatmentPlanResponse(**result)


@router.post("/{plan_id}/cancel", response_model=TreatmentPlanResponse)
async def cancel_treatment_plan(
    patient_id: str,
    plan_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> TreatmentPlanResponse:
    """Cancel a treatment plan."""
    result = await treatment_plan_service.cancel_plan(
        db=db, patient_id=patient_id, plan_id=plan_id
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="cancel",
        resource_type="treatment_plan",
        resource_id=plan_id,
    )

    return TreatmentPlanResponse(**result)


@router.get("/{plan_id}/pdf")
async def get_treatment_plan_pdf(
    patient_id: str,
    plan_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("treatment_plans:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> Response:
    """Generate and return a PDF for a treatment plan."""
    result = await treatment_plan_service.get_plan(
        db=db, patient_id=patient_id, plan_id=plan_id
    )
    if result is None:
        raise ResourceNotFoundError(
            error="TREATMENT_PLAN_not_found",
            resource_name="TreatmentPlan",
        )

    watermark = "BORRADOR" if result["status"] == "draft" else None

    pdf_bytes = await treatment_plan_service.generate_pdf(
        plan_data=result,
        watermark=watermark,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="plan-{plan_id[:8]}.pdf"'},
    )
