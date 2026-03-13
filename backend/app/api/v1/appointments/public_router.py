"""Public booking API routes — AP-15 and AP-16.

These endpoints require NO authentication. They use a tenant slug from the URL
path to resolve the clinic context. Patient data is never logged.

Endpoint map:
  GET  /public/booking/{slug}  — AP-15: Get booking configuration for a clinic
  POST /public/booking/{slug}  — AP-16: Create a public self-booking
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.core.tenant import validate_schema_name
from app.models.public.tenant import Tenant
from app.schemas.public_booking import (
    BookingConfigResponse,
    PublicBookingRequest,
    PublicBookingResponse,
)

logger = logging.getLogger("dentalos.public_booking")

router = APIRouter(prefix="/public/booking", tags=["public-booking"])


# ─── Tenant resolution helper ─────────────────────────────────────────────────


async def resolve_tenant_by_slug(slug: str, db: AsyncSession) -> Tenant:
    """Resolve an active tenant from a URL slug.

    Queries public.tenants and returns the Tenant ORM object.

    Raises:
        HTTPException (404) — slug does not exist or tenant is not active.
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == slug,
            Tenant.status == "active",
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TENANT_not_found",
                "message": "No se encontro una clinica activa con ese enlace.",
                "details": {},
            },
        )
    return tenant


# ─── AP-15: Get booking configuration ────────────────────────────────────────


@router.get("/{slug}", response_model=BookingConfigResponse)
async def get_booking_config(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BookingConfigResponse:
    """Return the public booking configuration for a clinic (AP-15).

    No authentication required. Returns clinic name, available doctors,
    supported appointment types, and the next 30 days with open slots.

    For MVP: available_dates returns the next 30 calendar days. A future
    iteration will filter by actual schedule availability.
    """
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(f"rl:public_config:{ip}", limit=30, window_seconds=60)

    tenant = await resolve_tenant_by_slug(slug, db)

    # Build the next 30 calendar days starting from tomorrow
    today = datetime.now(UTC).date()
    available_dates = [
        (today + timedelta(days=i)).isoformat()
        for i in range(1, 31)
    ]

    # G5: Query tenant schema for active doctors
    schema = tenant.schema_name
    if validate_schema_name(schema):
        await db.execute(text(f"SET search_path TO {schema}, public"))

        from app.models.tenant.user import User

        doctors_result = await db.execute(
            select(User.id, User.name).where(
                User.role == "doctor",
                User.is_active.is_(True),
            )
        )
        doctors = [
            {"id": str(row.id), "name": row.name}
            for row in doctors_result.all()
        ]

        # Reset search_path
        await db.execute(text("SET search_path TO public"))
    else:
        doctors = []

    return BookingConfigResponse(
        clinic_name=tenant.name,
        clinic_slug=tenant.slug,
        doctors=doctors,
        appointment_types=["consultation", "procedure", "emergency", "follow_up"],
        available_dates=available_dates,
    )


# ─── AP-16: Create public booking ─────────────────────────────────────────────


@router.post("/{slug}", response_model=PublicBookingResponse, status_code=201)
async def create_public_booking(
    slug: str,
    body: PublicBookingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PublicBookingResponse:
    """Create a self-booking for a patient (AP-16).

    No authentication required. Flow:
      1. Apply rate limit (5 per hour per IP).
      2. Resolve tenant by slug.
      3. Log a warning if captcha_token is absent (CAPTCHA stub for MVP).
      4. Validate schema name before using it in SET search_path.
      5. Switch to tenant schema.
      6. Find or create the patient by document_number.
      7. Create the appointment.
      8. Return booking confirmation.

    PHI is never logged (patient names, document numbers, phone, email).
    """
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(f"rl:public_booking:{ip}", limit=5, window_seconds=3600)

    tenant = await resolve_tenant_by_slug(slug, db)

    # CAPTCHA stub: log a warning if no token is present (MVP)
    if body.captcha_token is None:
        logger.warning(
            "Public booking submitted without captcha token for tenant=%s",
            tenant.slug,
        )

    # Validate schema name before interpolating into SQL
    schema = tenant.schema_name
    if not validate_schema_name(schema):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TENANT_invalid_schema",
                "message": "Internal configuration error.",
                "details": {},
            },
        )

    # Set the tenant search_path for the remainder of this operation
    await db.execute(text(f"SET search_path TO {schema}, public"))

    # Resolve or create patient
    from app.models.tenant.patient import Patient

    patient_result = await db.execute(
        select(Patient).where(
            Patient.document_number == body.patient_document_number,
            Patient.is_active.is_(True),
        )
    )
    patient = patient_result.scalar_one_or_none()

    if patient is None:
        # Auto-create a minimal patient record
        patient = Patient(
            first_name=body.patient_first_name.strip(),
            last_name=body.patient_last_name.strip(),
            document_type=body.patient_document_type,
            document_number=body.patient_document_number,
            phone=body.patient_phone,
            email=body.patient_email,
            is_active=True,
        )
        db.add(patient)
        await db.flush()
        await db.refresh(patient)
        logger.info("Public booking: auto-created patient record")

    # Resolve doctor name (best-effort, non-blocking)
    from app.models.tenant.user import User

    doctor_result = await db.execute(
        select(User.name).where(User.id == uuid.UUID(body.doctor_id))
    )
    doctor_name = doctor_result.scalar_one_or_none() or "Doctor"

    # Create appointment
    from datetime import timedelta as _td

    duration_defaults = {"consultation": 30, "procedure": 60, "follow_up": 20}
    duration = duration_defaults.get(body.type, 30)
    end_time = body.start_time + _td(minutes=duration)

    from app.models.tenant.appointment import Appointment

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=uuid.UUID(body.doctor_id),
        start_time=body.start_time,
        end_time=end_time,
        duration_minutes=duration,
        type=body.type,
        status="scheduled",
        completion_notes=body.notes,
        # Public bookings are not linked to a staff creator
        created_by=patient.id,
        is_active=True,
    )
    db.add(appointment)
    await db.flush()
    await db.refresh(appointment)

    logger.info(
        "Public booking created: appointment=%s tenant=%s",
        str(appointment.id)[:8],
        tenant.slug,
    )

    return PublicBookingResponse(
        appointment_id=str(appointment.id),
        patient_id=str(patient.id),
        doctor_name=doctor_name,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        type=appointment.type,
        status=appointment.status,
        confirmation_message=(
            f"Su cita ha sido agendada exitosamente en {tenant.name}. "
            "Le enviaremos un recordatorio antes de su cita."
        ),
    )
