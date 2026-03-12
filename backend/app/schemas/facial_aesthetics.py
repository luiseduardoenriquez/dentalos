"""Facial aesthetics request/response schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Valid values ────────────────────────────────────────────────────────────

VALID_DIAGRAM_TYPES = {"face_front", "face_lateral_left", "face_lateral_right"}

VALID_INJECTION_TYPES = {
    "botulinum_toxin",
    "hyaluronic_acid",
    "calcium_hydroxylapatite",
    "poly_lactic_acid",
    "prf",
    "other",
}

VALID_DEPTHS = {"intradermal", "subcutaneous", "supraperiosteal", "intramuscular"}

VALID_ZONES = {
    "forehead_left",
    "forehead_center",
    "forehead_right",
    "glabella",
    "temporal_left",
    "temporal_right",
    "periorbital_left",
    "periorbital_right",
    "infraorbital_left",
    "infraorbital_right",
    "nose_bridge",
    "nose_tip",
    "nasolabial_left",
    "nasolabial_right",
    "cheek_left",
    "cheek_right",
    "lip_upper",
    "lip_lower",
    "marionette_left",
    "marionette_right",
    "masseter_left",
    "masseter_right",
    "chin",
    "jaw_left",
    "jaw_right",
    "neck_left",
    "neck_center",
    "neck_right",
}


# ─── Request Schemas ──────────────────────────────────────────────────────────


class SessionCreate(BaseModel):
    """Fields required to create a facial aesthetics session."""

    diagram_type: str = Field(default="face_front")
    session_date: date
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("diagram_type")
    @classmethod
    def validate_diagram_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_DIAGRAM_TYPES:
            valid = ", ".join(sorted(VALID_DIAGRAM_TYPES))
            raise ValueError(
                f"Tipo de diagrama inválido '{stripped}'. Valores permitidos: {valid}."
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


class SessionUpdate(BaseModel):
    """Fields for updating an existing session."""

    diagram_type: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("diagram_type")
    @classmethod
    def validate_diagram_type(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if stripped not in VALID_DIAGRAM_TYPES:
                valid = ", ".join(sorted(VALID_DIAGRAM_TYPES))
                raise ValueError(
                    f"Tipo de diagrama inválido '{stripped}'. Valores permitidos: {valid}."
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


class InjectionCreate(BaseModel):
    """Fields required to record an injection point."""

    zone_id: str
    injection_type: str
    product_name: str | None = Field(default=None, max_length=100)
    dose_units: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    dose_volume_ml: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    depth: str | None = None
    coordinates_x: Decimal | None = Field(default=None, ge=0, le=1)
    coordinates_y: Decimal | None = Field(default=None, ge=0, le=1)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("zone_id")
    @classmethod
    def validate_zone_id(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_ZONES:
            valid = ", ".join(sorted(VALID_ZONES))
            raise ValueError(
                f"Zona inválida '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("injection_type")
    @classmethod
    def validate_injection_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_INJECTION_TYPES:
            valid = ", ".join(sorted(VALID_INJECTION_TYPES))
            raise ValueError(
                f"Tipo de inyección inválido '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if stripped not in VALID_DEPTHS:
                valid = ", ".join(sorted(VALID_DEPTHS))
                raise ValueError(
                    f"Profundidad inválida '{stripped}'. Valores permitidos: {valid}."
                )
            return stripped
        return v

    @field_validator("product_name", "notes")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


class InjectionUpdate(BaseModel):
    """Fields for updating an existing injection."""

    injection_type: str | None = None
    product_name: str | None = Field(default=None, max_length=100)
    dose_units: Decimal | None = Field(default=None, ge=0)
    dose_volume_ml: Decimal | None = Field(default=None, ge=0)
    depth: str | None = None
    coordinates_x: Decimal | None = Field(default=None, ge=0, le=1)
    coordinates_y: Decimal | None = Field(default=None, ge=0, le=1)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("injection_type")
    @classmethod
    def validate_injection_type(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if stripped not in VALID_INJECTION_TYPES:
                valid = ", ".join(sorted(VALID_INJECTION_TYPES))
                raise ValueError(
                    f"Tipo de inyección inválido '{stripped}'. Valores permitidos: {valid}."
                )
            return stripped
        return v

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if stripped not in VALID_DEPTHS:
                valid = ", ".join(sorted(VALID_DEPTHS))
                raise ValueError(
                    f"Profundidad inválida '{stripped}'. Valores permitidos: {valid}."
                )
            return stripped
        return v

    @field_validator("product_name", "notes")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


class SnapshotCreate(BaseModel):
    """Fields for creating a facial aesthetics snapshot."""

    label: str | None = Field(default=None, max_length=200)
    linked_record_id: str | None = None

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


class InjectionResponse(BaseModel):
    """Full injection detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    patient_id: str
    zone_id: str
    injection_type: str
    product_name: str | None = None
    dose_units: float | None = None
    dose_volume_ml: float | None = None
    depth: str | None = None
    coordinates_x: float | None = None
    coordinates_y: float | None = None
    notes: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionResponse(BaseModel):
    """Session metadata returned from list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    diagram_type: str
    session_date: date
    notes: str | None = None
    injection_count: int = 0
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(BaseModel):
    """Full session detail including all injections."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    diagram_type: str
    session_date: date
    notes: str | None = None
    injections: list[InjectionResponse]
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    items: list[SessionResponse]
    total: int
    page: int
    page_size: int


class HistoryEntry(BaseModel):
    """Single audit entry in a facial aesthetics history."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    zone_id: str
    action: str
    injection_type: str
    previous_data: dict | None = None
    new_data: dict | None = None
    performed_by: str | None = None
    performed_by_name: str | None = None
    created_at: datetime


class HistoryListResponse(BaseModel):
    """Cursor-paginated list of history entries."""

    items: list[HistoryEntry]
    next_cursor: str | None = None
    has_more: bool


class SnapshotResponse(BaseModel):
    """Snapshot metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    session_id: str | None = None
    diagram_type: str
    label: str | None = None
    linked_record_id: str | None = None
    created_by: str | None = None
    created_at: datetime


class SnapshotDetailResponse(SnapshotResponse):
    """Full snapshot including data payload."""

    snapshot_data: dict


class SnapshotListResponse(BaseModel):
    """List of snapshots."""

    items: list[SnapshotResponse]
    total: int
