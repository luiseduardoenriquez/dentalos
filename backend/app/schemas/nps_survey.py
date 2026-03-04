"""NPS/CSAT survey schemas — VP-21.

Pydantic v2 request/response models for NPS/CSAT surveys,
NPS dashboard aggregation, and per-doctor breakdowns.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Request schemas ──────────────────────────────────────────────────────────


class NPSSurveySubmission(BaseModel):
    """Payload for a patient submitting their NPS/CSAT survey response.

    nps_score: 0-10 (NPS standard). 0-6 = detractor, 7-8 = passive, 9-10 = promoter.
    csat_score: 1-5 (optional supplementary satisfaction score).
    comments: optional free-text from the patient (max 2000 chars).
    """

    nps_score: int = Field(
        ge=0,
        le=10,
        description="NPS score from 0 to 10.",
    )
    csat_score: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Optional CSAT score from 1 to 5.",
    )
    comments: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text feedback from the patient.",
    )

    @model_validator(mode="after")
    def strip_comments(self) -> "NPSSurveySubmission":
        if self.comments is not None:
            self.comments = self.comments.strip() or None
        return self


class NPSSurveySendRequest(BaseModel):
    """Request body for staff to trigger sending an NPS survey to a patient."""

    patient_id: UUID
    doctor_id: UUID
    appointment_id: UUID | None = None
    channel: str = Field(
        default="whatsapp",
        pattern=r"^(whatsapp|sms|email)$",
        description="Channel to send the survey through.",
    )


# ── Response schemas ─────────────────────────────────────────────────────────


class NPSSurveyResponse(BaseModel):
    """Full NPS survey record returned to staff."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    appointment_id: UUID | None = None
    doctor_id: UUID | None = None
    nps_score: int | None = None
    csat_score: int | None = None
    comments: str | None = None
    channel_sent: str
    sent_at: datetime
    responded_at: datetime | None = None


class NPSTrendItem(BaseModel):
    """A single data point in the NPS trend series."""

    period: str = Field(description="Period label, e.g. '2026-01'.")
    nps_score: float = Field(description="NPS score for this period.")
    responses: int = Field(description="Number of responses in this period.")


class NPSDashboardResponse(BaseModel):
    """Aggregated NPS/CSAT dashboard metrics."""

    nps_score: float = Field(
        description="Net Promoter Score: (promoters% - detractors%). Range -100 to 100."
    )
    promoters: int = Field(description="Count of promoters (NPS 9-10).")
    passives: int = Field(description="Count of passives (NPS 7-8).")
    detractors: int = Field(description="Count of detractors (NPS 0-6).")
    total_responses: int = Field(description="Total responded surveys.")
    trend: list[NPSTrendItem] = Field(
        description="Monthly NPS trend, most recent last.",
    )


class NPSByDoctorItem(BaseModel):
    """NPS breakdown for a single doctor."""

    doctor_id: str
    doctor_name: str
    nps_score: float
    promoters: int
    passives: int
    detractors: int
    total: int


class NPSByDoctorResponse(BaseModel):
    """NPS breakdown per doctor."""

    items: list[NPSByDoctorItem]


class NPSSurveyListResponse(BaseModel):
    """Paginated list of NPS survey responses."""

    items: list[NPSSurveyResponse]
    total: int
    page: int
    page_size: int


class NPSSurveyPublicInfo(BaseModel):
    """Public-facing survey metadata shown to the patient before they respond."""

    doctor_name: str
    clinic_name: str
    already_responded: bool = False
