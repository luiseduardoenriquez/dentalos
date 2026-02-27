"""Analytics service — AN-01 through AN-07.

Aggregation queries for the analytics dashboard, patient demographics,
appointment utilization, revenue breakdowns, and audit trail access.
All monetary values in cents (COP).  Doctor role sees own data only.
"""

import asyncio
import base64
import hashlib
import logging
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Date, String, case, cast, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.cache import get_cached, set_cached
from app.core.exceptions import AuthError, BusinessValidationError
from app.models.audit import AuditLog
from app.models.tenant.appointment import Appointment
from app.models.tenant.clinical_record import ClinicalRecord
from app.models.tenant.invoice import Invoice, InvoiceItem
from app.models.tenant.patient import Patient
from app.models.tenant.payment import Payment
from app.models.tenant.user import User
from app.schemas.analytics import (
    AcquisitionPoint,
    AppointmentAnalyticsResponse,
    AppointmentStats,
    AuditLogEntry,
    AuditTrailResponse,
    DashboardResponse,
    DemographicBucket,
    DoctorOccupancy,
    NoShowTrendPoint,
    PatientAnalyticsResponse,
    PatientStats,
    PaymentMethodBreakdown,
    PeakHour,
    PeriodInfo,
    RevenueAnalyticsResponse,
    RevenueByDoctor,
    RevenueByProcedure,
    RevenueStats,
    RevenueTrendPoint,
    TopProcedure,
    UtilizationPoint,
)
from app.services.audit_service import write_audit_log

logger = logging.getLogger("dentalos.analytics")

# Maximum date range for custom periods (366 days inclusive).
MAX_RANGE_DAYS = 366
# Default cache TTL for analytics endpoints (seconds).
ANALYTICS_CACHE_TTL = 300

# PHI-sensitive keys that must be masked in audit trail output.
_PHI_REDACT_KEYS = frozenset({
    "phone", "email", "first_name", "last_name", "notes",
    "phone_secondary", "emergency_contact_name", "emergency_contact_phone",
    "address",
})
_PHI_PARTIAL_KEYS = frozenset({"document_number"})
_PHI_YEAR_KEYS = frozenset({"birthdate"})


class AnalyticsService:
    """Stateless service for analytics aggregation queries."""

    # ─── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def resolve_date_range(
        period: str,
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[date, date]:
        """Convert a named period into a concrete (start, end) date pair.

        For 'custom' periods both date_from and date_to must be provided and
        the range must not exceed MAX_RANGE_DAYS days.
        """
        today = date.today()

        if period == "today":
            return today, today
        elif period == "week":
            monday = today - timedelta(days=today.weekday())
            return monday, today
        elif period == "month":
            return today.replace(day=1), today
        elif period == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            return today.replace(month=quarter_month, day=1), today
        elif period == "year":
            return today.replace(month=1, day=1), today
        elif period == "custom":
            if date_from is None or date_to is None:
                raise BusinessValidationError(
                    "Rango de fechas requerido para periodo personalizado.",
                    field_errors={
                        "date_from": ["Requerido cuando period='custom'."],
                        "date_to": ["Requerido cuando period='custom'."],
                    },
                )
            if date_from > date_to:
                raise BusinessValidationError(
                    "Rango de fechas invalido.",
                    field_errors={
                        "date_from": [
                            "La fecha de inicio debe ser anterior a la fecha de fin."
                        ]
                    },
                )
            if (date_to - date_from).days > MAX_RANGE_DAYS:
                raise BusinessValidationError(
                    "Rango de fechas invalido.",
                    field_errors={
                        "date_range": [
                            "El rango de fechas no puede superar 366 dias."
                        ]
                    },
                )
            return date_from, date_to
        else:
            raise BusinessValidationError(
                "Periodo no soportado.",
                field_errors={"period": [f"Periodo '{period}' no reconocido."]},
            )

    @staticmethod
    def compute_growth(current_value: int | float, previous_value: int | float) -> float:
        """Percentage growth between two values.  Returns 0.0 on zero-division."""
        if previous_value == 0:
            return 0.0
        return round(((current_value - previous_value) / previous_value) * 100, 2)

    @staticmethod
    def get_doctor_scope(
        current_user: AuthenticatedUser,
        doctor_id_param: UUID | None = None,
    ) -> UUID | None:
        """Determine the doctor-level filter for queries.

        - doctor role: always own user_id (param ignored).
        - clinic_owner: None (all doctors) unless doctor_id_param given.
        """
        if current_user.role == "doctor":
            return UUID(current_user.user_id)
        # clinic_owner or other privileged roles
        return doctor_id_param

    @staticmethod
    def _cache_key(
        tenant_id: str,
        endpoint: str,
        role: str,
        doctor_scope: UUID | None,
        date_from: date,
        date_to: date,
    ) -> str:
        scope_hash = hashlib.md5(
            str(doctor_scope).encode() if doctor_scope else b"all"
        ).hexdigest()[:8]
        return (
            f"dentalos:{tenant_id}:analytics:{endpoint}"
            f":{role}:{scope_hash}:{date_from.isoformat()}:{date_to.isoformat()}"
        )

    @staticmethod
    async def cache_or_compute(
        cache_key: str,
        compute_fn: Any,
        ttl: int = ANALYTICS_CACHE_TTL,
    ) -> Any:
        """Check Redis cache; on miss call *compute_fn*, cache result, return."""
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached
        result = await compute_fn()
        await set_cached(cache_key, result, ttl)
        return result

    # ─── Private: previous-period helper ─────────────────────────────────

    @staticmethod
    def _previous_period(d_from: date, d_to: date) -> tuple[date, date]:
        """Return a same-length date range immediately preceding the given one."""
        delta = (d_to - d_from).days + 1
        prev_end = d_from - timedelta(days=1)
        prev_start = prev_end - timedelta(days=delta - 1)
        return prev_start, prev_end

    # ─── AN-01: Dashboard ────────────────────────────────────────────────

    async def get_dashboard(
        self,
        db: AsyncSession,
        tenant_id: str,
        current_user: AuthenticatedUser,
        period: str,
        date_from: date | None,
        date_to: date | None,
        doctor_id: UUID | None,
    ) -> DashboardResponse:
        d_from, d_to = self.resolve_date_range(period, date_from, date_to)
        doctor_scope = self.get_doctor_scope(current_user, doctor_id)

        cache_key = self._cache_key(
            tenant_id, "dashboard", current_user.role, doctor_scope, d_from, d_to
        )

        async def _compute() -> dict:
            results = await asyncio.gather(
                self._dashboard_patients(db, d_from, d_to),
                self._dashboard_appointments(db, d_from, d_to, doctor_scope),
                self._dashboard_revenue(db, d_from, d_to, doctor_scope),
                self._dashboard_top_procedures(db, d_from, d_to, doctor_scope),
                self._dashboard_doctor_occupancy(db, d_from, d_to, doctor_scope),
            )
            return {
                "period": PeriodInfo(
                    date_from=d_from.isoformat(),
                    date_to=d_to.isoformat(),
                    period=period,
                ).model_dump(),
                "patients": results[0],
                "appointments": results[1],
                "revenue": results[2],
                "top_procedures": results[3],
                "doctor_occupancy": results[4],
            }

        data = await self.cache_or_compute(cache_key, _compute)
        return DashboardResponse(**data)

    async def _dashboard_patients(
        self, db: AsyncSession, d_from: date, d_to: date
    ) -> dict:
        """Patient totals and growth."""
        # Total active patients
        total_result = await db.execute(
            select(func.count(Patient.id)).where(Patient.is_active.is_(True))
        )
        total = total_result.scalar_one()

        # New patients in period
        new_result = await db.execute(
            select(func.count(Patient.id)).where(
                Patient.is_active.is_(True),
                cast(Patient.created_at, Date) >= d_from,
                cast(Patient.created_at, Date) <= d_to,
            )
        )
        new_in_period = new_result.scalar_one()

        # Previous period for growth
        prev_from, prev_to = self._previous_period(d_from, d_to)
        prev_result = await db.execute(
            select(func.count(Patient.id)).where(
                Patient.is_active.is_(True),
                cast(Patient.created_at, Date) >= prev_from,
                cast(Patient.created_at, Date) <= prev_to,
            )
        )
        prev_new = prev_result.scalar_one()

        return PatientStats(
            total=total,
            new_in_period=new_in_period,
            growth_percentage=self.compute_growth(new_in_period, prev_new),
        ).model_dump()

    async def _dashboard_appointments(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> dict:
        """Appointment counts by status."""
        today = date.today()

        doctor_filter = []
        if doctor_scope is not None:
            doctor_filter.append(Appointment.doctor_id == doctor_scope)

        # Today's appointments
        today_result = await db.execute(
            select(func.count(Appointment.id)).where(
                cast(Appointment.start_time, Date) == today,
                Appointment.is_active.is_(True),
                *doctor_filter,
            )
        )
        today_count = today_result.scalar_one()

        # Period breakdown by status
        status_result = await db.execute(
            select(
                Appointment.status,
                func.count(Appointment.id).label("cnt"),
            )
            .where(
                cast(Appointment.start_time, Date) >= d_from,
                cast(Appointment.start_time, Date) <= d_to,
                Appointment.is_active.is_(True),
                *doctor_filter,
            )
            .group_by(Appointment.status)
        )
        status_rows = status_result.all()

        counts: dict[str, int] = {}
        for row in status_rows:
            counts[row.status] = row.cnt

        period_total = sum(counts.values())
        completed = counts.get("completed", 0)
        cancelled = counts.get("cancelled", 0)
        no_show_count = counts.get("no_show", 0)
        no_show_rate = round(
            (no_show_count / period_total * 100) if period_total > 0 else 0.0, 2
        )

        return AppointmentStats(
            today_count=today_count,
            period_total=period_total,
            completed=completed,
            cancelled=cancelled,
            no_show_count=no_show_count,
            no_show_rate=no_show_rate,
        ).model_dump()

    async def _dashboard_revenue(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> dict:
        """Revenue collected and pending."""
        # Payments in period
        pay_filter = [
            cast(Payment.payment_date, Date) >= d_from,
            cast(Payment.payment_date, Date) <= d_to,
        ]
        if doctor_scope is not None:
            # Filter payments through their invoice creator
            pay_filter.append(
                Payment.invoice_id.in_(
                    select(Invoice.id).where(Invoice.created_by == doctor_scope)
                )
            )

        collected_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(*pay_filter)
        )
        collected = collected_result.scalar_one()

        # Previous period for growth
        prev_from, prev_to = self._previous_period(d_from, d_to)
        prev_pay_filter = [
            cast(Payment.payment_date, Date) >= prev_from,
            cast(Payment.payment_date, Date) <= prev_to,
        ]
        if doctor_scope is not None:
            prev_pay_filter.append(
                Payment.invoice_id.in_(
                    select(Invoice.id).where(Invoice.created_by == doctor_scope)
                )
            )
        prev_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(*prev_pay_filter)
        )
        prev_collected = prev_result.scalar_one()

        # Pending collection (outstanding invoice balance)
        pending_filter = [
            Invoice.status.in_(["sent", "partial", "overdue"]),
            Invoice.is_active.is_(True),
        ]
        if doctor_scope is not None:
            pending_filter.append(Invoice.created_by == doctor_scope)

        pending_result = await db.execute(
            select(func.coalesce(func.sum(Invoice.balance), 0)).where(*pending_filter)
        )
        pending_collection = pending_result.scalar_one()

        return RevenueStats(
            collected=int(collected),
            growth_percentage=self.compute_growth(collected, prev_collected),
            pending_collection=int(pending_collection),
        ).model_dump()

    async def _dashboard_top_procedures(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        """Top 5 procedures by count in invoiced items."""
        filters = [
            cast(Invoice.created_at, Date) >= d_from,
            cast(Invoice.created_at, Date) <= d_to,
            Invoice.is_active.is_(True),
            InvoiceItem.cups_code.isnot(None),
        ]
        if doctor_scope is not None:
            filters.append(Invoice.created_by == doctor_scope)

        result = await db.execute(
            select(
                InvoiceItem.cups_code,
                InvoiceItem.description,
                func.count(InvoiceItem.id).label("cnt"),
            )
            .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
            .where(*filters)
            .group_by(InvoiceItem.cups_code, InvoiceItem.description)
            .order_by(func.count(InvoiceItem.id).desc())
            .limit(5)
        )
        rows = result.all()

        return [
            TopProcedure(
                cups_code=row.cups_code,
                description=row.description,
                count=row.cnt,
            ).model_dump()
            for row in rows
        ]

    async def _dashboard_doctor_occupancy(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        """Per-doctor completed / scheduled ratio."""
        filters = [
            cast(Appointment.start_time, Date) >= d_from,
            cast(Appointment.start_time, Date) <= d_to,
            Appointment.is_active.is_(True),
        ]
        if doctor_scope is not None:
            filters.append(Appointment.doctor_id == doctor_scope)

        result = await db.execute(
            select(
                Appointment.doctor_id,
                User.name.label("doctor_name"),
                func.count(
                    case((Appointment.status == "completed", Appointment.id))
                ).label("completed"),
                func.count(
                    case(
                        (
                            Appointment.status.in_(
                                ["scheduled", "confirmed", "in_progress", "completed"]
                            ),
                            Appointment.id,
                        )
                    )
                ).label("scheduled"),
            )
            .join(User, Appointment.doctor_id == User.id)
            .where(*filters)
            .group_by(Appointment.doctor_id, User.name)
        )
        rows = result.all()

        return [
            DoctorOccupancy(
                doctor_id=str(row.doctor_id),
                doctor_name=row.doctor_name,
                completed=row.completed,
                scheduled=row.scheduled,
                occupancy_rate=round(
                    (row.completed / row.scheduled * 100) if row.scheduled > 0 else 0.0,
                    2,
                ),
            ).model_dump()
            for row in rows
        ]

    # ─── AN-02: Patient analytics ────────────────────────────────────────

    async def get_patient_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        current_user: AuthenticatedUser,
        period: str,
        date_from: date | None,
        date_to: date | None,
    ) -> PatientAnalyticsResponse:
        d_from, d_to = self.resolve_date_range(period, date_from, date_to)

        cache_key = self._cache_key(
            tenant_id, "patients", current_user.role, None, d_from, d_to
        )

        async def _compute() -> dict:
            (
                gender_data,
                age_data,
                city_data,
                acquisition_data,
                retention_data,
                active_inactive,
            ) = await asyncio.gather(
                self._patient_gender(db),
                self._patient_age(db),
                self._patient_city(db),
                self._patient_acquisition(db, d_from, d_to),
                self._patient_retention(db),
                self._patient_active_inactive(db),
            )
            return {
                "period": PeriodInfo(
                    date_from=d_from.isoformat(),
                    date_to=d_to.isoformat(),
                    period=period,
                ).model_dump(),
                "demographics_gender": gender_data,
                "demographics_age": age_data,
                "demographics_city": city_data,
                "acquisition_trend": acquisition_data,
                "retention_rate": retention_data,
                "total_active": active_inactive[0],
                "total_inactive": active_inactive[1],
            }

        data = await self.cache_or_compute(cache_key, _compute)
        return PatientAnalyticsResponse(**data)

    async def _patient_gender(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                func.coalesce(Patient.gender, "unknown").label("gender"),
                func.count(Patient.id).label("cnt"),
            )
            .where(Patient.is_active.is_(True))
            .group_by(func.coalesce(Patient.gender, "unknown"))
        )
        return [
            DemographicBucket(label=row.gender, count=row.cnt).model_dump()
            for row in result.all()
        ]

    async def _patient_age(self, db: AsyncSession) -> list[dict]:
        today = date.today()
        age_expr = func.extract("year", func.age(today, Patient.birthdate))

        bucket_expr = case(
            (Patient.birthdate.is_(None), "unknown"),
            (age_expr < 18, "0-17"),
            (age_expr < 31, "18-30"),
            (age_expr < 51, "31-50"),
            (age_expr < 71, "51-70"),
            else_="71+",
        )

        result = await db.execute(
            select(
                bucket_expr.label("bucket"),
                func.count(Patient.id).label("cnt"),
            )
            .where(Patient.is_active.is_(True))
            .group_by(bucket_expr)
        )
        return [
            DemographicBucket(label=row.bucket, count=row.cnt).model_dump()
            for row in result.all()
        ]

    async def _patient_city(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                func.coalesce(Patient.city, "Sin ciudad").label("city"),
                func.count(Patient.id).label("cnt"),
            )
            .where(Patient.is_active.is_(True))
            .group_by(func.coalesce(Patient.city, "Sin ciudad"))
            .order_by(func.count(Patient.id).desc())
            .limit(10)
        )
        return [
            DemographicBucket(label=row.city, count=row.cnt).model_dump()
            for row in result.all()
        ]

    async def _patient_acquisition(
        self, db: AsyncSession, d_from: date, d_to: date
    ) -> list[dict]:
        result = await db.execute(
            select(
                func.date_trunc("month", Patient.created_at).label("month"),
                func.count(Patient.id).label("cnt"),
            )
            .where(
                Patient.is_active.is_(True),
                cast(Patient.created_at, Date) >= d_from,
                cast(Patient.created_at, Date) <= d_to,
            )
            .group_by(func.date_trunc("month", Patient.created_at))
            .order_by(func.date_trunc("month", Patient.created_at))
        )
        return [
            AcquisitionPoint(
                date=row.month.date().isoformat() if row.month else "",
                count=row.cnt,
            ).model_dump()
            for row in result.all()
        ]

    async def _patient_retention(self, db: AsyncSession) -> float:
        """Retention = patients with appointment in last 6 months / total active."""
        six_months_ago = date.today() - timedelta(days=180)

        active_result = await db.execute(
            select(func.count(Patient.id)).where(Patient.is_active.is_(True))
        )
        total_active = active_result.scalar_one()
        if total_active == 0:
            return 0.0

        retained_result = await db.execute(
            select(func.count(func.distinct(Appointment.patient_id))).where(
                Appointment.is_active.is_(True),
                cast(Appointment.start_time, Date) >= six_months_ago,
                Appointment.patient_id.in_(
                    select(Patient.id).where(Patient.is_active.is_(True))
                ),
            )
        )
        retained = retained_result.scalar_one()

        return round((retained / total_active) * 100, 2)

    async def _patient_active_inactive(self, db: AsyncSession) -> tuple[int, int]:
        result = await db.execute(
            select(
                func.count(case((Patient.is_active.is_(True), Patient.id))).label(
                    "active"
                ),
                func.count(case((Patient.is_active.is_(False), Patient.id))).label(
                    "inactive"
                ),
            )
        )
        row = result.one()
        return row.active, row.inactive

    # ─── AN-03: Appointment analytics ────────────────────────────────────

    async def get_appointment_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        current_user: AuthenticatedUser,
        period: str,
        date_from: date | None,
        date_to: date | None,
        doctor_id: UUID | None,
    ) -> AppointmentAnalyticsResponse:
        d_from, d_to = self.resolve_date_range(period, date_from, date_to)
        doctor_scope = self.get_doctor_scope(current_user, doctor_id)

        cache_key = self._cache_key(
            tenant_id, "appointments", current_user.role, doctor_scope, d_from, d_to
        )

        async def _compute() -> dict:
            utilization, peak_hours, no_show_trend, avg_duration = (
                await asyncio.gather(
                    self._appt_utilization(db, d_from, d_to, doctor_scope),
                    self._appt_peak_hours(db, d_from, d_to, doctor_scope),
                    self._appt_no_show_trend(db, d_from, d_to, doctor_scope),
                    self._appt_avg_duration(db, d_from, d_to, doctor_scope),
                )
            )
            return {
                "period": PeriodInfo(
                    date_from=d_from.isoformat(),
                    date_to=d_to.isoformat(),
                    period=period,
                ).model_dump(),
                "utilization": utilization,
                "peak_hours": peak_hours,
                "no_show_trend": no_show_trend,
                "average_duration_minutes": avg_duration,
            }

        data = await self.cache_or_compute(cache_key, _compute)
        return AppointmentAnalyticsResponse(**data)

    async def _appt_utilization(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Appointment.start_time, Date) >= d_from,
            cast(Appointment.start_time, Date) <= d_to,
            Appointment.is_active.is_(True),
        ]
        if doctor_scope is not None:
            filters.append(Appointment.doctor_id == doctor_scope)

        result = await db.execute(
            select(
                cast(Appointment.start_time, Date).label("day"),
                func.count(
                    case(
                        (
                            Appointment.status.in_(
                                ["scheduled", "confirmed", "in_progress"]
                            ),
                            Appointment.id,
                        )
                    )
                ).label("scheduled"),
                func.count(
                    case((Appointment.status == "completed", Appointment.id))
                ).label("completed"),
                func.count(
                    case((Appointment.status == "cancelled", Appointment.id))
                ).label("cancelled"),
                func.count(
                    case((Appointment.status == "no_show", Appointment.id))
                ).label("no_show"),
            )
            .where(*filters)
            .group_by(cast(Appointment.start_time, Date))
            .order_by(cast(Appointment.start_time, Date))
        )
        return [
            UtilizationPoint(
                date=row.day.isoformat(),
                scheduled=row.scheduled,
                completed=row.completed,
                cancelled=row.cancelled,
                no_show=row.no_show,
            ).model_dump()
            for row in result.all()
        ]

    async def _appt_peak_hours(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Appointment.start_time, Date) >= d_from,
            cast(Appointment.start_time, Date) <= d_to,
            Appointment.is_active.is_(True),
        ]
        if doctor_scope is not None:
            filters.append(Appointment.doctor_id == doctor_scope)

        result = await db.execute(
            select(
                cast(func.extract("hour", Appointment.start_time), Integer).label(
                    "hour"
                ),
                cast(func.extract("dow", Appointment.start_time), Integer).label(
                    "dow"
                ),
                func.count(Appointment.id).label("cnt"),
            )
            .where(*filters)
            .group_by(
                func.extract("hour", Appointment.start_time),
                func.extract("dow", Appointment.start_time),
            )
            .order_by(func.count(Appointment.id).desc())
        )
        from sqlalchemy import Integer as SAInteger

        return [
            PeakHour(
                hour=int(row.hour),
                day_of_week=int(row.dow),
                count=row.cnt,
            ).model_dump()
            for row in result.all()
        ]

    async def _appt_no_show_trend(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Appointment.start_time, Date) >= d_from,
            cast(Appointment.start_time, Date) <= d_to,
            Appointment.is_active.is_(True),
        ]
        if doctor_scope is not None:
            filters.append(Appointment.doctor_id == doctor_scope)

        result = await db.execute(
            select(
                func.date_trunc("week", Appointment.start_time).label("week"),
                func.count(Appointment.id).label("total"),
                func.count(
                    case((Appointment.status == "no_show", Appointment.id))
                ).label("no_show"),
            )
            .where(*filters)
            .group_by(func.date_trunc("week", Appointment.start_time))
            .order_by(func.date_trunc("week", Appointment.start_time))
        )
        return [
            NoShowTrendPoint(
                date=row.week.date().isoformat() if row.week else "",
                rate=round((row.no_show / row.total * 100) if row.total > 0 else 0.0, 2),
            ).model_dump()
            for row in result.all()
        ]

    async def _appt_avg_duration(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> float | None:
        filters = [
            cast(Appointment.start_time, Date) >= d_from,
            cast(Appointment.start_time, Date) <= d_to,
            Appointment.is_active.is_(True),
            Appointment.status == "completed",
        ]
        if doctor_scope is not None:
            filters.append(Appointment.doctor_id == doctor_scope)

        result = await db.execute(
            select(
                func.avg(Appointment.duration_minutes).label("avg_dur"),
            ).where(*filters)
        )
        avg = result.scalar_one()
        return round(float(avg), 1) if avg is not None else None

    # ─── AN-04: Revenue analytics ────────────────────────────────────────

    async def get_revenue_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        current_user: AuthenticatedUser,
        period: str,
        date_from: date | None,
        date_to: date | None,
        doctor_id: UUID | None,
    ) -> RevenueAnalyticsResponse:
        d_from, d_to = self.resolve_date_range(period, date_from, date_to)
        doctor_scope = self.get_doctor_scope(current_user, doctor_id)

        cache_key = self._cache_key(
            tenant_id, "revenue", current_user.role, doctor_scope, d_from, d_to
        )

        async def _compute() -> dict:
            trend, by_doctor, by_procedure, methods, ar = await asyncio.gather(
                self._revenue_trend(db, d_from, d_to, doctor_scope),
                self._revenue_by_doctor(db, d_from, d_to, doctor_scope),
                self._revenue_by_procedure(db, d_from, d_to, doctor_scope),
                self._revenue_payment_methods(db, d_from, d_to, doctor_scope),
                self._revenue_accounts_receivable(db, doctor_scope),
            )
            return {
                "period": PeriodInfo(
                    date_from=d_from.isoformat(),
                    date_to=d_to.isoformat(),
                    period=period,
                ).model_dump(),
                "trend": trend,
                "by_doctor": by_doctor,
                "by_procedure": by_procedure,
                "payment_methods": methods,
                "accounts_receivable": ar,
            }

        data = await self.cache_or_compute(cache_key, _compute)
        return RevenueAnalyticsResponse(**data)

    async def _revenue_trend(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Payment.payment_date, Date) >= d_from,
            cast(Payment.payment_date, Date) <= d_to,
        ]
        if doctor_scope is not None:
            filters.append(
                Payment.invoice_id.in_(
                    select(Invoice.id).where(Invoice.created_by == doctor_scope)
                )
            )

        result = await db.execute(
            select(
                func.date_trunc("month", Payment.payment_date).label("month"),
                func.coalesce(func.sum(Payment.amount), 0).label("total"),
            )
            .where(*filters)
            .group_by(func.date_trunc("month", Payment.payment_date))
            .order_by(func.date_trunc("month", Payment.payment_date))
        )
        return [
            RevenueTrendPoint(
                date=row.month.date().isoformat() if row.month else "",
                amount=int(row.total),
            ).model_dump()
            for row in result.all()
        ]

    async def _revenue_by_doctor(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Invoice.created_at, Date) >= d_from,
            cast(Invoice.created_at, Date) <= d_to,
            Invoice.is_active.is_(True),
        ]
        if doctor_scope is not None:
            filters.append(Invoice.created_by == doctor_scope)

        result = await db.execute(
            select(
                Invoice.created_by.label("doctor_id"),
                User.name.label("doctor_name"),
                func.coalesce(func.sum(InvoiceItem.line_total), 0).label("amount"),
            )
            .join(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
            .join(User, Invoice.created_by == User.id)
            .where(*filters)
            .group_by(Invoice.created_by, User.name)
            .order_by(func.coalesce(func.sum(InvoiceItem.line_total), 0).desc())
        )
        return [
            RevenueByDoctor(
                doctor_id=str(row.doctor_id),
                doctor_name=row.doctor_name,
                amount=int(row.amount),
            ).model_dump()
            for row in result.all()
        ]

    async def _revenue_by_procedure(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Invoice.created_at, Date) >= d_from,
            cast(Invoice.created_at, Date) <= d_to,
            Invoice.is_active.is_(True),
            InvoiceItem.cups_code.isnot(None),
        ]
        if doctor_scope is not None:
            filters.append(Invoice.created_by == doctor_scope)

        result = await db.execute(
            select(
                InvoiceItem.cups_code,
                InvoiceItem.description,
                func.coalesce(func.sum(InvoiceItem.line_total), 0).label("amount"),
                func.count(InvoiceItem.id).label("cnt"),
            )
            .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
            .where(*filters)
            .group_by(InvoiceItem.cups_code, InvoiceItem.description)
            .order_by(func.coalesce(func.sum(InvoiceItem.line_total), 0).desc())
        )
        return [
            RevenueByProcedure(
                cups_code=row.cups_code,
                description=row.description,
                amount=int(row.amount),
                count=row.cnt,
            ).model_dump()
            for row in result.all()
        ]

    async def _revenue_payment_methods(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> list[dict]:
        filters = [
            cast(Payment.payment_date, Date) >= d_from,
            cast(Payment.payment_date, Date) <= d_to,
        ]
        if doctor_scope is not None:
            filters.append(
                Payment.invoice_id.in_(
                    select(Invoice.id).where(Invoice.created_by == doctor_scope)
                )
            )

        result = await db.execute(
            select(
                Payment.payment_method,
                func.coalesce(func.sum(Payment.amount), 0).label("amount"),
                func.count(Payment.id).label("cnt"),
            )
            .where(*filters)
            .group_by(Payment.payment_method)
            .order_by(func.coalesce(func.sum(Payment.amount), 0).desc())
        )
        return [
            PaymentMethodBreakdown(
                method=row.payment_method,
                amount=int(row.amount),
                count=row.cnt,
            ).model_dump()
            for row in result.all()
        ]

    async def _revenue_accounts_receivable(
        self,
        db: AsyncSession,
        doctor_scope: UUID | None,
    ) -> int:
        filters = [
            Invoice.status.in_(["sent", "partial", "overdue"]),
            Invoice.is_active.is_(True),
        ]
        if doctor_scope is not None:
            filters.append(Invoice.created_by == doctor_scope)

        result = await db.execute(
            select(func.coalesce(func.sum(Invoice.balance), 0)).where(*filters)
        )
        return int(result.scalar_one())

    # ─── AN-07: Audit trail ──────────────────────────────────────────────

    async def get_audit_trail(
        self,
        db: AsyncSession,
        tenant_id: str,
        tenant_schema: str,
        current_user: AuthenticatedUser,
        cursor: str | None = None,
        page_size: int = 20,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AuditTrailResponse:
        """Cursor-based audit trail retrieval.  clinic_owner only.

        Cursor encodes (created_at, id) as base64.  Results ordered
        by (created_at DESC, id DESC).
        """
        if current_user.role != "clinic_owner":
            raise AuthError(
                error="AUTH_insufficient_role",
                message="Solo el propietario de la clinica puede acceder al historial de auditoria.",
                status_code=403,
            )

        # Validate page_size
        page_size = min(max(page_size, 1), 100)

        # Build filters
        filters: list[Any] = []

        if user_id is not None:
            filters.append(AuditLog.user_id == user_id)
        if resource_type is not None:
            filters.append(AuditLog.resource_type == resource_type)
        if action is not None:
            filters.append(AuditLog.action == action)
        if date_from is not None:
            filters.append(cast(AuditLog.created_at, Date) >= date_from)
        if date_to is not None:
            filters.append(cast(AuditLog.created_at, Date) <= date_to)

        # Decode cursor
        if cursor is not None:
            try:
                decoded = base64.b64decode(cursor).decode("utf-8")
                parts = decoded.split("|")
                cursor_ts = datetime.fromisoformat(parts[0])
                cursor_id = parts[1]
                # Keyset pagination: (created_at, id) < (cursor_ts, cursor_id)
                filters.append(
                    (AuditLog.created_at < cursor_ts)
                    | (
                        (AuditLog.created_at == cursor_ts)
                        & (cast(AuditLog.id, String) < cursor_id)
                    )
                )
            except Exception:
                raise BusinessValidationError(
                    "Cursor de paginacion invalido.",
                    field_errors={"cursor": ["El cursor proporcionado no es valido."]},
                )

        # Query with LEFT JOIN to User for user_name
        stmt = (
            select(
                AuditLog.id,
                AuditLog.user_id,
                User.name.label("user_name"),
                AuditLog.resource_type,
                AuditLog.resource_id,
                AuditLog.action,
                AuditLog.changes,
                AuditLog.ip_address,
                AuditLog.created_at,
            )
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(page_size + 1)  # Fetch one extra to detect has_more
        )

        result = await db.execute(stmt)
        rows = result.all()

        has_more = len(rows) > page_size
        items_rows = rows[:page_size]

        items = [
            AuditLogEntry(
                id=str(row.id),
                user_id=str(row.user_id) if row.user_id else "",
                user_name=row.user_name,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                action=row.action,
                changes=self._mask_phi(row.changes) if row.changes else {},
                ip_address=row.ip_address,
                created_at=row.created_at.isoformat(),
            )
            for row in items_rows
        ]

        # Compute next cursor from the last item
        next_cursor: str | None = None
        if has_more and items_rows:
            last = items_rows[-1]
            raw_cursor = f"{last.created_at.isoformat()}|{last.id}"
            next_cursor = base64.b64encode(raw_cursor.encode("utf-8")).decode("utf-8")

        # Meta-audit: log that someone accessed the audit trail
        try:
            await write_audit_log(
                db=db,
                tenant_schema=tenant_schema,
                user_id=current_user.user_id,
                action="read",
                resource_type="audit_log",
                resource_id=None,
                changes={"filters": {
                    "user_id": str(user_id) if user_id else None,
                    "resource_type": resource_type,
                    "action": action,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                }},
            )
        except Exception:
            logger.warning("Failed to write meta-audit log for audit trail access.")

        return AuditTrailResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    # ─── AN-06: Export ───────────────────────────────────────────────────

    async def export_analytics_data(
        self,
        db: AsyncSession,
        tenant_id: str,
        tenant_schema: str,
        current_user: AuthenticatedUser,
        report_type: str,
        period: str,
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query the dataset for the requested report type and return rows + count.

        Role scoping rules:
          - doctor: always sees own data only (appointments by doctor_id,
            revenue by invoice creator, clinical records by doctor_id).
            Patient export is clinic-wide for doctors (demographic data only).
          - clinic_owner / others: full clinic data.
          - revenue export: restricted to clinic_owner only.

        PHI safeguards:
          - patients report: patient_id replaced with sequential anonymous number.
          - clinical report: record_id anonymized; content field never included,
            only a boolean has_notes flag.
          - diagnoses/procedures represented as joined arrays, not free text.

        Returns:
            (rows, total_count) — rows is a list of flat dicts suitable for CSV.
        """
        _VALID_TYPES = {"patients", "appointments", "revenue", "clinical"}
        if report_type not in _VALID_TYPES:
            raise BusinessValidationError(
                "Tipo de reporte no soportado.",
                field_errors={
                    "report_type": [
                        f"'{report_type}' no es valido. Opciones: {', '.join(sorted(_VALID_TYPES))}."
                    ]
                },
            )

        # Revenue is restricted to clinic_owner
        if report_type == "revenue" and current_user.role not in (
            "clinic_owner",
            "superadmin",
        ):
            raise AuthError(
                error="AUTH_insufficient_role",
                message="El reporte de ingresos solo esta disponible para el propietario de la clinica.",
                status_code=403,
            )

        d_from, d_to = self.resolve_date_range(period, date_from, date_to)
        doctor_scope = self.get_doctor_scope(current_user)

        if report_type == "patients":
            return await self._export_patients(db, d_from, d_to)
        elif report_type == "appointments":
            return await self._export_appointments(db, d_from, d_to, doctor_scope)
        elif report_type == "revenue":
            return await self._export_revenue(db, d_from, d_to)
        else:  # clinical
            return await self._export_clinical(db, d_from, d_to, doctor_scope)

    async def _export_patients(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
    ) -> tuple[list[dict[str, Any]], int]:
        """patients report: demographic data with anonymized patient_id.

        Columns: patient_id (sequential), full_name, date_of_birth, gender,
                 phone, email, document_type, document_number, city,
                 created_at, total_visits, last_visit_date
        """
        # Subquery: visit counts and last visit per patient
        visit_sq = (
            select(
                Appointment.patient_id,
                func.count(Appointment.id).label("total_visits"),
                func.max(cast(Appointment.start_time, Date)).label("last_visit_date"),
            )
            .where(
                Appointment.is_active.is_(True),
                Appointment.status == "completed",
            )
            .group_by(Appointment.patient_id)
            .subquery()
        )

        stmt = (
            select(
                Patient.id,
                Patient.first_name,
                Patient.last_name,
                Patient.birthdate,
                Patient.gender,
                Patient.phone,
                Patient.email,
                Patient.document_type,
                Patient.document_number,
                Patient.city,
                Patient.created_at,
                func.coalesce(visit_sq.c.total_visits, 0).label("total_visits"),
                visit_sq.c.last_visit_date,
            )
            .outerjoin(visit_sq, Patient.id == visit_sq.c.patient_id)
            .where(
                Patient.is_active.is_(True),
                cast(Patient.created_at, Date) >= d_from,
                cast(Patient.created_at, Date) <= d_to,
            )
            .order_by(Patient.created_at)
        )

        result = await db.execute(stmt)
        db_rows = result.all()

        rows: list[dict[str, Any]] = []
        for seq_num, row in enumerate(db_rows, start=1):
            rows.append(
                {
                    "patient_id": seq_num,
                    "full_name": f"{row.first_name} {row.last_name}",
                    "date_of_birth": row.birthdate.isoformat() if row.birthdate else "",
                    "gender": row.gender or "",
                    "phone": row.phone or "",
                    "email": row.email or "",
                    "document_type": row.document_type,
                    "document_number": row.document_number,
                    "city": row.city or "",
                    "created_at": row.created_at.date().isoformat() if row.created_at else "",
                    "total_visits": row.total_visits,
                    "last_visit_date": (
                        row.last_visit_date.isoformat() if row.last_visit_date else ""
                    ),
                }
            )

        return rows, len(rows)

    async def _export_appointments(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> tuple[list[dict[str, Any]], int]:
        """appointments report: scheduling data without clinical notes.

        Columns: appointment_id, patient_name, doctor_name, appointment_type,
                 scheduled_at, status, duration_scheduled_min
        """
        from sqlalchemy.orm import aliased

        DoctorAlias = aliased(User, name="doc")

        filters = [
            Appointment.is_active.is_(True),
            cast(Appointment.start_time, Date) >= d_from,
            cast(Appointment.start_time, Date) <= d_to,
        ]
        if doctor_scope is not None:
            filters.append(Appointment.doctor_id == doctor_scope)

        stmt = (
            select(
                Appointment.id,
                Patient.first_name.label("patient_first_name"),
                Patient.last_name.label("patient_last_name"),
                DoctorAlias.name.label("doctor_name"),
                Appointment.type,
                Appointment.start_time,
                Appointment.status,
                Appointment.duration_minutes,
            )
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(DoctorAlias, Appointment.doctor_id == DoctorAlias.id)
            .where(*filters)
            .order_by(Appointment.start_time)
        )

        result = await db.execute(stmt)
        db_rows = result.all()

        rows: list[dict[str, Any]] = []
        for row in db_rows:
            rows.append(
                {
                    "appointment_id": str(row.id),
                    "patient_name": f"{row.patient_first_name} {row.patient_last_name}",
                    "doctor_name": row.doctor_name,
                    "appointment_type": row.type,
                    "scheduled_at": (
                        row.start_time.isoformat() if row.start_time else ""
                    ),
                    "status": row.status,
                    "duration_scheduled_min": row.duration_minutes,
                }
            )

        return rows, len(rows)

    async def _export_revenue(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
    ) -> tuple[list[dict[str, Any]], int]:
        """revenue report: invoice-level financial data (clinic_owner only).

        Columns: invoice_id, patient_name, doctor_name, issue_date,
                 total_amount, status, payment_method

        payment_method: comma-separated list from all payments on the invoice.
        total_amount: Invoice.total in cents (COP).
        """
        from sqlalchemy.orm import aliased

        DoctorAlias = aliased(User, name="doc")

        # Subquery: aggregate payment methods per invoice
        method_sq = (
            select(
                Payment.invoice_id,
                func.string_agg(
                    func.distinct(Payment.payment_method), literal_column("', '")
                ).label("methods"),
            )
            .group_by(Payment.invoice_id)
            .subquery()
        )

        stmt = (
            select(
                Invoice.id,
                Patient.first_name.label("patient_first_name"),
                Patient.last_name.label("patient_last_name"),
                DoctorAlias.name.label("doctor_name"),
                cast(Invoice.created_at, Date).label("issue_date"),
                Invoice.total,
                Invoice.status,
                method_sq.c.methods,
            )
            .join(Patient, Invoice.patient_id == Patient.id)
            .join(DoctorAlias, Invoice.created_by == DoctorAlias.id)
            .outerjoin(method_sq, Invoice.id == method_sq.c.invoice_id)
            .where(
                Invoice.is_active.is_(True),
                cast(Invoice.created_at, Date) >= d_from,
                cast(Invoice.created_at, Date) <= d_to,
            )
            .order_by(Invoice.created_at)
        )

        result = await db.execute(stmt)
        db_rows = result.all()

        rows: list[dict[str, Any]] = []
        for row in db_rows:
            rows.append(
                {
                    "invoice_id": str(row.id),
                    "patient_name": f"{row.patient_first_name} {row.patient_last_name}",
                    "doctor_name": row.doctor_name,
                    "issue_date": (
                        row.issue_date.isoformat() if row.issue_date else ""
                    ),
                    "total_amount": row.total,  # cents (COP)
                    "status": row.status,
                    "payment_method": row.methods or "",
                }
            )

        return rows, len(rows)

    async def _export_clinical(
        self,
        db: AsyncSession,
        d_from: date,
        d_to: date,
        doctor_scope: UUID | None,
    ) -> tuple[list[dict[str, Any]], int]:
        """clinical report: record metadata only — no free-text content.

        Columns: record_id (sequential anon), doctor_name, record_date,
                 diagnoses_cie10, procedures_cups, has_notes

        diagnoses_cie10 / procedures_cups: extracted from content JSONB as
        pipe-separated strings.  has_notes: boolean (True if content->notes
        is non-empty).  The raw content field is never returned.
        """
        from sqlalchemy.orm import aliased

        DoctorAlias = aliased(User, name="doc")

        filters = [
            ClinicalRecord.is_active.is_(True),
            cast(ClinicalRecord.created_at, Date) >= d_from,
            cast(ClinicalRecord.created_at, Date) <= d_to,
        ]
        if doctor_scope is not None:
            filters.append(ClinicalRecord.doctor_id == doctor_scope)

        # Extract diagnoses and procedures safely from JSONB content.
        # content->>'diagnoses' and content->>'procedures' are expected to be
        # JSON arrays; coalesce to empty array if absent.
        diagnoses_expr = func.coalesce(
            ClinicalRecord.content["diagnoses"].as_string(),
            "[]",
        ).label("diagnoses_raw")
        procedures_expr = func.coalesce(
            ClinicalRecord.content["procedures"].as_string(),
            "[]",
        ).label("procedures_raw")
        has_notes_expr = (
            ClinicalRecord.content["notes"].as_string().isnot(None)
            & (func.length(func.coalesce(ClinicalRecord.content["notes"].as_string(), "")) > 0)
        ).label("has_notes")

        stmt = (
            select(
                ClinicalRecord.id,
                DoctorAlias.name.label("doctor_name"),
                cast(ClinicalRecord.created_at, Date).label("record_date"),
                diagnoses_expr,
                procedures_expr,
                has_notes_expr,
            )
            .join(DoctorAlias, ClinicalRecord.doctor_id == DoctorAlias.id)
            .where(*filters)
            .order_by(ClinicalRecord.created_at)
        )

        result = await db.execute(stmt)
        db_rows = result.all()

        rows: list[dict[str, Any]] = []
        for seq_num, row in enumerate(db_rows, start=1):
            # Parse the raw JSON arrays returned as strings into pipe-joined codes.
            try:
                import json as _json

                diag_list = _json.loads(row.diagnoses_raw) if row.diagnoses_raw else []
                proc_list = _json.loads(row.procedures_raw) if row.procedures_raw else []

                # Each element may be a dict with a "code" key or a plain string.
                def _extract_codes(items: list) -> str:
                    codes = []
                    for item in items:
                        if isinstance(item, dict):
                            code = item.get("code") or item.get("cups_code") or item.get("cie10_code", "")
                        else:
                            code = str(item)
                        if code:
                            codes.append(code)
                    return " | ".join(codes)

                diagnoses_str = _extract_codes(diag_list)
                procedures_str = _extract_codes(proc_list)
            except Exception:
                diagnoses_str = ""
                procedures_str = ""

            rows.append(
                {
                    "record_id": seq_num,
                    "doctor_name": row.doctor_name,
                    "record_date": (
                        row.record_date.isoformat() if row.record_date else ""
                    ),
                    "diagnoses_cie10": diagnoses_str,
                    "procedures_cups": procedures_str,
                    "has_notes": bool(row.has_notes),
                }
            )

        return rows, len(rows)

    @staticmethod
    def _mask_phi(changes: dict) -> dict:
        """Mask PHI-sensitive fields in audit log changes JSONB.

        - document_number: show last 4 characters only
        - birthdate: show year only
        - phone, email, first_name, last_name, notes, etc.: '[REDACTED]'
        """
        if not changes:
            return {}

        masked = {}
        for key, value in changes.items():
            key_lower = key.lower()

            if key_lower in _PHI_REDACT_KEYS:
                if isinstance(value, dict):
                    masked[key] = {
                        k: "[REDACTED]" for k in value
                    }
                else:
                    masked[key] = "[REDACTED]"
            elif key_lower in _PHI_PARTIAL_KEYS:
                if isinstance(value, dict):
                    masked[key] = {
                        k: (
                            f"***{str(v)[-4:]}" if v and len(str(v)) >= 4 else "[REDACTED]"
                        )
                        for k, v in value.items()
                    }
                else:
                    val_str = str(value) if value else ""
                    masked[key] = (
                        f"***{val_str[-4:]}" if len(val_str) >= 4 else "[REDACTED]"
                    )
            elif key_lower in _PHI_YEAR_KEYS:
                if isinstance(value, dict):
                    masked[key] = {
                        k: (str(v)[:4] if v and len(str(v)) >= 4 else "[REDACTED]")
                        for k, v in value.items()
                    }
                else:
                    val_str = str(value) if value else ""
                    masked[key] = val_str[:4] if len(val_str) >= 4 else "[REDACTED]"
            else:
                masked[key] = value

        return masked


# Module-level singleton
analytics_service = AnalyticsService()
