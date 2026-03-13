"""Appointment API routes — AP-01 through AP-11.

Endpoint map:
  POST /appointments                              — AP-01: Create appointment
  GET  /appointments                              — AP-02: List appointments (cursor)
  GET  /appointments/calendar                     — AP-03: Calendar view (date-keyed)
  GET  /appointments/{appointment_id}             — AP-04: Get appointment detail
  PUT  /appointments/{appointment_id}             — AP-05: Update appointment
  POST /appointments/{appointment_id}/confirm     — AP-06: Confirm
  POST /appointments/{appointment_id}/cancel      — AP-07: Cancel
  POST /appointments/{appointment_id}/complete    — AP-08: Complete
  POST /appointments/{appointment_id}/no-show     — AP-09: No-show
  POST /appointments/{appointment_id}/reschedule  — AP-10: Reschedule (drag-drop)
  GET  /appointments/{appointment_id}/hmac-token  — AP-11: Generate HMAC token
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
    CalendarResponse,
    CancelRequest,
    CompleteRequest,
    ConfirmRequest,
    NoShowRequest,
    RescheduleRequest,
)
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


# ─── AP-01: Create appointment ────────────────────────────────────────────────


@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    body: AppointmentCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Create a new appointment (AP-01).

    Validates that the doctor and patient exist and are active, that the
    start time is in the future, and that no overlapping appointment exists
    for the same doctor slot (emergency appointments skip the overlap check).
    """
    result = await appointment_service.create_appointment(
        db=db,
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        start_time=body.start_time,
        type=body.type,
        created_by=current_user.user_id,
        duration_minutes=body.duration_minutes,
        treatment_plan_item_id=body.treatment_plan_item_id,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="appointment",
        resource_id=result["id"],
    )

    return AppointmentResponse(**result)


# ─── AP-03: Calendar view — MUST be registered before /{appointment_id} ──────


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar_view(
    date_from: str = Query(..., description="Start date in ISO format (YYYY-MM-DD or datetime)"),
    date_to: str = Query(..., description="End date in ISO format (YYYY-MM-DD or datetime)"),
    doctor_id: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> CalendarResponse:
    """Return appointments grouped by date for a calendar view (AP-03).

    Maximum range is 90 days. Every date in the range is included as a key
    even if it has no appointments (empty list). Ordered by start_time within
    each date bucket.
    """
    parsed_from = datetime.fromisoformat(date_from)
    parsed_to = datetime.fromisoformat(date_to)

    # Fix timezone: interpret naive datetimes as tenant local time (COT)
    # and convert to UTC for DB comparison. The tenant timezone is available
    # on the auth context but defaults to America/Bogota for Colombia.
    tenant_tz = ZoneInfo(getattr(current_user.tenant, "timezone", "America/Bogota") or "America/Bogota")
    if parsed_from.tzinfo is None:
        parsed_from = parsed_from.replace(tzinfo=tenant_tz).astimezone(timezone.utc)
    if parsed_to.tzinfo is None:
        parsed_to = parsed_to.replace(tzinfo=tenant_tz).astimezone(timezone.utc)

    result = await appointment_service.list_appointments(
        db=db,
        mode="calendar",
        doctor_id=doctor_id,
        patient_id=patient_id,
        date_from=parsed_from,
        date_to=parsed_to,
        tenant_tz=tenant_tz,
    )

    return CalendarResponse(**result)


# ─── AP-02: List appointments (cursor-based) ──────────────────────────────────


@router.get("", response_model=AppointmentListResponse)
async def list_appointments(
    doctor_id: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentListResponse:
    """Return a cursor-paginated list of appointments (AP-02).

    Ordered by (start_time, id) ascending. Pass the next_cursor from a
    previous response to advance through pages.
    """
    parsed_from: datetime | None = None
    parsed_to: datetime | None = None

    # Interpret naive datetimes as tenant local time (COT) and convert to UTC.
    # Date-only strings (YYYY-MM-DD) get time 00:00 for from and 23:59:59 for to.
    tenant_tz = ZoneInfo(getattr(current_user.tenant, "timezone", "America/Bogota") or "America/Bogota")
    if date_from:
        parsed_from = datetime.fromisoformat(date_from)
        if parsed_from.tzinfo is None:
            parsed_from = parsed_from.replace(tzinfo=tenant_tz).astimezone(timezone.utc)
    if date_to:
        parsed_to = datetime.fromisoformat(date_to)
        if parsed_to.tzinfo is None:
            # If date-only (no time component), set to end of day
            if "T" not in date_to:
                parsed_to = parsed_to.replace(hour=23, minute=59, second=59, tzinfo=tenant_tz).astimezone(timezone.utc)
            else:
                parsed_to = parsed_to.replace(tzinfo=tenant_tz).astimezone(timezone.utc)

    result = await appointment_service.list_appointments(
        db=db,
        mode="list",
        doctor_id=doctor_id,
        patient_id=patient_id,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        cursor=cursor,
        page_size=page_size,
    )

    return AppointmentListResponse(**result)


# ─── AP-04: Get appointment detail ────────────────────────────────────────────


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_detail(
    appointment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Return the full detail of a single appointment (AP-04)."""
    result = await appointment_service.get_appointment(
        db=db,
        appointment_id=appointment_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="APPOINTMENT_not_found",
            resource_name="Appointment",
        )
    return AppointmentResponse(**result)


# ─── AP-05: Update appointment ────────────────────────────────────────────────


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    body: AppointmentUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Update an appointment's schedule or metadata (AP-05).

    Only appointments in 'scheduled' or 'confirmed' status can be updated.
    Changing the time triggers an overlap re-check.
    """
    result = await appointment_service.update_appointment(
        db=db,
        appointment_id=appointment_id,
        start_time=body.start_time,
        duration_minutes=body.duration_minutes,
        type=body.type,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="appointment",
        resource_id=appointment_id,
        changes=body.model_dump(exclude_none=True),
    )

    return AppointmentResponse(**result)


# ─── AP-06: Confirm appointment ───────────────────────────────────────────────


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: str,
    body: ConfirmRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Confirm an appointment (AP-06).

    Supports two confirmation modes:
      - JWT (staff via dashboard): token field is omitted or None.
      - HMAC token (patient self-confirms from reminder email/SMS link).
    """
    result = await appointment_service.confirm_appointment(
        db=db,
        appointment_id=appointment_id,
        hmac_token=body.token,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="confirm",
        resource_type="appointment",
        resource_id=appointment_id,
    )

    return AppointmentResponse(**result)


# ─── AP-07: Cancel appointment ────────────────────────────────────────────────


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: str,
    body: CancelRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Cancel an appointment (AP-07).

    Patient self-cancellations require at least 2 hours of advance notice.
    Appointments in terminal states (completed, no_show) cannot be cancelled.
    """
    result = await appointment_service.cancel_appointment(
        db=db,
        appointment_id=appointment_id,
        reason=body.reason,
        cancelled_by_patient=body.cancelled_by_patient,
        current_user_role=current_user.role,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="cancel",
        resource_type="appointment",
        resource_id=appointment_id,
        changes={"reason": body.reason, "cancelled_by_patient": body.cancelled_by_patient},
    )

    return AppointmentResponse(**result)


# ─── AP-06b: Start appointment (confirmed → in_progress) ─────────────────


@router.post("/{appointment_id}/start", response_model=AppointmentResponse)
async def start_appointment(
    appointment_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Transition a confirmed appointment to in_progress (AP-06b).

    Used when the doctor begins the consultation. Only confirmed
    appointments can be started.
    """
    result = await appointment_service.start_appointment(
        db=db,
        appointment_id=appointment_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="start",
        resource_type="appointment",
        resource_id=appointment_id,
    )

    return AppointmentResponse(**result)


# ─── AP-08: Complete appointment ──────────────────────────────────────────────


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: str,
    body: CompleteRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Mark an appointment as completed (AP-08).

    Only appointments in 'confirmed' or 'in_progress' status can be completed.
    """
    result = await appointment_service.complete_appointment(
        db=db,
        appointment_id=appointment_id,
        completion_notes=body.completion_notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="complete",
        resource_type="appointment",
        resource_id=appointment_id,
    )

    return AppointmentResponse(**result)


# ─── AP-09: No-show ───────────────────────────────────────────────────────────


@router.post("/{appointment_id}/no-show", response_model=AppointmentResponse)
async def mark_no_show(
    appointment_id: str,
    body: NoShowRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:manage")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Mark an appointment as no-show (AP-09).

    Increments the patient's no_show_count counter. Only allowed for
    appointments in 'scheduled' or 'confirmed' status.
    Requires appointments:manage permission.
    """
    result = await appointment_service.no_show(
        db=db,
        appointment_id=appointment_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="no_show",
        resource_type="appointment",
        resource_id=appointment_id,
    )

    return AppointmentResponse(**result)


# ─── AP-10: Reschedule (drag-drop) ────────────────────────────────────────────


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: str,
    body: RescheduleRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    """Reschedule an appointment to a new time slot (AP-10).

    Designed for drag-and-drop in the agenda view. The duration is preserved
    from the original when not explicitly provided. Triggers an overlap check
    at the new time.
    """
    result = await appointment_service.reschedule(
        db=db,
        appointment_id=appointment_id,
        start_time=body.start_time,
        duration_minutes=body.duration_minutes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="reschedule",
        resource_type="appointment",
        resource_id=appointment_id,
        changes={"start_time": body.start_time.isoformat(), "duration_minutes": body.duration_minutes},
    )

    return AppointmentResponse(**result)


# ─── AP-11: Generate HMAC token for reminders ────────────────────────────────


@router.get("/{appointment_id}/hmac-token")
async def get_hmac_token(
    appointment_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("appointments:manage")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Generate an HMAC confirmation token for this appointment (AP-11).

    The token is embedded in reminder emails/SMS so patients can self-confirm
    without a JWT. Tokens carry a 48-hour TTL and are tied to the appointment
    and patient IDs via HMAC-SHA256.

    Requires appointments:manage permission (typically clinic_owner or doctor).
    """
    result = await appointment_service.get_appointment(
        db=db,
        appointment_id=appointment_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="APPOINTMENT_not_found",
            resource_name="Appointment",
        )

    token = appointment_service._generate_hmac_token(
        appointment_id=appointment_id,
        patient_id=result["patient_id"],
    )

    return {"token": token}
