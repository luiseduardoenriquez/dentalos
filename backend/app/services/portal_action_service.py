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
from app.services.digital_signature_service import digital_signature_service
from app.services.notification_dispatch import dispatch_notification

logger = logging.getLogger("dentalos.portal_actions")


# ─── Helper: find clinic owner user_id for notifications ─────────────────────


async def _find_clinic_owner_id(db: AsyncSession) -> str | None:
    """Find the first active clinic_owner user id for notification dispatch."""
    from app.models.tenant.user import User

    result = await db.execute(
        select(User.id).where(
            User.role == "clinic_owner",
            User.is_active.is_(True),
        ).limit(1)
    )
    owner_id = result.scalar_one_or_none()
    return str(owner_id) if owner_id else None


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
        tenant_id: str,
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

        # G2: Store digital signature
        try:
            await digital_signature_service.create_signature(
                db=db,
                tenant_id=tenant_id,
                signer_id=patient_id,
                document_type="treatment_plan",
                document_id=plan_id,
                signer_type="patient",
                signature_image_b64=signature_data,
            )
        except Exception:
            logger.warning("Failed to store signature for plan=%s", plan_id[:8])

        # G3: Dispatch notification to clinic
        owner_id = await _find_clinic_owner_id(db)
        if owner_id:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=owner_id,
                event_type="treatment_plan_approved",
                data={
                    "plan_id": plan_id,
                    "plan_name": plan.name,
                    "patient_id": patient_id,
                },
            )

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
        tenant_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Book an appointment from the portal (PP-08).

        Creates appointment with status 'scheduled' — requires clinic confirmation.
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

        # G3: Dispatch notification to assigned doctor
        await dispatch_notification(
            tenant_id=tenant_id,
            user_id=doctor_id,
            event_type="appointment_booked_portal",
            data={
                "appointment_id": str(appointment.id),
                "patient_id": patient_id,
                "start_time": scheduled_at.isoformat(),
                "type": appt_type,
            },
        )

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
        tenant_id: str,
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

        if appt.status not in ("confirmed", "pending", "scheduled"):
            raise DentalOSError(
                error="APPOINTMENT_cannot_cancel",
                message="Esta cita no puede ser cancelada.",
                status_code=409,
            )

        appt.status = "cancelled_by_patient"
        if hasattr(appt, "cancellation_reason"):
            appt.cancellation_reason = reason
        await db.flush()

        # G3: Dispatch notification to assigned doctor
        if appt.doctor_id:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=str(appt.doctor_id),
                event_type="appointment_cancelled_patient",
                data={
                    "appointment_id": appointment_id,
                    "patient_id": patient_id,
                    "reason": reason,
                },
            )

        logger.info("Appointment cancelled via portal")

        return {
            "id": str(appt.id),
            "status": appt.status,
            "message": "Cita cancelada exitosamente.",
        }

    async def reschedule_appointment(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        appointment_id: str,
        tenant_id: str,
        new_date: str,
        new_time: str,
    ) -> dict[str, Any]:
        """Reschedule an appointment atomically (V3).

        Validates new slot → creates new appointment → cancels old one.
        """
        from datetime import timedelta
        from datetime import datetime as dt

        from app.services.appointment_service import appointment_service

        pid = uuid.UUID(patient_id)
        aid = uuid.UUID(appointment_id)

        # Load old appointment
        result = await db.execute(
            select(Appointment).where(
                Appointment.id == aid,
                Appointment.patient_id == pid,
            )
        )
        old_appt = result.scalar_one_or_none()

        if old_appt is None:
            raise ResourceNotFoundError(
                error="APPOINTMENT_not_found",
                resource_name="Cita",
            )

        if old_appt.status not in ("confirmed", "pending", "scheduled"):
            raise DentalOSError(
                error="APPOINTMENT_cannot_reschedule",
                message="Esta cita no puede ser reagendada.",
                status_code=409,
            )

        # Parse new date/time
        try:
            new_scheduled_at = dt.fromisoformat(f"{new_date}T{new_time}:00")
        except ValueError:
            raise DentalOSError(
                error="VALIDATION_invalid_datetime",
                message="Fecha u hora inválida.",
                status_code=422,
            )

        duration = old_appt.duration_minutes
        new_end = new_scheduled_at + timedelta(minutes=duration)

        # Validate slot availability
        has_overlap = await appointment_service._check_overlap(
            db=db,
            doctor_id=old_appt.doctor_id,
            start_time=new_scheduled_at,
            end_time=new_end,
            exclude_appointment_id=None,
        )
        if has_overlap:
            raise DentalOSError(
                error="APPOINTMENT_slot_unavailable",
                message="El nuevo horario no está disponible.",
                status_code=409,
            )

        # Create new appointment
        new_appt = Appointment(
            patient_id=pid,
            doctor_id=old_appt.doctor_id,
            start_time=new_scheduled_at,
            end_time=new_end,
            duration_minutes=duration,
            type=old_appt.type,
            status="scheduled",
            notes=old_appt.notes,
            source="portal",
        )
        db.add(new_appt)

        # Cancel old appointment
        old_appt.status = "rescheduled"
        if hasattr(old_appt, "cancellation_reason"):
            old_appt.cancellation_reason = "Reagendada por el paciente"
        await db.flush()

        # Dispatch notification to doctor
        if old_appt.doctor_id:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=str(old_appt.doctor_id),
                event_type="appointment_rescheduled_patient",
                data={
                    "old_appointment_id": appointment_id,
                    "new_appointment_id": str(new_appt.id),
                    "patient_id": patient_id,
                    "new_start_time": new_scheduled_at.isoformat(),
                },
            )

        logger.info("Appointment rescheduled via portal")

        return {
            "id": str(new_appt.id),
            "old_appointment_id": appointment_id,
            "start_time": new_appt.start_time,
            "duration_minutes": new_appt.duration_minutes,
            "status": new_appt.status,
            "message": "Cita reagendada exitosamente.",
        }

    async def upload_document(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        file_name: str,
        file_content: bytes,
        doc_type: str,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload a document from the patient portal (V4).

        Validates file type and size, uploads to S3, creates PatientDocument record.
        """
        from app.core.storage import storage_client
        from app.models.tenant.patient_document import PatientDocument

        # Validate file size (10MB max)
        max_size = 10 * 1024 * 1024
        if len(file_content) > max_size:
            raise DentalOSError(
                error="VALIDATION_file_too_large",
                message="El archivo excede el tamaño máximo de 10MB.",
                status_code=422,
            )

        # Validate content type
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        if content_type not in allowed_types:
            raise DentalOSError(
                error="VALIDATION_invalid_file_type",
                message="Tipo de archivo no permitido. Solo JPEG, PNG y PDF.",
                status_code=422,
            )

        ext_map = {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}
        ext = ext_map.get(content_type, "bin")
        file_id = str(uuid.uuid4())
        s3_key = f"/{tenant_id}/{patient_id}/uploads/{file_id}.{ext}"

        # Upload to S3
        await storage_client.upload_file(
            key=s3_key,
            data=file_content,
            content_type=content_type,
        )

        # Create document record
        pid = uuid.UUID(patient_id)
        doc = PatientDocument(
            patient_id=pid,
            document_type=doc_type,
            file_name=file_name,
            file_url=s3_key,
            description=f"Subido por paciente: {doc_type}",
            is_active=True,
        )
        db.add(doc)
        await db.flush()

        logger.info("Document uploaded via portal: type=%s", doc_type)

        return {
            "id": str(doc.id),
            "document_type": doc_type,
            "file_name": file_name,
            "created_at": doc.created_at,
            "message": "Documento subido exitosamente.",
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
        tenant_id: str,
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

        # G2: Store digital signature
        try:
            await digital_signature_service.create_signature(
                db=db,
                tenant_id=tenant_id,
                signer_id=patient_id,
                document_type="consent",
                document_id=consent_id,
                signer_type="patient",
                signature_image_b64=signature_data,
            )
        except Exception:
            logger.warning("Failed to store signature for consent=%s", consent_id[:8])

        # G3: Dispatch notification to clinic
        owner_id = await _find_clinic_owner_id(db)
        if owner_id:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=owner_id,
                event_type="consent_signed",
                data={
                    "consent_id": consent_id,
                    "patient_id": patient_id,
                },
            )

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
        tenant_id: str,
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

        # G3: Dispatch notification to clinic owner
        owner_id = await _find_clinic_owner_id(db)
        if owner_id:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=owner_id,
                event_type="intake_submitted",
                data={
                    "patient_id": patient_id,
                    "appointment_id": appointment_id,
                },
            )

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

        # G3: Dispatch notification to clinic_owner
        owner_id = await _find_clinic_owner_id(db)
        if owner_id:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=owner_id,
                event_type="membership_cancel_requested",
                data={
                    "patient_id": patient_id,
                    "reason": reason,
                },
            )

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


    async def update_health_history(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update patient health history from portal (F11)."""
        from app.models.tenant.patient import Patient

        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Paciente",
            )

        metadata: dict[str, Any] = patient.metadata or {} if hasattr(patient, "metadata") else {}
        health = metadata.get("health_history", {})

        allowed = {"allergies", "medications", "conditions", "surgeries", "notes"}
        for field, value in data.items():
            if field in allowed and value is not None:
                health[field] = value

        health["updated_at"] = datetime.now(UTC).isoformat()
        metadata["health_history"] = health

        if hasattr(patient, "metadata"):
            patient.metadata = metadata
        await db.flush()

        logger.info("Health history updated via portal: patient=%s", patient_id[:8])

        return {
            "message": "Historia de salud actualizada exitosamente.",
            **{k: v for k, v in health.items() if k != "updated_at"},
        }


# Module-level singleton
portal_action_service = PortalActionService()
