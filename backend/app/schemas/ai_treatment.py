"""AI treatment suggestion request/response schemas (VP-13)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────


class AITreatmentSuggestRequest(BaseModel):
    """Request body to generate AI treatment suggestions.

    Only the patient_id is required; the service gathers all clinical
    context (odontogram conditions, medical history, catalog) server-side.
    """

    patient_id: str = Field(..., min_length=1, max_length=36)


class ReviewItemAction(BaseModel):
    """A single review decision for one suggestion item."""

    cups_code: str = Field(..., min_length=4, max_length=10)
    action: str = Field(..., description="accept, modify, or reject")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"accept", "modify", "reject"}
        if v not in allowed:
            raise ValueError(f"Acción inválida. Permitidas: {', '.join(sorted(allowed))}")
        return v


class AITreatmentReviewRequest(BaseModel):
    """Request body to review AI treatment suggestions."""

    items: list[ReviewItemAction] = Field(..., min_length=1)


# ── Response schemas ─────────────────────────────────────────────


class SuggestionItem(BaseModel):
    """A single AI-generated treatment suggestion."""

    cups_code: str
    cups_description: str
    tooth_number: str | None = None
    rationale: str
    confidence: str = Field(description="high, medium, or low")
    priority_order: int
    estimated_cost: int = Field(description="Amount in COP cents")
    action: str | None = Field(
        default=None,
        description="Set after review: accept, modify, or reject",
    )


class AITreatmentSuggestResponse(BaseModel):
    """Response after generating or retrieving AI treatment suggestions."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    suggestions: list[SuggestionItem]
    model_used: str
    status: str
    input_tokens: int
    output_tokens: int
    reviewed_at: datetime | None = None
    treatment_plan_id: str | None = None
    created_at: datetime


class AITreatmentUsageResponse(BaseModel):
    """Token usage statistics for AI treatment suggestions."""

    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    period_from: str
    period_to: str


class AITreatmentPlanCreatedResponse(BaseModel):
    """Response after converting accepted suggestions into a treatment plan."""

    suggestion_id: str
    treatment_plan_id: str
    items_created: int
    status: str
