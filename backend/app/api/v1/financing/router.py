"""Patient financing API routes -- VP-11 / Sprint 29-30.

Endpoint map (all JWT-protected):
  POST /billing/invoices/{invoice_id}/financing-request     — FIN-01: Request financing
  GET  /billing/invoices/{invoice_id}/financing-eligibility — FIN-02: Check eligibility
  GET  /financing/applications                              — FIN-03: List applications
  GET  /financing/report                                    — FIN-04: Aggregate report

Auth:
  - financing:write — create financing applications
  - financing:read  — view applications and eligibility
  - FIN-04 additionally requires clinic_owner or superadmin role
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.exceptions import DentalOSError
from app.models.tenant.invoice import Invoice
from app.schemas.financing import (
    FinancingApplicationListResponse,
    FinancingApplicationResponse,
    FinancingEligibilityResponse,
    FinancingReportResponse,
    FinancingRequestCreate,
)
from app.services.financing_service import financing_service

router = APIRouter(tags=["financing"])


# ── FIN-01: Request financing for an invoice ─────────────────────────────────


@router.post(
    "/billing/invoices/{invoice_id}/financing-request",
    response_model=FinancingApplicationResponse,
    status_code=201,
    summary="Solicitar financiamiento para una factura",
)
async def request_financing(
    invoice_id: str,
    body: FinancingRequestCreate,
    patient_id: str = Query(..., description="UUID del paciente dueño de la factura"),
    current_user: AuthenticatedUser = Depends(require_permission("financing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FinancingApplicationResponse:
    """Create a new BNPL financing application for a specific invoice.

    Validates patient eligibility with the selected provider, then submits
    the application. Returns the created application with provider reference
    and redirect URL for the patient onboarding flow.

    The invoice outstanding balance is used as the financing amount. The
    invoice must belong to the specified patient and have an outstanding balance.
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
        patient_uuid = uuid.UUID(patient_id)
    except ValueError:
        raise DentalOSError(
            error="VALIDATION_invalid_field",
            message="ID inválido.",
            status_code=400,
        )

    result = await financing_service.request_financing(
        db=db,
        patient_id=patient_uuid,
        invoice_id=invoice_uuid,
        provider=body.provider,
        installments=body.installments,
        tenant_id=current_user.tenant.schema_name,
    )
    return FinancingApplicationResponse(**result)


# ── FIN-02: Check eligibility ────────────────────────────────────────────────


@router.get(
    "/billing/invoices/{invoice_id}/financing-eligibility",
    response_model=FinancingEligibilityResponse,
    summary="Verificar elegibilidad de financiamiento",
)
async def check_financing_eligibility(
    invoice_id: str,
    patient_id: str = Query(..., description="UUID del paciente"),
    provider: str = Query(..., description="Proveedor: addi | sistecredito | mercadopago"),
    current_user: AuthenticatedUser = Depends(require_permission("financing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FinancingEligibilityResponse:
    """Check if a patient is eligible for financing their invoice balance.

    Does not create any records. Use this before presenting financing options
    to the patient on the billing screen. The invoice balance is used as the
    amount to check eligibility for.
    """
    try:
        patient_uuid = uuid.UUID(patient_id)
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise DentalOSError(
            error="VALIDATION_invalid_field",
            message="ID inválido.",
            status_code=400,
        )

    # Fetch invoice balance to use as the check amount
    invoice_result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_uuid,
            Invoice.patient_id == patient_uuid,
            Invoice.is_active.is_(True),
        )
    )
    invoice = invoice_result.scalar_one_or_none()
    if invoice is None:
        raise DentalOSError(
            error="BILLING_invoice_not_found",
            message="Factura no encontrada.",
            status_code=404,
        )

    result = await financing_service.check_eligibility(
        db=db,
        patient_id=patient_uuid,
        amount_cents=invoice.balance,
        provider=provider,
    )
    return FinancingEligibilityResponse(**result)


# ── FIN-03: List financing applications ──────────────────────────────────────


@router.get(
    "/financing/applications",
    response_model=FinancingApplicationListResponse,
    summary="Listar solicitudes de financiamiento",
)
async def list_financing_applications(
    patient_id: str | None = Query(default=None, description="Filtrar por UUID de paciente"),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("financing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FinancingApplicationListResponse:
    """Return a paginated list of financing applications for the tenant.

    Optionally filtered by patient UUID and/or application status.
    """
    patient_uuid: uuid.UUID | None = None
    if patient_id is not None:
        try:
            patient_uuid = uuid.UUID(patient_id)
        except ValueError:
            raise DentalOSError(
                error="VALIDATION_invalid_field",
                message="patient_id inválido.",
                status_code=400,
            )

    result = await financing_service.get_applications(
        db=db,
        patient_id=patient_uuid,
        status=status,
        page=page,
        page_size=page_size,
    )

    return FinancingApplicationListResponse(
        items=[FinancingApplicationResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ── FIN-04: Aggregate financing report ───────────────────────────────────────


@router.get(
    "/financing/report",
    response_model=FinancingReportResponse,
    summary="Reporte agregado de financiamiento",
)
async def get_financing_report(
    current_user: AuthenticatedUser = Depends(require_permission("financing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FinancingReportResponse:
    """Return aggregate financing metrics for clinic owners.

    Requires clinic_owner or superadmin role in addition to financing:read permission.
    Shows total applications, total amounts, and breakdowns by provider and status.
    """
    if current_user.role not in ("clinic_owner", "superadmin"):
        raise DentalOSError(
            error="AUTH_insufficient_role",
            message="Solo el propietario de la clínica puede ver este reporte.",
            status_code=403,
        )

    result = await financing_service.get_report(db=db)
    return FinancingReportResponse(**result)
