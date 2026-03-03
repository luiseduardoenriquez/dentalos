"""Schedule Intelligence request/response schemas — VP-10.

Provides risk scoring, gap analysis, utilization metrics, and
fill suggestions for the clinic's daily appointment schedule.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── No-Show Risk ─────────────────────────────────────────────────────────────


class NoShowRisk(BaseModel):
    """Predicted no-show risk for a single confirmed/scheduled appointment."""

    patient_id: UUID
    patient_name: str = Field(
        ..., description="Display name (first + last). Never logged."
    )
    appointment_id: UUID
    risk_score: int = Field(
        ..., ge=0, le=100, description="Weighted no-show probability (0-100)."
    )
    risk_level: str = Field(
        ...,
        pattern=r"^(low|medium|high)$",
        description="low (0-30), medium (31-60), high (61-100).",
    )
    factors: dict = Field(
        default_factory=dict,
        description="Breakdown of contributing risk factors and their scores.",
    )


# ── Gap Analysis ─────────────────────────────────────────────────────────────


class GapAnalysis(BaseModel):
    """An unfilled time slot within a doctor's working hours."""

    slot_start: datetime
    slot_end: datetime
    doctor_id: UUID
    doctor_name: str
    suggested_patients: list[dict] = Field(
        default_factory=list,
        description=(
            "Candidate patients to fill this gap. Each dict contains "
            "patient_id (str), name (str), reason ('waitlist' | 'recall' | 'reschedule')."
        ),
    )


# ── Suggested Fill ───────────────────────────────────────────────────────────


class SuggestedFill(BaseModel):
    """A concrete fill suggestion pairing a gap with a patient."""

    slot_start: datetime
    slot_end: datetime
    doctor_id: UUID
    patient_id: UUID
    patient_name: str
    reason: str = Field(
        ...,
        description="Why this patient is suggested: waitlist, recall, or reschedule.",
    )
    contact_info: str | None = Field(
        default=None,
        description="Patient phone number for quick outreach (masked in logs).",
    )


# ── Utilization Metric ───────────────────────────────────────────────────────


class UtilizationMetric(BaseModel):
    """Chair-time utilization for a single doctor on a given date."""

    doctor_id: UUID
    doctor_name: str
    date: date
    completed_minutes: int = Field(
        ..., ge=0, description="Sum of duration_minutes for completed appointments."
    )
    available_minutes: int = Field(
        ..., ge=0, description="Total working minutes minus breaks."
    )
    utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="completed / available * 100."
    )


# ── Intelligence Response ────────────────────────────────────────────────────


class IntelligenceResponse(BaseModel):
    """Aggregated schedule intelligence for a target date."""

    date: date
    no_show_risks: list[NoShowRisk] = Field(default_factory=list)
    gaps: list[GapAnalysis] = Field(default_factory=list)
    utilization: list[UtilizationMetric] = Field(default_factory=list)
    overbooking_suggestions: list[dict] = Field(
        default_factory=list,
        description="Future: slots where double-booking may be safe based on no-show risk.",
    )


# ── Suggested Fills Response (paginated) ─────────────────────────────────────


class SuggestedFillsResponse(BaseModel):
    """Paginated list of fill suggestions."""

    items: list[SuggestedFill] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total suggestions available.")
