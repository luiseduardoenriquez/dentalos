"""Periodontal charting request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Constants ───────────────────────────────────────────────────────────────

VALID_PERIO_SITES: frozenset[str] = frozenset({
    "mesial_buccal",
    "buccal",
    "distal_buccal",
    "mesial_lingual",
    "lingual",
    "distal_lingual",
})

_VALID_DENTITION_TYPES: frozenset[str] = frozenset({"adult", "pediatric", "mixed"})
_VALID_SOURCES: frozenset[str] = frozenset({"manual", "voice"})


# ─── Request Schemas ─────────────────────────────────────────────────────────


class MeasurementInput(BaseModel):
    """A single periodontal measurement at one site of one tooth."""

    tooth_number: int = Field(ge=11, le=85)
    site: str
    pocket_depth: int | None = None
    recession: int | None = None
    clinical_attachment_level: int | None = None
    bleeding_on_probing: bool | None = None
    plaque_index: bool | None = None
    mobility: int | None = Field(default=None, ge=0, le=3)
    furcation: int | None = Field(default=None, ge=0, le=3)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_PERIO_SITES:
            valid = ", ".join(sorted(VALID_PERIO_SITES))
            raise ValueError(
                f"Sitio periodontal invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped


class RecordCreate(BaseModel):
    """Fields required to create a new periodontal charting record."""

    dentition_type: str = Field(default="adult")
    source: str = Field(default="manual")
    notes: str | None = Field(default=None, max_length=2000)
    measurements: list[MeasurementInput] = Field(min_length=1, max_length=192)

    @field_validator("dentition_type")
    @classmethod
    def validate_dentition_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in _VALID_DENTITION_TYPES:
            valid = ", ".join(sorted(_VALID_DENTITION_TYPES))
            raise ValueError(
                f"Tipo de denticion invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in _VALID_SOURCES:
            valid = ", ".join(sorted(_VALID_SOURCES))
            raise ValueError(
                f"Fuente invalida '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


# ─── Response Schemas ────────────────────────────────────────────────────────


class MeasurementResponse(BaseModel):
    """Full measurement detail -- returned within a record response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tooth_number: int
    site: str
    pocket_depth: int | None = None
    recession: int | None = None
    clinical_attachment_level: int | None = None
    bleeding_on_probing: bool | None = None
    plaque_index: bool | None = None
    mobility: int | None = None
    furcation: int | None = None


class RecordResponse(BaseModel):
    """Full periodontal record with measurements."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    recorded_by: str
    dentition_type: str
    source: str
    notes: str | None = None
    measurements: list[MeasurementResponse]
    created_at: datetime
    updated_at: datetime


class RecordListItem(BaseModel):
    """Condensed periodontal record for list views (no measurements)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    recorded_by: str
    dentition_type: str
    source: str
    measurement_count: int
    created_at: datetime


class RecordListResponse(BaseModel):
    """Paginated list of periodontal records."""

    items: list[RecordListItem]
    total: int
    page: int
    page_size: int


# ─── Comparison Schemas ──────────────────────────────────────────────────────


class ComparisonDelta(BaseModel):
    """Delta between two measurements at the same (tooth, site) pair."""

    tooth_number: int
    site: str
    pocket_depth_delta: int | None = None
    recession_delta: int | None = None
    cal_delta: int | None = None
    status: str  # improved / worsened / unchanged


class ComparisonResponse(BaseModel):
    """Result of comparing two periodontal records."""

    record_a_id: str
    record_b_id: str
    record_a_date: datetime
    record_b_date: datetime
    deltas: list[ComparisonDelta]
