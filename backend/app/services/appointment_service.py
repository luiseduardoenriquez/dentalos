"""Appointment service -- create, schedule, confirm, complete, and cancel appointments.

Security invariants:
  - PHI is NEVER logged (patient names, phone numbers, document numbers).
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - IDs are truncated to 8 chars in log messages.
  - HMAC tokens use SHA-256 with time-limited payloads (48h TTL).
"""

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.error_codes import AppointmentErrors
from app.core.exceptions import AppointmentError, DentalOSError, ResourceNotFoundError
from app.models.tenant.appointment import Appointment
from app.models.tenant.patient import Patient
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.appointment")

# Default durations by appointment type (minutes).
_DEFAULT_DURATIONS: dict[str, int] = {
    "consultation": 30,
    "procedure": 60,
    "emergency": 30,
    "follow_up": 20,
}

# Statuses that are considered "terminal" -- no further transitions.
_TERMINAL_STATUSES = frozenset({"completed", "cancelled", "no_show"})

# Statuses excluded from overlap checks -- these slots are "free".
_OVERLAP_EXCLUDED_STATUSES = frozenset({"cancelled", "no_show"})


class AppointmentService:
    """Stateless appointment service.

    All state flows through the ``db: AsyncSession`` parameter.
    """

    # ------------------------------------------------------------------
    # 1. Create
    # ------------------------------------------------------------------

    async def create_appointment(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        start_time: datetime,
        type: str,
        created_by: str,
        duration_minutes: int | None = None,
        treatment_plan_item_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new appointment.

        Raises:
            DentalOSError (404) -- patient or doctor not found / inactive.
            AppointmentError (422) -- start_time in the past.
            AppointmentError (409) -- slot overlap for non-emergency types.
        """
        pid = uuid.UUID(patient_id)
        did = uuid.UUID(doctor_id)

        # Validate patient exists and is active
        patient = await self._get_patient_or_raise(db, pid)

        # Validate doctor exists and is active
        doctor = await self._get_doctor_or_raise(db, did)

        # Reject past start times
        if start_time < datetime.now(UTC):
            raise AppointmentError(
                error=AppointmentErrors.PAST_START_TIME,
                message="No se puede agendar una cita en el pasado.",
                status_code=422,
            )

        # Resolve duration
        if duration_minutes is None:
            duration_minutes = _DEFAULT_DURATIONS.get(type, 30)

        end_time = start_time + timedelta(minutes=duration_minutes)

        # Overlap check (skip for emergency appointments)
        if type != "emergency":
            has_overlap = await self._check_overlap(
                db=db,
                doctor_id=did,
                start_time=start_time,
                end_time=end_time,
                exclude_appointment_id=None,
            )
            if has_overlap:
                raise AppointmentError(
                    error=AppointmentErrors.SLOT_UNAVAILABLE,
                    message="El horario seleccionado no esta disponible para este doctor.",
                    status_code=409,
                )

        appointment = Appointment(
            patient_id=pid,
            doctor_id=did,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            type=type,
            status="scheduled",
            treatment_plan_item_id=uuid.UUID(treatment_plan_item_id) if treatment_plan_item_id else None,
            completion_notes=notes,
            created_by=uuid.UUID(created_by),
            is_active=True,
        )
        db.add(appointment)
        await db.flush()
        await db.refresh(appointment)

        logger.info(
            "Appointment created: patient=%s doctor=%s type=%s",
            patient_id[:8],
            doctor_id[:8],
            type,
        )

        return self._to_dict(
            appointment,
            patient_name=f"{patient.first_name} {patient.last_name}",
            doctor_name=doctor.name,
        )

    # ------------------------------------------------------------------
    # 2. Get single
    # ------------------------------------------------------------------

    async def get_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single appointment by ID.

        Returns None if not found or soft-deleted.
        """
        aid = uuid.UUID(appointment_id)

        result = await db.execute(
            select(Appointment).where(
                Appointment.id == aid,
                Appointment.is_active.is_(True),
            )
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            return None

        # Resolve names with separate queries to avoid join complexity
        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 3. List (cursor-based) / Calendar view
    # ------------------------------------------------------------------

    async def list_appointments(
        self,
        *,
        db: AsyncSession,
        mode: str = "list",
        doctor_id: str | None = None,
        patient_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List appointments in two modes.

        mode="list":
            Cursor-based pagination ordered by (start_time, id).
            Returns {items, total, next_cursor}.

        mode="calendar":
            Returns ALL appointments grouped by date within the range.
            Max 90-day range.
            Returns {dates: {YYYY-MM-DD: [...]}, date_from, date_to}.

        Raises:
            AppointmentError (422) -- calendar mode with >90 day range.
        """
        # Base filters
        filters = [Appointment.is_active.is_(True)]

        if doctor_id:
            filters.append(Appointment.doctor_id == uuid.UUID(doctor_id))
        if patient_id:
            filters.append(Appointment.patient_id == uuid.UUID(patient_id))
        if date_from:
            filters.append(Appointment.start_time >= date_from)
        if date_to:
            filters.append(Appointment.start_time <= date_to)
        if status:
            filters.append(Appointment.status == status)

        if mode == "calendar":
            return await self._list_calendar(
                db=db,
                filters=filters,
                date_from=date_from,
                date_to=date_to,
            )

        # Default: cursor-based list mode
        return await self._list_cursor(
            db=db,
            filters=filters,
            cursor=cursor,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # 4. Update
    # ------------------------------------------------------------------

    async def update_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
        start_time: datetime | None = None,
        duration_minutes: int | None = None,
        type: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update an appointment's schedule or metadata.

        Only allowed when status is 'scheduled' or 'confirmed'.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (409) -- invalid status for update.
            AppointmentError (409) -- slot overlap after time change.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        if appointment.status not in ("scheduled", "confirmed"):
            raise AppointmentError(
                error=AppointmentErrors.INVALID_STATUS_TRANSITION,
                message="Solo se pueden modificar citas en estado agendada o confirmada.",
                status_code=409,
            )

        time_changed = False

        if type is not None:
            appointment.type = type

        if start_time is not None:
            appointment.start_time = start_time
            time_changed = True

        if duration_minutes is not None:
            appointment.duration_minutes = duration_minutes
            time_changed = True

        # Recalculate end_time when timing changes
        if time_changed:
            appointment.end_time = appointment.start_time + timedelta(
                minutes=appointment.duration_minutes
            )

            # Re-validate overlap (exclude self)
            if appointment.type != "emergency":
                has_overlap = await self._check_overlap(
                    db=db,
                    doctor_id=appointment.doctor_id,
                    start_time=appointment.start_time,
                    end_time=appointment.end_time,
                    exclude_appointment_id=appointment.id,
                )
                if has_overlap:
                    raise AppointmentError(
                        error=AppointmentErrors.SLOT_UNAVAILABLE,
                        message="El nuevo horario no esta disponible para este doctor.",
                        status_code=409,
                    )

        if notes is not None:
            appointment.completion_notes = notes

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info("Appointment updated: id=%s", appointment_id[:8])

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 5. Cancel
    # ------------------------------------------------------------------

    async def cancel_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
        reason: str,
        cancelled_by_patient: bool = False,
        current_user_role: str | None = None,
    ) -> dict[str, Any]:
        """Cancel an appointment.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (409) -- already in a terminal status.
            AppointmentError (422) -- patient cancellation without 2h notice.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        if appointment.status in _TERMINAL_STATUSES:
            raise AppointmentError(
                error=AppointmentErrors.ALREADY_CANCELLED,
                message="La cita ya fue completada, cancelada o marcada como inasistencia.",
                status_code=409,
            )

        # Patient self-cancellation requires minimum 2-hour notice
        if cancelled_by_patient:
            min_notice = appointment.start_time - timedelta(hours=2)
            if datetime.now(UTC) > min_notice:
                raise AppointmentError(
                    error=AppointmentErrors.MIN_CANCEL_NOTICE,
                    message="Las cancelaciones por el paciente requieren al menos 2 horas de anticipacion.",
                    status_code=422,
                )

        appointment.status = "cancelled"
        appointment.cancellation_reason = reason
        appointment.cancelled_by_patient = cancelled_by_patient

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info(
            "Appointment cancelled: id=%s by_patient=%s",
            appointment_id[:8],
            cancelled_by_patient,
        )

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 6. Confirm
    # ------------------------------------------------------------------

    async def confirm_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
        hmac_token: str | None = None,
    ) -> dict[str, Any]:
        """Confirm an appointment.

        Two modes:
          - JWT-authenticated (hmac_token is None): staff confirms via dashboard.
          - HMAC token from email/SMS link: patient self-confirms.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (401) -- invalid or expired HMAC token.
            AppointmentError (409) -- already confirmed.
            AppointmentError (409) -- invalid status transition.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        # HMAC token verification for patient self-confirmation
        if hmac_token is not None:
            if not self._verify_hmac_token(hmac_token, appointment_id):
                raise AppointmentError(
                    error="AUTH_invalid_token",
                    message="El enlace de confirmacion es invalido o ha expirado.",
                    status_code=401,
                )

        if appointment.status == "confirmed":
            raise AppointmentError(
                error=AppointmentErrors.ALREADY_CONFIRMED,
                message="La cita ya fue confirmada.",
                status_code=409,
            )

        if appointment.status != "scheduled":
            raise AppointmentError(
                error=AppointmentErrors.INVALID_STATUS_TRANSITION,
                message="Solo se pueden confirmar citas en estado agendada.",
                status_code=409,
            )

        appointment.status = "confirmed"

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info("Appointment confirmed: id=%s", appointment_id[:8])

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 6b. Start (confirmed → in_progress)
    # ------------------------------------------------------------------

    async def start_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
    ) -> dict[str, Any]:
        """Transition a confirmed appointment to in_progress.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (409) -- invalid status for starting.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        if appointment.status != "confirmed":
            raise AppointmentError(
                error=AppointmentErrors.INVALID_STATUS_TRANSITION,
                message="Solo se pueden iniciar citas en estado confirmada.",
                status_code=409,
            )

        appointment.status = "in_progress"

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info("Appointment started: id=%s", appointment_id[:8])

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 7. Complete
    # ------------------------------------------------------------------

    async def complete_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
        completion_notes: str | None = None,
    ) -> dict[str, Any]:
        """Mark an appointment as completed.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (409) -- invalid status for completion.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        if appointment.status not in ("confirmed", "in_progress"):
            raise AppointmentError(
                error=AppointmentErrors.CANNOT_COMPLETE,
                message="Solo se pueden completar citas en estado confirmada o en progreso.",
                status_code=409,
            )

        appointment.status = "completed"
        appointment.completed_at = datetime.now(UTC)
        if completion_notes is not None:
            appointment.completion_notes = completion_notes

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info("Appointment completed: id=%s", appointment_id[:8])

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 8. No-show
    # ------------------------------------------------------------------

    async def no_show(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
    ) -> dict[str, Any]:
        """Mark an appointment as no-show.

        Increments the patient's no_show_count counter.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (409) -- invalid status for no-show.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        if appointment.status not in ("scheduled", "confirmed"):
            raise AppointmentError(
                error=AppointmentErrors.CANNOT_NO_SHOW,
                message="Solo se puede marcar inasistencia en citas agendadas o confirmadas.",
                status_code=409,
            )

        appointment.status = "no_show"
        appointment.no_show_at = datetime.now(UTC)

        await db.flush()

        # Increment patient no_show_count (defensive: column may not exist in older schemas)
        try:
            await db.execute(
                update(Patient)
                .where(Patient.id == appointment.patient_id)
                .values(no_show_count=Patient.no_show_count + 1)
            )
        except Exception:
            logger.warning(
                "Could not increment no_show_count for patient=%s (column may not exist)",
                str(appointment.patient_id)[:8],
            )

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info(
            "Appointment no-show: id=%s patient=%s",
            appointment_id[:8],
            str(appointment.patient_id)[:8],
        )

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ------------------------------------------------------------------
    # 9. Reschedule (optimized for drag-drop)
    # ------------------------------------------------------------------

    async def reschedule(
        self,
        *,
        db: AsyncSession,
        appointment_id: str,
        start_time: datetime,
        duration_minutes: int | None = None,
    ) -> dict[str, Any]:
        """Reschedule an appointment to a new time slot.

        Designed for drag-and-drop in the agenda view -- minimal payload.
        Preserves the original duration when not explicitly provided.

        Raises:
            ResourceNotFoundError (404) -- appointment not found.
            AppointmentError (409) -- invalid status for reschedule.
            AppointmentError (409) -- slot overlap at new time.
        """
        appointment = await self._get_appointment_or_raise(db, appointment_id)

        if appointment.status not in ("scheduled", "confirmed"):
            raise AppointmentError(
                error=AppointmentErrors.INVALID_STATUS_TRANSITION,
                message="Solo se pueden reprogramar citas en estado agendada o confirmada.",
                status_code=409,
            )

        # Preserve original duration if not provided
        if duration_minutes is not None:
            appointment.duration_minutes = duration_minutes

        appointment.start_time = start_time
        appointment.end_time = start_time + timedelta(minutes=appointment.duration_minutes)

        # Validate overlap at new time (exclude self)
        if appointment.type != "emergency":
            has_overlap = await self._check_overlap(
                db=db,
                doctor_id=appointment.doctor_id,
                start_time=appointment.start_time,
                end_time=appointment.end_time,
                exclude_appointment_id=appointment.id,
            )
            if has_overlap:
                raise AppointmentError(
                    error=AppointmentErrors.SLOT_UNAVAILABLE,
                    message="El nuevo horario no esta disponible para este doctor.",
                    status_code=409,
                )

        await db.flush()
        await db.refresh(appointment)

        patient_name = await self._resolve_patient_name(db, appointment.patient_id)
        doctor_name = await self._resolve_doctor_name(db, appointment.doctor_id)

        logger.info("Appointment rescheduled: id=%s new_start=%s", appointment_id[:8], start_time)

        return self._to_dict(appointment, patient_name=patient_name, doctor_name=doctor_name)

    # ==================================================================
    # HMAC token helpers (for email/SMS confirmation links)
    # ==================================================================

    def _generate_hmac_token(self, appointment_id: str, patient_id: str) -> str:
        """Generate HMAC-SHA256 confirmation token with 48h TTL.

        Token format: ``{appointment_id}:{patient_id}:{expires_timestamp}:{signature}``
        """
        expires_at = int((datetime.now(UTC) + timedelta(hours=48)).timestamp())
        payload = f"{appointment_id}:{patient_id}:{expires_at}"
        secret = getattr(settings, "secret_key", "dentalos-dev-secret")
        signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}:{signature}"

    def _verify_hmac_token(self, token: str, appointment_id: str) -> bool:
        """Verify an HMAC-SHA256 confirmation token.

        Returns True only when the signature is valid, the token has not
        expired, and the embedded appointment ID matches.
        """
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False
            appt_id, patient_id, expires_str, signature = parts
            if appt_id != appointment_id:
                return False
            expires_at = int(expires_str)
            if datetime.now(UTC).timestamp() > expires_at:
                return False
            payload = f"{appt_id}:{patient_id}:{expires_str}"
            secret = getattr(settings, "secret_key", "dentalos-dev-secret")
            expected = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except (ValueError, IndexError):
            return False

    # ==================================================================
    # Private helpers
    # ==================================================================

    def _to_dict(
        self,
        appointment: Appointment,
        patient_name: str | None = None,
        doctor_name: str | None = None,
    ) -> dict[str, Any]:
        """Serialize an Appointment ORM instance to a plain dict."""
        return {
            "id": str(appointment.id),
            "patient_id": str(appointment.patient_id),
            "doctor_id": str(appointment.doctor_id),
            "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
            "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
            "duration_minutes": appointment.duration_minutes,
            "type": appointment.type,
            "status": appointment.status,
            "treatment_plan_item_id": (
                str(appointment.treatment_plan_item_id)
                if appointment.treatment_plan_item_id
                else None
            ),
            "cancellation_reason": appointment.cancellation_reason,
            "cancelled_by_patient": appointment.cancelled_by_patient,
            "no_show_at": (
                appointment.no_show_at.isoformat() if appointment.no_show_at else None
            ),
            "completed_at": (
                appointment.completed_at.isoformat() if appointment.completed_at else None
            ),
            "completion_notes": appointment.completion_notes,
            "created_by": str(appointment.created_by),
            "is_active": appointment.is_active,
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
            "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
        }

    async def _get_appointment_or_raise(
        self,
        db: AsyncSession,
        appointment_id: str,
    ) -> Appointment:
        """Fetch an active appointment or raise 404."""
        aid = uuid.UUID(appointment_id)
        result = await db.execute(
            select(Appointment).where(
                Appointment.id == aid,
                Appointment.is_active.is_(True),
            )
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            raise ResourceNotFoundError(
                error=AppointmentErrors.NOT_FOUND,
                resource_name="Appointment",
            )
        return appointment

    async def _get_patient_or_raise(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
    ) -> Patient:
        """Fetch an active patient or raise 404."""
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="El paciente no existe o esta inactivo.",
                status_code=404,
            )
        return patient

    async def _get_doctor_or_raise(
        self,
        db: AsyncSession,
        doctor_id: uuid.UUID,
    ) -> User:
        """Fetch an active doctor (user) or raise 404."""
        result = await db.execute(
            select(User).where(
                User.id == doctor_id,
                User.is_active.is_(True),
            )
        )
        doctor = result.scalar_one_or_none()
        if doctor is None:
            raise DentalOSError(
                error="APPOINTMENT_doctor_not_available",
                message="El doctor no existe o esta inactivo.",
                status_code=404,
            )
        return doctor

    async def _check_overlap(
        self,
        *,
        db: AsyncSession,
        doctor_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if the proposed time range overlaps with existing appointments.

        Two intervals overlap when:
            existing.start_time < new_end_time AND existing.end_time > new_start_time

        Excludes cancelled and no_show appointments.
        Optionally excludes a specific appointment (for updates/reschedules).

        Returns True if there is an overlap.
        """
        overlap_filters = [
            Appointment.doctor_id == doctor_id,
            Appointment.is_active.is_(True),
            Appointment.status.notin_(list(_OVERLAP_EXCLUDED_STATUSES)),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        ]

        if exclude_appointment_id is not None:
            overlap_filters.append(Appointment.id != exclude_appointment_id)

        result = await db.execute(
            select(func.count(Appointment.id)).where(and_(*overlap_filters))
        )
        count = result.scalar_one()
        return count > 0

    async def _resolve_patient_name(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
    ) -> str | None:
        """Resolve a patient's display name. Returns None if not found."""
        result = await db.execute(
            select(Patient.first_name, Patient.last_name).where(Patient.id == patient_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return f"{row.first_name} {row.last_name}"

    async def _resolve_doctor_name(
        self,
        db: AsyncSession,
        doctor_id: uuid.UUID,
    ) -> str | None:
        """Resolve a doctor's display name. Returns None if not found."""
        result = await db.execute(
            select(User.name).where(User.id == doctor_id)
        )
        name = result.scalar_one_or_none()
        return name

    async def _list_cursor(
        self,
        *,
        db: AsyncSession,
        filters: list,
        cursor: str | None,
        page_size: int,
    ) -> dict[str, Any]:
        """Cursor-based pagination ordered by (start_time, id).

        Cursor format: ``{start_time_iso}|{appointment_id}``
        """
        # Total count (for informational purposes)
        total_result = await db.execute(
            select(func.count(Appointment.id)).where(and_(*filters))
        )
        total = total_result.scalar_one()

        # Apply cursor
        query_filters = list(filters)
        if cursor:
            try:
                cursor_time_str, cursor_id_str = cursor.split("|", 1)
                cursor_time = datetime.fromisoformat(cursor_time_str)
                cursor_id = uuid.UUID(cursor_id_str)
                # Seek past the cursor position: records after (start_time, id)
                query_filters.append(
                    or_(
                        Appointment.start_time > cursor_time,
                        and_(
                            Appointment.start_time == cursor_time,
                            Appointment.id > cursor_id,
                        ),
                    )
                )
            except (ValueError, IndexError):
                pass  # Ignore malformed cursors -- start from the beginning

        result = await db.execute(
            select(Appointment)
            .where(and_(*query_filters))
            .order_by(Appointment.start_time.asc(), Appointment.id.asc())
            .limit(page_size + 1)  # Fetch one extra to detect next page
        )
        appointments = result.scalars().all()

        # Determine next cursor
        has_next = len(appointments) > page_size
        if has_next:
            appointments = appointments[:page_size]

        next_cursor: str | None = None
        if has_next and appointments:
            last = appointments[-1]
            next_cursor = f"{last.start_time.isoformat()}|{last.id}"

        # Batch-resolve names
        items = []
        for appt in appointments:
            patient_name = await self._resolve_patient_name(db, appt.patient_id)
            doctor_name = await self._resolve_doctor_name(db, appt.doctor_id)
            items.append(self._to_dict(appt, patient_name=patient_name, doctor_name=doctor_name))

        return {
            "items": items,
            "total": total,
            "next_cursor": next_cursor,
        }

    async def _list_calendar(
        self,
        *,
        db: AsyncSession,
        filters: list,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> dict[str, Any]:
        """Calendar mode: group appointments by date within the range.

        Returns every date in the range as a key, even if it has no
        appointments (empty list). Max 90-day range.

        Raises:
            AppointmentError (422) -- range exceeds 90 days.
        """
        # Default range: today + 30 days
        now = datetime.now(UTC)
        if date_from is None:
            date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if date_to is None:
            date_to = date_from + timedelta(days=30)

        # Validate max range
        delta = date_to - date_from
        if delta.days > 90:
            raise AppointmentError(
                error="VALIDATION_failed",
                message="El rango de fechas para vista calendario no puede exceder 90 dias.",
                status_code=422,
            )

        # Ensure date_from/date_to are in the filters
        calendar_filters = list(filters)
        # Remove any existing date filters to avoid duplicates, then add canonical ones
        calendar_filters = [
            f
            for f in calendar_filters
            if not (
                hasattr(f, "left")
                and hasattr(f.left, "key")
                and str(getattr(f.left, "key", "")) == "start_time"
            )
        ]
        calendar_filters.append(Appointment.start_time >= date_from)
        calendar_filters.append(Appointment.start_time <= date_to)

        result = await db.execute(
            select(Appointment)
            .where(and_(*calendar_filters))
            .order_by(Appointment.start_time.asc())
        )
        appointments = result.scalars().all()

        # Build date-keyed dict with every date in range
        dates: dict[str, list[dict[str, Any]]] = {}
        current_date = date_from.date() if hasattr(date_from, "date") else date_from
        end_date = date_to.date() if hasattr(date_to, "date") else date_to
        while current_date <= end_date:
            dates[current_date.isoformat()] = []
            current_date += timedelta(days=1)

        # Populate with appointments
        for appt in appointments:
            appt_date = appt.start_time.date().isoformat()
            if appt_date in dates:
                patient_name = await self._resolve_patient_name(db, appt.patient_id)
                doctor_name = await self._resolve_doctor_name(db, appt.doctor_id)
                dates[appt_date].append(
                    self._to_dict(appt, patient_name=patient_name, doctor_name=doctor_name)
                )

        return {
            "dates": dates,
            "date_from": date_from.isoformat() if hasattr(date_from, "isoformat") else str(date_from),
            "date_to": date_to.isoformat() if hasattr(date_to, "isoformat") else str(date_to),
        }


# Module-level singleton
appointment_service = AppointmentService()
