"""AI clinical summary service (AI-02).

Aggregates patient data from 8 sources, builds an anonymised prompt,
calls Claude Haiku, parses the structured JSON response, and caches the
result in Redis (TTL 5 min).

Security invariants:
  - PHI is NEVER logged (patient names, document numbers, phone, email).
  - The prompt sent to Claude contains ONLY clinical data:
    age, gender, blood type, allergy flags, conditions, treatments,
    financial totals, appointment dates.  No identifying information.
  - All Spanish (es-419) output for clinical staff.
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, set_cached
from app.core.config import settings
from app.core.error_codes import AIClinicalSummaryErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.ai_usage_log import AIUsageLog
from app.models.tenant.appointment import Appointment
from app.models.tenant.clinical_record import ClinicalRecord
from app.models.tenant.diagnosis import Diagnosis
from app.models.tenant.invoice import Invoice
from app.models.tenant.odontogram import OdontogramCondition
from app.models.tenant.patient import Patient
from app.models.tenant.payment import Payment
from app.models.tenant.prescription import Prescription
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.schemas.clinical_summary import (
    ActionSuggestion,
    ActionSuggestionsSection,
    ActiveConditionItem,
    ActiveConditionsSection,
    ClinicalSummaryResponse,
    ClinicalSummarySections,
    FinancialStatusData,
    FinancialStatusSection,
    LastVisitData,
    LastVisitSection,
    PatientSnapshotData,
    PatientSnapshotSection,
    PendingTreatmentItem,
    PendingTreatmentsSection,
    RiskAlert,
    RiskAlertsSection,
    TodayContextData,
    TodayContextSection,
)
from app.services.ai_claude_client import call_claude, extract_json_object

logger = logging.getLogger("dentalos.ai.clinical_summary")

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300

# Haiku model for fast, low-cost summaries
_MODEL = "claude-haiku-4-5-20251001"


# ── Helpers ───────────────────────────────────────────────────────


def _compute_age(birthdate: date | None) -> int | None:
    """Compute age in years from a birthdate, or None if unknown."""
    if birthdate is None:
        return None
    today = date.today()
    return today.year - birthdate.year - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )


def _format_date(dt: datetime | date | None) -> str | None:
    """Format a datetime to ISO date string, or None."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.date().isoformat()
    return dt.isoformat()


def _cache_key(tenant_id: str, patient_id: str) -> str:
    """Build Redis cache key for a clinical summary."""
    tid_short = tenant_id[:12] if tenant_id else "unknown"
    return f"dentalos:{tid_short}:clinical:summary:{patient_id}"


# ── System prompt ─────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Eres un asistente clínico dental experto para una clínica dental en Colombia.
Se te proporciona el contexto clínico anonimizado de un paciente (sin nombre,
documento, teléfono ni correo). Tu tarea es generar un resumen clínico
estructurado en español (es-419) que el doctor pueda revisar rápidamente
antes de una cita.

REGLAS:
1. Todo el texto generado debe estar en español (es-419).
2. Sé conciso y directo. Cada campo "content" debe ser 1-3 oraciones.
3. Las alertas de riesgo deben priorizar seguridad del paciente.
4. No inventes información que no esté en los datos proporcionados.
5. Los costos están en centavos de COP. Presenta montos legibles cuando
   los menciones en el texto (ej: "$150.000 COP").
6. Clasifica la severidad de alertas como: "critical", "warning", "info".
7. Prioridad de sugerencias: "high", "medium", "low".
8. Categorías de sugerencias: "safety", "treatment_planning", "financial",
   "follow_up", "compliance".

Devuelve ÚNICAMENTE un objeto JSON con exactamente estas 8 secciones:

{
  "patient_snapshot": {
    "title": "Resumen del Paciente",
    "content": "<resumen conciso>",
    "data": {
      "age": <int|null>,
      "gender": "<string|null>",
      "total_visits": <int>,
      "last_visit_date": "<YYYY-MM-DD|null>",
      "patient_since": "<YYYY-MM-DD|null>"
    }
  },
  "today_context": {
    "title": "Contexto de la Cita de Hoy",
    "content": "<descripción del contexto>",
    "data": {
      "appointment_type": "<string|null>",
      "scheduled_time": "<HH:MM|null>",
      "doctor_name": "<string|null>",
      "estimated_duration_minutes": <int|null>,
      "related_teeth": ["<diente1>", ...]
    }
  },
  "active_conditions": {
    "title": "Condiciones Activas",
    "content": "<resumen>",
    "items": [
      {
        "diagnosis": "<nombre>",
        "cie10_code": "<código|null>",
        "tooth": "<diente|null>",
        "severity": "<mild|moderate|severe>",
        "diagnosed_date": "<YYYY-MM-DD|null>",
        "relevant_to_today": <bool>
      }
    ]
  },
  "risk_alerts": {
    "title": "Alertas de Riesgo",
    "content": "<resumen>",
    "alerts": [
      {
        "type": "<allergy|medication_interaction|medical_condition|compliance>",
        "severity": "<critical|warning|info>",
        "message": "<mensaje>",
        "recommendation": "<recomendación>"
      }
    ]
  },
  "pending_treatments": {
    "title": "Tratamientos Pendientes",
    "content": "<resumen>",
    "items": [
      {
        "procedure": "<nombre>",
        "cups_code": "<código|null>",
        "tooth": "<diente|null>",
        "status": "<pending|scheduled>",
        "estimated_cost_cents": <int>,
        "planned_for_today": <bool>
      }
    ],
    "total_pending_cost_cents": <int>
  },
  "last_visit_summary": {
    "title": "Resumen Última Visita",
    "content": "<resumen>",
    "data": {
      "date": "<YYYY-MM-DD|null>",
      "procedures_performed": ["<proc1>", ...],
      "notes_excerpt": "<extracto|null>",
      "doctor_name": "<nombre|null>"
    }
  },
  "financial_status": {
    "title": "Estado Financiero",
    "content": "<resumen>",
    "data": {
      "outstanding_balance_cents": <int>,
      "last_payment_date": "<YYYY-MM-DD|null>",
      "last_payment_amount_cents": <int>,
      "payment_history": "<good|fair|poor|unknown>",
      "has_active_financing": false
    }
  },
  "action_suggestions": {
    "title": "Sugerencias de Acción",
    "content": "<resumen>",
    "suggestions": [
      {
        "priority": "<high|medium|low>",
        "action": "<descripción>",
        "category": "<safety|treatment_planning|financial|follow_up|compliance>"
      }
    ]
  }
}
"""


# ── Data aggregation queries ──────────────────────────────────────


async def _fetch_patient_demographics(
    db: AsyncSession, patient_id: uuid.UUID
) -> dict[str, Any] | None:
    """Fetch patient demographics (no PII: name, document, phone, email excluded)."""
    result = await db.execute(
        select(
            Patient.id,
            Patient.birthdate,
            Patient.gender,
            Patient.blood_type,
            Patient.allergies,
            Patient.chronic_conditions,
            Patient.insurance_provider,
            Patient.no_show_count,
            Patient.created_at,
        ).where(Patient.id == patient_id, Patient.is_active.is_(True))
    )
    row = result.one_or_none()
    if row is None:
        return None

    return {
        "age": _compute_age(row.birthdate),
        "gender": row.gender,
        "blood_type": row.blood_type,
        "allergies": row.allergies or [],
        "chronic_conditions": row.chronic_conditions or [],
        "insurance_provider": row.insurance_provider,
        "no_show_count": row.no_show_count,
        "patient_since": _format_date(row.created_at),
    }


async def _fetch_odontogram_conditions(
    db: AsyncSession, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Fetch active odontogram conditions."""
    result = await db.execute(
        select(
            OdontogramCondition.tooth_number,
            OdontogramCondition.zone,
            OdontogramCondition.condition_code,
            OdontogramCondition.severity,
        ).where(
            OdontogramCondition.patient_id == patient_id,
            OdontogramCondition.is_active.is_(True),
        )
    )
    return [
        {
            "tooth_number": row.tooth_number,
            "zone": row.zone,
            "condition_code": row.condition_code,
            "severity": row.severity,
        }
        for row in result.all()
    ]


async def _fetch_active_diagnoses(
    db: AsyncSession, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Fetch active diagnoses."""
    result = await db.execute(
        select(
            Diagnosis.cie10_code,
            Diagnosis.cie10_description,
            Diagnosis.severity,
            Diagnosis.tooth_number,
            Diagnosis.created_at,
        ).where(
            Diagnosis.patient_id == patient_id,
            Diagnosis.status == "active",
            Diagnosis.is_active.is_(True),
        )
    )
    return [
        {
            "cie10_code": row.cie10_code,
            "cie10_description": row.cie10_description,
            "severity": row.severity,
            "tooth_number": row.tooth_number,
            "diagnosed_date": _format_date(row.created_at),
        }
        for row in result.all()
    ]


async def _fetch_treatment_plans(
    db: AsyncSession, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Fetch active/draft treatment plans with pending items."""
    result = await db.execute(
        select(TreatmentPlan)
        .where(
            TreatmentPlan.patient_id == patient_id,
            TreatmentPlan.status.in_(["active", "draft"]),
            TreatmentPlan.is_active.is_(True),
        )
    )
    plans = result.scalars().all()

    items_data: list[dict[str, Any]] = []
    for plan in plans:
        for item in plan.items:
            if item.status in ("pending", "scheduled"):
                items_data.append({
                    "cups_code": item.cups_code,
                    "cups_description": item.cups_description,
                    "tooth_number": item.tooth_number,
                    "status": item.status,
                    "estimated_cost": item.estimated_cost,
                })
    return items_data


async def _fetch_appointments(
    db: AsyncSession, patient_id: uuid.UUID
) -> dict[str, Any]:
    """Fetch last completed appointment and next upcoming appointment."""
    now = datetime.now(UTC)

    # Last completed appointment
    last_result = await db.execute(
        select(
            Appointment.start_time,
            Appointment.type,
            Appointment.duration_minutes,
            Appointment.completion_notes,
        )
        .where(
            Appointment.patient_id == patient_id,
            Appointment.status == "completed",
            Appointment.is_active.is_(True),
        )
        .order_by(Appointment.start_time.desc())
        .limit(1)
    )
    last_row = last_result.one_or_none()

    # Next upcoming appointment (today or future)
    next_result = await db.execute(
        select(
            Appointment.start_time,
            Appointment.end_time,
            Appointment.type,
            Appointment.duration_minutes,
            Appointment.treatment_plan_item_id,
        )
        .where(
            Appointment.patient_id == patient_id,
            Appointment.status.in_(["scheduled", "confirmed"]),
            Appointment.start_time >= now,
            Appointment.is_active.is_(True),
        )
        .order_by(Appointment.start_time.asc())
        .limit(1)
    )
    next_row = next_result.one_or_none()

    # Total completed visit count
    count_result = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.patient_id == patient_id,
            Appointment.status == "completed",
            Appointment.is_active.is_(True),
        )
    )
    total_visits = count_result.scalar() or 0

    return {
        "total_visits": total_visits,
        "last_appointment": {
            "date": _format_date(last_row.start_time) if last_row else None,
            "type": last_row.type if last_row else None,
            "duration_minutes": last_row.duration_minutes if last_row else None,
            "completion_notes": last_row.completion_notes if last_row else None,
        } if last_row else None,
        "next_appointment": {
            "date": _format_date(next_row.start_time) if next_row else None,
            "time": (
                next_row.start_time.strftime("%H:%M") if next_row else None
            ),
            "type": next_row.type if next_row else None,
            "duration_minutes": next_row.duration_minutes if next_row else None,
        } if next_row else None,
    }


async def _fetch_evolution_notes(
    db: AsyncSession, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Fetch last 3 evolution notes."""
    result = await db.execute(
        select(
            ClinicalRecord.type,
            ClinicalRecord.content,
            ClinicalRecord.tooth_numbers,
            ClinicalRecord.created_at,
        )
        .where(
            ClinicalRecord.patient_id == patient_id,
            ClinicalRecord.type == "evolution_note",
            ClinicalRecord.is_active.is_(True),
        )
        .order_by(ClinicalRecord.created_at.desc())
        .limit(3)
    )
    return [
        {
            "type": row.type,
            "content_summary": _summarize_content(row.content),
            "tooth_numbers": row.tooth_numbers or [],
            "date": _format_date(row.created_at),
        }
        for row in result.all()
    ]


async def _fetch_financial_status(
    db: AsyncSession, patient_id: uuid.UUID
) -> dict[str, Any]:
    """Fetch outstanding balance and last payment info."""
    # Outstanding balance from unpaid invoices
    balance_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.balance), 0).label("total_balance")
        ).where(
            Invoice.patient_id == patient_id,
            Invoice.status.in_(["sent", "partial", "overdue"]),
            Invoice.is_active.is_(True),
        )
    )
    outstanding = balance_result.scalar() or 0

    # Last payment
    payment_result = await db.execute(
        select(
            Payment.amount,
            Payment.created_at,
        )
        .where(Payment.patient_id == patient_id)
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    last_payment = payment_result.one_or_none()

    # Count overdue invoices for payment history assessment
    overdue_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.patient_id == patient_id,
            Invoice.status == "overdue",
            Invoice.is_active.is_(True),
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Simple payment history heuristic
    if overdue_count == 0 and outstanding == 0:
        payment_history = "good"
    elif overdue_count <= 1:
        payment_history = "fair"
    elif overdue_count > 1:
        payment_history = "poor"
    else:
        payment_history = "unknown"

    return {
        "outstanding_balance_cents": outstanding,
        "last_payment_date": (
            _format_date(last_payment.created_at) if last_payment else None
        ),
        "last_payment_amount_cents": (
            last_payment.amount if last_payment else 0
        ),
        "payment_history": payment_history,
    }


async def _fetch_prescriptions(
    db: AsyncSession, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Fetch active prescriptions (recent, last 90 days)."""
    cutoff = datetime.now(UTC) - timedelta(days=90)
    result = await db.execute(
        select(
            Prescription.medications,
            Prescription.created_at,
        )
        .where(
            Prescription.patient_id == patient_id,
            Prescription.is_active.is_(True),
            Prescription.created_at >= cutoff,
        )
        .order_by(Prescription.created_at.desc())
        .limit(5)
    )
    prescriptions: list[dict[str, Any]] = []
    for row in result.all():
        meds = row.medications
        if isinstance(meds, list):
            for med in meds:
                prescriptions.append({
                    "name": med.get("name", "Desconocido"),
                    "dosis": med.get("dosis", ""),
                    "prescribed_date": _format_date(row.created_at),
                })
        elif isinstance(meds, dict):
            # Single medication stored as dict
            prescriptions.append({
                "name": meds.get("name", "Desconocido"),
                "dosis": meds.get("dosis", ""),
                "prescribed_date": _format_date(row.created_at),
            })
    return prescriptions


def _summarize_content(content: dict | None) -> str:
    """Extract a brief text summary from JSONB clinical record content.

    Tries common keys and truncates to 200 chars to avoid sending
    excessive text to the LLM.
    """
    if not content or not isinstance(content, dict):
        return ""

    # Try common content keys from evolution note templates
    for key in ("resumen", "summary", "nota", "notes", "descripcion",
                "description", "observaciones", "motivo_consulta"):
        val = content.get(key)
        if val and isinstance(val, str):
            return val[:200]

    # Fallback: stringify first 200 chars of the dict
    raw = json.dumps(content, ensure_ascii=False, default=str)
    return raw[:200]


# ── Prompt builder ────────────────────────────────────────────────


def _build_user_prompt(
    *,
    demographics: dict[str, Any],
    odontogram_conditions: list[dict[str, Any]],
    diagnoses: list[dict[str, Any]],
    treatment_items: list[dict[str, Any]],
    appointments: dict[str, Any],
    evolution_notes: list[dict[str, Any]],
    financial: dict[str, Any],
    prescriptions: list[dict[str, Any]],
) -> str:
    """Build the user message with anonymised clinical data."""
    parts: list[str] = []

    # 1. Demographics (no PII)
    parts.append("## Datos Demográficos del Paciente")
    if demographics.get("age") is not None:
        parts.append(f"- Edad: {demographics['age']} años")
    if demographics.get("gender"):
        parts.append(f"- Género: {demographics['gender']}")
    if demographics.get("blood_type"):
        parts.append(f"- Tipo de sangre: {demographics['blood_type']}")
    if demographics.get("allergies"):
        parts.append(f"- Alergias: {', '.join(demographics['allergies'])}")
    if demographics.get("chronic_conditions"):
        parts.append(
            f"- Condiciones crónicas: {', '.join(demographics['chronic_conditions'])}"
        )
    if demographics.get("insurance_provider"):
        parts.append(f"- Aseguradora: {demographics['insurance_provider']}")
    if demographics.get("patient_since"):
        parts.append(f"- Paciente desde: {demographics['patient_since']}")
    parts.append(f"- Inasistencias registradas: {demographics.get('no_show_count', 0)}")

    # 2. Odontogram conditions
    parts.append("\n## Condiciones del Odontograma (Activas)")
    if odontogram_conditions:
        for cond in odontogram_conditions:
            line = (
                f"- Diente {cond['tooth_number']} ({cond['zone']}): "
                f"{cond['condition_code']}"
            )
            if cond.get("severity"):
                line += f" (severidad: {cond['severity']})"
            parts.append(line)
    else:
        parts.append("- Sin condiciones activas registradas")

    # 3. Diagnoses
    parts.append("\n## Diagnósticos Activos")
    if diagnoses:
        for dx in diagnoses:
            line = f"- {dx['cie10_code']}: {dx['cie10_description']} (severidad: {dx['severity']})"
            if dx.get("tooth_number"):
                line += f" [Diente {dx['tooth_number']}]"
            if dx.get("diagnosed_date"):
                line += f" — diagnosticado: {dx['diagnosed_date']}"
            parts.append(line)
    else:
        parts.append("- Sin diagnósticos activos")

    # 4. Treatment plan items
    parts.append("\n## Tratamientos Pendientes")
    if treatment_items:
        total_cost = 0
        for item in treatment_items:
            line = f"- {item['cups_code']}: {item['cups_description']} (estado: {item['status']})"
            if item.get("tooth_number"):
                line += f" [Diente {item['tooth_number']}]"
            line += f" — costo estimado: {item['estimated_cost']} centavos COP"
            total_cost += item.get("estimated_cost", 0)
            parts.append(line)
        parts.append(f"- Costo total pendiente: {total_cost} centavos COP")
    else:
        parts.append("- Sin tratamientos pendientes")

    # 5. Appointments
    parts.append("\n## Historial de Citas")
    parts.append(f"- Total de visitas completadas: {appointments.get('total_visits', 0)}")
    last_appt = appointments.get("last_appointment")
    if last_appt:
        parts.append(
            f"- Última visita: {last_appt['date']} (tipo: {last_appt['type']}, "
            f"duración: {last_appt['duration_minutes']} min)"
        )
    next_appt = appointments.get("next_appointment")
    if next_appt:
        parts.append(
            f"- Próxima cita: {next_appt['date']} a las {next_appt['time']} "
            f"(tipo: {next_appt['type']}, duración: {next_appt['duration_minutes']} min)"
        )

    # 6. Evolution notes
    parts.append("\n## Notas de Evolución Recientes (últimas 3)")
    if evolution_notes:
        for note in evolution_notes:
            line = f"- [{note['date']}] {note['content_summary']}"
            if note.get("tooth_numbers"):
                line += f" [Dientes: {', '.join(str(t) for t in note['tooth_numbers'])}]"
            parts.append(line)
    else:
        parts.append("- Sin notas de evolución recientes")

    # 7. Financial status
    parts.append("\n## Estado Financiero")
    parts.append(
        f"- Saldo pendiente: {financial.get('outstanding_balance_cents', 0)} centavos COP"
    )
    if financial.get("last_payment_date"):
        parts.append(
            f"- Último pago: {financial['last_payment_date']} "
            f"por {financial['last_payment_amount_cents']} centavos COP"
        )
    parts.append(f"- Historial de pago: {financial.get('payment_history', 'unknown')}")

    # 8. Prescriptions
    parts.append("\n## Medicamentos/Prescripciones Activas (últimos 90 días)")
    if prescriptions:
        for rx in prescriptions:
            parts.append(
                f"- {rx['name']} ({rx.get('dosis', 'sin dosis')}) — "
                f"prescrito: {rx.get('prescribed_date', 'fecha desconocida')}"
            )
    else:
        parts.append("- Sin prescripciones recientes")

    return "\n".join(parts)


# ── Response parser ───────────────────────────────────────────────


def _parse_summary_response(
    raw: dict[str, Any],
    demographics: dict[str, Any],
    appointments: dict[str, Any],
    financial: dict[str, Any],
    treatment_items: list[dict[str, Any]],
) -> ClinicalSummarySections:
    """Parse Claude's JSON response into validated Pydantic sections.

    Falls back to data-only defaults when Claude omits or malforms a section.
    """
    sections = ClinicalSummarySections()

    # -- patient_snapshot --
    ps = raw.get("patient_snapshot", {})
    sections.patient_snapshot = PatientSnapshotSection(
        title=ps.get("title", "Resumen del Paciente"),
        content=ps.get("content", ""),
        data=PatientSnapshotData(
            age=demographics.get("age"),
            gender=demographics.get("gender"),
            total_visits=appointments.get("total_visits", 0),
            last_visit_date=(
                appointments.get("last_appointment", {}).get("date")
                if appointments.get("last_appointment") else None
            ),
            patient_since=demographics.get("patient_since"),
        ),
    )

    # -- today_context --
    tc = raw.get("today_context", {})
    tc_data = tc.get("data", {})
    next_appt = appointments.get("next_appointment")
    sections.today_context = TodayContextSection(
        title=tc.get("title", "Contexto de la Cita de Hoy"),
        content=tc.get("content", ""),
        data=TodayContextData(
            appointment_type=(
                tc_data.get("appointment_type")
                or (next_appt.get("type") if next_appt else None)
            ),
            scheduled_time=(
                tc_data.get("scheduled_time")
                or (next_appt.get("time") if next_appt else None)
            ),
            doctor_name=tc_data.get("doctor_name"),
            estimated_duration_minutes=(
                tc_data.get("estimated_duration_minutes")
                or (next_appt.get("duration_minutes") if next_appt else None)
            ),
            related_teeth=tc_data.get("related_teeth", []),
        ),
    )

    # -- active_conditions --
    ac = raw.get("active_conditions", {})
    ac_items_raw = ac.get("items", [])
    ac_items = []
    for item in ac_items_raw:
        if isinstance(item, dict):
            ac_items.append(ActiveConditionItem(
                diagnosis=item.get("diagnosis", ""),
                cie10_code=item.get("cie10_code"),
                tooth=item.get("tooth"),
                severity=item.get("severity", "low"),
                diagnosed_date=item.get("diagnosed_date"),
                relevant_to_today=item.get("relevant_to_today", False),
            ))
    sections.active_conditions = ActiveConditionsSection(
        title=ac.get("title", "Condiciones Activas"),
        content=ac.get("content", ""),
        items=ac_items,
    )

    # -- risk_alerts --
    ra = raw.get("risk_alerts", {})
    ra_items_raw = ra.get("alerts", [])
    ra_alerts = []
    for alert in ra_items_raw:
        if isinstance(alert, dict):
            ra_alerts.append(RiskAlert(
                type=alert.get("type", "medical_condition"),
                severity=alert.get("severity", "info"),
                message=alert.get("message", ""),
                recommendation=alert.get("recommendation", ""),
            ))
    sections.risk_alerts = RiskAlertsSection(
        title=ra.get("title", "Alertas de Riesgo"),
        content=ra.get("content", ""),
        alerts=ra_alerts,
    )

    # -- pending_treatments --
    pt = raw.get("pending_treatments", {})
    pt_items_raw = pt.get("items", [])
    pt_items = []
    total_pending = 0
    for item in pt_items_raw:
        if isinstance(item, dict):
            cost = item.get("estimated_cost_cents", 0)
            if not isinstance(cost, int):
                cost = 0
            total_pending += cost
            pt_items.append(PendingTreatmentItem(
                procedure=item.get("procedure", ""),
                cups_code=item.get("cups_code"),
                tooth=item.get("tooth"),
                status=item.get("status", "pending"),
                estimated_cost_cents=cost,
                planned_for_today=item.get("planned_for_today", False),
            ))
    # Use aggregated cost from real data as fallback
    if not pt_items and treatment_items:
        for ti in treatment_items:
            cost = ti.get("estimated_cost", 0)
            total_pending += cost
            pt_items.append(PendingTreatmentItem(
                procedure=ti.get("cups_description", ""),
                cups_code=ti.get("cups_code"),
                tooth=str(ti["tooth_number"]) if ti.get("tooth_number") else None,
                status=ti.get("status", "pending"),
                estimated_cost_cents=cost,
            ))
    sections.pending_treatments = PendingTreatmentsSection(
        title=pt.get("title", "Tratamientos Pendientes"),
        content=pt.get("content", ""),
        items=pt_items,
        total_pending_cost_cents=pt.get("total_pending_cost_cents", total_pending),
    )

    # -- last_visit_summary --
    lv = raw.get("last_visit_summary", {})
    lv_data = lv.get("data", {})
    last_appt = appointments.get("last_appointment")
    sections.last_visit_summary = LastVisitSection(
        title=lv.get("title", "Resumen Última Visita"),
        content=lv.get("content", ""),
        data=LastVisitData(
            date=(
                lv_data.get("date")
                or (last_appt.get("date") if last_appt else None)
            ),
            procedures_performed=lv_data.get("procedures_performed", []),
            notes_excerpt=lv_data.get("notes_excerpt"),
            doctor_name=lv_data.get("doctor_name"),
        ),
    )

    # -- financial_status --
    fs = raw.get("financial_status", {})
    fs_data = fs.get("data", {})
    sections.financial_status = FinancialStatusSection(
        title=fs.get("title", "Estado Financiero"),
        content=fs.get("content", ""),
        data=FinancialStatusData(
            outstanding_balance_cents=(
                fs_data.get("outstanding_balance_cents")
                or financial.get("outstanding_balance_cents", 0)
            ),
            last_payment_date=(
                fs_data.get("last_payment_date")
                or financial.get("last_payment_date")
            ),
            last_payment_amount_cents=(
                fs_data.get("last_payment_amount_cents")
                or financial.get("last_payment_amount_cents", 0)
            ),
            payment_history=(
                fs_data.get("payment_history")
                or financial.get("payment_history", "unknown")
            ),
            has_active_financing=fs_data.get("has_active_financing", False),
        ),
    )

    # -- action_suggestions --
    asec = raw.get("action_suggestions", {})
    as_items_raw = asec.get("suggestions", [])
    suggestions = []
    for sug in as_items_raw:
        if isinstance(sug, dict):
            suggestions.append(ActionSuggestion(
                priority=sug.get("priority", "medium"),
                action=sug.get("action", ""),
                category=sug.get("category", "follow_up"),
            ))
    sections.action_suggestions = ActionSuggestionsSection(
        title=asec.get("title", "Sugerencias de Acción"),
        content=asec.get("content", ""),
        suggestions=suggestions,
    )

    return sections


# ── Main service class ────────────────────────────────────────────


class ClinicalSummaryService:
    """Generates AI-powered clinical summaries for a patient.

    Aggregates data from 8 sources, builds an anonymised prompt,
    calls Claude Haiku, parses the structured JSON response, and
    caches the result in Redis (TTL 5 min).
    """

    async def generate_summary(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        tenant_id: str,
        tenant_features: dict[str, Any],
        force_refresh: bool = False,
    ) -> ClinicalSummaryResponse:
        """Generate or retrieve a cached clinical summary.

        Args:
            db: Tenant-scoped async DB session.
            patient_id: UUID string of the patient.
            doctor_id: UUID string of the requesting doctor.
            tenant_id: Tenant identifier for cache key namespacing.
            tenant_features: Tenant feature flags dict.
            force_refresh: Skip cache and regenerate.

        Returns:
            ClinicalSummaryResponse with 8 structured sections.

        Raises:
            DentalOSError (402): Feature not enabled for tenant's plan.
            ResourceNotFoundError (404): Patient not found.
            DentalOSError (502): Claude API or parsing failure.
        """
        # 1. Check feature gate (Pro+ plan)
        if not tenant_features.get("ai_clinical_summary", True):
            raise DentalOSError(
                error=AIClinicalSummaryErrors.FEATURE_DISABLED,
                message=(
                    "La función de Resumen Clínico AI no está habilitada "
                    "para su plan. Actualice a Pro o superior."
                ),
                status_code=402,
            )

        pid = uuid.UUID(patient_id)
        cache_key = _cache_key(tenant_id, patient_id)

        # 2. Check cache (unless force refresh)
        if not force_refresh:
            cached = await get_cached(cache_key)
            if cached is not None:
                logger.info(
                    "Clinical summary cache hit: patient=%s",
                    patient_id[:8],
                )
                try:
                    response = ClinicalSummaryResponse(**cached)
                    response.cached = True
                    return response
                except Exception:
                    # Corrupted cache entry — regenerate
                    logger.warning(
                        "Corrupted cache entry for clinical summary, regenerating"
                    )

        # 3. Aggregate data from 8 sources in parallel
        (
            demographics,
            odontogram_conditions,
            diagnoses,
            treatment_items,
            appointments,
            evolution_notes,
            financial,
            prescriptions,
        ) = await asyncio.gather(
            _fetch_patient_demographics(db, pid),
            _fetch_odontogram_conditions(db, pid),
            _fetch_active_diagnoses(db, pid),
            _fetch_treatment_plans(db, pid),
            _fetch_appointments(db, pid),
            _fetch_evolution_notes(db, pid),
            _fetch_financial_status(db, pid),
            _fetch_prescriptions(db, pid),
        )

        # 4. Verify patient exists
        if demographics is None:
            raise ResourceNotFoundError(
                error=AIClinicalSummaryErrors.PATIENT_NOT_FOUND,
                resource_name="Patient",
            )

        # 5. Build the prompt
        user_content = _build_user_prompt(
            demographics=demographics,
            odontogram_conditions=odontogram_conditions,
            diagnoses=diagnoses,
            treatment_items=treatment_items,
            appointments=appointments,
            evolution_notes=evolution_notes,
            financial=financial,
            prescriptions=prescriptions,
        )

        # 6. Call Claude Haiku
        try:
            claude_response = await call_claude(
                system_prompt=_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=2048,
                temperature=0.2,
                model_override=_MODEL,
            )
        except Exception:
            logger.exception("Claude API call failed for clinical summary")
            raise DentalOSError(
                error=AIClinicalSummaryErrors.GENERATION_FAILED,
                message=(
                    "No se pudo generar el resumen clínico. "
                    "Intente nuevamente en unos minutos."
                ),
                status_code=502,
            ) from None

        # 7. Parse response
        raw_json = extract_json_object(claude_response["content"])
        if not raw_json:
            logger.warning(
                "Claude returned empty/invalid JSON for clinical summary"
            )
            raise DentalOSError(
                error=AIClinicalSummaryErrors.GENERATION_FAILED,
                message=(
                    "El modelo de IA no generó un resumen válido. "
                    "Intente nuevamente."
                ),
                status_code=502,
            )

        # 8. Build structured response
        sections = _parse_summary_response(
            raw=raw_json,
            demographics=demographics,
            appointments=appointments,
            financial=financial,
            treatment_items=treatment_items,
        )

        now = datetime.now(UTC)
        response = ClinicalSummaryResponse(
            patient_id=patient_id,
            generated_at=now,
            cached=False,
            cached_until=now + timedelta(seconds=_CACHE_TTL),
            model_used=_MODEL,
            sections=sections,
        )

        # 9. Log AI usage
        try:
            usage_log = AIUsageLog(
                doctor_id=uuid.UUID(doctor_id),
                feature="clinical_summary",
                model=_MODEL,
                input_tokens=claude_response["input_tokens"],
                output_tokens=claude_response["output_tokens"],
            )
            db.add(usage_log)
            await db.flush()
        except Exception:
            logger.warning("Failed to log AI usage for clinical summary")

        # 10. Cache the response
        try:
            cache_data = response.model_dump(mode="json")
            await set_cached(cache_key, cache_data, _CACHE_TTL)
        except Exception:
            logger.warning("Failed to cache clinical summary")

        logger.info(
            "Clinical summary generated: patient=%s tokens=%d+%d",
            patient_id[:8],
            claude_response["input_tokens"],
            claude_response["output_tokens"],
        )

        return response

    async def invalidate_cache(
        self,
        *,
        tenant_id: str,
        patient_id: str,
    ) -> None:
        """Invalidate the cached clinical summary for a patient.

        Should be called when patient data changes significantly
        (new diagnosis, treatment update, appointment completion, etc.).
        """
        from app.core.cache import cache_delete

        cache_key = _cache_key(tenant_id, patient_id)
        await cache_delete(cache_key)
        logger.info(
            "Clinical summary cache invalidated: patient=%s",
            patient_id[:8],
        )


# Module-level singleton
clinical_summary_service = ClinicalSummaryService()
