"""Voice clinical note request/response schemas (AI-03)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ──────────────────────────────────────────────


class VoiceClinicalNoteStructureRequest(BaseModel):
    """Request to structure a voice transcription into a SOAP note."""

    session_id: str = Field(..., min_length=1, max_length=36)
    template_id: str | None = Field(
        default=None,
        description="Optional evolution template ID to map SOAP sections to",
    )


class VoiceClinicalNoteSaveRequest(BaseModel):
    """Request to save a structured note as a clinical record."""

    edited_note: dict | None = Field(
        default=None,
        description="Doctor-edited structured note (overrides AI output if provided)",
    )


# ── Response schemas ─────────────────────────────────────────────


class SOAPSection(BaseModel):
    """A single SOAP section."""

    title: str
    content: str


class LinkedCode(BaseModel):
    """A linked CIE-10 or CUPS code."""

    code: str
    description: str
    confidence: float = 0.0


class VoiceClinicalNoteResponse(BaseModel):
    """Response for a voice clinical note."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    patient_id: str
    doctor_id: str
    status: str
    input_text: str
    structured_note: dict
    linked_teeth: list[int] | None = None
    linked_cie10_codes: list[LinkedCode] = Field(default_factory=list)
    linked_cups_codes: list[LinkedCode] = Field(default_factory=list)
    template_id: str | None = None
    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: str | None = None
    reviewed_at: datetime | None = None
    clinical_record_id: str | None = None
    created_at: datetime
    updated_at: datetime
