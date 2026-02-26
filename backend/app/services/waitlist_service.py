"""Waitlist service -- manage appointment waitlist entries.

Patients on the waitlist are notified when a matching slot becomes available
(e.g. after a cancellation or no-show). The notification service scans
waiting entries and bumps notification_count on each contact attempt.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - All log identifiers truncated to 8 chars.
"""

import logging
import uuid
from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import WaitlistErrors
from app.core.exceptions import DentalOSError, ResourceConflictError, ResourceNotFoundError
from app.models.tenant.patient import Patient
from app.models.tenant.waitlist_entry import WaitlistEntry

logger = logging.getLogger("dentalos.waitlist")


def _parse_time(time_str: str) -> time:
    """Parse 'HH:MM' string to time object."""
    h, m = time_str.split(":")
    return time(int(h), int(m))


def _entry_to_dict(entry: WaitlistEntry, patient_name: str | None = None) -> dict[str, Any]:
    """Serialize a WaitlistEntry ORM instance to a plain dict."""
    return {
        "id": str(entry.id),
        "patient_id": str(entry.patient_id),
        "patient_name": patient_name,
        "preferred_doctor_id": str(entry.preferred_doctor_id) if entry.preferred_doctor_id else None,
        "procedure_type": entry.procedure_type,
        "preferred_days": entry.preferred_days,
        "preferred_time_from": entry.preferred_time_from.strftime("%H:%M") if entry.preferred_time_from else None,
        "preferred_time_to": entry.preferred_time_to.strftime("%H:%M") if entry.preferred_time_to else None,
        "valid_until": entry.valid_until.isoformat() if entry.valid_until else None,
        "status": entry.status,
        "notification_count": entry.notification_count,
        "last_notified_at": entry.last_notified_at,
        "is_active": entry.is_active,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


class WaitlistService:
    """Stateless waitlist service."""

    async def add_to_waitlist(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        preferred_doctor_id: str | None = None,
        procedure_type: str | None = None,
        preferred_days: list[int] | None = None,
        preferred_time_from: str | None = None,
        preferred_time_to: str | None = None,
        valid_until: str | None = None,
    ) -> dict[str, Any]:
        """Add a patient to the appointment waitlist.

        Raises:
            DentalOSError (404) -- patient not found or inactive.
            ResourceConflictError (409) -- duplicate active entry for same
                patient + doctor combination.
        """
        pid = uuid.UUID(patient_id)

        # Validate patient exists and is active
        patient_result = await db.execute(
            select(Patient.id, Patient.first_name, Patient.last_name).where(
                Patient.id == pid,
                Patient.is_active.is_(True),
            )
        )
        patient_row = patient_result.one_or_none()
        if patient_row is None:
            raise DentalOSError(
                error=WaitlistErrors.PATIENT_NOT_FOUND,
                message="El paciente no existe o esta inactivo.",
                status_code=404,
            )
        patient_name = f"{patient_row.first_name} {patient_row.last_name}"

        # Check for existing active waitlist entry for same patient + doctor
        dup_stmt = select(WaitlistEntry.id).where(
            WaitlistEntry.patient_id == pid,
            WaitlistEntry.status.in_(["waiting", "notified"]),
            WaitlistEntry.is_active.is_(True),
        )
        if preferred_doctor_id:
            dup_stmt = dup_stmt.where(
                WaitlistEntry.preferred_doctor_id == uuid.UUID(preferred_doctor_id)
            )
        else:
            dup_stmt = dup_stmt.where(WaitlistEntry.preferred_doctor_id.is_(None))

        dup_result = await db.execute(dup_stmt)
        if dup_result.scalar_one_or_none() is not None:
            raise ResourceConflictError(
                error=WaitlistErrors.ALREADY_EXISTS,
                message="Ya existe una entrada activa en lista de espera para este paciente y doctor.",
            )

        # Parse optional time/date strings
        time_from = _parse_time(preferred_time_from) if preferred_time_from else None
        time_to = _parse_time(preferred_time_to) if preferred_time_to else None
        valid_date = datetime.fromisoformat(valid_until).date() if valid_until else None

        entry = WaitlistEntry(
            patient_id=pid,
            preferred_doctor_id=uuid.UUID(preferred_doctor_id) if preferred_doctor_id else None,
            procedure_type=procedure_type,
            preferred_days=preferred_days or [],
            preferred_time_from=time_from,
            preferred_time_to=time_to,
            valid_until=valid_date,
            status="waiting",
            notification_count=0,
            is_active=True,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)

        logger.info(
            "Waitlist entry created: entry=%s patient=%s",
            str(entry.id)[:8], patient_id[:8],
        )

        return _entry_to_dict(entry, patient_name=patient_name)

    async def list_waitlist(
        self,
        *,
        db: AsyncSession,
        status: str | None = None,
        doctor_id: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List waitlist entries with cursor-based pagination.

        Cursor format: 'created_at|id' (ISO datetime pipe UUID).
        """
        base_where = [WaitlistEntry.is_active.is_(True)]

        if status:
            base_where.append(WaitlistEntry.status == status)
        if doctor_id:
            base_where.append(
                WaitlistEntry.preferred_doctor_id == uuid.UUID(doctor_id)
            )

        # Total count
        count_stmt = select(func.count(WaitlistEntry.id)).where(*base_where)
        total = (await db.execute(count_stmt)).scalar_one()

        # Items query with cursor
        items_stmt = (
            select(WaitlistEntry, Patient.first_name, Patient.last_name)
            .join(Patient, Patient.id == WaitlistEntry.patient_id)
            .where(*base_where)
            .order_by(WaitlistEntry.created_at.desc(), WaitlistEntry.id.desc())
            .limit(page_size + 1)  # fetch one extra to determine next_cursor
        )

        if cursor:
            cursor_parts = cursor.split("|")
            cursor_ts = datetime.fromisoformat(cursor_parts[0])
            cursor_id = uuid.UUID(cursor_parts[1])
            # Rows strictly before the cursor position (descending order)
            items_stmt = items_stmt.where(
                (WaitlistEntry.created_at < cursor_ts)
                | (
                    (WaitlistEntry.created_at == cursor_ts)
                    & (WaitlistEntry.id < cursor_id)
                )
            )

        result = await db.execute(items_stmt)
        rows = result.all()

        # Determine next_cursor
        has_more = len(rows) > page_size
        if has_more:
            rows = rows[:page_size]

        items: list[dict[str, Any]] = []
        for entry, first_name, last_name in rows:
            patient_name = f"{first_name} {last_name}"
            items.append(_entry_to_dict(entry, patient_name=patient_name))

        next_cursor: str | None = None
        if has_more and rows:
            last_entry = rows[-1][0]
            next_cursor = f"{last_entry.created_at.isoformat()}|{last_entry.id}"

        return {
            "items": items,
            "total": total,
            "next_cursor": next_cursor,
        }

    async def notify_entry(
        self,
        *,
        db: AsyncSession,
        entry_id: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Mark a waitlist entry as notified and increment contact counter.

        Raises:
            ResourceNotFoundError (404) -- entry not found.
        """
        eid = uuid.UUID(entry_id)

        result = await db.execute(
            select(WaitlistEntry).where(
                WaitlistEntry.id == eid,
                WaitlistEntry.is_active.is_(True),
            )
        )
        entry = result.scalar_one_or_none()

        if entry is None:
            raise ResourceNotFoundError(
                error=WaitlistErrors.NOT_FOUND,
                resource_name="WaitlistEntry",
            )

        entry.status = "notified"
        entry.notification_count += 1
        entry.last_notified_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(entry)

        logger.info(
            "Waitlist entry notified: entry=%s count=%d",
            entry_id[:8], entry.notification_count,
        )

        return _entry_to_dict(entry)

    async def check_and_notify(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
        freed_time: datetime,
    ) -> list[dict[str, Any]]:
        """Find waitlist entries matching a freed slot.

        Called internally when an appointment is cancelled or marked as no-show.
        Returns matching entries so the caller can decide how to notify them
        (e.g. via the notification queue).

        Matching criteria:
        - preferred_doctor_id matches OR is null (any doctor).
        - status is 'waiting'.
        - valid_until is null or >= the freed date.
        - preferred_days includes the day-of-week of freed_time (or empty = any day).
        - preferred_time_from/to overlap with the freed time (or null = any time).
        """
        did = uuid.UUID(doctor_id)
        freed_date = freed_time.date()
        freed_dow = freed_time.weekday()  # 0=Monday (ISO)

        # Base query: waiting entries that match doctor preference
        stmt = (
            select(WaitlistEntry, Patient.first_name, Patient.last_name)
            .join(Patient, Patient.id == WaitlistEntry.patient_id)
            .where(
                WaitlistEntry.status == "waiting",
                WaitlistEntry.is_active.is_(True),
                (
                    (WaitlistEntry.preferred_doctor_id == did)
                    | (WaitlistEntry.preferred_doctor_id.is_(None))
                ),
            )
            .order_by(WaitlistEntry.created_at.asc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        matches: list[dict[str, Any]] = []
        freed_time_only = freed_time.timetz()

        for entry, first_name, last_name in rows:
            # Filter: valid_until
            if entry.valid_until is not None and entry.valid_until < freed_date:
                continue

            # Filter: preferred_days (empty list = any day)
            if entry.preferred_days and freed_dow not in entry.preferred_days:
                continue

            # Filter: preferred time window
            if entry.preferred_time_from is not None and freed_time_only < entry.preferred_time_from:
                continue
            if entry.preferred_time_to is not None and freed_time_only > entry.preferred_time_to:
                continue

            patient_name = f"{first_name} {last_name}"
            matches.append(_entry_to_dict(entry, patient_name=patient_name))

        logger.info(
            "Waitlist check: doctor=%s freed=%s matches=%d",
            doctor_id[:8], freed_time.isoformat()[:16], len(matches),
        )

        return matches


# Module-level singleton
waitlist_service = WaitlistService()
