"""Clinical record request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Request Schemas ──────────────────────────────────────────────────────────

_VALID_RECORD_TYPES: frozenset[str] = frozenset(
    {"examination", "evolution_note", "procedure"}
)


class ClinicalRecordCreate(BaseModel):
    """Fields required to create a new clinical record entry."""

    type: str
    content: dict
    tooth_numbers: list[int] | None = None
    template_id: str | None = None
    template_variables: dict | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped == "anamnesis":
            raise ValueError(
                "El tipo 'anamnesis' no se puede crear aquí. "
                "Use el endpoint dedicado /patients/{id}/anamnesis."
            )
        if stripped not in _VALID_RECORD_TYPES:
            valid = ", ".join(sorted(_VALID_RECORD_TYPES))
            raise ValueError(
                f"Tipo de registro inválido '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("El contenido del registro no puede estar vacío.")
        return v


class ClinicalRecordUpdate(BaseModel):
    """Fields that can be updated on an existing clinical record."""

    content: dict | None = None
    tooth_numbers: list[int] | None = None

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: dict | None) -> dict | None:
        if v is not None and not v:
            raise ValueError("El contenido del registro no puede estar vacío.")
        return v


# ─── Response Schemas ─────────────────────────────────────────────────────────


class ClinicalRecordResponse(BaseModel):
    """Full clinical record detail — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    doctor_name: str | None = None
    type: str
    content: dict
    tooth_numbers: list[int] | None = None
    template_id: str | None = None
    is_editable: bool
    edit_locked_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClinicalRecordListItem(BaseModel):
    """Condensed clinical record for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    doctor_name: str | None = None
    tooth_numbers: list[int] | None = None
    is_editable: bool
    created_at: datetime


class ClinicalRecordListResponse(BaseModel):
    """Paginated list of clinical records."""

    items: list[ClinicalRecordListItem]
    total: int
    page: int
    page_size: int


# ─── Anamnesis Schemas ────────────────────────────────────────────────────────


class AnamnesisCreate(BaseModel):
    """Fields for creating or replacing a patient's medical anamnesis.

    All sections are optional — only provided sections are updated.
    Each section is a free-form JSONB dict to accommodate varying clinic
    templates without forcing a rigid schema at the API layer.
    """

    allergies: dict | None = None
    medications: dict | None = None
    medical_history: dict | None = None
    dental_history: dict | None = None
    family_history: dict | None = None
    habits: dict | None = None


class AnamnesisResponse(BaseModel):
    """Full anamnesis response — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    allergies: dict | None = None
    medications: dict | None = None
    medical_history: dict | None = None
    dental_history: dict | None = None
    family_history: dict | None = None
    habits: dict | None = None
    last_updated_by: str | None = None
    created_at: datetime
    updated_at: datetime
