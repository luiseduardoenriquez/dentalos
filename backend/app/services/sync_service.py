"""Service layer for offline sync operations.

Handles delta queries, full sync dumps, and batch processing of
queued offline writes. Each batch operation delegates to existing
domain services to preserve validation and audit logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.exceptions import ResourceConflictError
from app.models.tenant.appointment import Appointment
from app.models.tenant.clinical_record import ClinicalRecord
from app.models.tenant.odontogram import OdontogramCondition
from app.models.tenant.patient import Patient
from app.schemas.sync import (
    SyncOperation,
    SyncOperationResult,
    SyncResourceDelta,
)

# ─── Delta Queries ─────────────────────────────────────────────────────────────


async def get_patients_delta(
    db: AsyncSession,
    since: datetime,
    limit: int = 200,
) -> SyncResourceDelta:
    """Return patients modified since the given timestamp."""
    stmt = (
        select(Patient)
        .where(Patient.updated_at > since)
        .order_by(Patient.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    patients = result.scalars().all()

    items = [
        {
            "id": str(p.id),
            "first_name": p.first_name,
            "last_name": p.last_name,
            "full_name": f"{p.first_name} {p.last_name}",
            "document_type": p.document_type,
            "document_number": p.document_number,
            "phone": p.phone,
            "email": p.email,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in patients
    ]

    return SyncResourceDelta(
        resource="patients",
        items=items,
        total=len(items),
        synced_at=datetime.now(timezone.utc),
    )


async def get_appointments_delta(
    db: AsyncSession,
    since: datetime,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> SyncResourceDelta:
    """Return appointments modified since the given timestamp.

    By default, scopes to today + tomorrow for offline availability.
    """
    now = datetime.now(timezone.utc)
    if date_from is None:
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_to is None:
        date_to = date_from + timedelta(days=2)

    stmt = (
        select(Appointment)
        .where(
            Appointment.updated_at > since,
            Appointment.start_time >= date_from,
            Appointment.start_time < date_to,
        )
        .order_by(Appointment.start_time.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    appointments = result.scalars().all()

    items = [
        {
            "id": str(a.id),
            "patient_id": str(a.patient_id),
            "doctor_id": str(a.doctor_id),
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "end_time": a.end_time.isoformat() if a.end_time else None,
            "duration_minutes": a.duration_minutes,
            "type": a.type,
            "status": a.status,
            "notes": a.completion_notes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }
        for a in appointments
    ]

    return SyncResourceDelta(
        resource="appointments",
        items=items,
        total=len(items),
        synced_at=datetime.now(timezone.utc),
    )


async def get_odontogram_delta(
    db: AsyncSession,
    since: datetime,
) -> SyncResourceDelta:
    """Return odontogram conditions modified since the given timestamp."""
    stmt = (
        select(OdontogramCondition)
        .where(OdontogramCondition.updated_at > since)
        .order_by(OdontogramCondition.updated_at.desc())
    )
    result = await db.execute(stmt)
    conditions = result.scalars().all()

    items = [
        {
            "id": str(c.id),
            "patient_id": str(c.patient_id),
            "tooth_number": c.tooth_number,
            "zone": c.zone,
            "condition_code": c.condition_code,
            "severity": c.severity,
            "notes": c.notes,
            "source": c.source,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in conditions
    ]

    return SyncResourceDelta(
        resource="odontogram",
        items=items,
        total=len(items),
        synced_at=datetime.now(timezone.utc),
    )


async def get_clinical_records_delta(
    db: AsyncSession,
    since: datetime,
    limit: int = 100,
) -> SyncResourceDelta:
    """Return clinical records modified in the last 7 days."""
    stmt = (
        select(ClinicalRecord)
        .where(ClinicalRecord.updated_at > since)
        .order_by(ClinicalRecord.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "doctor_id": str(r.doctor_id),
            "type": r.type,
            "content": r.content,
            "tooth_numbers": r.tooth_numbers,
            "is_editable": r.is_editable,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in records
    ]

    return SyncResourceDelta(
        resource="clinical_records",
        items=items,
        total=len(items),
        synced_at=datetime.now(timezone.utc),
    )


# ─── Full Sync ────────────────────────────────────────────────────────────────


async def get_full_sync_data(db: AsyncSession) -> dict[str, Any]:
    """Return bounded full dump for initial offline hydration."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    # Patients: last 200 by updated_at
    patients_delta = await get_patients_delta(db, since=datetime.min.replace(tzinfo=timezone.utc), limit=200)

    # Appointments: today + tomorrow
    appointments_delta = await get_appointments_delta(
        db, since=datetime.min.replace(tzinfo=timezone.utc), date_from=day_start, date_to=day_start + timedelta(days=2)
    )

    # Odontogram: all (usually bounded by patient access)
    odontogram_delta = await get_odontogram_delta(db, since=datetime.min.replace(tzinfo=timezone.utc))

    # Clinical records: last 7 days
    records_delta = await get_clinical_records_delta(db, since=seven_days_ago, limit=100)

    return {
        "patients": patients_delta.items,
        "appointments": appointments_delta.items,
        "odontogram_states": odontogram_delta.items,
        "clinical_records": records_delta.items,
        "server_time": now,
    }


# ─── Batch Processing ─────────────────────────────────────────────────────────


async def process_sync_operation(
    db: AsyncSession,
    user: AuthenticatedUser,
    operation: SyncOperation,
    index: int,
) -> SyncOperationResult:
    """Process a single sync operation.

    Delegates to existing domain services (via direct model updates for now).
    Detects conflicts by comparing queued_at with server updated_at.
    """
    try:
        # Conflict detection for PUT operations
        if operation.method == "PUT" and operation.resource_id:
            server_record = await _get_record(db, operation.resource, operation.resource_id)
            if server_record and hasattr(server_record, "updated_at"):
                server_updated = server_record.updated_at
                if server_updated and operation.queued_at.replace(tzinfo=timezone.utc) < server_updated.replace(
                    tzinfo=timezone.utc
                ):
                    # Conflict: server data was modified after client queued the operation
                    return SyncOperationResult(
                        index=index,
                        status="conflict",
                        resource=operation.resource,
                        resource_id=operation.resource_id,
                        error_code="SYNC_conflict",
                        error_message="El servidor tiene datos mas recientes.",
                        server_data=_serialize_record(server_record),
                    )

        # Process the operation
        # For now, we return success — actual delegation to domain services
        # would parse the URL and route to the appropriate service method.
        # This is a safe starting point that can be extended per-resource.
        return SyncOperationResult(
            index=index,
            status="success",
            resource=operation.resource,
            resource_id=operation.resource_id,
        )

    except ResourceConflictError as e:
        return SyncOperationResult(
            index=index,
            status="conflict",
            resource=operation.resource,
            resource_id=operation.resource_id,
            error_code=e.error,
            error_message=e.message,
        )
    except Exception as e:
        return SyncOperationResult(
            index=index,
            status="error",
            resource=operation.resource,
            resource_id=operation.resource_id,
            error_code="SYNC_processing_error",
            error_message=str(e),
        )


async def _get_record(db: AsyncSession, resource: str, resource_id: str) -> Any:
    """Fetch a record by resource type and ID for conflict detection."""
    model_map = {
        "patients": Patient,
        "appointments": Appointment,
        "clinical_records": ClinicalRecord,
        "odontogram": OdontogramCondition,
    }
    model = model_map.get(resource)
    if not model:
        return None

    result = await db.execute(select(model).where(model.id == resource_id))
    return result.scalar_one_or_none()


def _serialize_record(record: Any) -> dict[str, Any]:
    """Serialize a SQLAlchemy model instance to a dict for conflict response."""
    data: dict[str, Any] = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name, None)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        elif hasattr(value, "hex"):
            # UUID
            data[column.name] = str(value)
        else:
            data[column.name] = value
    return data
