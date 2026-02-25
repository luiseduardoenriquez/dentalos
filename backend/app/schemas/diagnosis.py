"""Diagnosis request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosisCreate(BaseModel):
    """Fields required to create a new diagnosis."""

    cie10_code: str = Field(..., min_length=3, max_length=10)
    cie10_description: str = Field(..., min_length=1, max_length=500)
    severity: str = Field(default="moderate")
    tooth_number: int | None = None
    notes: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"mild", "moderate", "severe"}
        if v not in allowed:
            raise ValueError(f"Severidad inválida. Valores permitidos: {', '.join(sorted(allowed))}.")
        return v

    @field_validator("cie10_code")
    @classmethod
    def validate_cie10_format(cls, v: str) -> str:
        import re
        if not re.match(r"^[A-Z][0-9]{2}(\.[0-9]{1,4})?$", v.strip()):
            raise ValueError("Código CIE-10 inválido. Formato esperado: X00 o X00.0")
        return v.strip()


class DiagnosisUpdate(BaseModel):
    """Fields that can be updated on an existing diagnosis."""

    severity: str | None = None
    notes: str | None = None
    status: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in {"mild", "moderate", "severe"}:
            raise ValueError("Severidad inválida.")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in {"active", "resolved"}:
            raise ValueError("Estado inválido.")
        return v


class DiagnosisResponse(BaseModel):
    """Full diagnosis detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    cie10_code: str
    cie10_description: str
    severity: str
    status: str
    tooth_number: int | None = None
    notes: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DiagnosisListResponse(BaseModel):
    """List of diagnoses (not paginated — < 50 per patient)."""

    items: list[DiagnosisResponse]
    total: int
