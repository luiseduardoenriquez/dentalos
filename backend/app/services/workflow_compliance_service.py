"""GAP-15: AI Workflow Compliance Monitor service.

Runs 7 concurrent SQL checks against the tenant schema to detect
incomplete clinical/administrative workflows. Optionally generates
a Claude narrative summary in Spanish using aggregate counts only
(zero PHI).
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.workflow_compliance import (
    CHECK_SEVERITY,
    CheckSummary,
    WorkflowComplianceResponse,
    WorkflowViolation,
)

logger = logging.getLogger("dentalos.workflow_compliance")

_VIOLATION_LIMIT = 50


class WorkflowComplianceService:
    """Detect incomplete workflows across a tenant schema."""

    async def get_compliance_snapshot(
        self,
        db: AsyncSession,
        tenant_id: str,
        lookback_days: int = 30,
        enable_ai: bool = False,
        tenant_features: dict[str, Any] | None = None,
    ) -> WorkflowComplianceResponse:
        """Run all checks concurrently and build the response."""
        cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

        results = await asyncio.gather(
            self._check_appointment_no_record(db, cutoff),
            self._check_record_no_diagnosis(db, cutoff),
            self._check_record_no_procedure(db, cutoff),
            self._check_plan_consent_unsigned(db),
            self._check_plan_item_overdue(db),
            self._check_lab_order_overdue(db),
            self._check_patient_no_anamnesis(db),
            return_exceptions=True,
        )

        checks: list[CheckSummary] = []
        check_types = list(CHECK_SEVERITY.keys())

        for idx, result in enumerate(results):
            check_type = check_types[idx]
            if isinstance(result, BaseException):
                logger.warning(
                    "Compliance check %s failed: %s", check_type, result
                )
                checks.append(
                    CheckSummary(
                        check_type=check_type,
                        severity=CHECK_SEVERITY[check_type],
                        count=0,
                        violations=[],
                    )
                )
            else:
                checks.append(result)

        total_violations = sum(c.count for c in checks)

        ai_narrative = None
        if enable_ai and total_violations > 0:
            ai_narrative = await self._generate_narrative(checks, lookback_days)

        return WorkflowComplianceResponse(
            tenant_id=tenant_id,
            generated_at=datetime.now(UTC),
            lookback_days=lookback_days,
            total_violations=total_violations,
            checks=checks,
            ai_narrative=ai_narrative,
            ai_enabled=enable_ai,
        )

    # ── Individual checks ────────────────────────────────────────────────

    async def _check_appointment_no_record(
        self, db: AsyncSession, cutoff: datetime
    ) -> CheckSummary:
        """Completed appointments with no clinical record afterwards."""
        from app.models.tenant.appointment import Appointment
        from app.models.tenant.clinical_record import ClinicalRecord

        subq = (
            select(ClinicalRecord.id)
            .where(
                and_(
                    ClinicalRecord.patient_id == Appointment.patient_id,
                    ClinicalRecord.created_at >= Appointment.end_time,
                    ClinicalRecord.is_active.is_(True),
                )
            )
            .correlate(Appointment)
            .exists()
        )

        stmt = (
            select(
                Appointment.id,
                Appointment.patient_id,
                Appointment.doctor_id,
                Appointment.end_time,
            )
            .where(
                and_(
                    Appointment.status == "completed",
                    Appointment.end_time >= cutoff,
                    Appointment.is_active.is_(True),
                    ~subq,
                )
            )
            .order_by(Appointment.end_time.desc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="appointment_no_record",
                severity="high",
                patient_id=r.patient_id,
                reference_id=r.id,
                reference_type="appointment",
                detected_at=now,
                days_overdue=(now - r.end_time).days if r.end_time else None,
                doctor_id=r.doctor_id,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="appointment_no_record",
            severity="high",
            count=len(violations),
            violations=violations,
        )

    async def _check_record_no_diagnosis(
        self, db: AsyncSession, cutoff: datetime
    ) -> CheckSummary:
        """Clinical records with no diagnosis created afterwards."""
        from app.models.tenant.clinical_record import ClinicalRecord
        from app.models.tenant.diagnosis import Diagnosis

        subq = (
            select(Diagnosis.id)
            .where(
                and_(
                    Diagnosis.patient_id == ClinicalRecord.patient_id,
                    Diagnosis.created_at >= ClinicalRecord.created_at,
                    Diagnosis.is_active.is_(True),
                )
            )
            .correlate(ClinicalRecord)
            .exists()
        )

        stmt = (
            select(
                ClinicalRecord.id,
                ClinicalRecord.patient_id,
                ClinicalRecord.doctor_id,
                ClinicalRecord.created_at,
            )
            .where(
                and_(
                    ClinicalRecord.created_at >= cutoff,
                    ClinicalRecord.is_active.is_(True),
                    ~subq,
                )
            )
            .order_by(ClinicalRecord.created_at.desc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="record_no_diagnosis",
                severity="medium",
                patient_id=r.patient_id,
                reference_id=r.id,
                reference_type="clinical_record",
                detected_at=now,
                doctor_id=r.doctor_id,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="record_no_diagnosis",
            severity="medium",
            count=len(violations),
            violations=violations,
        )

    async def _check_record_no_procedure(
        self, db: AsyncSession, cutoff: datetime
    ) -> CheckSummary:
        """Clinical records with no linked procedure."""
        from app.models.tenant.clinical_record import ClinicalRecord
        from app.models.tenant.procedure import Procedure

        subq = (
            select(Procedure.id)
            .where(
                and_(
                    Procedure.clinical_record_id == ClinicalRecord.id,
                    Procedure.is_active.is_(True),
                )
            )
            .correlate(ClinicalRecord)
            .exists()
        )

        stmt = (
            select(
                ClinicalRecord.id,
                ClinicalRecord.patient_id,
                ClinicalRecord.doctor_id,
                ClinicalRecord.created_at,
            )
            .where(
                and_(
                    ClinicalRecord.created_at >= cutoff,
                    ClinicalRecord.is_active.is_(True),
                    ~subq,
                )
            )
            .order_by(ClinicalRecord.created_at.desc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="record_no_procedure",
                severity="medium",
                patient_id=r.patient_id,
                reference_id=r.id,
                reference_type="clinical_record",
                detected_at=now,
                doctor_id=r.doctor_id,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="record_no_procedure",
            severity="medium",
            count=len(violations),
            violations=violations,
        )

    async def _check_plan_consent_unsigned(
        self, db: AsyncSession
    ) -> CheckSummary:
        """Active treatment plans with no signed consent."""
        from app.models.tenant.consent import Consent
        from app.models.tenant.treatment_plan import TreatmentPlan

        subq = (
            select(Consent.id)
            .where(
                and_(
                    Consent.patient_id == TreatmentPlan.patient_id,
                    Consent.status == "signed",
                    Consent.signed_at >= TreatmentPlan.created_at,
                    Consent.is_active.is_(True),
                )
            )
            .correlate(TreatmentPlan)
            .exists()
        )

        stmt = (
            select(
                TreatmentPlan.id,
                TreatmentPlan.patient_id,
                TreatmentPlan.doctor_id,
                TreatmentPlan.created_at,
            )
            .where(
                and_(
                    TreatmentPlan.status == "active",
                    TreatmentPlan.is_active.is_(True),
                    ~subq,
                )
            )
            .order_by(TreatmentPlan.created_at.desc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="plan_consent_unsigned",
                severity="high",
                patient_id=r.patient_id,
                reference_id=r.id,
                reference_type="treatment_plan",
                detected_at=now,
                doctor_id=r.doctor_id,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="plan_consent_unsigned",
            severity="high",
            count=len(violations),
            violations=violations,
        )

    async def _check_plan_item_overdue(self, db: AsyncSession) -> CheckSummary:
        """Pending items on active plans older than 90 days."""
        from app.models.tenant.treatment_plan import TreatmentPlan
        from app.models.tenant.treatment_plan_item import TreatmentPlanItem

        cutoff_90 = datetime.now(UTC) - timedelta(days=90)

        stmt = (
            select(
                TreatmentPlanItem.id,
                TreatmentPlan.patient_id,
                TreatmentPlan.doctor_id,
                TreatmentPlan.created_at,
            )
            .join(
                TreatmentPlan,
                TreatmentPlanItem.treatment_plan_id == TreatmentPlan.id,
            )
            .where(
                and_(
                    TreatmentPlan.status == "active",
                    TreatmentPlan.is_active.is_(True),
                    TreatmentPlanItem.status == "pending",
                    TreatmentPlan.created_at < cutoff_90,
                )
            )
            .order_by(TreatmentPlan.created_at.asc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="plan_item_overdue",
                severity="medium",
                patient_id=r.patient_id,
                reference_id=r.id,
                reference_type="treatment_plan_item",
                detected_at=now,
                days_overdue=(now - r.created_at).days - 90,
                doctor_id=r.doctor_id,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="plan_item_overdue",
            severity="medium",
            count=len(violations),
            violations=violations,
        )

    async def _check_lab_order_overdue(self, db: AsyncSession) -> CheckSummary:
        """Lab orders past due date and not delivered/cancelled."""
        from datetime import date

        from app.models.tenant.lab_order import LabOrder

        today = date.today()

        stmt = (
            select(
                LabOrder.id,
                LabOrder.patient_id,
                LabOrder.created_by,
                LabOrder.due_date,
            )
            .where(
                and_(
                    LabOrder.due_date < today,
                    LabOrder.status.not_in(["delivered", "cancelled"]),
                    LabOrder.is_active.is_(True),
                )
            )
            .order_by(LabOrder.due_date.asc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="lab_order_overdue",
                severity="medium",
                patient_id=r.patient_id,
                reference_id=r.id,
                reference_type="lab_order",
                detected_at=now,
                days_overdue=(today - r.due_date).days if r.due_date else None,
                doctor_id=r.created_by,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="lab_order_overdue",
            severity="medium",
            count=len(violations),
            violations=violations,
        )

    async def _check_patient_no_anamnesis(
        self, db: AsyncSession
    ) -> CheckSummary:
        """Patients with completed appointments but no anamnesis record."""
        from app.models.tenant.anamnesis import Anamnesis
        from app.models.tenant.appointment import Appointment
        from app.models.tenant.patient import Patient

        # Subquery: patient has at least one completed appointment
        has_completed_apt = (
            select(Appointment.id)
            .where(
                and_(
                    Appointment.patient_id == Patient.id,
                    Appointment.status == "completed",
                    Appointment.is_active.is_(True),
                )
            )
            .correlate(Patient)
            .exists()
        )

        # Subquery: patient has anamnesis
        has_anamnesis = (
            select(Anamnesis.id)
            .where(
                and_(
                    Anamnesis.patient_id == Patient.id,
                    Anamnesis.is_active.is_(True),
                )
            )
            .correlate(Patient)
            .exists()
        )

        stmt = (
            select(Patient.id)
            .where(
                and_(
                    Patient.is_active.is_(True),
                    has_completed_apt,
                    ~has_anamnesis,
                )
            )
            .order_by(Patient.created_at.desc())
            .limit(_VIOLATION_LIMIT)
        )

        rows = (await db.execute(stmt)).all()
        now = datetime.now(UTC)
        violations = [
            WorkflowViolation(
                check_type="patient_no_anamnesis",
                severity="low",
                patient_id=r.id,
                detected_at=now,
            )
            for r in rows
        ]
        return CheckSummary(
            check_type="patient_no_anamnesis",
            severity="low",
            count=len(violations),
            violations=violations,
        )

    # ── AI narrative ─────────────────────────────────────────────────────

    async def _generate_narrative(
        self, checks: list[CheckSummary], lookback_days: int
    ) -> str | None:
        """Generate a Spanish narrative from aggregate counts. Fails-open."""
        try:
            from app.services.ai_claude_client import call_claude

            summary_lines = []
            for c in checks:
                if c.count > 0:
                    summary_lines.append(f"- {c.check_type}: {c.count} ({c.severity})")

            if not summary_lines:
                return None

            summary_text = "\n".join(summary_lines)

            result = await call_claude(
                system_prompt=(
                    "Eres un monitor de cumplimiento para una clinica dental. "
                    "Genera un parrafo breve en espanol resumiendo las brechas "
                    "detectadas y sugiriendo acciones prioritarias. No menciones "
                    "nombres de pacientes ni datos personales. Responde solo con "
                    "el parrafo, sin encabezados ni listas."
                ),
                user_content=(
                    f"Periodo de analisis: ultimos {lookback_days} dias.\n"
                    f"Brechas detectadas:\n{summary_text}"
                ),
                max_tokens=512,
                temperature=0.3,
            )
            return result.get("content")
        except Exception:
            logger.warning("AI narrative generation failed, skipping", exc_info=True)
            return None


# Singleton
workflow_compliance_service = WorkflowComplianceService()
