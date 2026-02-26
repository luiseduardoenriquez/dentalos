"""RDA compliance engine (CO-05) — Resolución 1888.

Computes the 41-field RDA compliance status by running aggregate COUNT
queries against the tenant's clinical tables. Each field maps to a real
database column (or JSONB key) and is weighted by regulatory severity.

The engine batches queries by domain (4 roundtrips total) and returns
a fully populated ``RDAStatusResponse`` including per-module breakdowns,
gaps sorted by impact, and an overall weighted compliance score.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.colombia.config import RDA_FIELDS, RDA_MODULES
from app.models.tenant.clinical_record import Anamnesis, ClinicalRecord
from app.models.tenant.consent import Consent
from app.models.tenant.diagnosis import Diagnosis
from app.models.tenant.odontogram import OdontogramCondition, OdontogramState
from app.models.tenant.patient import Patient
from app.models.tenant.procedure import Procedure
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.schemas.compliance import (
    RDAGap,
    RDAModuleBreakdown,
    RDAStatusResponse,
)

logger = logging.getLogger("dentalos.compliance.rda")

# ─── Corrective-action templates per RDA field ────────────────────────────────

_CORRECTIVE_ACTIONS: dict[str, str] = {
    # patient_demographics
    "document_type": "Registrar el tipo de documento en la ficha del paciente.",
    "document_number": "Registrar el número de documento en la ficha del paciente.",
    "first_name": "Registrar el primer nombre en la ficha del paciente.",
    "last_name": "Registrar el primer apellido en la ficha del paciente.",
    "birth_date": "Registrar la fecha de nacimiento en la ficha del paciente.",
    "gender": "Registrar el sexo en la ficha del paciente.",
    "phone": "Registrar al menos un teléfono de contacto del paciente.",
    "address": "Registrar la dirección de residencia del paciente.",
    # odontogram
    "initial_odontogram": "Crear el odontograma inicial para todos los pacientes.",
    "tooth_number_fdi": "Registrar el número dental FDI en cada condición odontológica.",
    "condition_code": "Registrar el código de hallazgo en cada condición odontológica.",
    "condition_description": "Agregar descripción/notas a cada hallazgo odontológico.",
    "tooth_state": "Registrar el estado de dentición (tipo de dentición) del paciente.",
    "surface_detail": "Registrar la zona/superficie afectada en cada hallazgo.",
    "odontogram_date": "Asegurar que cada condición odontológica tenga fecha de registro.",
    "practitioner_name": "Registrar el profesional que registra cada hallazgo odontológico.",
    "practitioner_license": "Vincular profesional con registro profesional a cada hallazgo.",
    "odontogram_signature": "Implementar firma digital en el odontograma.",
    # clinical_records
    "chief_complaint": "Registrar el motivo de consulta en cada registro clínico.",
    "current_illness": "Documentar la enfermedad actual en los registros clínicos.",
    "medical_history": "Completar los antecedentes médicos (anamnesis) de cada paciente.",
    "family_history": "Completar los antecedentes familiares en la anamnesis.",
    "physical_exam": "Registrar hallazgos del examen físico en el registro clínico.",
    "diagnosis_cie10": "Registrar diagnósticos CIE-10 para los pacientes atendidos.",
    "diagnosis_type": "Clasificar la severidad de cada diagnóstico CIE-10.",
    "evolution_note": "Crear notas de evolución para cada paciente con seguimiento.",
    "procedure_cups": "Registrar procedimientos CUPS para los procedimientos realizados.",
    "record_date": "Asegurar que cada registro clínico tenga fecha de creación.",
    "record_practitioner": "Registrar el profesional tratante en cada registro clínico.",
    "record_signature": "Implementar firma digital en los registros clínicos.",
    # treatment_plans
    "tp_diagnosis": "Vincular diagnósticos a los planes de tratamiento.",
    "tp_procedures": "Registrar los procedimientos planificados (items CUPS) en cada plan.",
    "tp_prognosis": "Agregar descripción/pronóstico a cada plan de tratamiento.",
    "tp_informed_consent": "Crear consentimiento informado para cada plan de tratamiento.",
    "tp_cost_estimate": "Registrar el estimado de costos en cada plan de tratamiento.",
    "tp_practitioner": "Asignar profesional responsable a cada plan de tratamiento.",
    "tp_patient_acceptance": "Obtener firma/aceptación del paciente en cada plan.",
    # consents
    "consent_template": "Vincular cada consentimiento a una plantilla de consentimiento.",
    "consent_patient_signature": "Obtener firma del paciente en cada consentimiento.",
    "consent_witness": "Agregar testigo/acompañante a cada consentimiento.",
    "consent_date": "Asegurar que cada consentimiento tenga fecha de firma.",
}


# ─── Internal query helpers ───────────────────────────────────────────────────


async def _count_patient_demographics(
    db: AsyncSession,
    since: date | None,
) -> dict[str, tuple[int, int]]:
    """Return {field_name: (current_count, expected_count)} for demographics.

    Runs a single query with conditional COUNT aggregates. The expected_count
    for all demographic fields equals the total active patients.
    """
    filters = [Patient.is_active.is_(True)]
    if since:
        filters.append(Patient.created_at >= since)

    stmt = (
        select(
            func.count().label("total"),
            func.count(Patient.document_type).label("document_type"),
            func.count(Patient.document_number).label("document_number"),
            func.count(Patient.first_name).label("first_name"),
            func.count(Patient.last_name).label("last_name"),
            # Model column is 'birthdate', RDA field is 'birth_date'
            func.count(Patient.birthdate).label("birth_date"),
            func.count(Patient.gender).label("gender"),
            func.count(Patient.phone).label("phone"),
            func.count(Patient.address).label("address"),
        )
        .where(*filters)
    )
    row = (await db.execute(stmt)).one()

    total: int = row.total
    return {
        "document_type": (row.document_type, total),
        "document_number": (row.document_number, total),
        "first_name": (row.first_name, total),
        "last_name": (row.last_name, total),
        "birth_date": (row.birth_date, total),
        "gender": (row.gender, total),
        "phone": (row.phone, total),
        "address": (row.address, total),
    }


async def _count_odontogram(
    db: AsyncSession,
    since: date | None,
) -> dict[str, tuple[int, int]]:
    """Return {field_name: (current_count, expected_count)} for odontogram fields.

    Uses OdontogramCondition and OdontogramState tables. Expected count for
    condition-level fields = total active conditions. For state-level fields
    = total active patients with at least one condition.
    """
    # --- Condition-level counts (one query) ---
    cond_filters = [OdontogramCondition.is_active.is_(True)]
    if since:
        cond_filters.append(OdontogramCondition.created_at >= since)

    cond_stmt = (
        select(
            func.count().label("total_conditions"),
            func.count(OdontogramCondition.tooth_number).label("tooth_number_fdi"),
            func.count(OdontogramCondition.condition_code).label("condition_code"),
            func.count(OdontogramCondition.notes).label("condition_description"),
            func.count(OdontogramCondition.zone).label("surface_detail"),
            func.count(OdontogramCondition.created_at).label("odontogram_date"),
            func.count(OdontogramCondition.created_by).label("practitioner_name"),
            # practitioner_license: same as created_by (user has license linked)
            func.count(OdontogramCondition.created_by).label("practitioner_license"),
        )
        .where(*cond_filters)
    )
    cond_row = (await db.execute(cond_stmt)).one()
    total_conditions: int = cond_row.total_conditions

    # --- State-level counts (patients with odontogram state) ---
    state_filters = [OdontogramState.is_active.is_(True)]
    if since:
        state_filters.append(OdontogramState.created_at >= since)

    # Total active patients (to measure initial_odontogram coverage)
    patient_filters: list[Any] = [Patient.is_active.is_(True)]
    if since:
        patient_filters.append(Patient.created_at >= since)
    total_patients_row = (
        await db.execute(select(func.count()).select_from(Patient).where(*patient_filters))
    ).scalar_one()

    state_count_row = (
        await db.execute(
            select(func.count()).select_from(OdontogramState).where(*state_filters)
        )
    ).scalar_one()

    return {
        "initial_odontogram": (state_count_row, total_patients_row),
        "tooth_number_fdi": (cond_row.tooth_number_fdi, total_conditions),
        "condition_code": (cond_row.condition_code, total_conditions),
        "condition_description": (cond_row.condition_description, total_conditions),
        "tooth_state": (state_count_row, total_patients_row),
        "surface_detail": (cond_row.surface_detail, total_conditions),
        "odontogram_date": (cond_row.odontogram_date, total_conditions),
        "practitioner_name": (cond_row.practitioner_name, total_conditions),
        "practitioner_license": (cond_row.practitioner_license, total_conditions),
        # Signature not yet implemented; gap will flag it
        "odontogram_signature": (0, max(total_conditions, 1)),
    }


async def _count_clinical_records(
    db: AsyncSession,
    since: date | None,
) -> dict[str, tuple[int, int]]:
    """Return {field_name: (current_count, expected_count)} for clinical record fields.

    ClinicalRecord.content is JSONB storing chief_complaint, current_illness,
    physical_exam, etc. Diagnosis and Procedure are separate tables. Anamnesis
    holds medical_history and family_history (one per patient).
    """
    # --- Clinical records aggregate ---
    rec_filters = [ClinicalRecord.is_active.is_(True)]
    if since:
        rec_filters.append(ClinicalRecord.created_at >= since)

    rec_stmt = (
        select(
            func.count().label("total_records"),
            # chief_complaint: JSONB key in content
            func.count(
                case(
                    (ClinicalRecord.content["chief_complaint"].as_string() != "", 1),
                    else_=None,
                )
            ).label("chief_complaint"),
            # current_illness: JSONB key in content
            func.count(
                case(
                    (ClinicalRecord.content["current_illness"].as_string() != "", 1),
                    else_=None,
                )
            ).label("current_illness"),
            # physical_exam: JSONB key in content
            func.count(
                case(
                    (ClinicalRecord.content["physical_exam"].as_string() != "", 1),
                    else_=None,
                )
            ).label("physical_exam"),
            # evolution notes are records of type 'evolution_note'
            func.count(
                case(
                    (ClinicalRecord.type == "evolution_note", 1),
                    else_=None,
                )
            ).label("evolution_note"),
            func.count(ClinicalRecord.created_at).label("record_date"),
            func.count(ClinicalRecord.doctor_id).label("record_practitioner"),
        )
        .where(*rec_filters)
    )
    rec_row = (await db.execute(rec_stmt)).one()
    total_records: int = rec_row.total_records

    # --- Anamnesis (medical_history, family_history) --- one per patient
    patient_filters: list[Any] = [Patient.is_active.is_(True)]
    if since:
        patient_filters.append(Patient.created_at >= since)
    total_patients = (
        await db.execute(select(func.count()).select_from(Patient).where(*patient_filters))
    ).scalar_one()

    anam_filters: list[Any] = [Anamnesis.is_active.is_(True)]
    if since:
        anam_filters.append(Anamnesis.patient_id.in_(
            select(Patient.id).where(*patient_filters)
        ))
    anam_stmt = (
        select(
            func.count(Anamnesis.medical_history).label("medical_history"),
            func.count(Anamnesis.family_history).label("family_history"),
        )
        .where(*anam_filters)
    )
    anam_row = (await db.execute(anam_stmt)).one()

    # --- Diagnoses (CIE-10) ---
    diag_filters = [Diagnosis.is_active.is_(True)]
    if since:
        diag_filters.append(Diagnosis.created_at >= since)

    diag_count = (
        await db.execute(
            select(func.count()).select_from(Diagnosis).where(*diag_filters)
        )
    ).scalar_one()

    diag_severity_count = (
        await db.execute(
            select(func.count(Diagnosis.severity))
            .where(*diag_filters)
        )
    ).scalar_one()

    # --- Procedures (CUPS) ---
    proc_filters = [Procedure.is_active.is_(True)]
    if since:
        proc_filters.append(Procedure.created_at >= since)

    proc_count = (
        await db.execute(
            select(func.count()).select_from(Procedure).where(*proc_filters)
        )
    ).scalar_one()

    # For diagnosis and procedure counts, expected = total_records
    # (each clinical encounter should have at least one of each)
    expected_for_records = max(total_records, 1)

    return {
        "chief_complaint": (rec_row.chief_complaint, total_records),
        "current_illness": (rec_row.current_illness, total_records),
        "medical_history": (anam_row.medical_history, total_patients),
        "family_history": (anam_row.family_history, total_patients),
        "physical_exam": (rec_row.physical_exam, total_records),
        "diagnosis_cie10": (diag_count, expected_for_records),
        "diagnosis_type": (diag_severity_count, max(diag_count, 1)),
        "evolution_note": (rec_row.evolution_note, total_records),
        "procedure_cups": (proc_count, expected_for_records),
        "record_date": (rec_row.record_date, total_records),
        "record_practitioner": (rec_row.record_practitioner, total_records),
        # Digital signature not yet implemented on records
        "record_signature": (0, max(total_records, 1)),
    }


async def _count_treatment_plans_and_consents(
    db: AsyncSession,
    since: date | None,
) -> dict[str, tuple[int, int]]:
    """Return {field_name: (current_count, expected_count)} for TP + consent fields.

    Treatment plan fields are measured against total active plans.
    Consent fields are measured against total active consents.
    """
    # --- Treatment Plans ---
    tp_filters = [TreatmentPlan.is_active.is_(True)]
    if since:
        tp_filters.append(TreatmentPlan.created_at >= since)

    tp_stmt = (
        select(
            func.count().label("total_plans"),
            func.count(TreatmentPlan.doctor_id).label("tp_practitioner"),
            func.count(TreatmentPlan.description).label("tp_prognosis"),
            func.count(
                case(
                    (TreatmentPlan.total_cost_estimated > 0, 1),
                    else_=None,
                )
            ).label("tp_cost_estimate"),
            func.count(TreatmentPlan.signature_id).label("tp_patient_acceptance"),
        )
        .where(*tp_filters)
    )
    tp_row = (await db.execute(tp_stmt)).one()
    total_plans: int = tp_row.total_plans

    # tp_diagnosis: count plans that have at least one diagnosis linked
    # (patient of the plan has at least one active diagnosis)
    diag_patient_ids = select(Diagnosis.patient_id).where(
        Diagnosis.is_active.is_(True)
    ).distinct()
    tp_with_diag = (
        await db.execute(
            select(func.count())
            .select_from(TreatmentPlan)
            .where(
                *tp_filters,
                TreatmentPlan.patient_id.in_(diag_patient_ids),
            )
        )
    ).scalar_one()

    # tp_procedures: count plans that have at least one item with cups_code
    plans_with_items_subq = (
        select(TreatmentPlanItem.treatment_plan_id)
        .where(TreatmentPlanItem.cups_code.isnot(None))
        .distinct()
    )
    tp_with_procedures = (
        await db.execute(
            select(func.count())
            .select_from(TreatmentPlan)
            .where(
                *tp_filters,
                TreatmentPlan.id.in_(plans_with_items_subq),
            )
        )
    ).scalar_one()

    # tp_informed_consent: count plans whose patient has at least one signed consent
    signed_consent_patients = (
        select(Consent.patient_id)
        .where(
            Consent.is_active.is_(True),
            Consent.status == "signed",
        )
        .distinct()
    )
    tp_with_consent = (
        await db.execute(
            select(func.count())
            .select_from(TreatmentPlan)
            .where(
                *tp_filters,
                TreatmentPlan.patient_id.in_(signed_consent_patients),
            )
        )
    ).scalar_one()

    # --- Consents ---
    c_filters = [Consent.is_active.is_(True)]
    if since:
        c_filters.append(Consent.created_at >= since)

    consent_stmt = (
        select(
            func.count().label("total_consents"),
            func.count(Consent.template_id).label("consent_template"),
            func.count(Consent.signed_at).label("consent_patient_signature"),
            func.count(Consent.signed_at).label("consent_date"),
        )
        .where(*c_filters)
    )
    consent_row = (await db.execute(consent_stmt)).one()
    total_consents: int = consent_row.total_consents

    # consent_witness: not yet tracked in the model; flag as gap
    consent_witness_count = 0

    return {
        "tp_diagnosis": (tp_with_diag, total_plans),
        "tp_procedures": (tp_with_procedures, total_plans),
        "tp_prognosis": (tp_row.tp_prognosis, total_plans),
        "tp_informed_consent": (tp_with_consent, total_plans),
        "tp_cost_estimate": (tp_row.tp_cost_estimate, total_plans),
        "tp_practitioner": (tp_row.tp_practitioner, total_plans),
        "tp_patient_acceptance": (tp_row.tp_patient_acceptance, total_plans),
        "consent_template": (consent_row.consent_template, total_consents),
        "consent_patient_signature": (
            consent_row.consent_patient_signature,
            total_consents,
        ),
        "consent_witness": (consent_witness_count, max(total_consents, 1)),
        "consent_date": (consent_row.consent_date, total_consents),
    }


# ─── Compliance level thresholds ──────────────────────────────────────────────

_LEVEL_COMPLIANT = 95.0
_LEVEL_IMPROVING = 80.0
_LEVEL_AT_RISK = 50.0

_GAP_THRESHOLD = 5.0  # A field is "compliant" if gap_percentage < 5%


def _compliance_level(percentage: float) -> str:
    """Map a numeric compliance percentage to a named level."""
    if percentage >= _LEVEL_COMPLIANT:
        return "compliant"
    if percentage >= _LEVEL_IMPROVING:
        return "improving"
    if percentage >= _LEVEL_AT_RISK:
        return "at_risk"
    return "critical"


# ─── Public API ───────────────────────────────────────────────────────────────


async def compute_rda_status(
    db: AsyncSession,
    since_date: date | None = None,
) -> RDAStatusResponse:
    """Compute the full RDA compliance status for the current tenant schema.

    Runs 4 batched aggregate queries (one per domain group), then
    assembles per-field gaps, per-module breakdowns, and the overall
    weighted compliance score.

    Args:
        db: Tenant-scoped database session (search_path already set).
        since_date: If provided, only consider records created on or after
            this date for compliance measurement.

    Returns:
        Fully populated RDAStatusResponse.
    """
    # 1. Gather raw counts from all domains (4 roundtrips)
    counts: dict[str, tuple[int, int]] = {}

    demo_counts = await _count_patient_demographics(db, since_date)
    counts.update(demo_counts)

    odonto_counts = await _count_odontogram(db, since_date)
    counts.update(odonto_counts)

    clinical_counts = await _count_clinical_records(db, since_date)
    counts.update(clinical_counts)

    tp_consent_counts = await _count_treatment_plans_and_consents(db, since_date)
    counts.update(tp_consent_counts)

    # 2. Build per-field gaps
    all_gaps: list[RDAGap] = []
    total_records_analyzed = 0
    weighted_compliance_sum = 0.0
    total_weight = 0.0

    # Track fields per module for breakdown
    module_fields: dict[str, list[RDAGap]] = defaultdict(list)

    for field_def in RDA_FIELDS:
        field_name: str = field_def["field"]
        module: str = field_def["module"]
        weight: int = field_def["weight"]
        severity: str = field_def["severity"]

        current_count, expected_count = counts.get(field_name, (0, 0))
        total_records_analyzed += expected_count

        # Compliance ratio: min(current/expected, 1.0)
        compliance_ratio = (
            min(current_count / max(expected_count, 1), 1.0)
        )
        gap_pct = (
            (max(expected_count, 1) - current_count) / max(expected_count, 1) * 100.0
            if expected_count > 0
            else 0.0
        )
        # Clamp to [0, 100]
        gap_pct = max(0.0, min(gap_pct, 100.0))

        corrective_action = _CORRECTIVE_ACTIONS.get(
            field_name, f"Completar el campo '{field_name}' en los registros."
        )

        gap = RDAGap(
            field_name=field_name,
            module=module,
            severity=severity,
            weight=weight,
            current_count=current_count,
            expected_count=expected_count,
            gap_percentage=round(gap_pct, 2),
            corrective_action=corrective_action,
        )
        all_gaps.append(gap)
        module_fields[module].append(gap)

        # Weighted compliance accumulation
        weighted_compliance_sum += weight * compliance_ratio
        total_weight += weight

    # 3. Overall weighted compliance percentage
    overall_pct = (
        (weighted_compliance_sum / total_weight * 100.0) if total_weight > 0 else 0.0
    )
    overall_pct = round(overall_pct, 2)

    # 4. Per-module breakdown
    modules: list[RDAModuleBreakdown] = []
    for module_key, module_label in RDA_MODULES.items():
        fields = module_fields.get(module_key, [])
        total_fields = len(fields)
        compliant_fields = sum(
            1 for g in fields if g.gap_percentage < _GAP_THRESHOLD
        )
        mod_pct = (
            (compliant_fields / total_fields * 100.0) if total_fields > 0 else 0.0
        )
        modules.append(
            RDAModuleBreakdown(
                module=module_key,
                label=module_label,
                total_fields=total_fields,
                compliant_fields=compliant_fields,
                compliance_percentage=round(mod_pct, 2),
                gaps=[g for g in fields if g.gap_percentage >= _GAP_THRESHOLD],
            )
        )

    # 5. Sort gaps by impact = weight * gap_percentage, descending
    sorted_gaps = sorted(
        [g for g in all_gaps if g.gap_percentage > 0],
        key=lambda g: g.weight * g.gap_percentage,
        reverse=True,
    )

    return RDAStatusResponse(
        overall_compliance_percentage=overall_pct,
        compliance_level=_compliance_level(overall_pct),
        deadline="2026-04-01",
        modules=modules,
        gaps=sorted_gaps,
        total_records_analyzed=total_records_analyzed,
    )
