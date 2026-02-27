"""Analytics request/response schemas — AN-01 through AN-07."""
from enum import Enum

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────


class AnalyticsPeriod(str, Enum):
    """Supported analytics time periods."""

    today = "today"
    week = "week"
    month = "month"
    quarter = "quarter"
    year = "year"
    custom = "custom"


class Granularity(str, Enum):
    """Supported aggregation granularities."""

    day = "day"
    week = "week"
    month = "month"


# ─── Shared ──────────────────────────────────────────────────────────────────


class PeriodInfo(BaseModel):
    """Date range metadata included in every analytics response."""

    date_from: str
    date_to: str
    period: str


# ─── AN-01: Dashboard ────────────────────────────────────────────────────────


class PatientStats(BaseModel):
    total: int
    new_in_period: int
    growth_percentage: float


class AppointmentStats(BaseModel):
    today_count: int
    period_total: int
    completed: int
    cancelled: int
    no_show_count: int
    no_show_rate: float


class RevenueStats(BaseModel):
    collected: int  # cents
    growth_percentage: float
    pending_collection: int  # cents


class TopProcedure(BaseModel):
    cups_code: str
    description: str
    count: int


class DoctorOccupancy(BaseModel):
    doctor_id: str
    doctor_name: str
    completed: int
    scheduled: int
    occupancy_rate: float


class DashboardResponse(BaseModel):
    period: PeriodInfo
    patients: PatientStats
    appointments: AppointmentStats
    revenue: RevenueStats
    top_procedures: list[TopProcedure]
    doctor_occupancy: list[DoctorOccupancy]


# ─── AN-02: Patient analytics ────────────────────────────────────────────────


class DemographicBucket(BaseModel):
    label: str
    count: int


class AcquisitionPoint(BaseModel):
    date: str
    count: int


class PatientAnalyticsResponse(BaseModel):
    period: PeriodInfo
    demographics_gender: list[DemographicBucket]
    demographics_age: list[DemographicBucket]
    demographics_city: list[DemographicBucket]
    acquisition_trend: list[AcquisitionPoint]
    retention_rate: float
    total_active: int
    total_inactive: int


# ─── AN-03: Appointment analytics ────────────────────────────────────────────


class UtilizationPoint(BaseModel):
    date: str
    scheduled: int
    completed: int
    cancelled: int
    no_show: int


class PeakHour(BaseModel):
    hour: int
    day_of_week: int
    count: int


class NoShowTrendPoint(BaseModel):
    date: str
    rate: float


class AppointmentAnalyticsResponse(BaseModel):
    period: PeriodInfo
    utilization: list[UtilizationPoint]
    peak_hours: list[PeakHour]
    no_show_trend: list[NoShowTrendPoint]
    average_duration_minutes: float | None


# ─── AN-04: Revenue analytics ────────────────────────────────────────────────


class RevenueTrendPoint(BaseModel):
    date: str
    amount: int  # cents


class RevenueByDoctor(BaseModel):
    doctor_id: str
    doctor_name: str
    amount: int  # cents


class RevenueByProcedure(BaseModel):
    cups_code: str
    description: str
    amount: int  # cents
    count: int


class PaymentMethodBreakdown(BaseModel):
    method: str
    amount: int  # cents
    count: int


class RevenueAnalyticsResponse(BaseModel):
    period: PeriodInfo
    trend: list[RevenueTrendPoint]
    by_doctor: list[RevenueByDoctor]
    by_procedure: list[RevenueByProcedure]
    payment_methods: list[PaymentMethodBreakdown]
    accounts_receivable: int  # cents


# ─── AN-07: Audit trail ──────────────────────────────────────────────────────


class AuditLogEntry(BaseModel):
    id: str
    user_id: str
    user_name: str | None
    resource_type: str
    resource_id: str | None
    action: str
    changes: dict = Field(default_factory=dict)  # PHI masked
    ip_address: str | None
    created_at: str


class AuditTrailResponse(BaseModel):
    items: list[AuditLogEntry]
    next_cursor: str | None
    has_more: bool
