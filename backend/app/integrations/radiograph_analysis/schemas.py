"""DTOs for radiograph analysis adapter layer (AI-01)."""

from pydantic import BaseModel, Field


class RadiographFinding(BaseModel):
    """A single finding detected in a dental radiograph."""

    tooth_number: str | None = Field(
        default=None,
        description="FDI tooth number (e.g. '11', '46') or null if general finding",
    )
    finding_type: str = Field(
        ...,
        description="Type: caries, bone_loss, periapical_lesion, restoration, "
        "impacted_tooth, root_canal, crown, missing_tooth, calculus, "
        "root_resorption, supernumerary, other",
    )
    severity: str = Field(
        ..., description="Severity: low, medium, high, critical"
    )
    description: str = Field(
        ..., description="Clinical description of the finding"
    )
    location_detail: str | None = Field(
        default=None,
        description="Specific location within the tooth (mesial, distal, occlusal, etc.)",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="AI confidence score 0.0-1.0"
    )
    suggested_action: str | None = Field(
        default=None,
        description="Suggested clinical action (e.g. 'restoration', 'extraction', 'monitoring')",
    )


class AnalysisResult(BaseModel):
    """Complete result from radiograph analysis."""

    findings: list[RadiographFinding] = Field(default_factory=list)
    summary: str = Field(
        ..., description="Overall summary of the radiograph analysis"
    )
    radiograph_quality: str = Field(
        default="adequate",
        description="Image quality assessment: good, adequate, poor",
    )
    recommendations: str | None = Field(
        default=None,
        description="General recommendations based on findings",
    )
    input_tokens: int = Field(default=0, description="Claude API input tokens")
    output_tokens: int = Field(default=0, description="Claude API output tokens")
