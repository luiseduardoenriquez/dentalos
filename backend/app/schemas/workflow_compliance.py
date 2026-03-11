"""Pydantic schemas for the AI Workflow Compliance Monitor (GAP-15).

Defines violation records, per-check summaries, and the top-level
response returned by the compliance snapshot endpoint.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# check_type → severity mapping (single source of truth)
CHECK_SEVERITY: dict[str, str] = {
    "appointment_no_record": "high",
    "record_no_diagnosis": "medium",
    "record_no_procedure": "medium",
    "plan_consent_unsigned": "high",
    "plan_item_overdue": "medium",
    "lab_order_overdue": "medium",
    "patient_no_anamnesis": "low",
}


class WorkflowViolation(BaseModel):
    """A single detected workflow gap."""

    check_type: str
    severity: str
    patient_id: UUID
    reference_id: UUID | None = None
    reference_type: str | None = None
    detected_at: datetime
    days_overdue: int | None = None
    doctor_id: UUID | None = None
    metadata: dict | None = None


class CheckSummary(BaseModel):
    """Aggregated result for one check type."""

    check_type: str
    severity: str
    count: int = 0
    violations: list[WorkflowViolation] = Field(default_factory=list)


class WorkflowComplianceResponse(BaseModel):
    """Top-level response for the compliance snapshot."""

    tenant_id: str
    generated_at: datetime
    lookback_days: int
    total_violations: int
    checks: list[CheckSummary] = Field(default_factory=list)
    ai_narrative: str | None = None
    ai_enabled: bool = False
