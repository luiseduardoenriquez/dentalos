"""Procedure request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MaterialUsed(BaseModel):
    """A material used during a procedure."""

    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(default=1, ge=1)
    lot_number: str | None = None


class ProcedureCreate(BaseModel):
    """Fields required to record a new procedure."""

    cups_code: str = Field(..., min_length=4, max_length=10)
    cups_description: str = Field(..., min_length=1, max_length=500)
    tooth_number: int | None = None
    zones: dict | None = None
    materials_used: list[MaterialUsed] | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    notes: str | None = None
    treatment_plan_item_id: str | None = None
    clinical_record_id: str | None = None

    @field_validator("cups_code")
    @classmethod
    def validate_cups_format(cls, v: str) -> str:
        import re
        if not re.match(r"^[0-9]{6}$", v.strip()):
            raise ValueError("Código CUPS inválido. Formato esperado: 6 dígitos.")
        return v.strip()


class ProcedureResponse(BaseModel):
    """Full procedure detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    cups_code: str
    cups_description: str
    tooth_number: int | None = None
    zones: dict | None = None
    materials_used: dict | None = None
    duration_minutes: int | None = None
    notes: str | None = None
    treatment_plan_item_id: str | None = None
    clinical_record_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProcedureListResponse(BaseModel):
    """Cursor-paginated list of procedures."""

    items: list[ProcedureResponse]
    next_cursor: str | None = None
    has_more: bool
