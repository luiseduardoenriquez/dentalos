"""Morning Huddle response schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class HuddleAppointment(BaseModel):
    """A single appointment in the huddle."""
    appointment_id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    start_time: datetime
    type: str
    status: str
    no_show_risk: bool = False


class ProductionGoal(BaseModel):
    """Production goal vs actual."""
    daily_goal_cents: int = 0
    daily_actual_cents: int = 0
    weekly_goal_cents: int = 0
    weekly_actual_cents: int = 0
    monthly_goal_cents: int = 0
    monthly_actual_cents: int = 0


class IncompletePlanItem(BaseModel):
    """A treatment plan needing follow-up."""
    treatment_plan_id: str
    patient_id: str
    patient_name: str
    total_cents: int
    remaining_cents: int
    status: str


class OutstandingBalance(BaseModel):
    """A patient with an outstanding balance."""
    patient_id: str
    patient_name: str
    total_balance_cents: int
    oldest_invoice_date: date | None = None


class BirthdayPatient(BaseModel):
    """A patient with a birthday today."""
    patient_id: str
    patient_name: str
    birthdate: date


class RecallDuePatient(BaseModel):
    """A patient due for recall (no visit in 6+ months)."""
    patient_id: str
    patient_name: str
    last_visit_date: date | None = None
    months_since_visit: int


class CollectionSummary(BaseModel):
    """Yesterday's collection summary."""
    total_collected_cents: int = 0
    payment_count: int = 0


class NoShowInfo(BaseModel):
    """No-show statistics."""
    yesterday_no_show_count: int = 0
    today_high_risk_count: int = 0
    today_high_risk_patients: list[HuddleAppointment] = []


class HuddleResponse(BaseModel):
    """Full morning huddle aggregation."""
    date: date
    appointments: list[HuddleAppointment] = []
    production: ProductionGoal
    incomplete_plans: list[IncompletePlanItem] = []
    outstanding_balances: list[OutstandingBalance] = []
    birthdays: list[BirthdayPatient] = []
    recall_due: list[RecallDuePatient] = []
    yesterday_collections: CollectionSummary
    no_shows: NoShowInfo
