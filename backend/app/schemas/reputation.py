"""Reputation management schemas — VP-09.

Pydantic v2 request/response models for satisfaction surveys,
reputation dashboard, and feedback listing.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────────────────


class SurveyCreate(BaseModel):
    """Request body for sending a satisfaction survey."""

    appointment_id: UUID
    channel: str = Field(
        default="whatsapp",
        pattern=r"^(whatsapp|sms|email)$",
        description="Channel to send the survey through.",
    )


class SurveyPublicResponse(BaseModel):
    """Public-facing survey response (used by the patient, no auth)."""

    score: int = Field(ge=1, le=5, description="Satisfaction score from 1 to 5.")
    feedback_text: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text feedback from the patient.",
    )


# ── Response schemas ─────────────────────────────────────────────────────────


class SurveyResponse(BaseModel):
    """Full survey details returned to staff."""

    id: str
    patient_id: str
    appointment_id: str | None = None
    score: int | None = None
    feedback_text: str | None = None
    channel_sent: str | None = None
    survey_token: str
    routed_to: str | None = None
    sent_at: datetime | None = None
    responded_at: datetime | None = None
    created_at: datetime


class DashboardResponse(BaseModel):
    """Aggregated reputation dashboard metrics."""

    average_score: float = Field(description="Average satisfaction score (1-5).")
    total_surveys: int = Field(description="Total surveys sent.")
    response_rate: float = Field(description="Percentage of surveys that received a response.")
    nps_score: float = Field(description="Net Promoter Score: (promoters - detractors) / total * 100.")
    review_count: int = Field(description="Number of responses routed to Google Reviews.")
    private_feedback_count: int = Field(description="Number of responses routed to private feedback.")


class FeedbackListResponse(BaseModel):
    """Paginated list of private feedback surveys."""

    items: list[SurveyResponse]
    total: int
    page: int
    page_size: int
