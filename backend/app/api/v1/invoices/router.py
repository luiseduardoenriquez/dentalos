"""Invoice API routes — B-01 through B-05.

Endpoint map:
  POST /patients/{patient_id}/invoices                     — B-01: Create invoice
  GET  /patients/{patient_id}/invoices                     — B-02: List invoices
  GET  /patients/{patient_id}/invoices/{invoice_id}        — B-03: Get invoice detail
  POST /patients/{patient_id}/invoices/{invoice_id}/cancel — B-04: Cancel invoice
  POST /patients/{patient_id}/invoices/{invoice_id}/send   — B-05: Send invoice
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
)
from app.services.invoice_service import invoice_service

router = APIRouter(
    prefix="/patients/{patient_id}/invoices",
    tags=["invoices"],
)


# ─── B-01: Create invoice ───────────────────────────────────────────────────


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    patient_id: str,
    body: InvoiceCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> InvoiceResponse:
    """Create a new invoice from quotation or manual items."""
    items = None
    if body.items:
        items = [i.model_dump() for i in body.items]

    result = await invoice_service.create_invoice(
        db=db,
        patient_id=patient_id,
        created_by=current_user.user_id,
        quotation_id=body.quotation_id,
        items=items,
        due_date=body.due_date,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="invoice",
        resource_id=result["id"],
    )

    return InvoiceResponse(**result)


# ─── B-02: List invoices ────────────────────────────────────────────────────


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> InvoiceListResponse:
    """List invoices for a patient."""
    result = await invoice_service.list_invoices(
        db=db,
        patient_id=patient_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return InvoiceListResponse(**result)


# ─── B-03: Get invoice detail ───────────────────────────────────────────────


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    patient_id: str,
    invoice_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> InvoiceResponse:
    """Get invoice detail with items."""
    result = await invoice_service.get_invoice(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="BILLING_invoice_not_found",
            resource_name="Invoice",
        )
    return InvoiceResponse(**result)


# ─── B-04: Cancel invoice ───────────────────────────────────────────────────


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    patient_id: str,
    invoice_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> InvoiceResponse:
    """Cancel an invoice (draft, sent, or overdue only)."""
    result = await invoice_service.cancel_invoice(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="cancel",
        resource_type="invoice",
        resource_id=invoice_id,
    )

    return InvoiceResponse(**result)


# ─── B-05: Send invoice ─────────────────────────────────────────────────────


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    patient_id: str,
    invoice_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> InvoiceResponse:
    """Send an invoice to the patient (transitions draft -> sent)."""
    result = await invoice_service.send_invoice(
        db=db,
        patient_id=patient_id,
        invoice_id=invoice_id,
        tenant_id=current_user.tenant_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="send",
        resource_type="invoice",
        resource_id=invoice_id,
    )

    return InvoiceResponse(**result)
