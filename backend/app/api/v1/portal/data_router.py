"""Portal data routes — read-only endpoints (PP-02 to PP-13).

Endpoint map:
  GET  /portal/me                   — PP-02: Patient profile
  GET  /portal/appointments         — PP-03: Appointment list
  GET  /portal/treatment-plans      — PP-04: Treatment plan list
  GET  /portal/invoices             — PP-06: Invoice list
  GET  /portal/documents            — PP-07: Document list
  GET  /portal/messages             — PP-10: Message threads
  GET  /portal/odontogram           — PP-13: Read-only odontogram
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.database import get_tenant_db
from app.schemas.portal import (
    PortalAppointmentListResponse,
    PortalDocumentListResponse,
    PortalInvoiceListResponse,
    PortalMessageListResponse,
    PortalOdontogramResponse,
    PortalPatientProfile,
    PortalTreatmentPlanListResponse,
)
from app.services.portal_data_service import portal_data_service

router = APIRouter(prefix="/portal", tags=["portal-data"])


@router.get("/me", response_model=PortalPatientProfile)
async def get_portal_profile(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalPatientProfile:
    """Get current patient profile with clinic info and summary."""
    result = await portal_data_service.get_profile(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_id=portal_user.tenant.tenant_id,
    )
    return PortalPatientProfile(**result)


@router.get("/appointments", response_model=PortalAppointmentListResponse)
async def list_portal_appointments(
    view: str | None = Query(default=None, pattern=r"^(upcoming|past|all)$"),
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalAppointmentListResponse:
    """List patient appointments with filtering and pagination."""
    result = await portal_data_service.list_appointments(
        db=db,
        patient_id=portal_user.patient_id,
        view=view,
        status=status,
        cursor=cursor,
        limit=limit,
    )
    return PortalAppointmentListResponse(**result)


@router.get("/treatment-plans", response_model=PortalTreatmentPlanListResponse)
async def list_portal_treatment_plans(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalTreatmentPlanListResponse:
    """List patient treatment plans with progress."""
    result = await portal_data_service.list_treatment_plans(
        db=db,
        patient_id=portal_user.patient_id,
        cursor=cursor,
        limit=limit,
    )
    return PortalTreatmentPlanListResponse(**result)


@router.get("/invoices", response_model=PortalInvoiceListResponse)
async def list_portal_invoices(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalInvoiceListResponse:
    """List patient invoices."""
    result = await portal_data_service.list_invoices(
        db=db,
        patient_id=portal_user.patient_id,
        cursor=cursor,
        limit=limit,
    )
    return PortalInvoiceListResponse(**result)


@router.get("/documents", response_model=PortalDocumentListResponse)
async def list_portal_documents(
    doc_type: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalDocumentListResponse:
    """List patient documents with optional type filter."""
    result = await portal_data_service.list_documents(
        db=db,
        patient_id=portal_user.patient_id,
        doc_type=doc_type,
        cursor=cursor,
        limit=limit,
    )
    return PortalDocumentListResponse(**result)


@router.get("/messages", response_model=PortalMessageListResponse)
async def list_portal_messages(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalMessageListResponse:
    """List message threads for the patient."""
    result = await portal_data_service.list_message_threads(
        db=db,
        patient_id=portal_user.patient_id,
        cursor=cursor,
        limit=limit,
    )
    return PortalMessageListResponse(**result)


@router.get("/odontogram", response_model=PortalOdontogramResponse)
async def get_portal_odontogram(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalOdontogramResponse:
    """Get read-only odontogram view for the patient."""
    result = await portal_data_service.get_odontogram(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return PortalOdontogramResponse(**result)
