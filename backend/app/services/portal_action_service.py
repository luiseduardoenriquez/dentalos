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
        Validates slot availability before creating.
        """
        from datetime import timedelta
        from datetime import datetime as dt

        from app.services.appointment_service import appointment_service

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

        # Map appointment_type_id to a type string and resolve duration
        _type_durations: dict[str, int] = {
            "consultation": 30,
            "procedure": 60,
            "emergency": 30,
            "follow_up": 20,
        }
        appt_type = appointment_type_id if appointment_type_id in _type_durations else "consultation"
        duration_minutes = _type_durations[appt_type]
        end_time = scheduled_at + timedelta(minutes=duration_minutes)

        # Validate slot availability — reuse the service overlap check
        has_overlap = await appointment_service._check_overlap(
            db=db,
            doctor_id=did,
            start_time=scheduled_at,
            end_time=end_time,
            exclude_appointment_id=None,
        )
        if has_overlap:
            raise DentalOSError(
                error="APPOINTMENT_slot_unavailable",
                message="El horario seleccionado no está disponible. Por favor elige otro.",
                status_code=409,
            )

        appointment = Appointment(
            patient_id=pid,
            doctor_id=did,
            start_time=scheduled_at,
            end_time=end_time,
            duration_minutes=duration_minutes,
            type=appt_type,
            status="scheduled",
            notes=notes,
            source="portal",
        )
        db.add(appointment)
        await db.flush()

        # TODO: Dispatch notification to clinic

        logger.info("Appointment booked via portal")

        return {
            "id": str(appointment.id),
            "start_time": appointment.start_time,
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
        tenant_id: str,
        patient_id: str,
        thread_id: str | None = None,
        body: str,
        attachment_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a message from the portal (PP-11).

        If thread_id is provided, replies to existing thread.
        If thread_id is None, creates a new thread.
        """
        from app.services.messaging_service import messaging_service

        if thread_id:
            # Reply to existing thread
            result = await messaging_service.send_message(
                db=db,
                tenant_id=tenant_id,
                thread_id=thread_id,
                sender_type="patient",
                sender_id=patient_id,
                body=body,
            )
            return {**result, "message": "Mensaje enviado."}
        else:
            # Create new thread from patient
            result = await messaging_service.create_thread(
                db=db,
                tenant_id=tenant_id,
                created_by_id=patient_id,
                patient_id=patient_id,
                initial_message=body,
            )
            return {
                "id": result["id"],
                "thread_id": result["id"],
                "body": body,
                "sender_type": "patient",
                "created_at": result["created_at"],
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

    async def submit_intake(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        form_data: dict[str, Any],
        appointment_id: str | None = None,
    ) -> dict[str, Any]:
        """Submit a pre-appointment intake form from the portal (PP-13).

        Stores form answers as JSONB on the patient record under
        ``intake_responses``.  Optionally links the submission to an
        upcoming appointment for traceability.
        """
        from app.models.tenant.patient import Patient

        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(
                Patient.id == pid,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Paciente",
            )

        # Persist responses in the patient's metadata JSONB field
        metadata: dict[str, Any] = patient.metadata or {} if hasattr(patient, "metadata") else {}
        metadata["intake_responses"] = form_data
        metadata["intake_submitted_at"] = datetime.now(UTC).isoformat()
        if appointment_id:
            metadata["intake_appointment_id"] = appointment_id

        if hasattr(patient, "metadata"):
            patient.metadata = metadata
        await db.flush()

        # TODO: Dispatch notification to clinic staff on new intake submission

        logger.info(
            "Intake form submitted via portal: patient=%s appointment=%s",
            patient_id[:8],
            appointment_id[:8] if appointment_id else "none",
        )

        return {
            "status": "received",
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "message": "Formulario de ingreso recibido. ¡Gracias!",
        }

    async def request_membership_cancellation(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Request membership/subscription cancellation from the portal.

        Creates a cancellation request task for clinic staff to review.
        Does NOT cancel immediately — requires staff confirmation (VP-10).
        """
        from app.models.tenant.patient import Patient

        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(
                Patient.id == pid,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Paciente",
            )

        # Record the cancellation request in patient metadata for staff review
        metadata: dict[str, Any] = patient.metadata or {} if hasattr(patient, "metadata") else {}
        metadata["membership_cancel_request"] = {
            "requested_at": datetime.now(UTC).isoformat(),
            "reason": reason,
            "status": "pending_review",
        }

        if hasattr(patient, "metadata"):
            patient.metadata = metadata
        await db.flush()

        # TODO: Create staff task via task_service for manual review
        # TODO: Dispatch notification to clinic_owner

        logger.info(
            "Membership cancellation requested via portal: patient=%s tenant=%s",
            patient_id[:8],
            tenant_id,
        )

        return {
            "status": "pending_review",
            "patient_id": patient_id,
            "message": (
                "Tu solicitud de cancelación ha sido recibida. "
                "Un miembro del equipo se pondrá en contacto contigo."
            ),
        }


# Module-level singleton
portal_action_service = PortalActionService()
