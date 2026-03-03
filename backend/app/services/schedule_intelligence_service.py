"""Schedule Intelligence service — VP-10.

Provides no-show risk prediction, gap analysis, utilization metrics,
and fill suggestions using pure SQL aggregations (no ML dependencies).

Security invariants:
  - PHI (patient names, phones) is included in responses but NEVER logged.
  - All log entries use truncated UUIDs (8 chars max).
  - Read-only aggregation -- no writes to any table.
"""

import asyncio
import logging
import math
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant.appointment import Appointment
from app.models.tenant.doctor_schedule import DoctorSchedule
from app.models.tenant.patient import Patient
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.models.tenant.user import User
from app.models.tenant.waitlist_entry import WaitlistEntry

logger = logging.getLogger("dentalos.schedule_intelligence")

# ── Weight constants for no-show scoring ─────────────────────────────────────

_W_PATIENT_HISTORY = 0.40
_W_DAY_OF_WEEK = 0.20
_W_TIME_OF_DAY = 0.15
_W_PROCEDURE_TYPE = 0.15
_W_RECENCY = 0.10

# Exponential decay half-life (days) for recent no-show weighting.
_RECENCY_HALF_LIFE_DAYS = 90

# How many months of appointment history to consider for scoring.
_HISTORY_MONTHS = 12

# Risk level thresholds.
_RISK_LOW_MAX = 30
_RISK_MEDIUM_MAX = 60


def _risk_level(score: int) -> str:
    """Map a 0-100 score to a risk label."""
    if score <= _RISK_LOW_MAX:
        return "low"
    if score <= _RISK_MEDIUM_MAX:
        return "medium"
    return "high"


def _time_bucket(t: time) -> str:
    """Bucket a time into a 2-hour window label for aggregation."""
    hour = t.hour
    if hour < 8:
        return "early"
    if hour < 10:
        return "08-10"
    if hour < 12:
        return "10-12"
    if hour < 14:
        return "12-14"
    if hour < 16:
        return "14-16"
    if hour < 18:
        return "16-18"
    return "late"


class ScheduleIntelligenceService:
    """Stateless service computing schedule intelligence metrics.

    All public methods accept a tenant-scoped AsyncSession that already has
    the correct search_path set.
    """

    # ── Main entry point ─────────────────────────────────────────────────

    async def get_intelligence(
        self,
        db: AsyncSession,
        target_date: date,
        doctor_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Run all intelligence queries in parallel and return a combined dict."""
        no_show_risks, gaps, utilization = await asyncio.gather(
            self.predict_no_shows(db, target_date, doctor_id),
            self.find_gaps(db, target_date, doctor_id),
            self.get_utilization(db, target_date, doctor_id),
        )

        logger.info(
            "schedule_intelligence computed: date=%s risks=%d gaps=%d doctors=%d",
            target_date.isoformat(),
            len(no_show_risks),
            len(gaps),
            len(utilization),
        )

        return {
            "date": target_date,
            "no_show_risks": no_show_risks,
            "gaps": gaps,
            "utilization": utilization,
            "overbooking_suggestions": [],  # Future: derive from high-risk slots
        }

    # ── No-show risk prediction ──────────────────────────────────────────

    async def predict_no_shows(
        self,
        db: AsyncSession,
        target_date: date,
        doctor_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Score each confirmed/scheduled appointment for no-show risk.

        Returns a list of dicts matching the NoShowRisk schema.
        """
        day_start = datetime.combine(target_date, time.min, tzinfo=UTC)
        day_end = datetime.combine(target_date, time.max, tzinfo=UTC)
        history_cutoff = datetime.now(UTC) - timedelta(days=_HISTORY_MONTHS * 30)

        # 1. Fetch today's appointments (confirmed or scheduled)
        appt_filters = [
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end,
            Appointment.status.in_(["confirmed", "scheduled"]),
            Appointment.is_active.is_(True),
        ]
        if doctor_id:
            appt_filters.append(Appointment.doctor_id == doctor_id)

        stmt = (
            select(
                Appointment.id.label("appointment_id"),
                Appointment.patient_id,
                Appointment.start_time,
                Appointment.type.label("appt_type"),
                Appointment.doctor_id,
                Patient.first_name,
                Patient.last_name,
            )
            .join(Patient, Patient.id == Appointment.patient_id)
            .where(and_(*appt_filters))
            .order_by(Appointment.start_time)
        )
        result = await db.execute(stmt)
        appointments = result.all()

        if not appointments:
            return []

        # 2. Pre-compute clinic-wide rates for the target day-of-week and time buckets
        target_dow = target_date.weekday()  # 0=Monday
        dow_rate = await self._clinic_dow_no_show_rate(db, target_dow, history_cutoff)
        time_rates = await self._clinic_time_no_show_rates(db, history_cutoff)
        type_rates = await self._clinic_type_no_show_rates(db, history_cutoff)

        # 3. Score each appointment individually
        results: list[dict[str, Any]] = []
        for row in appointments:
            patient_rate = await self._patient_no_show_rate(
                db, row.patient_id, history_cutoff
            )
            recency_score = await self._patient_recency_score(
                db, row.patient_id, history_cutoff
            )

            appt_time = row.start_time.time() if row.start_time else time(9, 0)
            bucket = _time_bucket(appt_time)
            time_rate = time_rates.get(bucket, 0.0)
            procedure_rate = type_rates.get(row.appt_type, 0.0)

            raw_score = (
                patient_rate * _W_PATIENT_HISTORY
                + dow_rate * _W_DAY_OF_WEEK
                + time_rate * _W_TIME_OF_DAY
                + procedure_rate * _W_PROCEDURE_TYPE
                + recency_score * _W_RECENCY
            )
            score = max(0, min(100, round(raw_score)))
            level = _risk_level(score)

            results.append(
                {
                    "patient_id": row.patient_id,
                    "patient_name": f"{row.first_name} {row.last_name}",
                    "appointment_id": row.appointment_id,
                    "risk_score": score,
                    "risk_level": level,
                    "factors": {
                        "patient_history": round(patient_rate * _W_PATIENT_HISTORY, 1),
                        "day_of_week": round(dow_rate * _W_DAY_OF_WEEK, 1),
                        "time_of_day": round(time_rate * _W_TIME_OF_DAY, 1),
                        "procedure_type": round(procedure_rate * _W_PROCEDURE_TYPE, 1),
                        "recency": round(recency_score * _W_RECENCY, 1),
                    },
                }
            )

        # Sort descending by risk_score so the UI shows highest risk first
        results.sort(key=lambda r: r["risk_score"], reverse=True)
        return results

    # ── Internal: patient-level no-show rate ─────────────────────────────

    async def _patient_no_show_rate(
        self, db: AsyncSession, patient_id: UUID, cutoff: datetime
    ) -> float:
        """Historical no-show rate for a single patient (0-100 scale)."""
        stmt = select(
            func.count().label("total"),
            func.count()
            .filter(Appointment.status == "no_show")
            .label("no_shows"),
        ).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.start_time >= cutoff,
                Appointment.is_active.is_(True),
                Appointment.status.in_(
                    ["completed", "no_show", "cancelled"]
                ),
            )
        )
        result = await db.execute(stmt)
        row = result.one()
        if row.total == 0:
            return 0.0
        return (row.no_shows / row.total) * 100

    # ── Internal: recency-weighted no-show score ─────────────────────────

    async def _patient_recency_score(
        self, db: AsyncSession, patient_id: UUID, cutoff: datetime
    ) -> float:
        """Recency-weighted score: recent no-shows count more via exponential decay.

        Returns 0-100 scale. A no-show yesterday scores ~100, one 90 days ago ~50.
        """
        stmt = select(Appointment.no_show_at).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status == "no_show",
                Appointment.no_show_at.is_not(None),
                Appointment.no_show_at >= cutoff,
                Appointment.is_active.is_(True),
            )
        )
        result = await db.execute(stmt)
        no_show_dates = [r[0] for r in result.all()]

        if not no_show_dates:
            return 0.0

        now = datetime.now(UTC)
        max_weight = 0.0
        for ns_dt in no_show_dates:
            days_ago = max((now - ns_dt).days, 0)
            weight = math.exp(-0.693 * days_ago / _RECENCY_HALF_LIFE_DAYS)
            max_weight = max(max_weight, weight)

        return max_weight * 100

    # ── Internal: clinic-wide day-of-week no-show rate ───────────────────

    async def _clinic_dow_no_show_rate(
        self, db: AsyncSession, dow: int, cutoff: datetime
    ) -> float:
        """Clinic-wide no-show rate for a given day-of-week (0-100 scale)."""
        stmt = select(
            func.count().label("total"),
            func.count()
            .filter(Appointment.status == "no_show")
            .label("no_shows"),
        ).where(
            and_(
                func.extract("dow", Appointment.start_time) == ((dow + 1) % 7),
                Appointment.start_time >= cutoff,
                Appointment.is_active.is_(True),
                Appointment.status.in_(
                    ["completed", "no_show", "cancelled"]
                ),
            )
        )
        result = await db.execute(stmt)
        row = result.one()
        if row.total == 0:
            return 0.0
        return (row.no_shows / row.total) * 100

    # ── Internal: clinic-wide time-of-day no-show rates ──────────────────

    async def _clinic_time_no_show_rates(
        self, db: AsyncSession, cutoff: datetime
    ) -> dict[str, float]:
        """No-show rate per 2-hour time bucket across the entire clinic.

        Returns a dict of bucket_label -> rate (0-100).
        """
        hour_expr = func.extract("hour", Appointment.start_time)
        bucket_expr = case(
            (hour_expr < 8, "early"),
            (and_(hour_expr >= 8, hour_expr < 10), "08-10"),
            (and_(hour_expr >= 10, hour_expr < 12), "10-12"),
            (and_(hour_expr >= 12, hour_expr < 14), "12-14"),
            (and_(hour_expr >= 14, hour_expr < 16), "14-16"),
            (and_(hour_expr >= 16, hour_expr < 18), "16-18"),
            else_="late",
        )

        stmt = (
            select(
                bucket_expr.label("bucket"),
                func.count().label("total"),
                func.count()
                .filter(Appointment.status == "no_show")
                .label("no_shows"),
            )
            .where(
                and_(
                    Appointment.start_time >= cutoff,
                    Appointment.is_active.is_(True),
                    Appointment.status.in_(
                        ["completed", "no_show", "cancelled"]
                    ),
                )
            )
            .group_by(bucket_expr)
        )
        result = await db.execute(stmt)
        rates: dict[str, float] = {}
        for row in result.all():
            if row.total > 0:
                rates[row.bucket] = (row.no_shows / row.total) * 100
        return rates

    # ── Internal: clinic-wide procedure-type no-show rates ───────────────

    async def _clinic_type_no_show_rates(
        self, db: AsyncSession, cutoff: datetime
    ) -> dict[str, float]:
        """No-show rate per appointment type across the entire clinic.

        Returns a dict of type -> rate (0-100).
        """
        stmt = (
            select(
                Appointment.type.label("appt_type"),
                func.count().label("total"),
                func.count()
                .filter(Appointment.status == "no_show")
                .label("no_shows"),
            )
            .where(
                and_(
                    Appointment.start_time >= cutoff,
                    Appointment.is_active.is_(True),
                    Appointment.status.in_(
                        ["completed", "no_show", "cancelled"]
                    ),
                )
            )
            .group_by(Appointment.type)
        )
        result = await db.execute(stmt)
        rates: dict[str, float] = {}
        for row in result.all():
            if row.total > 0:
                rates[row.appt_type] = (row.no_shows / row.total) * 100
        return rates

    # ── Gap analysis ─────────────────────────────────────────────────────

    async def find_gaps(
        self,
        db: AsyncSession,
        target_date: date,
        doctor_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Find unfilled time slots within doctors' working hours.

        For each gap, suggests patients from:
        1. Waitlist entries (status='waiting') matching the doctor/day
        2. Recall campaign recipients (status='pending')
        3. Patients with pending treatment plan items not yet scheduled
        """
        day_start = datetime.combine(target_date, time.min, tzinfo=UTC)
        day_end = datetime.combine(target_date, time.max, tzinfo=UTC)
        target_dow = target_date.weekday()

        # 1. Get doctor schedules for this day of week
        schedule_filters = [
            DoctorSchedule.day_of_week == target_dow,
            DoctorSchedule.is_working.is_(True),
            DoctorSchedule.start_time.is_not(None),
            DoctorSchedule.end_time.is_not(None),
        ]
        if doctor_id:
            schedule_filters.append(DoctorSchedule.user_id == doctor_id)

        sched_stmt = (
            select(
                DoctorSchedule.user_id.label("doctor_id"),
                DoctorSchedule.start_time.label("work_start"),
                DoctorSchedule.end_time.label("work_end"),
                DoctorSchedule.breaks,
                User.name.label("doctor_name"),
            )
            .join(User, User.id == DoctorSchedule.user_id)
            .where(and_(*schedule_filters))
        )
        sched_result = await db.execute(sched_stmt)
        schedules = sched_result.all()

        if not schedules:
            return []

        # 2. Get booked appointments for each doctor on the target date
        appt_stmt = (
            select(
                Appointment.doctor_id,
                Appointment.start_time,
                Appointment.end_time,
            )
            .where(
                and_(
                    Appointment.start_time >= day_start,
                    Appointment.start_time <= day_end,
                    Appointment.is_active.is_(True),
                    Appointment.status.in_(
                        ["scheduled", "confirmed", "in_progress"]
                    ),
                )
            )
            .order_by(Appointment.doctor_id, Appointment.start_time)
        )
        if doctor_id:
            appt_stmt = appt_stmt.where(Appointment.doctor_id == doctor_id)

        appt_result = await db.execute(appt_stmt)
        all_appts = appt_result.all()

        # Group appointments by doctor
        appts_by_doctor: dict[UUID, list[tuple[datetime, datetime]]] = {}
        for row in all_appts:
            appts_by_doctor.setdefault(row.doctor_id, []).append(
                (row.start_time, row.end_time)
            )

        # 3. Compute gaps for each doctor
        gaps: list[dict[str, Any]] = []
        for sched in schedules:
            doc_id = sched.doctor_id
            work_start_dt = datetime.combine(
                target_date, sched.work_start, tzinfo=UTC
            )
            work_end_dt = datetime.combine(
                target_date, sched.work_end, tzinfo=UTC
            )

            # Collect blocked intervals: booked appointments + breaks
            blocked: list[tuple[datetime, datetime]] = list(
                appts_by_doctor.get(doc_id, [])
            )

            # Add breaks as blocked intervals
            breaks = sched.breaks or []
            for brk in breaks:
                if isinstance(brk, dict) and "start" in brk and "end" in brk:
                    try:
                        brk_start = datetime.combine(
                            target_date,
                            time.fromisoformat(brk["start"]),
                            tzinfo=UTC,
                        )
                        brk_end = datetime.combine(
                            target_date,
                            time.fromisoformat(brk["end"]),
                            tzinfo=UTC,
                        )
                        blocked.append((brk_start, brk_end))
                    except (ValueError, TypeError):
                        continue

            # Sort blocked intervals by start time
            blocked.sort(key=lambda x: x[0])

            # Find gaps between blocked intervals within working hours
            doc_gaps = self._compute_gaps(work_start_dt, work_end_dt, blocked)

            # Only include gaps >= 15 minutes (minimum useful slot)
            for gap_start, gap_end in doc_gaps:
                if (gap_end - gap_start) >= timedelta(minutes=15):
                    gaps.append(
                        {
                            "slot_start": gap_start,
                            "slot_end": gap_end,
                            "doctor_id": doc_id,
                            "doctor_name": sched.doctor_name,
                            "suggested_patients": [],
                        }
                    )

        # 4. Suggest patients to fill gaps
        if gaps:
            suggestions = await self._get_fill_suggestions(
                db, target_date, doctor_id
            )
            for gap in gaps:
                gap["suggested_patients"] = suggestions[: 5]  # Top 5 per gap

        return gaps

    @staticmethod
    def _compute_gaps(
        work_start: datetime,
        work_end: datetime,
        blocked: list[tuple[datetime, datetime]],
    ) -> list[tuple[datetime, datetime]]:
        """Compute free intervals between blocked slots within working hours."""
        if not blocked:
            return [(work_start, work_end)]

        gaps: list[tuple[datetime, datetime]] = []
        current = work_start

        for blk_start, blk_end in blocked:
            # Clamp to working hours
            blk_start = max(blk_start, work_start)
            blk_end = min(blk_end, work_end)

            if blk_start > current:
                gaps.append((current, blk_start))
            current = max(current, blk_end)

        # Trailing gap after last blocked interval
        if current < work_end:
            gaps.append((current, work_end))

        return gaps

    # ── Internal: fill suggestions ───────────────────────────────────────

    async def _get_fill_suggestions(
        self,
        db: AsyncSession,
        target_date: date,
        doctor_id: UUID | None,
    ) -> list[dict[str, Any]]:
        """Collect candidate patients from waitlist, recall, and pending plans."""
        suggestions: list[dict[str, Any]] = []

        # A. Waitlist entries (status='waiting', not expired)
        wl_filters = [
            WaitlistEntry.status == "waiting",
            WaitlistEntry.is_active.is_(True),
        ]
        if doctor_id:
            wl_filters.append(
                (WaitlistEntry.preferred_doctor_id == doctor_id)
                | (WaitlistEntry.preferred_doctor_id.is_(None))
            )

        wl_stmt = (
            select(
                WaitlistEntry.patient_id,
                Patient.first_name,
                Patient.last_name,
            )
            .join(Patient, Patient.id == WaitlistEntry.patient_id)
            .where(and_(*wl_filters))
            .limit(10)
        )
        wl_result = await db.execute(wl_stmt)
        for row in wl_result.all():
            suggestions.append(
                {
                    "patient_id": str(row.patient_id),
                    "name": f"{row.first_name} {row.last_name}",
                    "reason": "waitlist",
                }
            )

        # B. Patients with pending treatment plan items (not yet scheduled)
        tp_stmt = (
            select(
                TreatmentPlan.patient_id,
                Patient.first_name,
                Patient.last_name,
            )
            .join(
                TreatmentPlanItem,
                TreatmentPlanItem.treatment_plan_id == TreatmentPlan.id,
            )
            .join(Patient, Patient.id == TreatmentPlan.patient_id)
            .where(
                and_(
                    TreatmentPlan.status == "active",
                    TreatmentPlan.is_active.is_(True),
                    TreatmentPlanItem.status == "pending",
                )
            )
            .group_by(
                TreatmentPlan.patient_id,
                Patient.first_name,
                Patient.last_name,
            )
            .limit(10)
        )
        tp_result = await db.execute(tp_stmt)
        for row in tp_result.all():
            # Avoid duplicate patient suggestions
            if not any(
                s["patient_id"] == str(row.patient_id) for s in suggestions
            ):
                suggestions.append(
                    {
                        "patient_id": str(row.patient_id),
                        "name": f"{row.first_name} {row.last_name}",
                        "reason": "reschedule",
                    }
                )

        return suggestions

    # ── Utilization metrics ──────────────────────────────────────────────

    async def get_utilization(
        self,
        db: AsyncSession,
        target_date: date,
        doctor_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Compute chair-time utilization for each doctor on the target date."""
        day_start = datetime.combine(target_date, time.min, tzinfo=UTC)
        day_end = datetime.combine(target_date, time.max, tzinfo=UTC)
        target_dow = target_date.weekday()

        # 1. Get doctor schedules for this day of week
        schedule_filters = [
            DoctorSchedule.day_of_week == target_dow,
            DoctorSchedule.is_working.is_(True),
            DoctorSchedule.start_time.is_not(None),
            DoctorSchedule.end_time.is_not(None),
        ]
        if doctor_id:
            schedule_filters.append(DoctorSchedule.user_id == doctor_id)

        sched_stmt = (
            select(
                DoctorSchedule.user_id.label("doctor_id"),
                DoctorSchedule.start_time.label("work_start"),
                DoctorSchedule.end_time.label("work_end"),
                DoctorSchedule.breaks,
                User.name.label("doctor_name"),
            )
            .join(User, User.id == DoctorSchedule.user_id)
            .where(and_(*schedule_filters))
        )
        sched_result = await db.execute(sched_stmt)
        schedules = sched_result.all()

        if not schedules:
            return []

        # 2. Get completed appointment minutes per doctor
        appt_stmt = (
            select(
                Appointment.doctor_id,
                func.coalesce(
                    func.sum(Appointment.duration_minutes), 0
                ).label("completed_minutes"),
            )
            .where(
                and_(
                    Appointment.start_time >= day_start,
                    Appointment.start_time <= day_end,
                    Appointment.status == "completed",
                    Appointment.is_active.is_(True),
                )
            )
            .group_by(Appointment.doctor_id)
        )
        if doctor_id:
            appt_stmt = appt_stmt.where(Appointment.doctor_id == doctor_id)

        appt_result = await db.execute(appt_stmt)
        completed_map: dict[UUID, int] = {}
        for row in appt_result.all():
            completed_map[row.doctor_id] = int(row.completed_minutes)

        # 3. Compute utilization per doctor
        metrics: list[dict[str, Any]] = []
        for sched in schedules:
            doc_id = sched.doctor_id

            # Total working minutes
            work_start_dt = datetime.combine(target_date, sched.work_start)
            work_end_dt = datetime.combine(target_date, sched.work_end)
            total_minutes = int(
                (work_end_dt - work_start_dt).total_seconds() / 60
            )

            # Subtract break minutes
            breaks = sched.breaks or []
            break_minutes = 0
            for brk in breaks:
                if isinstance(brk, dict) and "start" in brk and "end" in brk:
                    try:
                        brk_start = datetime.combine(
                            target_date, time.fromisoformat(brk["start"])
                        )
                        brk_end = datetime.combine(
                            target_date, time.fromisoformat(brk["end"])
                        )
                        break_minutes += max(
                            0,
                            int((brk_end - brk_start).total_seconds() / 60),
                        )
                    except (ValueError, TypeError):
                        continue

            available_minutes = max(0, total_minutes - break_minutes)
            completed_minutes = completed_map.get(doc_id, 0)

            utilization_pct = 0.0
            if available_minutes > 0:
                utilization_pct = round(
                    (completed_minutes / available_minutes) * 100, 1
                )
                utilization_pct = min(100.0, utilization_pct)

            metrics.append(
                {
                    "doctor_id": doc_id,
                    "doctor_name": sched.doctor_name,
                    "date": target_date,
                    "completed_minutes": completed_minutes,
                    "available_minutes": available_minutes,
                    "utilization_pct": utilization_pct,
                }
            )

        return metrics

    # ── Suggested fills (paginated) ──────────────────────────────────────

    async def suggest_fills(
        self,
        db: AsyncSession,
        target_date: date,
        doctor_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Generate paginated fill suggestions by combining gaps with candidates.

        Each gap is paired with each suggested patient, producing a flat list
        sorted by slot_start, then paginated.
        """
        gaps = await self.find_gaps(db, target_date, doctor_id)

        # Build flat list of SuggestedFill dicts
        all_fills: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()

        for gap in gaps:
            for suggestion in gap.get("suggested_patients", []):
                pair_key = (
                    str(gap["doctor_id"]) + gap["slot_start"].isoformat(),
                    suggestion["patient_id"],
                )
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Look up contact info (phone) for the suggested patient
                contact_info = await self._get_patient_phone(
                    db, UUID(suggestion["patient_id"])
                )

                all_fills.append(
                    {
                        "slot_start": gap["slot_start"],
                        "slot_end": gap["slot_end"],
                        "doctor_id": gap["doctor_id"],
                        "patient_id": UUID(suggestion["patient_id"]),
                        "patient_name": suggestion["name"],
                        "reason": suggestion["reason"],
                        "contact_info": contact_info,
                    }
                )

        # Sort by slot_start
        all_fills.sort(key=lambda f: f["slot_start"])

        # Paginate
        total = len(all_fills)
        offset = (page - 1) * page_size
        items = all_fills[offset: offset + page_size]

        return {"items": items, "total": total}

    async def _get_patient_phone(
        self, db: AsyncSession, patient_id: UUID
    ) -> str | None:
        """Fetch patient phone for fill suggestion contact info."""
        stmt = select(Patient.phone).where(Patient.id == patient_id)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return row


# ── Singleton instance ───────────────────────────────────────────────────────

schedule_intelligence_service = ScheduleIntelligenceService()
