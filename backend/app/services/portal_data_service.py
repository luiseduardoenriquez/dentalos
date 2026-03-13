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
from app.models.tenant.postop_instruction import PostopInstruction
from app.models.tenant.prescription import Prescription
from app.models.tenant.quotation import Quotation
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

        # Get clinic info from public.tenants (accessible via search_path)
        from app.models.public.tenant import Tenant
        clinic_name = "Clínica"
        clinic_slug = tenant_id[:8]
        clinic_logo_url = None
        clinic_phone = None
        clinic_address = None
        tenant_result = await db.execute(
            select(
                Tenant.name, Tenant.slug, Tenant.logo_url,
                Tenant.phone, Tenant.address,
            ).where(
                Tenant.id == uuid.UUID(tenant_id),
            )
        )
        tenant_row = tenant_result.first()
        if tenant_row:
            clinic_name = tenant_row.name
            clinic_slug = tenant_row.slug
            clinic_logo_url = tenant_row.logo_url
            clinic_phone = tenant_row.phone
            clinic_address = tenant_row.address

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

        # Count unread messages (F3)
        unread_messages = 0
        try:
            from app.services.messaging_service import messaging_service
            threads = await messaging_service.list_threads(
                db=db, patient_id=patient_id, cursor=None, limit=50,
            )
            unread_messages = sum(
                t.get("unread_count", 0) for t in threads.get("data", [])
            )
        except Exception:
            pass  # Best-effort — messaging may not be configured

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
                "name": clinic_name,
                "slug": clinic_slug,
                "logo_url": clinic_logo_url,
                "phone": clinic_phone,
                "address": clinic_address,
            },
            "outstanding_balance": int(outstanding),
            "unread_messages": unread_messages,
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

        conditions = [TreatmentPlan.patient_id == pid, TreatmentPlan.is_active.is_(True)]

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

        # Pre-fetch paid amounts per treatment plan from linked invoices
        plan_ids = [plan.id for plan in items]
        paid_map: dict[uuid.UUID, int] = {}
        if plan_ids:
            paid_result = await db.execute(
                select(
                    Quotation.treatment_plan_id,
                    func.coalesce(func.sum(Invoice.amount_paid), 0).label("paid"),
                )
                .join(Invoice, Invoice.quotation_id == Quotation.id)
                .where(
                    Quotation.treatment_plan_id.in_(plan_ids),
                )
                .group_by(Quotation.treatment_plan_id)
            )
            paid_map = {row.treatment_plan_id: int(row.paid) for row in paid_result.all()}

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
                    "tooth_number": str(item.tooth_number) if hasattr(item, "tooth_number") and item.tooth_number is not None else None,
                }
                for item in plan_items
            ]

            data.append({
                "id": str(plan.id),
                "name": plan.name,
                "status": plan.status,
                "procedures": procedures,
                "total": total,
                "paid": paid_map.get(plan.id, 0),
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

    async def get_postop_instructions(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List post-operative instructions for a patient (G1)."""
        pid = uuid.UUID(patient_id)

        conditions = [PostopInstruction.patient_id == pid]

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    PostopInstruction.sent_at < cursor_dt,
                    and_(
                        PostopInstruction.sent_at == cursor_dt,
                        PostopInstruction.id < cursor_id,
                    ),
                )
            )

        rows = (
            await db.execute(
                select(PostopInstruction, User)
                .outerjoin(User, PostopInstruction.doctor_id == User.id)
                .where(*conditions)
                .order_by(PostopInstruction.sent_at.desc(), PostopInstruction.id.desc())
                .limit(limit + 1)
            )
        ).all()

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1][0]
            next_cursor = _encode_cursor(last.sent_at, last.id)

        data = []
        for instr, doctor in items:
            data.append({
                "id": str(instr.id),
                "procedure_type": instr.procedure_type,
                "title": instr.title,
                "instruction_content": instr.instruction_content,
                "channel": instr.channel,
                "doctor_name": doctor.name if doctor else None,
                "sent_at": instr.sent_at,
                "is_read": instr.is_read,
                "read_at": instr.read_at,
            })

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def update_patient_profile(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update patient profile — only allowed fields (V1)."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="Paciente no encontrado.",
                status_code=404,
            )

        allowed = {"phone", "email", "address", "emergency_contact_name", "emergency_contact_phone"}
        for field, value in data.items():
            if field in allowed and value is not None:
                if hasattr(patient, field):
                    setattr(patient, field, value.strip() if isinstance(value, str) else value)

        await db.flush()

        return {
            "message": "Perfil actualizado exitosamente.",
            "id": str(patient.id),
        }

    async def get_notification_preferences(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any]:
        """Get patient notification preferences (V2)."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="Paciente no encontrado.",
                status_code=404,
            )

        metadata = patient.metadata or {} if hasattr(patient, "metadata") else {}
        prefs = metadata.get("notification_preferences", {})

        return {
            "email_enabled": prefs.get("email_enabled", True),
            "whatsapp_enabled": prefs.get("whatsapp_enabled", True),
            "sms_enabled": prefs.get("sms_enabled", True),
            "appointment_reminders": prefs.get("appointment_reminders", True),
            "treatment_updates": prefs.get("treatment_updates", True),
            "billing_notifications": prefs.get("billing_notifications", True),
            "marketing_messages": prefs.get("marketing_messages", False),
        }

    async def update_notification_preferences(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update patient notification preferences (V2)."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="Paciente no encontrado.",
                status_code=404,
            )

        metadata = patient.metadata or {} if hasattr(patient, "metadata") else {}
        prefs = metadata.get("notification_preferences", {})

        allowed = {
            "email_enabled", "whatsapp_enabled", "sms_enabled",
            "appointment_reminders", "treatment_updates",
            "billing_notifications", "marketing_messages",
        }
        for field, value in data.items():
            if field in allowed and value is not None:
                prefs[field] = value

        metadata["notification_preferences"] = prefs
        if hasattr(patient, "metadata"):
            patient.metadata = metadata
        await db.flush()

        return {**prefs, "message": "Preferencias actualizadas."}

    async def get_odontogram_history(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """Get odontogram snapshot history for timeline (V5)."""
        from app.models.tenant.odontogram import OdontogramSnapshot

        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(OdontogramSnapshot)
            .where(OdontogramSnapshot.patient_id == pid)
            .order_by(OdontogramSnapshot.created_at.desc())
            .limit(50)
        )
        snapshots = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "snapshot_date": s.created_at,
                "tooth_count": len(s.snapshot_data.get("teeth", [])) if isinstance(s.snapshot_data, dict) else 0,
                "condition_count": sum(
                    len(t.get("conditions", []))
                    for t in s.snapshot_data.get("teeth", [])
                ) if isinstance(s.snapshot_data, dict) else 0,
                "notes": s.snapshot_data.get("notes") if isinstance(s.snapshot_data, dict) else None,
            }
            for s in snapshots
        ]

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

        # Get conditions — linked by patient_id, not by state FK
        conditions_result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.patient_id == pid,
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
                "condition_name": cond.condition_code,
                "surface": cond.zone,
                "description": None,
            })
            if cond.condition_code not in legend:
                legend[cond.condition_code] = cond.condition_code

        teeth = [
            {
                "tooth_number": str(tn),
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


    async def get_intake_form(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Get intake form configuration for the patient's tenant (F4)."""
        from app.models.public.tenant import Tenant

        tid = uuid.UUID(tenant_id)
        result = await db.execute(
            select(Tenant.settings).where(Tenant.id == tid)
        )
        settings = result.scalar_one_or_none() or {}
        intake_config = settings.get("intake_form", {})

        # Default form sections if not configured
        if not intake_config:
            intake_config = {
                "sections": [
                    {
                        "key": "health_history",
                        "title": "Historia médica",
                        "fields": [
                            {"key": "allergies", "label": "Alergias", "type": "text"},
                            {"key": "medications", "label": "Medicamentos actuales", "type": "text"},
                            {"key": "conditions", "label": "Condiciones médicas", "type": "text"},
                            {"key": "surgeries", "label": "Cirugías previas", "type": "text"},
                        ],
                    },
                    {
                        "key": "dental_history",
                        "title": "Historia dental",
                        "fields": [
                            {"key": "last_visit", "label": "Última visita al dentista", "type": "text"},
                            {"key": "main_concern", "label": "Motivo de consulta", "type": "textarea"},
                        ],
                    },
                ],
            }

        return {"form_config": intake_config}

    async def get_survey_history(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """Get patient's NPS/CSAT survey responses (F6)."""
        from app.models.tenant.nps_survey import NPSSurveyResponse

        pid = uuid.UUID(patient_id)
        result = await db.execute(
            select(NPSSurveyResponse)
            .where(
                NPSSurveyResponse.patient_id == pid,
                NPSSurveyResponse.responded_at.isnot(None),
            )
            .order_by(NPSSurveyResponse.responded_at.desc())
            .limit(50)
        )
        surveys = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "nps_score": s.nps_score,
                "csat_score": s.csat_score,
                "comments": s.comments,
                "channel_sent": s.channel_sent,
                "sent_at": s.sent_at,
                "responded_at": s.responded_at,
            }
            for s in surveys
        ]

    async def get_financing_applications(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """Get patient's financing applications (F7)."""
        from app.models.tenant.financing import FinancingApplication

        pid = uuid.UUID(patient_id)
        result = await db.execute(
            select(FinancingApplication)
            .where(FinancingApplication.patient_id == pid)
            .order_by(FinancingApplication.created_at.desc())
            .limit(50)
        )
        apps = result.scalars().all()

        return [
            {
                "id": str(a.id),
                "provider": a.provider,
                "status": a.status,
                "amount_cents": a.amount_cents,
                "installments": a.installments,
                "created_at": a.created_at,
            }
            for a in apps
        ]

    async def get_family_group(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any] | None:
        """Get patient's family group with members and billing summary (F8)."""
        from app.models.tenant.family import FamilyGroup, FamilyMember

        pid = uuid.UUID(patient_id)

        # Find patient's family membership
        member_result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.patient_id == pid,
                FamilyMember.is_active.is_(True),
            )
        )
        membership = member_result.scalar_one_or_none()
        if membership is None:
            return None

        # Load the family group
        group_result = await db.execute(
            select(FamilyGroup).where(
                FamilyGroup.id == membership.family_group_id,
                FamilyGroup.is_active.is_(True),
            )
        )
        group = group_result.scalar_one_or_none()
        if group is None:
            return None

        # Load all members
        members_result = await db.execute(
            select(FamilyMember, Patient)
            .join(Patient, FamilyMember.patient_id == Patient.id)
            .where(
                FamilyMember.family_group_id == group.id,
                FamilyMember.is_active.is_(True),
            )
        )
        members_data = members_result.all()

        # Total outstanding across all family members
        member_ids = [m.patient_id for m, _ in members_data]
        total_outstanding = 0
        if member_ids:
            bal_result = await db.execute(
                select(func.coalesce(func.sum(Invoice.balance), 0)).where(
                    Invoice.patient_id.in_(member_ids),
                    Invoice.status.in_(["sent", "partial", "overdue"]),
                )
            )
            total_outstanding = int(bal_result.scalar_one())

        members = [
            {
                "id": str(p.id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "relationship": fm.relationship,
            }
            for fm, p in members_data
        ]

        return {
            "id": str(group.id),
            "name": group.name,
            "members": members,
            "total_outstanding": total_outstanding,
        }

    async def get_lab_orders(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """Get patient's lab orders (F9)."""
        from app.models.tenant.lab_order import DentalLab, LabOrder

        pid = uuid.UUID(patient_id)
        result = await db.execute(
            select(LabOrder, DentalLab)
            .outerjoin(DentalLab, LabOrder.lab_id == DentalLab.id)
            .where(
                LabOrder.patient_id == pid,
                LabOrder.is_active.is_(True),
            )
            .order_by(LabOrder.created_at.desc())
            .limit(50)
        )
        rows = result.all()

        return [
            {
                "id": str(order.id),
                "order_type": order.order_type,
                "status": order.status,
                "due_date": str(order.due_date) if order.due_date else None,
                "lab_name": lab.name if lab else None,
                "created_at": order.created_at,
            }
            for order, lab in rows
        ]

    async def get_tooth_photos(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Get patient's tooth photos with signed URLs (F10)."""
        from app.core.storage import storage_client
        from app.models.tenant.tooth_photo import ToothPhoto

        pid = uuid.UUID(patient_id)
        result = await db.execute(
            select(ToothPhoto)
            .where(
                ToothPhoto.patient_id == pid,
                ToothPhoto.is_active.is_(True),
            )
            .order_by(ToothPhoto.tooth_number, ToothPhoto.created_at.desc())
            .limit(100)
        )
        photos = result.scalars().all()

        data = []
        for p in photos:
            try:
                url = await storage_client.generate_signed_url(p.s3_key, expires_in=900)
                thumb_url = None
                if p.thumbnail_s3_key:
                    thumb_url = await storage_client.generate_signed_url(
                        p.thumbnail_s3_key, expires_in=900,
                    )
            except Exception:
                url = p.s3_key
                thumb_url = p.thumbnail_s3_key

            data.append({
                "id": str(p.id),
                "tooth_number": p.tooth_number,
                "url": url,
                "thumbnail_url": thumb_url,
                "created_at": p.created_at,
            })

        return data

    async def get_health_history(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any]:
        """Get patient's health history from intake responses (F11)."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="Paciente no encontrado.",
                status_code=404,
            )

        metadata = patient.metadata or {} if hasattr(patient, "metadata") else {}
        intake = metadata.get("intake_responses", {})
        health = metadata.get("health_history", {})

        return {
            "allergies": health.get("allergies", intake.get("allergies", [])),
            "medications": health.get("medications", intake.get("medications", [])),
            "conditions": health.get("conditions", intake.get("conditions", [])),
            "surgeries": health.get("surgeries", intake.get("surgeries", [])),
            "notes": health.get("notes"),
        }

    async def simulate_financing(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        amount_cents: int,
        provider: str,
    ) -> dict[str, Any]:
        """Simulate financing installment options (F12)."""
        # Provider-specific interest rates and terms
        provider_config = {
            "addi": {
                "rates": [(3, 0.0), (6, 1.5), (12, 2.5)],
                "min_amount": 5000000,  # 50k COP min
            },
            "sistecredito": {
                "rates": [(3, 0.0), (6, 2.0), (12, 3.0), (24, 3.5)],
                "min_amount": 10000000,  # 100k COP min
            },
            "mercadopago": {
                "rates": [(3, 0.0), (6, 1.8), (12, 2.8)],
                "min_amount": 5000000,
            },
        }

        config = provider_config.get(provider)
        if config is None:
            return {
                "provider": provider,
                "eligible": False,
                "options": [],
                "message": "Proveedor no disponible.",
            }

        if amount_cents < config["min_amount"]:
            return {
                "provider": provider,
                "eligible": False,
                "options": [],
                "message": f"El monto mínimo es ${config['min_amount'] // 100:,.0f} COP.",
            }

        options = []
        for installments, rate in config["rates"]:
            if rate == 0:
                monthly = amount_cents // installments
                total = amount_cents
            else:
                r = rate / 100
                monthly = int(amount_cents * (r * (1 + r) ** installments) / ((1 + r) ** installments - 1))
                total = monthly * installments
            options.append({
                "installments": installments,
                "monthly_payment_cents": monthly,
                "total_cents": total,
                "interest_rate_pct": rate,
            })

        return {
            "provider": provider,
            "eligible": True,
            "options": options,
            "message": None,
        }

    async def get_treatment_timeline(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Get treatment timeline combining procedures and photos (F13)."""
        from app.models.tenant.tooth_photo import ToothPhoto
        from app.models.tenant.treatment_plan import TreatmentPlanItem

        pid = uuid.UUID(patient_id)
        events: list[dict[str, Any]] = []

        # Completed procedures
        proc_result = await db.execute(
            select(TreatmentPlanItem, TreatmentPlan)
            .join(TreatmentPlan, TreatmentPlanItem.treatment_plan_id == TreatmentPlan.id)
            .where(
                TreatmentPlan.patient_id == pid,
                TreatmentPlanItem.status == "completed",
            )
            .order_by(TreatmentPlanItem.updated_at.desc())
            .limit(100)
        )
        for item, plan in proc_result.all():
            events.append({
                "id": str(item.id),
                "event_type": "procedure",
                "title": item.cups_description or "Procedimiento",
                "date": item.updated_at,
                "status": item.status,
                "photo_url": None,
                "tooth_number": str(item.tooth_number) if hasattr(item, "tooth_number") and item.tooth_number else None,
                "treatment_plan_name": plan.name,
            })

        # Tooth photos
        photo_result = await db.execute(
            select(ToothPhoto)
            .where(
                ToothPhoto.patient_id == pid,
                ToothPhoto.is_active.is_(True),
            )
            .order_by(ToothPhoto.created_at.desc())
            .limit(50)
        )
        photos = photo_result.scalars().all()

        for photo in photos:
            try:
                from app.core.storage import storage_client
                url = await storage_client.generate_signed_url(photo.s3_key, expires_in=900)
            except Exception:
                url = photo.s3_key

            events.append({
                "id": str(photo.id),
                "event_type": "photo",
                "title": f"Foto diente {photo.tooth_number}",
                "date": photo.created_at,
                "status": None,
                "photo_url": url,
                "tooth_number": str(photo.tooth_number),
                "treatment_plan_name": None,
            })

        # Sort all events by date descending
        events.sort(key=lambda e: e["date"], reverse=True)

        return events


# Module-level singleton
portal_data_service = PortalDataService()
