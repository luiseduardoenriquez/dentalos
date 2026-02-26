"""Payment API routes — B-06 through B-10.

Endpoint map:
  POST /patients/{pid}/invoices/{iid}/payments                       — B-06: Record payment
  GET  /patients/{pid}/invoices/{iid}/payments                       — B-07: List payments
  POST /patients/{pid}/invoices/{iid}/payment-plan                   — B-08: Create payment plan
  GET  /patients/{pid}/invoices/{iid}/payment-plan                   — B-09: Get payment plan
  POST /patients/{pid}/invoices/{iid}/payment-plan/{inst_num}/pay    — B-10: Pay installment
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.payment import PaymentCreate, PaymentListResponse, PaymentResponse
from app.schemas.payment_plan import PaymentPlanCreate, PaymentPlanResponse
from app.services.payment_service import payment_service

router = APIRouter(
    prefix="/patients/{patient_id}/invoices/{invoice_id}",
    tags=["payments"],
)


# ─── B-06: Record payment ───────────────────────────────────────────────────


@router.post("/payments", response_model=PaymentResponse, status_code=201)
async def record_payment(
    patient_id: str,
    invoice_id: str,
    body: PaymentCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentResponse:
    """Record a payment against an invoice."""
    result = await payment_service.record_payment(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
        amount=body.amount,
        payment_method=body.payment_method,
        received_by=current_user.user_id,
        reference_number=body.reference_number,
        notes=body.notes,
        tenant_id=current_user.tenant_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="payment",
        resource_id=result["id"],
    )

    return PaymentResponse(**result)


# ─── B-07: List payments ────────────────────────────────────────────────────


@router.get("/payments", response_model=PaymentListResponse)
async def list_payments(
    patient_id: str,
    invoice_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentListResponse:
    """List payments for an invoice."""
    result = await payment_service.list_payments(
        db=db,
        invoice_id=invoice_id,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return PaymentListResponse(**result)


# ─── B-08: Create payment plan ──────────────────────────────────────────────


@router.post("/payment-plan", response_model=PaymentPlanResponse, status_code=201)
async def create_payment_plan(
    patient_id: str,
    invoice_id: str,
    body: PaymentPlanCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentPlanResponse:
    """Create a payment plan for an invoice."""
    result = await payment_service.create_payment_plan(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
        num_installments=body.num_installments,
        first_due_date=body.first_due_date,
        created_by=current_user.user_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="payment_plan",
        resource_id=result["id"],
    )

    return PaymentPlanResponse(**result)


# ─── B-09: Get payment plan ─────────────────────────────────────────────────


@router.get("/payment-plan", response_model=PaymentPlanResponse)
async def get_payment_plan(
    patient_id: str,
    invoice_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentPlanResponse:
    """Get the active payment plan for an invoice."""
    result = await payment_service.get_payment_plan(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="BILLING_plan_not_found",
            resource_name="PaymentPlan",
        )
    return PaymentPlanResponse(**result)


# ─── B-10: Pay installment ──────────────────────────────────────────────────


@router.post("/payment-plan/{installment_number}/pay", response_model=PaymentResponse)
async def pay_installment(
    patient_id: str,
    invoice_id: str,
    installment_number: int,
    body: PaymentCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentResponse:
    """Pay a specific installment in a payment plan."""
    result = await payment_service.pay_installment(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
        installment_number=installment_number,
        payment_method=body.payment_method,
        received_by=current_user.user_id,
        reference_number=body.reference_number,
        notes=body.notes,
        tenant_id=current_user.tenant_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="payment",
        resource_id=result["id"],
        changes={"installment_number": installment_number},
    )

    return PaymentResponse(**result)
