"""Doctor schedule and availability service.

Handles weekly schedule configuration, availability blocks (vacations, etc.),
and the core slot availability algorithm.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - All log identifiers truncated to 8 chars.
"""

import logging
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, set_cached
from app.core.error_codes import ScheduleErrors
from app.core.exceptions import ResourceNotFoundError, ScheduleError
from app.models.tenant.appointment import Appointment
from app.models.tenant.doctor_schedule import AvailabilityBlock, DoctorSchedule

logger = logging.getLogger("dentalos.schedule")

# Default appointment durations in minutes per type
DEFAULT_DURATIONS: dict[str, int] = {
    "consultation": 30,
    "procedure": 60,
    "emergency": 30,
    "follow_up": 20,
}

# Default weekly schedule: Mon-Fri 08:00-18:00, Sat-Sun off
_DEFAULT_SCHEDULE: list[dict[str, Any]] = [
    {"day_of_week": d, "is_working": d <= 4,
     "start_time": "08:00" if d <= 4 else None,
     "end_time": "18:00" if d <= 4 else None,
     "breaks": [{"start": "12:00", "end": "13:00"}] if d <= 4 else []}
    for d in range(7)
]


def _parse_time(time_str: str) -> time:
    """Parse 'HH:MM' string to time object."""
    h, m = time_str.split(":")
    return time(int(h), int(m))


def _schedule_row_to_dict(row: DoctorSchedule) -> dict[str, Any]:
    """Serialize a DoctorSchedule ORM instance to a plain dict."""
    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "day_of_week": row.day_of_week,
        "is_working": row.is_working,
        "start_time": row.start_time.strftime("%H:%M") if row.start_time else None,
        "end_time": row.end_time.strftime("%H:%M") if row.end_time else None,
        "breaks": row.breaks,
        "appointment_duration_defaults": row.appointment_duration_defaults,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _block_to_dict(block: AvailabilityBlock) -> dict[str, Any]:
    """Serialize an AvailabilityBlock ORM instance to a plain dict."""
    return {
        "id": str(block.id),
        "doctor_id": str(block.doctor_id),
        "start_time": block.start_time,
        "end_time": block.end_time,
        "reason": block.reason,
        "description": block.description,
        "is_recurring": block.is_recurring,
        "recurring_until": block.recurring_until,
        "is_active": block.is_active,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }


class ScheduleService:
    """Stateless doctor schedule and availability service."""

    # ─── Weekly schedule management ──────────────────────────────────────

    async def get_schedule(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
    ) -> dict[str, Any]:
        """Fetch the weekly schedule for a doctor.

        If no rows exist returns the default schedule
        (Mon-Fri 08:00-18:00 with lunch break, Sat/Sun off).
        """
        did = uuid.UUID(doctor_id)

        result = await db.execute(
            select(DoctorSchedule)
            .where(DoctorSchedule.user_id == did)
            .order_by(DoctorSchedule.day_of_week)
        )
        rows = result.scalars().all()

        if not rows:
            logger.info(
                "No schedule found for doctor=%s, returning defaults",
                doctor_id[:8],
            )
            return {
                "doctor_id": doctor_id,
                "schedule": _DEFAULT_SCHEDULE,
            }

        return {
            "doctor_id": doctor_id,
            "schedule": [_schedule_row_to_dict(r) for r in rows],
        }

    async def set_schedule(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
        schedule: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Upsert the weekly schedule (7 rows, one per day_of_week 0-6).

        Raises:
            ScheduleError — invalid day, missing working hours, or break
                            outside working hours.
        """
        did = uuid.UUID(doctor_id)

        # Validate all 7 days present
        days_seen: set[int] = set()
        for day_data in schedule:
            dow = day_data.get("day_of_week")
            if dow is None or not (0 <= dow <= 6):
                raise ScheduleError(
                    error=ScheduleErrors.INVALID_DAY,
                    message=f"Dia de la semana invalido: {dow}. Debe ser 0-6.",
                    status_code=422,
                )
            days_seen.add(dow)

        # Validate working-day constraints
        for day_data in schedule:
            is_working = day_data.get("is_working", False)
            if is_working:
                start_str = day_data.get("start_time")
                end_str = day_data.get("end_time")
                if not start_str or not end_str:
                    raise ScheduleError(
                        error=ScheduleErrors.MISSING_WORKING_HOURS,
                        message="Hora de inicio y fin son requeridas para dias laborales.",
                        status_code=422,
                    )
                start = _parse_time(start_str)
                end = _parse_time(end_str)
                if start >= end:
                    raise ScheduleError(
                        error=ScheduleErrors.INVALID_TIME_RANGE,
                        message="La hora de inicio debe ser anterior a la hora de fin.",
                        status_code=422,
                    )
                # Validate breaks are within working hours
                for brk in day_data.get("breaks", []):
                    brk_start = _parse_time(brk["start"])
                    brk_end = _parse_time(brk["end"])
                    if brk_start >= brk_end:
                        raise ScheduleError(
                            error=ScheduleErrors.INVALID_TIME_RANGE,
                            message="La hora de inicio del descanso debe ser anterior a su hora de fin.",
                            status_code=422,
                        )
                    if brk_start < start or brk_end > end:
                        raise ScheduleError(
                            error=ScheduleErrors.BREAK_OUTSIDE_HOURS,
                            message="Los descansos deben estar dentro del horario laboral.",
                            status_code=422,
                        )

        # Load existing rows keyed by day_of_week
        existing_result = await db.execute(
            select(DoctorSchedule).where(DoctorSchedule.user_id == did)
        )
        existing_by_day: dict[int, DoctorSchedule] = {
            r.day_of_week: r for r in existing_result.scalars().all()
        }

        saved_rows: list[DoctorSchedule] = []

        for day_data in schedule:
            dow = day_data["day_of_week"]
            is_working = day_data.get("is_working", False)
            start_t = _parse_time(day_data["start_time"]) if is_working and day_data.get("start_time") else None
            end_t = _parse_time(day_data["end_time"]) if is_working and day_data.get("end_time") else None
            breaks = day_data.get("breaks", [])
            duration_defaults = day_data.get("appointment_duration_defaults", DEFAULT_DURATIONS)

            if dow in existing_by_day:
                row = existing_by_day[dow]
                row.is_working = is_working
                row.start_time = start_t
                row.end_time = end_t
                row.breaks = breaks
                row.appointment_duration_defaults = duration_defaults
            else:
                row = DoctorSchedule(
                    user_id=did,
                    day_of_week=dow,
                    is_working=is_working,
                    start_time=start_t,
                    end_time=end_t,
                    breaks=breaks,
                    appointment_duration_defaults=duration_defaults,
                )
                db.add(row)

            saved_rows.append(row)

        await db.flush()
        for row in saved_rows:
            await db.refresh(row)

        saved_rows.sort(key=lambda r: r.day_of_week)

        logger.info("Schedule updated for doctor=%s (%d days)", doctor_id[:8], len(saved_rows))

        return {
            "doctor_id": doctor_id,
            "schedule": [_schedule_row_to_dict(r) for r in saved_rows],
        }

    # ─── Availability blocks ─────────────────────────────────────────────

    async def create_block(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
        start_time: datetime,
        end_time: datetime,
        reason: str,
        description: str | None = None,
        is_recurring: bool = False,
        recurring_until: date | None = None,
    ) -> dict[str, Any]:
        """Create an availability block (vacation, conference, etc.).

        Raises:
            ScheduleError — end before start or start in the past.
        """
        if start_time >= end_time:
            raise ScheduleError(
                error=ScheduleErrors.INVALID_TIME_RANGE,
                message="La hora de inicio debe ser anterior a la hora de fin del bloqueo.",
                status_code=422,
            )

        now = datetime.now(UTC)
        if start_time < now:
            raise ScheduleError(
                error=ScheduleErrors.BLOCK_IN_PAST,
                message="No se puede crear un bloqueo en el pasado.",
                status_code=422,
            )

        block = AvailabilityBlock(
            doctor_id=uuid.UUID(doctor_id),
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            description=description,
            is_recurring=is_recurring,
            recurring_until=recurring_until,
            is_active=True,
        )
        db.add(block)
        await db.flush()
        await db.refresh(block)

        logger.info(
            "Block created: doctor=%s reason=%s block=%s",
            doctor_id[:8], reason, str(block.id)[:8],
        )

        return _block_to_dict(block)

    async def list_blocks(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """List active availability blocks for a doctor, optionally filtered by date range."""
        did = uuid.UUID(doctor_id)

        stmt = (
            select(AvailabilityBlock)
            .where(
                AvailabilityBlock.doctor_id == did,
                AvailabilityBlock.is_active.is_(True),
            )
            .order_by(AvailabilityBlock.start_time)
        )

        if date_from is not None:
            day_start = datetime.combine(date_from, time.min, tzinfo=UTC)
            stmt = stmt.where(AvailabilityBlock.end_time >= day_start)

        if date_to is not None:
            day_end = datetime.combine(date_to, time.max, tzinfo=UTC)
            stmt = stmt.where(AvailabilityBlock.start_time <= day_end)

        result = await db.execute(stmt)
        blocks = result.scalars().all()

        return [_block_to_dict(b) for b in blocks]

    async def delete_block(
        self,
        *,
        db: AsyncSession,
        block_id: str,
    ) -> dict[str, Any]:
        """Soft-delete an availability block.

        Raises:
            ResourceNotFoundError — block not found or already deleted.
        """
        bid = uuid.UUID(block_id)

        result = await db.execute(
            select(AvailabilityBlock).where(
                AvailabilityBlock.id == bid,
                AvailabilityBlock.is_active.is_(True),
            )
        )
        block = result.scalar_one_or_none()

        if block is None:
            raise ResourceNotFoundError(
                error=ScheduleErrors.NOT_FOUND,
                resource_name="AvailabilityBlock",
            )

        block.is_active = False
        block.deleted_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(block)

        logger.info("Block soft-deleted: block=%s", block_id[:8])

        return _block_to_dict(block)

    # ─── Slot availability algorithm ─────────────────────────────────────

    async def get_available_slots(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
        date_from: date,
        date_to: date,
        slot_duration_minutes: int = 30,
        appointment_type: str | None = None,
    ) -> dict[str, Any]:
        """Compute available appointment slots for a doctor within a date range.

        Algorithm:
        1. Load the weekly schedule (7 rows).
        2. Resolve effective slot duration from appointment_type if provided.
        3. For each date in range:
           a. Determine the schedule for that day_of_week.
           b. Generate candidate slots at the resolved duration granularity.
           c. Remove slots overlapping break periods.
           d. Mark slots overlapping existing appointments as unavailable.
           e. Mark slots overlapping availability blocks as unavailable.
        4. Return the slot map keyed by ISO date string.
        """
        did = uuid.UUID(doctor_id)

        # Cache check — TTL 60s per CLAUDE.md spec (appointment:slots key).
        # appointment_type is included because it can resolve a different effective
        # duration from the doctor's schedule defaults.
        _cache_key = (
            f"dentalos:shared:appointment:slots:{str(doctor_id)[:8]}:"
            f"{date_from}:{date_to}:{slot_duration_minutes}:{appointment_type or 'none'}"
        )
        _cached = await get_cached(_cache_key)
        if _cached is not None:
            return _cached

        # 1. Load weekly schedule
        sched_result = await db.execute(
            select(DoctorSchedule)
            .where(DoctorSchedule.user_id == did)
            .order_by(DoctorSchedule.day_of_week)
        )
        sched_rows = sched_result.scalars().all()

        schedule_by_day: dict[int, DoctorSchedule] = {}
        for row in sched_rows:
            schedule_by_day[row.day_of_week] = row

        # 2. Resolve effective slot duration
        effective_duration = slot_duration_minutes
        if appointment_type and sched_rows:
            # Use the first row's appointment_duration_defaults (same for all days)
            custom_durations = sched_rows[0].appointment_duration_defaults or {}
            if appointment_type in custom_durations:
                effective_duration = custom_durations[appointment_type]

        # 3. Load existing appointments in the date range
        range_start = datetime.combine(date_from, time.min, tzinfo=UTC)
        range_end = datetime.combine(date_to, time.max, tzinfo=UTC)

        appt_result = await db.execute(
            select(Appointment.start_time, Appointment.end_time)
            .where(
                Appointment.doctor_id == did,
                Appointment.start_time <= range_end,
                Appointment.end_time >= range_start,
                Appointment.status.notin_(["cancelled", "no_show"]),
                Appointment.is_active.is_(True),
            )
        )
        appointments = appt_result.all()

        # Load availability blocks in the date range
        block_result = await db.execute(
            select(AvailabilityBlock.start_time, AvailabilityBlock.end_time)
            .where(
                AvailabilityBlock.doctor_id == did,
                AvailabilityBlock.start_time <= range_end,
                AvailabilityBlock.end_time >= range_start,
                AvailabilityBlock.is_active.is_(True),
            )
        )
        blocks = block_result.all()

        # 4. Generate slots day by day
        slots_by_date: dict[str, list[dict[str, Any]]] = {}
        current_date = date_from

        while current_date <= date_to:
            dow = current_date.weekday()  # 0=Monday (ISO, matches our model)
            date_key = current_date.isoformat()

            if dow not in schedule_by_day:
                # No schedule row for this day — use default (working Mon-Fri)
                if dow <= 4:
                    day_slots = self._generate_day_slots(
                        current_date,
                        time(8, 0),
                        time(18, 0),
                        [{"start": "12:00", "end": "13:00"}],
                        effective_duration,
                    )
                else:
                    day_slots = []
            else:
                sched = schedule_by_day[dow]
                if not sched.is_working or sched.start_time is None or sched.end_time is None:
                    slots_by_date[date_key] = []
                    current_date += timedelta(days=1)
                    continue

                day_slots = self._generate_day_slots(
                    current_date,
                    sched.start_time,
                    sched.end_time,
                    sched.breaks or [],
                    effective_duration,
                )

            # Mark unavailable slots based on appointments and blocks
            slot_dicts: list[dict[str, Any]] = []
            for slot_start, slot_end in day_slots:
                available = True

                # Check against existing appointments
                for appt_start, appt_end in appointments:
                    if slot_start < appt_end and slot_end > appt_start:
                        available = False
                        break

                # Check against availability blocks
                if available:
                    for blk_start, blk_end in blocks:
                        if slot_start < blk_end and slot_end > blk_start:
                            available = False
                            break

                slot_dicts.append({
                    "start_time": slot_start,
                    "end_time": slot_end,
                    "available": available,
                })

            slots_by_date[date_key] = slot_dicts
            current_date += timedelta(days=1)

        logger.info(
            "Slots computed: doctor=%s range=%s..%s duration=%dmin",
            doctor_id[:8], date_from.isoformat(), date_to.isoformat(), effective_duration,
        )

        result = {
            "doctor_id": doctor_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "slot_duration_minutes": effective_duration,
            "slots": slots_by_date,
        }
        await set_cached(_cache_key, result, ttl_seconds=60)
        return result

    # ─── Private helpers ─────────────────────────────────────────────────

    def _generate_day_slots(
        self,
        target_date: date,
        work_start: time,
        work_end: time,
        breaks: list[dict],
        slot_minutes: int,
    ) -> list[tuple[datetime, datetime]]:
        """Generate candidate (start, end) tuples for a working day.

        Slots that overlap with a break period are skipped and the cursor
        advances to the end of the break.
        """
        slots: list[tuple[datetime, datetime]] = []
        current = datetime.combine(target_date, work_start, tzinfo=UTC)
        day_end = datetime.combine(target_date, work_end, tzinfo=UTC)

        # Pre-parse break windows for the target date
        parsed_breaks: list[tuple[datetime, datetime]] = []
        for brk in breaks:
            brk_start = datetime.combine(target_date, _parse_time(brk["start"]), tzinfo=UTC)
            brk_end = datetime.combine(target_date, _parse_time(brk["end"]), tzinfo=UTC)
            parsed_breaks.append((brk_start, brk_end))

        while current + timedelta(minutes=slot_minutes) <= day_end:
            slot_end = current + timedelta(minutes=slot_minutes)

            # Check if slot overlaps with any break
            in_break = False
            for brk_start, brk_end in parsed_breaks:
                if current < brk_end and slot_end > brk_start:
                    in_break = True
                    # Skip to end of break
                    current = brk_end
                    break

            if not in_break:
                slots.append((current, slot_end))
                current = slot_end

        return slots


# Module-level singleton
schedule_service = ScheduleService()
