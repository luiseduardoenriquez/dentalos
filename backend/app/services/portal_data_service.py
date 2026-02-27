"""Portal data service — read-only endpoints for patient portal.

All methods enforce ownership: queries always filter by patient_id.
PHI is never logged.
"""

import base64
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, set_cached
from app.core.exceptions import DentalOSError
from app.models.tenant.appointment import Appointment
from app.models.tenant.consent import Consent
from app.models.tenant.invoice import Invoice
from app.models.tenant.odontogram import OdontogramCondition, OdontogramState
from app.models.tenant.patient import Patient
from app.models.tenant.patient_document import PatientDocument
from app.models.tenant.prescription import Prescription
from app.models.tenant.treatment_plan import TreatmentPlan
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.portal_data")


# ─── Cursor Helpers ──────────────────────────────────────────────────────────


def _encode_cursor(dt: datetime, item_id: uuid.UUID) -> str:
    payload = {"c": dt.isoformat(), "i": str(item_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(raw)
        return datetime.fromisoformat(data["c"]), uuid.UUID(data["i"])
    except Exception:
        raise DentalOSError(
            error="VALIDATION_invalid_cursor",
            message="El cursor de paginación no es válido.",
            status_code=400,
        )


class PortalDataService:
    """Stateless portal data read service."""

    async def get_profile(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Get patient profile with clinic info and summary data (PP-02)."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(
                Patient.id == pid,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="Paciente no encontrado.",
                status_code=404,
            )

        # Get next upcoming appointment
        next_appt = None
        appt_result = await db.execute(
            select(Appointment, User)
            .outerjoin(User, Appointment.doctor_id == User.id)
            .where(
                Appointment.patient_id == pid,
                Appointment.start_time > datetime.now(UTC),
                Appointment.status.in_(["confirmed", "pending"]),
            )
            .order_by(Appointment.start_time.asc())
            .limit(1)
        )
        row = appt_result.first()
        if row:
            appt, doctor = row
            next_appt = {
                "id": str(appt.id),
                "scheduled_at": appt.start_time,
                "duration_minutes": appt.duration_minutes,
                "status": appt.status,
                "appointment_type": appt.type if hasattr(appt, "type") else None,
                "doctor_name": doctor.name if doctor else "Sin asignar",
                "doctor_specialty": None,
                "notes_for_patient": appt.completion_notes if hasattr(appt, "completion_notes") else None,
            }

        # Get outstanding balance from invoices
        balance_result = await db.execute(
            select(
                func.coalesce(func.sum(Invoice.balance), 0)
            ).where(
                Invoice.patient_id == pid,
                Invoice.status.in_(["sent", "partial", "overdue"]),
            )
        )
        outstanding = balance_result.scalar_one()

        return {
            "id": str(patient.id),
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "email": patient.email,
            "phone": patient.phone,
            "birthdate": str(patient.birthdate) if patient.birthdate else None,
            "gender": patient.gender,
            "document_type": patient.document_type,
            "document_number": patient.document_number,
            "insurance_provider": patient.insurance_provider,
            "insurance_policy_number": patient.insurance_policy_number,
            "clinic": {
                "name": "Clínica",  # TODO: join with public.tenants
                "slug": tenant_id[:8],
                "logo_url": None,
                "phone": None,
                "address": None,
            },
            "outstanding_balance": int(outstanding),
            "next_appointment": next_appt,
        }

    async def list_appointments(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        view: str | None = None,
        status: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List patient appointments with cursor pagination (PP-03)."""
        pid = uuid.UUID(patient_id)

        conditions = [Appointment.patient_id == pid]

        if view == "upcoming":
            conditions.append(Appointment.start_time > datetime.now(UTC))
            conditions.append(Appointment.status.in_(["confirmed", "pending"]))
        elif view == "past":
            conditions.append(Appointment.start_time <= datetime.now(UTC))

        if status:
            conditions.append(Appointment.status == status)

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    Appointment.start_time < cursor_dt,
                    and_(
                        Appointment.start_time == cursor_dt,
                        Appointment.id < cursor_id,
                    ),
                )
            )

        rows = (
            await db.execute(
                select(Appointment, User)
                .outerjoin(User, Appointment.doctor_id == User.id)
                .where(*conditions)
                .order_by(Appointment.start_time.desc(), Appointment.id.desc())
                .limit(limit + 1)
            )
        ).all()

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last_appt = items[-1][0]
            next_cursor = _encode_cursor(last_appt.start_time, last_appt.id)

        data = []
        for appt, doctor in items:
            data.append({
                "id": str(appt.id),
                "scheduled_at": appt.start_time,
                "duration_minutes": appt.duration_minutes,
                "status": appt.status,
                "appointment_type": appt.type if hasattr(appt, "type") else None,
                "doctor_name": doctor.name if doctor else "Sin asignar",
                "doctor_specialty": None,
                "notes_for_patient": appt.notes if hasattr(appt, "notes") else None,
            })

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def list_treatment_plans(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List treatment plans with progress (PP-04)."""
        pid = uuid.UUID(patient_id)

        conditions = [TreatmentPlan.patient_id == pid]

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    TreatmentPlan.created_at < cursor_dt,
                    and_(
                        TreatmentPlan.created_at == cursor_dt,
                        TreatmentPlan.id < cursor_id,
                    ),
                )
            )

        plans = (
            await db.execute(
                select(TreatmentPlan)
                .where(*conditions)
                .order_by(TreatmentPlan.created_at.desc(), TreatmentPlan.id.desc())
                .limit(limit + 1)
            )
        ).scalars().all()

        has_more = len(plans) > limit
        items = plans[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        data = []
        for plan in items:
            # Use the selectin-loaded relationship — no extra query per plan
            plan_items = plan.items

            total = sum(item.estimated_cost for item in plan_items)
            completed = sum(1 for item in plan_items if item.status == "completed")
            progress = int((completed / len(plan_items) * 100)) if plan_items else 0

            procedures = [
                {
                    "id": str(item.id),
                    "name": item.cups_description,
                    "status": item.status,
                    "cost": item.estimated_cost,
                    "tooth_number": item.tooth_number if hasattr(item, "tooth_number") else None,
                }
                for item in plan_items
            ]

            data.append({
                "id": str(plan.id),
                "name": plan.name,
                "status": plan.status,
                "procedures": procedures,
                "total": total,
                "paid": 0,  # TODO: calculate from payments
                "progress_pct": progress,
                "created_at": plan.created_at,
            })

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def list_invoices(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List patient invoices (PP-06)."""
        pid = uuid.UUID(patient_id)

        conditions = [Invoice.patient_id == pid]

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    Invoice.created_at < cursor_dt,
                    and_(
                        Invoice.created_at == cursor_dt,
                        Invoice.id < cursor_id,
                    ),
                )
            )

        invoices = (
            await db.execute(
                select(Invoice)
                .where(*conditions)
                .order_by(Invoice.created_at.desc(), Invoice.id.desc())
                .limit(limit + 1)
            )
        ).scalars().all()

        has_more = len(invoices) > limit
        items = invoices[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        data = []
        for inv in items:
            # Use the selectin-loaded relationship — no extra query per invoice
            line_items = inv.items

            data.append({
                "id": str(inv.id),
                "invoice_number": inv.invoice_number if hasattr(inv, "invoice_number") else None,
                "date": inv.created_at,
                "total": inv.total,
                "paid": inv.amount_paid,
                "balance": inv.total - inv.amount_paid,
                "status": inv.status,
                "line_items": [
                    {
                        "description": li.description,
                        "quantity": li.quantity,
                        "unit_price": li.unit_price,
                        "total": li.line_total,
                    }
                    for li in line_items
                ],
            })

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def list_documents(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doc_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List patient documents unified — consents, xrays, prescriptions (PP-07)."""
        pid = uuid.UUID(patient_id)

        conditions = [
            PatientDocument.patient_id == pid,
            PatientDocument.is_active.is_(True),
        ]

        if doc_type:
            conditions.append(PatientDocument.document_type == doc_type)

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    PatientDocument.created_at < cursor_dt,
                    and_(
                        PatientDocument.created_at == cursor_dt,
                        PatientDocument.id < cursor_id,
                    ),
                )
            )

        docs = (
            await db.execute(
                select(PatientDocument)
                .where(*conditions)
                .order_by(PatientDocument.created_at.desc(), PatientDocument.id.desc())
                .limit(limit + 1)
            )
        ).scalars().all()

        has_more = len(docs) > limit
        items = docs[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        data = [
            {
                "id": str(doc.id),
                "document_type": doc.document_type,
                "name": doc.file_name if hasattr(doc, "file_name") else doc.description or "Documento",
                "created_at": doc.created_at,
                "signed_at": None,
                "url": doc.file_url if hasattr(doc, "file_url") else None,
            }
            for doc in items
        ]

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def list_message_threads(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List message threads for a patient (PP-10).

        Delegates to the messaging service for real thread data.
        """
        from app.services.messaging_service import messaging_service

        return await messaging_service.list_threads(
            db=db,
            patient_id=patient_id,
            cursor=cursor,
            limit=limit,
        )

    async def get_odontogram(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any]:
        """Get read-only odontogram for portal (PP-13)."""
        pid = uuid.UUID(patient_id)

        # Get odontogram state
        state_result = await db.execute(
            select(OdontogramState).where(OdontogramState.patient_id == pid)
        )
        state = state_result.scalar_one_or_none()

        if state is None:
            return {
                "teeth": [],
                "last_updated": None,
                "legend": {},
            }

        # Get conditions
        conditions_result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.odontogram_state_id == state.id,
                OdontogramCondition.is_active.is_(True),
            )
        )
        conditions = conditions_result.scalars().all()

        # Group by tooth
        teeth_map: dict[str, list[dict]] = {}
        legend: dict[str, str] = {}
        for cond in conditions:
            tn = cond.tooth_number
            if tn not in teeth_map:
                teeth_map[tn] = []
            teeth_map[tn].append({
                "condition_code": cond.condition_code,
                "condition_name": cond.condition_name if hasattr(cond, "condition_name") else cond.condition_code,
                "surface": cond.surface if hasattr(cond, "surface") else None,
                "description": None,
            })
            if cond.condition_code not in legend:
                legend[cond.condition_code] = cond.condition_name if hasattr(cond, "condition_name") else cond.condition_code

        teeth = [
            {
                "tooth_number": tn,
                "conditions": conds,
                "status": None,
            }
            for tn, conds in sorted(teeth_map.items())
        ]

        return {
            "teeth": teeth,
            "last_updated": state.updated_at,
            "legend": legend,
        }


# Module-level singleton
portal_data_service = PortalDataService()
