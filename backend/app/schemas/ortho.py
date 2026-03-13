"""Orthodontics request/response schemas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Constants ───────────────────────────────────────────────────────────────

VALID_STATUSES: frozenset[str] = frozenset({
    "planning", "bonding", "active_treatment", "retention", "completed", "cancelled",
})

VALID_ANGLE_CLASSES: frozenset[str] = frozenset({
    "class_i", "class_ii_div1", "class_ii_div2", "class_iii",
})

VALID_APPLIANCE_TYPES: frozenset[str] = frozenset({
    "brackets", "aligners", "mixed",
})

VALID_BRACKET_STATUSES: frozenset[str] = frozenset({
    "pending", "bonded", "removed", "not_applicable",
})

VALID_BRACKET_TYPES: frozenset[str] = frozenset({
    "metalico", "ceramico", "autoligado", "lingual",
})

VALID_PAYMENT_STATUSES: frozenset[str] = frozenset({
    "pending", "paid", "waived",
})

# Status transitions: current_status -> allowed_next_statuses
VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "planning": frozenset({"bonding", "cancelled"}),
    "bonding": frozenset({"active_treatment", "cancelled"}),
    "active_treatment": frozenset({"retention", "cancelled"}),
    "retention": frozenset({"completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _strip_or_none(v: str | None) -> str | None:
    if v is not None:
        stripped = v.strip()
        return stripped if stripped else None
    return v


# ─── OrthoCase Schemas ──────────────────────────────────────────────────────


class OrthoCaseCreate(BaseModel):
    """Fields required to create a new orthodontic case."""

    appliance_type: str
    angle_class: str | None = None
    malocclusion_type: str | None = Field(default=None, max_length=100)
    treatment_plan_id: str | None = None
    estimated_duration_months: int | None = Field(default=None, ge=1, le=120)
    total_cost_estimated: int = Field(default=0, ge=0)
    initial_payment: int = Field(default=0, ge=0)
    monthly_payment: int = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("appliance_type")
    @classmethod
    def validate_appliance_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_APPLIANCE_TYPES:
            valid = ", ".join(sorted(VALID_APPLIANCE_TYPES))
            raise ValueError(
                f"Tipo de aparatologia invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("angle_class")
    @classmethod
    def validate_angle_class(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if stripped not in VALID_ANGLE_CLASSES:
            valid = ", ".join(sorted(VALID_ANGLE_CLASSES))
            raise ValueError(
                f"Clase de Angle invalida '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("malocclusion_type", "notes")
    @classmethod
    def strip_optional_text(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class OrthoCaseUpdate(BaseModel):
    """Fields that can be updated on an existing case."""

    angle_class: str | None = None
    malocclusion_type: str | None = None
    appliance_type: str | None = None
    estimated_duration_months: int | None = Field(default=None, ge=1, le=120)
    total_cost_estimated: int | None = Field(default=None, ge=0)
    initial_payment: int | None = Field(default=None, ge=0)
    monthly_payment: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("appliance_type")
    @classmethod
    def validate_appliance_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if stripped not in VALID_APPLIANCE_TYPES:
            valid = ", ".join(sorted(VALID_APPLIANCE_TYPES))
            raise ValueError(
                f"Tipo de aparatologia invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("angle_class")
    @classmethod
    def validate_angle_class(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if stripped not in VALID_ANGLE_CLASSES:
            valid = ", ".join(sorted(VALID_ANGLE_CLASSES))
            raise ValueError(
                f"Clase de Angle invalida '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("malocclusion_type", "notes")
    @classmethod
    def strip_optional_text(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class TransitionRequest(BaseModel):
    """Request body for transitioning a case status."""

    target_status: str

    @field_validator("target_status")
    @classmethod
    def validate_target_status(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_STATUSES:
            valid = ", ".join(sorted(VALID_STATUSES))
            raise ValueError(
                f"Estado invalido '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped


class OrthoCaseResponse(BaseModel):
    """Full orthodontic case detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    treatment_plan_id: str | None = None
    case_number: str
    status: str
    angle_class: str | None = None
    malocclusion_type: str | None = None
    appliance_type: str
    estimated_duration_months: int | None = None
    actual_start_date: date | None = None
    actual_end_date: date | None = None
    total_cost_estimated: int
    initial_payment: int
    monthly_payment: int
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrthoCaseListItem(BaseModel):
    """Condensed case for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_number: str
    status: str
    appliance_type: str
    doctor_id: str
    total_cost_estimated: int
    visit_count: int
    created_at: datetime


class OrthoCaseListResponse(BaseModel):
    """Paginated list of orthodontic cases."""

    items: list[OrthoCaseListItem]
    total: int
    page: int
    page_size: int


# ─── Bonding Record Schemas ────────────────────────────────────────────────


class BondingToothInput(BaseModel):
    """Per-tooth bracket data for a bonding record."""

    tooth_number: int = Field(ge=11, le=48)
    bracket_status: str
    bracket_type: str | None = None
    slot_size: str | None = Field(default=None, max_length=10)
    wire_type: str | None = Field(default=None, max_length=50)
    band: bool = False
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("bracket_status")
    @classmethod
    def validate_bracket_status(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in VALID_BRACKET_STATUSES:
            valid = ", ".join(sorted(VALID_BRACKET_STATUSES))
            raise ValueError(
                f"Estado de bracket invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("bracket_type")
    @classmethod
    def validate_bracket_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if stripped not in VALID_BRACKET_TYPES:
            valid = ", ".join(sorted(VALID_BRACKET_TYPES))
            raise ValueError(
                f"Tipo de bracket invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class BondingRecordCreate(BaseModel):
    """Create a new bonding record with per-tooth data."""

    notes: str | None = Field(default=None, max_length=2000)
    teeth: list[BondingToothInput] = Field(min_length=1, max_length=32)

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class BondingToothResponse(BaseModel):
    """Per-tooth bracket state in a bonding record response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tooth_number: int
    bracket_status: str
    bracket_type: str | None = None
    slot_size: str | None = None
    wire_type: str | None = None
    band: bool
    notes: str | None = None


class BondingRecordResponse(BaseModel):
    """Full bonding record with teeth."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    ortho_case_id: str
    recorded_by: str
    notes: str | None = None
    teeth: list[BondingToothResponse]
    created_at: datetime
    updated_at: datetime


class BondingRecordListItem(BaseModel):
    """Condensed bonding record for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    recorded_by: str
    tooth_count: int
    created_at: datetime


class BondingRecordListResponse(BaseModel):
    """Paginated list of bonding records."""

    items: list[BondingRecordListItem]
    total: int
    page: int
    page_size: int


# ─── Visit Schemas ──────────────────────────────────────────────────────────


class OrthoVisitCreate(BaseModel):
    """Fields required to create a new ortho visit."""

    visit_date: date
    wire_upper: str | None = Field(default=None, max_length=50)
    wire_lower: str | None = Field(default=None, max_length=50)
    elastics: str | None = Field(default=None, max_length=200)
    adjustments: str | None = Field(default=None, max_length=5000)
    next_visit_date: date | None = None
    payment_amount: int | None = None
    notes: str | None = None

    @field_validator("wire_upper", "wire_lower", "elastics", "adjustments", "notes")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class OrthoVisitUpdate(BaseModel):
    """Fields that can be updated on a visit."""

    wire_upper: str | None = None
    wire_lower: str | None = None
    elastics: str | None = None
    adjustments: str | None = None
    next_visit_date: date | None = None
    payment_status: str | None = None
    payment_amount: int | None = Field(default=None, ge=0)

    @field_validator("payment_status")
    @classmethod
    def validate_payment_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if stripped not in VALID_PAYMENT_STATUSES:
            valid = ", ".join(sorted(VALID_PAYMENT_STATUSES))
            raise ValueError(
                f"Estado de pago invalido '{stripped}'. "
                f"Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("wire_upper", "wire_lower", "elastics", "adjustments")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class OrthoVisitResponse(BaseModel):
    """Full visit detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    ortho_case_id: str
    visit_number: int
    doctor_id: str
    visit_date: date
    wire_upper: str | None = None
    wire_lower: str | None = None
    elastics: str | None = None
    adjustments: str | None = None
    next_visit_date: date | None = None
    payment_status: str
    payment_amount: int
    payment_id: str | None = None
    created_at: datetime
    updated_at: datetime


class OrthoVisitListResponse(BaseModel):
    """Paginated list of visits."""

    items: list[OrthoVisitResponse]
    total: int
    page: int
    page_size: int


# ─── Material Schemas ───────────────────────────────────────────────────────


class MaterialCreate(BaseModel):
    """Add a material consumption record."""

    inventory_item_id: str
    visit_id: str | None = None
    quantity_used: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        return _strip_or_none(v)


class MaterialResponse(BaseModel):
    """Material consumption record response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    ortho_case_id: str
    visit_id: str | None = None
    inventory_item_id: str
    quantity_used: float
    notes: str | None = None
    created_by: str
    created_at: datetime


class MaterialListResponse(BaseModel):
    """Paginated list of material records."""

    items: list[MaterialResponse]
    total: int
    page: int
    page_size: int


# ─── Summary Schema ─────────────────────────────────────────────────────────


class OrthoCaseSummary(BaseModel):
    """Aggregated statistics for a case."""

    case_id: str
    status: str
    total_visits: int
    visits_paid: int
    visits_pending: int
    total_collected: int  # cents COP
    total_expected: int  # cents COP (initial + monthly * visits)
    balance_remaining: int  # cents COP
    materials_count: int
    last_visit_date: date | None = None
    next_visit_date: date | None = None
