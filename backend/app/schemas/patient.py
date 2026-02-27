"""Patient request/response schemas."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator


# ─── Shared helpers ───────────────────────────────────────────────────────────


def _compute_dentition_type(birthdate: date | None) -> str | None:
    """Compute pediatric dentition classification from a birthdate.

    adult  — age >= 12
    mixed  — age 6-11
    pediatric — age < 6
    None   — no birthdate provided
    """
    if birthdate is None:
        return None
    today = date.today()
    age = today.year - birthdate.year - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )
    if age >= 12:
        return "adult"
    elif age >= 6:
        return "mixed"
    else:
        return "pediatric"


# ─── Request Schemas ──────────────────────────────────────────────────────────


class PatientCreate(BaseModel):
    """Fields required to register a new patient."""

    document_type: str = Field(
        pattern=r"^(CC|CE|PA|PEP|TI)$",
        description="Colombian document type: CC, CE, PA, PEP, or TI.",
    )
    document_number: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[a-zA-Z0-9\-]+$",
        description="Document identifier — alphanumeric and hyphens only.",
    )
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birthdate: date | None = None
    gender: str | None = Field(default=None, pattern=r"^(male|female|other)$")
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    phone_secondary: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state_province: str | None = Field(default=None, max_length=100)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{7,15}$"
    )
    insurance_provider: str | None = Field(default=None, max_length=100)
    insurance_policy_number: str | None = Field(default=None, max_length=50)
    blood_type: str | None = Field(default=None, pattern=r"^(A|B|AB|O)[+-]$")
    allergies: list[str] | None = None
    chronic_conditions: list[str] | None = None
    referral_source: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be blank or whitespace only.")
        return stripped

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr | None) -> str | None:
        if v is not None:
            return str(v).strip().lower()
        return v

    @field_validator("birthdate")
    @classmethod
    def birthdate_not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Birthdate cannot be in the future.")
        return v

    @field_validator("allergies", "chronic_conditions")
    @classmethod
    def strip_list_strings(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [s.strip() for s in v if s.strip()]
        return v


class PatientUpdate(BaseModel):
    """All patient fields are optional for partial updates.

    Only non-None fields are applied. To explicitly clear an optional
    field (e.g., remove a phone number), send null.
    """

    document_type: str | None = Field(
        default=None,
        pattern=r"^(CC|CE|PA|PEP|TI)$",
    )
    document_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        pattern=r"^[a-zA-Z0-9\-]+$",
    )
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    birthdate: date | None = None
    gender: str | None = Field(default=None, pattern=r"^(male|female|other)$")
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    phone_secondary: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state_province: str | None = Field(default=None, max_length=100)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{7,15}$"
    )
    insurance_provider: str | None = Field(default=None, max_length=100)
    insurance_policy_number: str | None = Field(default=None, max_length=50)
    blood_type: str | None = Field(default=None, pattern=r"^(A|B|AB|O)[+-]$")
    allergies: list[str] | None = None
    chronic_conditions: list[str] | None = None
    referral_source: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field cannot be blank or whitespace only.")
            return stripped
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr | None) -> str | None:
        if v is not None:
            return str(v).strip().lower()
        return v

    @field_validator("birthdate")
    @classmethod
    def birthdate_not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Birthdate cannot be in the future.")
        return v

    @field_validator("allergies", "chronic_conditions")
    @classmethod
    def strip_list_strings(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [s.strip() for s in v if s.strip()]
        return v


# ─── Response Schemas ─────────────────────────────────────────────────────────


class PatientResponse(BaseModel):
    """Full patient detail response — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_type: str
    document_number: str
    first_name: str
    last_name: str
    birthdate: date | None = None
    gender: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    state_province: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    insurance_provider: str | None = None
    insurance_policy_number: str | None = None
    blood_type: str | None = None
    allergies: list[str] | None = None
    chronic_conditions: list[str] | None = None
    referral_source: str | None = None
    notes: str | None = None
    is_active: bool
    deleted_at: datetime | None = None
    no_show_count: int
    portal_access: bool
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    # Computed from birthdate — not stored in DB
    dentition_type: str | None = None

    # Clinical summary stub — populated by service layer
    clinical_summary: dict[str, Any] | None = None

    @computed_field  # type: ignore[misc]
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class PatientListItem(BaseModel):
    """Condensed patient record for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    document_type: str
    document_number: str
    phone: str | None = None
    email: str | None = None
    is_active: bool
    created_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class PatientListResponse(BaseModel):
    """Paginated list of patients."""

    items: list[PatientListItem]
    total: int
    page: int
    page_size: int


class PatientSearchResult(BaseModel):
    """Minimal patient record for type-ahead / search widgets."""

    id: str
    full_name: str
    document_number: str
    phone: str | None = None
    is_active: bool


class PatientSearchResponse(BaseModel):
    """Response envelope for patient search results."""

    data: list[PatientSearchResult]
    count: int
