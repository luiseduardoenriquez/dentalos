"""Quotation API routes — B-16 through B-19.

Endpoint map:
  POST /patients/{patient_id}/quotations                     — Create quotation
  GET  /patients/{patient_id}/quotations                     — List quotations
  GET  /patients/{patient_id}/quotations/{quotation_id}      — Get quotation detail
  POST /patients/{patient_id}/quotations/{quotation_id}/approve — Approve quotation
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.quotation import (
    QuotationApproveRequest,
    QuotationCreate,
    QuotationListResponse,
    QuotationResponse,
)
from app.services.quotation_service import quotation_service

router = APIRouter(
    prefix="/patients/{patient_id}/quotations",
    tags=["quotations"],
)


@router.post("", response_model=QuotationResponse, status_code=201)
async def create_quotation(
    patient_id: str,
    body: QuotationCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("quotations:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> QuotationResponse:
    """Create a new quotation."""
    items = None
    if body.items:
        items = [i.model_dump() for i in body.items]

    result = await quotation_service.create_quotation(
        db=db,
        patient_id=patient_id,
        created_by=current_user.user_id,
        treatment_plan_id=body.treatment_plan_id,
        items=items,
        valid_until=body.valid_until,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="quotation",
        resource_id=result["id"],
    )

    return QuotationResponse(**result)


@router.get("", response_model=QuotationListResponse)
async def list_quotations(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("quotations:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> QuotationListResponse:
    """List quotations for a patient."""
    result = await quotation_service.list_quotations(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return QuotationListResponse(**result)


@router.get("/{quotation_id}", response_model=QuotationResponse)
async def get_quotation(
    patient_id: str,
    quotation_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("quotations:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> QuotationResponse:
    """Get quotation detail."""
    result = await quotation_service.get_quotation(
        db=db,
        patient_id=patient_id,
        quotation_id=quotation_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="QUOTATION_not_found",
            resource_name="Quotation",
        )
    return QuotationResponse(**result)


@router.post("/{quotation_id}/approve", response_model=QuotationResponse)
async def approve_quotation(
    patient_id: str,
    quotation_id: str,
    body: QuotationApproveRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("quotations:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> QuotationResponse:
    """Approve a quotation with a digital signature."""
    result = await quotation_service.approve_quotation(
        db=db,
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        quotation_id=quotation_id,
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
        resource_type="quotation",
        resource_id=quotation_id,
    )

    return QuotationResponse(**result)
