"""Voice-to-odontogram pipeline schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Session Schemas ──────────────────────────────────────────────────────────


class VoiceSessionCreate(BaseModel):
    """Fields required to open a new voice dictation session."""

    patient_id: str
    context: str = Field(
        default="odontogram",
        pattern=r"^(odontogram|evolution|examination)$",
    )


class TranscriptionStatusResponse(BaseModel):
    """Status of a single audio chunk transcription job."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    chunk_index: int
    status: str
    text: str | None = None
    duration_seconds: float | None = None


class VoiceSessionResponse(BaseModel):
    """Full voice session detail including nested transcription statuses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    context: str
    status: str
    expires_at: datetime
    created_at: datetime
    transcriptions: list[TranscriptionStatusResponse] = Field(default_factory=list)


# ─── Audio Upload Schemas ─────────────────────────────────────────────────────


class AudioUploadResponse(BaseModel):
    """Returned after a successful audio chunk upload."""

    transcription_id: str
    session_id: str
    s3_key: str
    status: str


# ─── Parse / Apply Schemas ────────────────────────────────────────────────────


class VoiceFinding(BaseModel):
    """A single odontogram finding extracted from transcribed speech."""

    tooth_number: int
    zone: str
    condition_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str | None = None


class ParseRequest(BaseModel):
    """Trigger NLP parsing on all transcriptions belonging to a session."""

    session_id: str


class ParseResponse(BaseModel):
    """Result of the LLM parsing step — findings ready for doctor review."""

    id: str
    session_id: str
    findings: list[VoiceFinding]
    corrections: list[dict] = Field(default_factory=list)
    filtered_speech: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    llm_model: str
    status: str


class ApplyRequest(BaseModel):
    """Doctor-confirmed findings to commit to the odontogram."""

    session_id: str
    confirmed_findings: list[VoiceFinding]


class ApplyResponse(BaseModel):
    """Summary of the odontogram write operation."""

    applied_count: int
    skipped_count: int
    errors: list[str] = Field(default_factory=list)


# ─── Settings Schemas ─────────────────────────────────────────────────────────


class VoiceSettingsResponse(BaseModel):
    """Current voice feature configuration for a tenant."""

    voice_enabled: bool = False
    max_session_duration_seconds: int = 1800
    max_sessions_per_hour: int = 50


class VoiceSettingsUpdate(BaseModel):
    """Fields that can be updated in the tenant voice configuration."""

    voice_enabled: bool | None = None
    max_session_duration_seconds: int | None = Field(default=None, ge=60, le=3600)
    max_sessions_per_hour: int | None = Field(default=None, ge=1, le=200)
