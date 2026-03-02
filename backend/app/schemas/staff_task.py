"""Staff task request/response schemas.

Covers GAP-05 (Delinquency) and GAP-06 (Acceptance) task management.
All monetary references use cents (COP). PHI is never stored in these schemas.
"""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StaffTaskCreate(BaseModel):
    """Manual task creation payload."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    task_type: str = Field(
        default="manual",
        pattern=r"^(delinquency|acceptance|manual)$",
    )
    priority: str = Field(
        default="normal",
        pattern=r"^(low|normal|high|urgent)$",
    )
    assigned_to: str | None = None
    patient_id: str | None = None
    due_date: date | None = None


class StaffTaskUpdate(BaseModel):
    """Update task status, assignee, or priority."""

    status: str | None = Field(
        default=None,
        pattern=r"^(open|in_progress|completed|dismissed)$",
    )
    assigned_to: str | None = None
    priority: str | None = Field(
        default=None,
        pattern=r"^(low|normal|high|urgent)$",
    )


class StaffTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    task_type: str
    status: str
    priority: str
    assigned_to: str | None = None
    patient_id: str | None = None
    reference_id: str | None = None
    reference_type: str | None = None
    due_date: date | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class StaffTaskListResponse(BaseModel):
    items: list[StaffTaskResponse]
    total: int
    page: int
    page_size: int


class AcceptanceRateResponse(BaseModel):
    """Quotation acceptance rate analytics (GAP-06)."""

    total_quotations: int
    accepted_count: int
    pending_count: int
    expired_count: int
    # 0.0 to 1.0 — (accepted / total_non_draft)
    acceptance_rate: float
    # None when there are no accepted quotations in the period
    average_days_to_accept: float | None = None
