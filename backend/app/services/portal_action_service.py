"""Portal action service — write endpoints for patient portal.

All methods enforce ownership: patient_id must match the authenticated user.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.appointment import Appointment
from app.models.tenant.consent import Consent
from app.models.tenant.treatment_plan import TreatmentPlan

logger = logging.getLogger("dentalos.portal_actions")


class PortalActionService:
    """Stateless portal action service."""

    async def approve_treatment_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
        signature_data: str,
        agreed_terms: bool,
    ) -> dict[str, Any]:
        """Approve a treatment plan with digital signature (PP-05)."""
        if not agreed_terms:
            raise DentalOSError(
                error="VALIDATION_terms_not_agreed",
                message="Debe aceptar los términos para aprobar el plan.",
                status_code=422,
            )

        pid = uuid.UUID(patient_id)
        plan_uuid = uuid.UUID(plan_id)

        result = await db.execute(
            select(TreatmentPlan).where(
                TreatmentPlan.id == plan_uuid,
                TreatmentPlan.patient_id == pid,
            )
        )
        plan = result.scalar_one_or_none()

        if plan is None:
            raise ResourceNotFoundError(
                error="TREATMENT_PLAN_not_found",
                resource_name="Plan de tratamiento",
            )

        if plan.status != "pending_approval":
            raise DentalOSError(
                error="TREATMENT_PLAN_invalid_status",
                message="El plan no está pendiente de aprobación.",
                status_code=409,
            )

        # Update status
        plan.status = "approved"
        plan.approved_at = datetime.now(UTC) if hasattr(plan, "approved_at") else None
        await db.flush()

        # TODO: Store digital signature via signature service
        # TODO: Dispatch notification to clinic

        logger.info("Treatment plan approved via portal: plan=%s", plan_id[:8])

        return {
            "id": str(plan.id),
            "name": plan.name,
            "status": plan.status,
            "message": "Plan de tratamiento aprobado exitosamente.",
        }

    async def book_appointment(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        appointment_type_id: str,
        preferred_date: str,
        preferred_time: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Book an appointment from the portal (PP-08).

        Creates appointment with status 'pending' — requires clinic confirmation.
        """
        from datetime import datetime as dt

        pid = uuid.UUID(patient_id)
        did = uuid.UUID(doctor_id)

        # Parse date and time
        try:
            scheduled_at = dt.fromisoformat(f"{preferred_date}T{preferred_time}:00")
        except ValueError:
            raise DentalOSError(
                error="VALIDATION_invalid_datetime",
                message="Fecha u hora inválida.",
                status_code=422,
            )

        # TODO: Validate slot availability via appointment service

        appointment = Appointment(
            patient_id=pid,
            doctor_id=did,
            scheduled_at=scheduled_at,
            duration_minutes=30,  # Default, TODO: get from appointment type
            status="pending",
            notes=notes,
            source="portal",
        )
        db.add(appointment)
        await db.flush()

        # TODO: Dispatch notification to clinic

        logger.info("Appointment booked via portal")

        return {
            "id": str(appointment.id),
            "scheduled_at": appointment.scheduled_at,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "message": "Cita solicitada. La clínica confirmará tu cita.",
        }

    async def cancel_appointment(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        appointment_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Cancel an appointment from the portal (PP-09)."""
        pid = uuid.UUID(patient_id)
        aid = uuid.UUID(appointment_id)

        result = await db.execute(
            select(Appointment).where(
                Appointment.id == aid,
                Appointment.patient_id == pid,
            )
        )
        appt = result.scalar_one_or_none()

        if appt is None:
            raise ResourceNotFoundError(
                error="APPOINTMENT_not_found",
                resource_name="Cita",
            )

        if appt.status not in ("confirmed", "pending"):
            raise DentalOSError(
                error="APPOINTMENT_cannot_cancel",
                message="Esta cita no puede ser cancelada.",
                status_code=409,
            )

        appt.status = "cancelled_by_patient"
        if hasattr(appt, "cancellation_reason"):
            appt.cancellation_reason = reason
        await db.flush()

        # TODO: Dispatch notification to clinic

        logger.info("Appointment cancelled via portal")

        return {
            "id": str(appt.id),
            "status": appt.status,
            "message": "Cita cancelada exitosamente.",
        }

    async def send_message(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        thread_id: str | None = None,
        body: str,
        attachment_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a message from the portal (PP-11).

        Note: Messaging tables don't exist yet. Returns placeholder.
        """
        # TODO: Implement when messaging tables are created
        logger.info("Portal message sent (placeholder)")

        return {
            "id": str(uuid.uuid4()),
            "thread_id": thread_id or str(uuid.uuid4()),
            "body": body,
            "sender_type": "patient",
            "created_at": datetime.now(UTC),
            "message": "Mensaje enviado.",
        }

    async def sign_consent(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        consent_id: str,
        signature_data: str,
        acknowledged: bool,
    ) -> dict[str, Any]:
        """Sign a consent document from the portal (PP-12)."""
        if not acknowledged:
            raise DentalOSError(
                error="VALIDATION_not_acknowledged",
                message="Debe confirmar que ha leído el consentimiento.",
                status_code=422,
            )

        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(consent_id)

        result = await db.execute(
            select(Consent).where(
                Consent.id == cid,
                Consent.patient_id == pid,
            )
        )
        consent = result.scalar_one_or_none()

        if consent is None:
            raise ResourceNotFoundError(
                error="CONSENT_not_found",
                resource_name="Consentimiento",
            )

        if consent.status == "signed":
            raise DentalOSError(
                error="CONSENT_already_signed",
                message="Este consentimiento ya fue firmado.",
                status_code=409,
            )

        consent.status = "signed"
        consent.signed_at = datetime.now(UTC)
        await db.flush()

        # TODO: Store digital signature via signature service
        # TODO: Dispatch notification to clinic

        logger.info("Consent signed via portal: consent=%s", consent_id[:8])

        return {
            "id": str(consent.id),
            "status": consent.status,
            "signed_at": consent.signed_at,
            "message": "Consentimiento firmado exitosamente.",
        }


# Module-level singleton
portal_action_service = PortalActionService()
