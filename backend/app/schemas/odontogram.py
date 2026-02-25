"""Odontogram request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.odontogram_constants import (
    ALL_ZONES,
    VALID_CONDITION_CODES,
    VALID_DENTITION_TYPES,
    VALID_SEVERITIES,
    VALID_SOURCES,
)


# ─── Request Schemas ──────────────────────────────────────────────────────────


class ConditionCreate(BaseModel):
    """Fields required to record a condition on a single tooth zone."""

    tooth_number: int = Field(ge=11, le=85)
    zone: str
    condition_code: str
    severity: str | None = None
    notes: str | None = Field(default=None, max_length=500)
    source: str = Field(default="manual")

    @field_validator("zone")
    @classmethod
    def validate_zone(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in ALL_ZONES:
            valid = ", ".join(sorted(ALL_ZONES))
            raise ValueError(
                f"Zona inválida '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("condition_code")
    @classmethod
    def validate_condition_code(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_CONDITION_CODES:
            valid = ", ".join(sorted(VALID_CONDITION_CODES))
            raise ValueError(
                f"Código de condición inválido '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if stripped not in VALID_SEVERITIES:
                valid = ", ".join(sorted(VALID_SEVERITIES))
                raise ValueError(
                    f"Severidad inválida '{stripped}'. Valores permitidos: {valid}."
                )
            return stripped
        return v

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_SOURCES:
            valid = ", ".join(sorted(VALID_SOURCES))
            raise ValueError(
                f"Fuente inválida '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped


class BulkConditionUpdate(BaseModel):
    """Batch of condition updates to apply in a single atomic operation."""

    updates: list[ConditionCreate] = Field(min_length=1, max_length=160)
    session_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("session_notes")
    @classmethod
    def strip_session_notes(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


class DentitionToggle(BaseModel):
    """Request to switch the dentition mode for an odontogram."""

    dentition_type: str

    @field_validator("dentition_type")
    @classmethod
    def validate_dentition_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_DENTITION_TYPES:
            valid = ", ".join(sorted(VALID_DENTITION_TYPES))
            raise ValueError(
                f"Tipo de dentición inválido '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped


class SnapshotCreate(BaseModel):
    """Fields for creating a point-in-time snapshot of an odontogram."""

    label: str | None = Field(default=None, max_length=200)
    linked_record_id: str | None = None
    linked_treatment_plan_id: str | None = None

    @field_validator("label")
    @classmethod
    def strip_label(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


# ─── Response Schemas ─────────────────────────────────────────────────────────


class ConditionResponse(BaseModel):
    """Full condition detail — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tooth_number: int
    zone: str
    condition_code: str
    condition_name: str | None = None
    condition_color: str | None = None
    severity: str | None = None
    notes: str | None = None
    source: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ZoneData(BaseModel):
    """Zone state within a single tooth — used in the full odontogram view."""

    zone: str
    condition: ConditionResponse | None = None


class ToothData(BaseModel):
    """All zone states and history count for a single FDI tooth number."""

    tooth_number: int
    zones: list[ZoneData]
    history_count: int = 0


class OdontogramResponse(BaseModel):
    """Full odontogram state for a patient — returned from GET odontogram."""

    patient_id: str
    dentition_type: str
    teeth: list[ToothData]
    total_conditions: int
    last_updated: datetime | None = None


class HistoryEntry(BaseModel):
    """Single audit entry in an odontogram's condition history."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tooth_number: int
    zone: str
    action: str
    condition_code: str
    previous_data: dict | None = None
    new_data: dict | None = None
    performed_by: str | None = None
    performed_by_name: str | None = None
    created_at: datetime


class HistoryListResponse(BaseModel):
    """Cursor-paginated list of odontogram history entries."""

    items: list[HistoryEntry]
    next_cursor: str | None = None
    has_more: bool


class SnapshotResponse(BaseModel):
    """Snapshot metadata — returned from list and create endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    dentition_type: str
    label: str | None = None
    linked_record_id: str | None = None
    linked_treatment_plan_id: str | None = None
    created_by: str | None = None
    created_at: datetime


class SnapshotDetailResponse(SnapshotResponse):
    """Full snapshot response including the serialized odontogram state."""

    snapshot_data: dict


class SnapshotListResponse(BaseModel):
    """Paginated list of odontogram snapshots."""

    items: list[SnapshotResponse]
    total: int


class CompareResponse(BaseModel):
    """Diff result between two odontogram snapshots."""

    snapshot_a_id: str
    snapshot_b_id: str
    added: list[dict]
    removed: list[dict]
    changed: list[dict]


class ConditionUpdateResult(BaseModel):
    """Result for a single condition in a POST condition or bulk operation."""

    condition_id: str
    action: str
    previous_condition: dict | None = None
    history_entry_id: str


class BulkUpdateResult(BaseModel):
    """Aggregated result from a bulk condition update operation."""

    processed: int
    added: int
    updated: int
    results: list[ConditionUpdateResult]


class CatalogConditionItem(BaseModel):
    """Single entry from the conditions catalog — returned from GET catalog."""

    code: str
    name_es: str
    name_en: str
    color_hex: str
    icon: str
    zones: list[str]
    severity_applicable: bool


class CatalogConditionsResponse(BaseModel):
    """Full conditions catalog response."""

    conditions: list[CatalogConditionItem]
