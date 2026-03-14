"""AI clinical summary response schemas (AI-02)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


# ── Section data models ──────────────────────────────────────────


class PatientSnapshotData(BaseModel):
    age: int | None = None
    gender: str | None = None
    total_visits: int = 0
    last_visit_date: str | None = None
    patient_since: str | None = None


class PatientSnapshotSection(BaseModel):
    title: str = "Resumen del Paciente"
    content: str = ""
    data: PatientSnapshotData = Field(default_factory=PatientSnapshotData)


class TodayContextData(BaseModel):
    appointment_type: str | None = None
    scheduled_time: str | None = None
    doctor_name: str | None = None
    estimated_duration_minutes: int | None = None
    related_teeth: list[str] = Field(default_factory=list)


class TodayContextSection(BaseModel):
    title: str = "Contexto de la Cita de Hoy"
    content: str = ""
    data: TodayContextData = Field(default_factory=TodayContextData)


class ActiveConditionItem(BaseModel):
    diagnosis: str
    cie10_code: str | None = None
    tooth: str | None = None
    severity: str = "low"
    diagnosed_date: str | None = None
    relevant_to_today: bool = False


class ActiveConditionsSection(BaseModel):
    title: str = "Condiciones Activas"
    content: str = ""
    items: list[ActiveConditionItem] = Field(default_factory=list)


class RiskAlert(BaseModel):
    type: str  # allergy, medication_interaction, medical_condition, compliance
    severity: str  # critical, warning, info
    message: str
    recommendation: str = ""


class RiskAlertsSection(BaseModel):
    title: str = "Alertas de Riesgo"
    content: str = ""
    alerts: list[RiskAlert] = Field(default_factory=list)


class PendingTreatmentItem(BaseModel):
    procedure: str
    cups_code: str | None = None
    tooth: str | None = None
    status: str = "pending"
    estimated_cost_cents: int = 0
    planned_for_today: bool = False


class PendingTreatmentsSection(BaseModel):
    title: str = "Tratamientos Pendientes"
    content: str = ""
    items: list[PendingTreatmentItem] = Field(default_factory=list)
    total_pending_cost_cents: int = 0


class LastVisitData(BaseModel):
    date: str | None = None
    procedures_performed: list[str] = Field(default_factory=list)
    notes_excerpt: str | None = None
    doctor_name: str | None = None


class LastVisitSection(BaseModel):
    title: str = "Resumen Última Visita"
    content: str = ""
    data: LastVisitData = Field(default_factory=LastVisitData)


class FinancialStatusData(BaseModel):
    outstanding_balance_cents: int = 0
    last_payment_date: str | None = None
    last_payment_amount_cents: int = 0
    payment_history: str = "unknown"
    has_active_financing: bool = False


class FinancialStatusSection(BaseModel):
    title: str = "Estado Financiero"
    content: str = ""
    data: FinancialStatusData = Field(default_factory=FinancialStatusData)


class ActionSuggestion(BaseModel):
    priority: str  # high, medium, low
    action: str
    category: str  # safety, treatment_planning, financial, follow_up, compliance


class ActionSuggestionsSection(BaseModel):
    title: str = "Sugerencias de Acción"
    content: str = ""
    suggestions: list[ActionSuggestion] = Field(default_factory=list)


class ClinicalSummarySections(BaseModel):
    patient_snapshot: PatientSnapshotSection = Field(
        default_factory=PatientSnapshotSection
    )
    today_context: TodayContextSection = Field(
        default_factory=TodayContextSection
    )
    active_conditions: ActiveConditionsSection = Field(
        default_factory=ActiveConditionsSection
    )
    risk_alerts: RiskAlertsSection = Field(default_factory=RiskAlertsSection)
    pending_treatments: PendingTreatmentsSection = Field(
        default_factory=PendingTreatmentsSection
    )
    last_visit_summary: LastVisitSection = Field(
        default_factory=LastVisitSection
    )
    financial_status: FinancialStatusSection = Field(
        default_factory=FinancialStatusSection
    )
    action_suggestions: ActionSuggestionsSection = Field(
        default_factory=ActionSuggestionsSection
    )


# ── Top-level response ───────────────────────────────────────────


class ClinicalSummaryResponse(BaseModel):
    """Full clinical summary response."""

    patient_id: str
    appointment_id: str | None = None
    generated_at: datetime
    cached: bool = False
    cached_until: datetime | None = None
    model_used: str | None = None
    sections: ClinicalSummarySections
