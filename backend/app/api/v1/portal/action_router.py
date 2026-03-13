"""Portal action routes — write endpoints (PP-05, PP-08, PP-09, PP-11, PP-12, PP-13, VP-10, V3, V4, F11).

Endpoint map:
  POST /portal/treatment-plans/{plan_id}/approve  — PP-05
  POST /portal/appointments                        — PP-08
  POST /portal/appointments/{id}/cancel            — PP-09
  POST /portal/appointments/{id}/reschedule        — V3
  POST /portal/appointments/{id}/confirm           — F3
  POST /portal/messages                             — PP-11
  POST /portal/consents/{consent_id}/sign           — PP-12
  POST /portal/intake                               — PP-13
  POST /portal/membership/cancel-request            — VP-10
  POST /portal/documents                            — V4
  PUT  /portal/health-history                       — F11
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user
from app.core.database import get_tenant_db
from app.schemas.portal import (
    PortalApprovePlanRequest,
    PortalBookAppointmentRequest,
    PortalCancelAppointmentRequest,
    PortalHealthHistoryUpdate,
    PortalSendMessageRequest,
    PortalSignConsentRequest,
    RescheduleRequest,
)
from app.schemas.portal_intake import PortalCancellationRequest, PortalIntakeSubmission
from app.services.portal_action_service import portal_action_service

router = APIRouter(prefix="/portal", tags=["portal-actions"])


@router.post("/treatment-plans/{plan_id}/approve")
async def approve_treatment_plan(
    plan_id: str,
    body: PortalApprovePlanRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Approve a treatment plan with digital signature."""
    return await portal_action_service.approve_treatment_plan(
        db=db,
        patient_id=portal_user.patient_id,
        plan_id=plan_id,
        signature_data=body.signature_data,
        agreed_terms=body.agreed_terms,
        tenant_id=portal_user.tenant.tenant_id,
    )


@router.post("/appointments")
async def book_appointment(
    body: PortalBookAppointmentRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Book an appointment from the portal."""
    return await portal_action_service.book_appointment(
        db=db,
        patient_id=portal_user.patient_id,
        doctor_id=body.doctor_id,
        appointment_type_id=body.appointment_type_id,
        preferred_date=body.preferred_date,
        preferred_time=body.preferred_time,
        notes=body.notes,
        tenant_id=portal_user.tenant.tenant_id,
    )


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    body: PortalCancelAppointmentRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Cancel an appointment from the portal."""
    return await portal_action_service.cancel_appointment(
        db=db,
        patient_id=portal_user.patient_id,
        appointment_id=appointment_id,
        reason=body.reason,
        tenant_id=portal_user.tenant.tenant_id,
    )


@router.post("/appointments/{appointment_id}/reschedule")
async def reschedule_appointment(
    appointment_id: str,
    body: RescheduleRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Reschedule an appointment from the portal (V3)."""
    return await portal_action_service.reschedule_appointment(
        db=db,
        patient_id=portal_user.patient_id,
        appointment_id=appointment_id,
        tenant_id=portal_user.tenant.tenant_id,
        new_date=body.new_date,
        new_time=body.new_time,
    )


@router.post("/messages")
async def send_message(
    body: PortalSendMessageRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Send a message from the portal."""
    return await portal_action_service.send_message(
        db=db,
        tenant_id=portal_user.tenant.tenant_id,
        patient_id=portal_user.patient_id,
        thread_id=body.thread_id,
        body=body.body,
        attachment_ids=body.attachment_ids,
    )


@router.post("/consents/{consent_id}/sign")
async def sign_consent(
    consent_id: str,
    body: PortalSignConsentRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Sign a consent document from the portal."""
    return await portal_action_service.sign_consent(
        db=db,
        patient_id=portal_user.patient_id,
        consent_id=consent_id,
        signature_data=body.signature_data,
        acknowledged=body.acknowledged,
        tenant_id=portal_user.tenant.tenant_id,
    )


@router.post("/intake")
async def submit_intake(
    body: PortalIntakeSubmission,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Submit pre-appointment intake form from the portal (PP-13)."""
    return await portal_action_service.submit_intake(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_id=portal_user.tenant.tenant_id,
        form_data=body.form_data,
        appointment_id=body.appointment_id,
    )


@router.post("/membership/cancel-request")
async def request_cancellation(
    body: PortalCancellationRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Patient requests membership cancellation (triggers staff review)."""
    return await portal_action_service.request_membership_cancellation(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_id=portal_user.tenant.tenant_id,
        reason=body.reason,
    )


@router.post("/appointments/{appointment_id}/confirm")
async def confirm_appointment(
    appointment_id: str,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Confirm patient attendance for an appointment (F3)."""
    import uuid as _uuid
    from app.models.tenant.appointment import Appointment as _Appt
    from sqlalchemy import select as _select

    pid = _uuid.UUID(portal_user.patient_id)
    aid = _uuid.UUID(appointment_id)

    result = await db.execute(
        _select(_Appt).where(_Appt.id == aid, _Appt.patient_id == pid)
    )
    appt = result.scalar_one_or_none()

    if appt is None:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(error="APPOINTMENT_not_found", resource_name="Cita")

    if appt.status in ("pending", "scheduled"):
        appt.status = "confirmed"
        await db.flush()

    return {"id": str(appt.id), "status": appt.status, "message": "Asistencia confirmada."}


@router.put("/health-history")
async def update_health_history(
    body: PortalHealthHistoryUpdate,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Update patient health history from portal (F11)."""
    return await portal_action_service.update_health_history(
        db=db,
        patient_id=portal_user.patient_id,
        data=body.model_dump(exclude_none=True),
    )


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(default="other"),
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Upload a document from the patient portal (V4)."""
    file_content = await file.read()
    return await portal_action_service.upload_document(
        db=db,
        patient_id=portal_user.patient_id,
        tenant_id=portal_user.tenant.tenant_id,
        file_name=file.filename or "document",
        file_content=file_content,
        doc_type=doc_type,
        content_type=file.content_type or "application/octet-stream",
    )
