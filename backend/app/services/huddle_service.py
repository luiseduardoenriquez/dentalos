"""Morning Huddle service — daily briefing aggregation.

Aggregates data from appointments, patients, invoices, payments, and
treatment plans into a single dashboard response. No new tables needed.

Security invariants:
  - PHI is included in response (patient names) but NEVER logged.
  - Read-only aggregation — no writes.
"""

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant.appointment import Appointment
from app.models.tenant.invoice import Invoice
from app.models.tenant.patient import Patient
from app.models.tenant.payment import Payment
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.huddle")


class HuddleService:
    """Aggregates morning huddle data from existing tables."""

    async def get_huddle(self, *, db: AsyncSession, tenant_id: str) -> dict[str, Any]:
        """Get the morning huddle — 8 parallel queries."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
        today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)
        yesterday_start = datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=UTC)
        yesterday_end = datetime.combine(yesterday, datetime.max.time()).replace(tzinfo=UTC)

        (
            appointments,
            production,
            incomplete_plans,
            outstanding_balances,
            birthdays,
            recall_due,
            yesterday_collections,
            no_shows,
        ) = await asyncio.gather(
            self._get_today_appointments(db, today_start, today_end),
            self._get_production_goals(db, today, yesterday),
            self._get_incomplete_plans(db),
            self._get_outstanding_balances(db),
            self._get_birthdays(db, today),
            self._get_recall_due(db, today),
            self._get_yesterday_collections(db, yesterday_start, yesterday_end),
            self._get_no_show_info(db, yesterday_start, yesterday_end, today_start, today_end),
        )

        return {
            "date": today,
            "appointments": appointments,
            "production": production,
            "incomplete_plans": incomplete_plans,
            "outstanding_balances": outstanding_balances,
            "birthdays": birthdays,
            "recall_due": recall_due,
            "yesterday_collections": yesterday_collections,
            "no_shows": no_shows,
        }

    async def _get_today_appointments(
        self, db: AsyncSession, today_start: datetime, today_end: datetime,
    ) -> list[dict[str, Any]]:
        """Section 1: Today's appointments with patient names."""
        result = await db.execute(
            select(
                Appointment.id,
                Appointment.patient_id,
                Appointment.doctor_id,
                Appointment.start_time,
                Appointment.type,
                Appointment.status,
                Patient.first_name,
                Patient.last_name,
                Patient.no_show_count,
                User.name.label("doctor_name"),
            )
            .join(Patient, Appointment.patient_id == Patient.id)
            .outerjoin(User, Appointment.doctor_id == User.id)
            .where(
                Appointment.start_time >= today_start,
                Appointment.start_time <= today_end,
                Appointment.is_active.is_(True),
                Appointment.status.notin_(["cancelled"]),
            )
            .order_by(Appointment.start_time)
        )
        rows = result.all()
        return [
            {
                "appointment_id": str(r.id),
                "patient_id": str(r.patient_id),
                "patient_name": f"{r.first_name} {r.last_name}",
                "doctor_id": str(r.doctor_id),
                "doctor_name": r.doctor_name or "Doctor",
                "start_time": r.start_time,
                "type": r.type,
                "status": r.status,
                "no_show_risk": (r.no_show_count or 0) >= 2,
            }
            for r in rows
        ]

    async def _get_production_goals(
        self, db: AsyncSession, today: date, yesterday: date,
    ) -> dict[str, Any]:
        """Section 2: Production goal vs actual."""
        # Daily actual: sum of payments today
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        daily_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                func.date(Payment.created_at) == today,
            )
        )
        daily_actual = daily_result.scalar_one()

        weekly_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                func.date(Payment.created_at) >= week_start,
                func.date(Payment.created_at) <= today,
            )
        )
        weekly_actual = weekly_result.scalar_one()

        monthly_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                func.date(Payment.created_at) >= month_start,
                func.date(Payment.created_at) <= today,
            )
        )
        monthly_actual = monthly_result.scalar_one()

        return {
            "daily_goal_cents": 0,
            "daily_actual_cents": daily_actual,
            "weekly_goal_cents": 0,
            "weekly_actual_cents": weekly_actual,
            "monthly_goal_cents": 0,
            "monthly_actual_cents": monthly_actual,
        }

    async def _get_incomplete_plans(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Section 3: Top 10 incomplete treatment plans by remaining value."""
        result = await db.execute(
            select(
                TreatmentPlan.id,
                TreatmentPlan.patient_id,
                TreatmentPlan.total_cost,
                TreatmentPlan.status,
                Patient.first_name,
                Patient.last_name,
                func.coalesce(
                    func.sum(
                        TreatmentPlanItem.unit_price * TreatmentPlanItem.quantity
                    ).filter(TreatmentPlanItem.status == "completed"),
                    0,
                ).label("completed_value"),
            )
            .join(Patient, TreatmentPlan.patient_id == Patient.id)
            .outerjoin(TreatmentPlanItem, TreatmentPlanItem.treatment_plan_id == TreatmentPlan.id)
            .where(
                TreatmentPlan.status.in_(["draft", "active", "approved"]),
                TreatmentPlan.is_active.is_(True),
            )
            .group_by(
                TreatmentPlan.id,
                TreatmentPlan.patient_id,
                TreatmentPlan.total_cost,
                TreatmentPlan.status,
                Patient.first_name,
                Patient.last_name,
            )
            .order_by((TreatmentPlan.total_cost - func.coalesce(
                func.sum(
                    TreatmentPlanItem.unit_price * TreatmentPlanItem.quantity
                ).filter(TreatmentPlanItem.status == "completed"),
                0,
            )).desc())
            .limit(10)
        )
        rows = result.all()
        return [
            {
                "treatment_plan_id": str(r.id),
                "patient_id": str(r.patient_id),
                "patient_name": f"{r.first_name} {r.last_name}",
                "total_cents": r.total_cost or 0,
                "remaining_cents": (r.total_cost or 0) - (r.completed_value or 0),
                "status": r.status,
            }
            for r in rows
        ]

    async def _get_outstanding_balances(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Section 4: Top 10 patients with outstanding balances."""
        result = await db.execute(
            select(
                Invoice.patient_id,
                Patient.first_name,
                Patient.last_name,
                func.sum(Invoice.balance).label("total_balance"),
                func.min(Invoice.created_at).label("oldest_date"),
            )
            .join(Patient, Invoice.patient_id == Patient.id)
            .where(
                Invoice.is_active.is_(True),
                Invoice.balance > 0,
                Invoice.status.in_(["sent", "overdue", "partial"]),
            )
            .group_by(Invoice.patient_id, Patient.first_name, Patient.last_name)
            .order_by(func.sum(Invoice.balance).desc())
            .limit(10)
        )
        rows = result.all()
        return [
            {
                "patient_id": str(r.patient_id),
                "patient_name": f"{r.first_name} {r.last_name}",
                "total_balance_cents": r.total_balance,
                "oldest_invoice_date": r.oldest_date.date() if r.oldest_date else None,
            }
            for r in rows
        ]

    async def _get_birthdays(self, db: AsyncSession, today: date) -> list[dict[str, Any]]:
        """Section 5: Patients with birthdays today."""
        result = await db.execute(
            select(Patient.id, Patient.first_name, Patient.last_name, Patient.birthdate)
            .where(
                Patient.is_active.is_(True),
                Patient.birthdate.isnot(None),
                func.extract("month", Patient.birthdate) == today.month,
                func.extract("day", Patient.birthdate) == today.day,
            )
        )
        rows = result.all()
        return [
            {
                "patient_id": str(r.id),
                "patient_name": f"{r.first_name} {r.last_name}",
                "birthdate": r.birthdate,
            }
            for r in rows
        ]

    async def _get_recall_due(self, db: AsyncSession, today: date) -> list[dict[str, Any]]:
        """Section 6: Patients with no visit in 6+ months."""
        six_months_ago = today - timedelta(days=180)

        # Subquery: latest appointment per patient
        latest_appt = (
            select(
                Appointment.patient_id,
                func.max(Appointment.start_time).label("last_visit"),
            )
            .where(
                Appointment.status == "completed",
                Appointment.is_active.is_(True),
            )
            .group_by(Appointment.patient_id)
            .subquery()
        )

        result = await db.execute(
            select(
                Patient.id,
                Patient.first_name,
                Patient.last_name,
                latest_appt.c.last_visit,
            )
            .outerjoin(latest_appt, Patient.id == latest_appt.c.patient_id)
            .where(
                Patient.is_active.is_(True),
                (latest_appt.c.last_visit < six_months_ago) | (latest_appt.c.last_visit.is_(None)),
            )
            .order_by(latest_appt.c.last_visit.asc().nullsfirst())
            .limit(10)
        )
        rows = result.all()
        return [
            {
                "patient_id": str(r.id),
                "patient_name": f"{r.first_name} {r.last_name}",
                "last_visit_date": r.last_visit.date() if r.last_visit else None,
                "months_since_visit": (
                    (today - r.last_visit.date()).days // 30
                    if r.last_visit
                    else 99
                ),
            }
            for r in rows
        ]

    async def _get_yesterday_collections(
        self, db: AsyncSession, yesterday_start: datetime, yesterday_end: datetime,
    ) -> dict[str, Any]:
        """Section 7: Yesterday's collection total."""
        result = await db.execute(
            select(
                func.coalesce(func.sum(Payment.amount), 0).label("total"),
                func.count(Payment.id).label("count"),
            ).where(
                Payment.created_at >= yesterday_start,
                Payment.created_at <= yesterday_end,
            )
        )
        row = result.one()
        return {
            "total_collected_cents": row.total,
            "payment_count": row.count,
        }

    async def _get_no_show_info(
        self,
        db: AsyncSession,
        yesterday_start: datetime,
        yesterday_end: datetime,
        today_start: datetime,
        today_end: datetime,
    ) -> dict[str, Any]:
        """Section 8: Yesterday no-shows + today's high-risk no-shows."""
        # Yesterday's no-show count
        yesterday_ns = await db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.start_time >= yesterday_start,
                Appointment.start_time <= yesterday_end,
                Appointment.status == "no_show",
                Appointment.is_active.is_(True),
            )
        )
        yesterday_count = yesterday_ns.scalar_one()

        # Today's high-risk: patients with 2+ prior no-shows and appointment today
        high_risk_result = await db.execute(
            select(
                Appointment.id,
                Appointment.patient_id,
                Appointment.doctor_id,
                Appointment.start_time,
                Appointment.type,
                Appointment.status,
                Patient.first_name,
                Patient.last_name,
                Patient.no_show_count,
                User.name.label("doctor_name"),
            )
            .join(Patient, Appointment.patient_id == Patient.id)
            .outerjoin(User, Appointment.doctor_id == User.id)
            .where(
                Appointment.start_time >= today_start,
                Appointment.start_time <= today_end,
                Appointment.is_active.is_(True),
                Appointment.status.notin_(["cancelled", "no_show"]),
                Patient.no_show_count >= 2,
            )
            .order_by(Appointment.start_time)
        )
        high_risk_rows = high_risk_result.all()

        return {
            "yesterday_no_show_count": yesterday_count,
            "today_high_risk_count": len(high_risk_rows),
            "today_high_risk_patients": [
                {
                    "appointment_id": str(r.id),
                    "patient_id": str(r.patient_id),
                    "patient_name": f"{r.first_name} {r.last_name}",
                    "doctor_id": str(r.doctor_id),
                    "doctor_name": r.doctor_name or "Doctor",
                    "start_time": r.start_time,
                    "type": r.type,
                    "status": r.status,
                    "no_show_risk": True,
                }
                for r in high_risk_rows
            ],
        }


huddle_service = HuddleService()
