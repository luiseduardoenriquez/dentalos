"""AI radiograph analysis request/response schemas (AI-01)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────


class RadiographAnalyzeRequest(BaseModel):
    """Request body to trigger AI radiograph analysis."""

    document_id: str = Field(..., min_length=1, max_length=36)
    radiograph_type: str = Field(
        ...,
        description="Type: periapical, bitewing, panoramic, cephalometric, occlusal",
    )

    @field_validator("radiograph_type")
    @classmethod
    def validate_radiograph_type(cls, v: str) -> str:
        allowed = {"periapical", "bitewing", "panoramic", "cephalometric", "occlusal"}
        if v not in allowed:
            raise ValueError(
                f"Tipo de radiografía inválido. Permitidos: {', '.join(sorted(allowed))}"
            )
        return v


class RadiographReviewItem(BaseModel):
    """A single review decision for one finding."""

    index: int = Field(..., ge=0, description="Finding index in the findings array")
    action: str = Field(..., description="accept, reject, or modify")
    edited_description: str | None = Field(
        default=None,
        description="Modified description (only when action=modify)",
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"accept", "reject", "modify"}
        if v not in allowed:
            raise ValueError(
                f"Acción inválida. Permitidas: {', '.join(sorted(allowed))}"
            )
        return v


class RadiographReviewRequest(BaseModel):
    """Request body to review radiograph analysis findings."""

    items: list[RadiographReviewItem] = Field(..., min_length=1)
    reviewer_notes: str | None = Field(
        default=None, max_length=2000, description="General review notes"
    )


# ── Response schemas ─────────────────────────────────────────────


class RadiographFindingResponse(BaseModel):
    """A single finding in the analysis response."""

    tooth_number: str | None = None
    finding_type: str
    severity: str
    description: str
    location_detail: str | None = None
    confidence: float
    suggested_action: str | None = None
    review_action: str | None = None
    review_note: str | None = None


class RadiographAnalysisResponse(BaseModel):
    """Response for a single radiograph analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    document_id: str
    radiograph_type: str
    status: str
    findings: list[RadiographFindingResponse] | None = None
    summary: str | None = None
    radiograph_quality: str | None = None
    recommendations: str | None = None
    model_used: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: str | None = None
    reviewed_at: datetime | None = None
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RadiographAnalysisListResponse(BaseModel):
    """Paginated list of radiograph analyses."""

    items: list[RadiographAnalysisResponse]
    total: int
    page: int
    page_size: int
