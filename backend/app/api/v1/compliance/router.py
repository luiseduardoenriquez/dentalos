"""Compliance API routes — CO-01 through CO-08.

Endpoint map:
  GET  /compliance/config               — CO-08: Get country compliance config
  GET  /compliance/rda/status            — CO-05: RDA compliance dashboard
  POST /compliance/rips/generate         — CO-01: Start RIPS batch generation
  GET  /compliance/rips/{batch_id}       — CO-02: Get RIPS batch detail
  GET  /compliance/rips                  — CO-03: List RIPS batches
  POST /compliance/rips/{id}/validate    — CO-04: Validate a RIPS batch
  POST /compliance/e-invoice             — CO-06: Submit e-invoice to DIAN
  GET  /compliance/e-invoice/{id}/status — CO-07: Check e-invoice status
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user
from app.compliance.base import ComplianceAdapter
from app.compliance.deps import get_compliance, require_colombia
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.models.tenant.e_invoice import EInvoice
from app.models.tenant.invoice import Invoice
from app.models.tenant.patient import Patient
from app.schemas.compliance import (
    CountryConfigResponse,
    EInvoiceCreateRequest,
    EInvoiceStatusResponse,
    RDAStatusResponse,
    RIPSBatchListResponse,
    RIPSBatchResponse,
    RIPSGenerateRequest,
    RIPSValidateResponse,
)
from app.services.compliance_config_service import get_country_config
from app.services.einvoice_service import create_einvoice, get_einvoice_status
from app.services.rda_service import get_rda_status
from app.services.rips_service import (
    create_rips_batch,
    get_rips_batch,
    list_rips_batches,
    validate_rips_batch,
)

router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
)


# ─── CO-08: Country Compliance Config ──────────────────────────────────────────


@router.get("/config", response_model=CountryConfigResponse)
async def get_compliance_config(
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(get_compliance),
) -> CountryConfigResponse:
    """Return the compliance configuration for the current tenant's country.

    Available to any authenticated user. Returns code systems, document types,
    retention rules, and regulatory references for the tenant's country.
    """
    return await get_country_config(
        country_code=adapter.country_code,
        lang="es",
    )


# ─── CO-05: RDA Compliance Dashboard ──────────────────────────────────────────


@router.get("/rda/status", response_model=RDAStatusResponse)
async def get_rda_compliance_status(
    refresh: bool = False,
    since_date: date | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> RDAStatusResponse:
    """Return the RDA compliance status for the current tenant.

    Only available to clinic_owner in Colombia tenants.
    Use refresh=true to bypass cache and recompute.
    """
    if current_user.role not in ("clinic_owner", "superadmin"):
        from app.core.exceptions import AuthError

        raise AuthError(
            error="AUTH_insufficient_role",
            message="Only clinic owners can access RDA compliance status.",
            status_code=403,
        )
    return await get_rda_status(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        refresh=refresh,
        since_date=since_date,
    )


# ─── CO-01 through CO-04: RIPS ────────────────────────────────────────────────


@router.post(
    "/rips/generate",
    response_model=RIPSBatchResponse,
    status_code=202,
)
async def generate_rips(
    request: Request,
    body: RIPSGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> RIPSBatchResponse:
    """Start RIPS batch generation.  Returns 202 with the batch ID.

    Only clinic_owner and superadmin roles are allowed to trigger RIPS
    generation.  The actual file generation is performed asynchronously
    by the compliance worker.
    """
    if current_user.role not in ("clinic_owner", "superadmin"):
        from app.core.exceptions import AuthError

        raise AuthError(
            error="AUTH_insufficient_role",
            message="Only clinic owners can generate RIPS.",
            status_code=403,
        )
    result = await create_rips_batch(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        user_id=current_user.user_id,
        period_start=body.period_start,
        period_end=body.period_end,
        file_types=body.file_types,
    )
    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="rips_batch",
        resource_id=str(result.id),
    )
    return result


@router.get("/rips/{batch_id}", response_model=RIPSBatchResponse)
async def get_rips_batch_detail(
    batch_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> RIPSBatchResponse:
    """Get a single RIPS batch with its files and validation errors."""
    return await get_rips_batch(db=db, batch_id=batch_id)


@router.get("/rips", response_model=RIPSBatchListResponse)
async def list_rips(
    page: int = 1,
    page_size: int = 20,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> RIPSBatchListResponse:
    """List RIPS batches with pagination."""
    return await list_rips_batches(db=db, page=page, page_size=page_size)


@router.post(
    "/rips/{batch_id}/validate",
    response_model=RIPSValidateResponse,
)
async def validate_rips(
    batch_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> RIPSValidateResponse:
    """Validate a RIPS batch.

    Only clinic_owner and superadmin roles are allowed to trigger
    validation.  The batch must be in ``generated`` or ``validated``
    status.
    """
    if current_user.role not in ("clinic_owner", "superadmin"):
        from app.core.exceptions import AuthError

        raise AuthError(
            error="AUTH_insufficient_role",
            message="Only clinic owners can validate RIPS.",
            status_code=403,
        )
    result = await validate_rips_batch(
        db=db,
        batch_id=batch_id,
        tenant_id=current_user.tenant.tenant_id,
    )
    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="validate",
        resource_type="rips_batch",
        resource_id=batch_id,
    )
    return result


# ─── E-Invoice list (cross-patient) ──────────────────────────────────────────


class EInvoiceListItem(BaseModel):
    id: str
    invoice_id: str
    invoice_number: str
    patient_name: str
    total: int  # cents
    status: str
    cufe: str | None
    created_at: str


class EInvoiceListResponse(BaseModel):
    items: list[EInvoiceListItem]
    total: int
    page: int
    page_size: int


@router.get("/e-invoices", response_model=EInvoiceListResponse)
async def list_electronic_invoices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> EInvoiceListResponse:
    """List all e-invoices submitted to DIAN."""
    conditions = []
    if status:
        conditions.append(EInvoice.status == status)

    count_result = await db.execute(
        select(func.count(EInvoice.id)).where(*conditions) if conditions
        else select(func.count(EInvoice.id))
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    base_query = (
        select(
            EInvoice.id,
            EInvoice.invoice_id,
            Invoice.invoice_number,
            (Patient.first_name + " " + Patient.last_name).label("patient_name"),
            Invoice.total,
            EInvoice.status,
            EInvoice.cufe,
            EInvoice.created_at,
        )
        .outerjoin(Invoice, Invoice.id == EInvoice.invoice_id)
        .outerjoin(Patient, Patient.id == Invoice.patient_id)
        .order_by(EInvoice.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    if conditions:
        base_query = base_query.where(*conditions)

    rows_result = await db.execute(base_query)
    rows = rows_result.all()

    items = [
        EInvoiceListItem(
            id=str(row.id),
            invoice_id=str(row.invoice_id),
            invoice_number=row.invoice_number or "—",
            patient_name=row.patient_name or "—",
            total=row.total or 0,
            status=row.status,
            cufe=row.cufe,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]

    return EInvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ─── CO-06, CO-07: DIAN E-Invoicing ──────────────────────────────────────────


@router.post(
    "/e-invoice",
    response_model=EInvoiceStatusResponse,
    status_code=202,
)
async def create_electronic_invoice(
    request: Request,
    body: EInvoiceCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> EInvoiceStatusResponse:
    """Submit an invoice for electronic invoicing via DIAN.

    Available to clinic_owner and receptionist roles in Colombia tenants.
    Returns 202 with the e-invoice record in pending status.
    """
    if current_user.role not in ("clinic_owner", "receptionist", "superadmin"):
        from app.core.exceptions import AuthError

        raise AuthError(
            error="AUTH_insufficient_role",
            message="Only clinic owners and receptionists can submit e-invoices.",
            status_code=403,
        )
    result = await create_einvoice(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        user_id=current_user.user_id,
        invoice_id=body.invoice_id,
    )
    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="e_invoice",
        resource_id=str(result.id),
    )
    return result


@router.get(
    "/e-invoice/{einvoice_id}/status",
    response_model=EInvoiceStatusResponse,
)
async def get_electronic_invoice_status(
    einvoice_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(require_colombia),
    db: AsyncSession = Depends(get_tenant_db),
) -> EInvoiceStatusResponse:
    """Get the status of an e-invoice submission.

    Polls MATIAS if the invoice is in 'submitted' status.
    """
    return await get_einvoice_status(db=db, einvoice_id=einvoice_id)
