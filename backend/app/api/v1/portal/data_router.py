"""Portal data routes — read-only endpoints (PP-02 to PP-13, Phase 2).

Endpoint map:
  GET  /portal/me                          — PP-02: Patient profile
  PUT  /portal/me                          — V1: Update patient profile
  GET  /portal/appointments                — PP-03: Appointment list
  GET  /portal/treatment-plans             — PP-04: Treatment plan list
  GET  /portal/invoices                    — PP-06: Invoice list
  GET  /portal/documents                   — PP-07: Document list
  GET  /portal/messages                    — PP-10: Message threads
  GET  /portal/odontogram                  — PP-13: Read-only odontogram
  GET  /portal/odontogram/history          — V5: Odontogram snapshot history
  GET  /portal/postop                      — G1: Post-operative instructions
  GET  /portal/notifications/preferences   — V2: Get notification preferences
  PUT  /portal/notifications/preferences   — V2: Update notification preferences
  GET  /portal/intake/form                 — F4: Intake form config
  GET  /portal/surveys                     — F6: Survey history
  GET  /portal/financing                   — F7: Financing applications
  POST /portal/financing/simulate          — F12: Financing calculator
  GET  /portal/family                      — F8: Family group + billing
  GET  /portal/lab-orders                  — F9: Lab orders
  GET  /portal/photos                      — F10: Tooth photos
  GET  /portal/health-history              — F11: Health history
  GET  /portal/treatment-timeline          — F13: Treatment timeline
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.database import get_tenant_db
from app.schemas.portal import (
    FinancingSimulationRequest,
    FinancingSimulationResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    PatientProfileUpdateRequest,
    PortalAppointmentListResponse,
    PortalDocumentListResponse,
    PortalFamilyResponse,
    PortalFinancingListResponse,
    PortalHealthHistory,
    PortalInvoiceListResponse,
    PortalLabOrderListResponse,
    PortalMessageListResponse,
    PortalOdontogramResponse,
    PortalPatientProfile,
    PortalSurveyListResponse,
    PortalTimelineResponse,
    PortalToothPhotoListResponse,
    PortalTreatmentPlanListResponse,
    PostopInstructionListResponse,
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


@router.get("/membership")
async def get_portal_membership(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get the patient's active membership plan details."""
    from app.services.membership_service import membership_service

    discount, sub_id = await membership_service.get_active_membership_discount(
        db=db, patient_id=portal_user.patient_id,
    )
    if sub_id is None:
        return {"has_membership": False, "subscription": None}

    subs = await membership_service.list_subscriptions(
        db=db, patient_id=str(portal_user.patient_id), status="active",
    )
    subscription = subs["items"][0] if subs["items"] else None
    return {"has_membership": True, "subscription": subscription}


@router.put("/me")
async def update_portal_profile(
    body: PatientProfileUpdateRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Update patient profile (phone, email, address, emergency contact)."""
    return await portal_data_service.update_patient_profile(
        db=db,
        patient_id=portal_user.patient_id,
        data=body.model_dump(exclude_none=True),
    )


@router.get("/postop", response_model=PostopInstructionListResponse)
async def get_portal_postop(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PostopInstructionListResponse:
    """Get post-operative instructions for the patient."""
    result = await portal_data_service.get_postop_instructions(
        db=db,
        patient_id=portal_user.patient_id,
        cursor=cursor,
        limit=limit,
    )
    return PostopInstructionListResponse(**result)


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> NotificationPreferencesResponse:
    """Get patient notification preferences."""
    result = await portal_data_service.get_notification_preferences(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return NotificationPreferencesResponse(**result)


@router.put("/notifications/preferences")
async def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Update patient notification preferences."""
    return await portal_data_service.update_notification_preferences(
        db=db,
        patient_id=portal_user.patient_id,
        data=body.model_dump(exclude_none=True),
    )


@router.get("/odontogram/history")
async def get_odontogram_history(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get odontogram snapshot history timeline."""
    snapshots = await portal_data_service.get_odontogram_history(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return {"snapshots": snapshots}


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


# ─── Phase 2 Endpoints ──────────────────────────────────────────────────────


@router.get("/intake/form")
async def get_intake_form(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Get intake form configuration for authenticated patient (F4)."""
    return await portal_data_service.get_intake_form(
        db=db,
        tenant_id=portal_user.tenant.tenant_id,
    )


@router.get("/surveys", response_model=PortalSurveyListResponse)
async def list_portal_surveys(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalSurveyListResponse:
    """Get patient's survey response history (F6)."""
    data = await portal_data_service.get_survey_history(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return PortalSurveyListResponse(data=data)


@router.get("/financing", response_model=PortalFinancingListResponse)
async def list_portal_financing(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalFinancingListResponse:
    """Get patient's financing applications (F7)."""
    data = await portal_data_service.get_financing_applications(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return PortalFinancingListResponse(data=data)


@router.post("/financing/simulate", response_model=FinancingSimulationResponse)
async def simulate_financing(
    body: FinancingSimulationRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> FinancingSimulationResponse:
    """Simulate financing installment options (F12)."""
    result = await portal_data_service.simulate_financing(
        db=db,
        patient_id=portal_user.patient_id,
        amount_cents=body.amount_cents,
        provider=body.provider,
    )
    return FinancingSimulationResponse(**result)


@router.get("/family", response_model=PortalFamilyResponse)
async def get_portal_family(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalFamilyResponse:
    """Get patient's family group with billing summary (F8)."""
    family = await portal_data_service.get_family_group(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return PortalFamilyResponse(family=family)


@router.get("/lab-orders", response_model=PortalLabOrderListResponse)
async def list_portal_lab_orders(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalLabOrderListResponse:
    """Get patient's lab orders with status (F9)."""
    data = await portal_data_service.get_lab_orders(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return PortalLabOrderListResponse(data=data)


@router.get("/photos", response_model=PortalToothPhotoListResponse)
async def list_portal_photos(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalToothPhotoListResponse:
    """Get patient's tooth photos (F10)."""
    data = await portal_data_service.get_tooth_photos(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_id=portal_user.tenant.tenant_id,
    )
    return PortalToothPhotoListResponse(data=data)


@router.get("/health-history", response_model=PortalHealthHistory)
async def get_health_history(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalHealthHistory:
    """Get patient's health history (F11)."""
    result = await portal_data_service.get_health_history(
        db=db,
        patient_id=portal_user.patient_id,
    )
    return PortalHealthHistory(**result)


@router.get("/treatment-timeline", response_model=PortalTimelineResponse)
async def get_treatment_timeline(
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalTimelineResponse:
    """Get treatment timeline combining procedures and photos (F13)."""
    events = await portal_data_service.get_treatment_timeline(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_id=portal_user.tenant.tenant_id,
    )
    return PortalTimelineResponse(events=events)
