"""Patient import, export, and merge request/response schemas."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


# ─── CSV Import Row ──────────────────────────────────────────────────────────


class PatientCSVRow(BaseModel):
    """Validates a single row from a patient CSV import file.

    Field names correspond to the expected CSV column headers (Spanish).
    Validation mirrors the constraints on the Patient model to catch
    errors before touching the database.
    """

    tipo_documento: str = Field(
        description="Document type code: CC, TI, CE, PA, RC, or NIT.",
    )
    numero_documento: str = Field(
        description="Document number — 6 to 12 digits.",
    )
    nombres: str = Field(
        min_length=1,
        max_length=100,
        description="Patient first name(s).",
    )
    apellidos: str = Field(
        min_length=1,
        max_length=100,
        description="Patient last name(s).",
    )
    fecha_nacimiento: date | None = Field(
        default=None,
        description="Birthdate in YYYY-MM-DD format.",
    )
    genero: str | None = Field(
        default=None,
        description="Gender: male, female, or other.",
    )
    email: str | None = Field(
        default=None,
        max_length=255,
        description="Email address.",
    )
    telefono: str | None = Field(
        default=None,
        description="Phone number in LATAM format.",
    )
    ciudad: str | None = Field(
        default=None,
        max_length=100,
        description="City name.",
    )

    @field_validator("tipo_documento")
    @classmethod
    def validate_tipo_documento(cls, v: str) -> str:
        v = v.strip().upper()
        allowed = {"CC", "TI", "CE", "PA", "RC", "NIT"}
        if v not in allowed:
            raise ValueError(
                f"tipo_documento must be one of {sorted(allowed)}, got '{v}'."
            )
        return v

    @field_validator("numero_documento")
    @classmethod
    def validate_numero_documento(cls, v: str) -> str:
        import re

        v = v.strip()
        if not re.match(r"^[0-9]{6,12}$", v):
            raise ValueError(
                "numero_documento must contain 6 to 12 digits only."
            )
        return v

    @field_validator("nombres", "apellidos")
    @classmethod
    def strip_names(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be blank or whitespace only.")
        return stripped

    @field_validator("telefono")
    @classmethod
    def validate_telefono(cls, v: str | None) -> str | None:
        import re

        if v is not None:
            v = v.strip()
            if v and not re.match(r"^\+?[0-9]{7,15}$", v):
                raise ValueError(
                    "telefono must match format: +?[0-9]{7,15}."
                )
            if not v:
                return None
        return v

    @field_validator("genero")
    @classmethod
    def validate_genero(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip().lower()
            if v and v not in ("male", "female", "other"):
                raise ValueError(
                    "genero must be 'male', 'female', or 'other'."
                )
            if not v:
                return None
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip().lower()
            if not v:
                return None
        return v

    @field_validator("fecha_nacimiento")
    @classmethod
    def birthdate_not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("fecha_nacimiento cannot be in the future.")
        return v


# ─── Import Job Response ─────────────────────────────────────────────────────


class PatientImportJobResponse(BaseModel):
    """Response for import job creation and status polling."""

    job_id: str
    status: str = Field(
        description="Job status: queued, processing, completed, or failed.",
    )
    total_rows: int | None = None
    processed_rows: int | None = None
    error_rows: int | None = None
    error_csv_url: str | None = None
    created_at: str


# ─── Patient Merge ───────────────────────────────────────────────────────────


class PatientMergeRequest(BaseModel):
    """Request to merge two patient records.

    The secondary patient's clinical records are transferred to the
    primary patient, and the secondary patient is deactivated.
    """

    primary_patient_id: uuid.UUID = Field(
        description="UUID of the patient that will receive all records.",
    )
    secondary_patient_id: uuid.UUID = Field(
        description="UUID of the patient to be merged and deactivated.",
    )

    @field_validator("secondary_patient_id")
    @classmethod
    def patients_must_differ(cls, v: uuid.UUID, info) -> uuid.UUID:
        if info.data.get("primary_patient_id") == v:
            raise ValueError(
                "primary_patient_id and secondary_patient_id must be different."
            )
        return v


class PatientMergeResponse(BaseModel):
    """Response after a successful patient merge."""

    primary_patient_id: str
    merged_records: dict[str, int] = Field(
        description="Count of records transferred per table.",
    )
    deactivated_secondary: bool


# ─── Export Params ───────────────────────────────────────────────────────────


class PatientExportParams(BaseModel):
    """Query parameters for patient CSV export."""

    is_active: bool | None = None
    created_from: date | None = None
    created_to: date | None = None
