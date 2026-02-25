"""Prescription request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MedicationItem(BaseModel):
    """A single medication in a prescription."""

    name: str = Field(..., min_length=1, max_length=200)
    dosis: str = Field(..., min_length=1, max_length=100)
    frecuencia: str = Field(..., min_length=1, max_length=100)
    duracion_dias: int = Field(..., ge=1, le=365)
    via: str = Field(default="oral", max_length=30)
    instrucciones: str | None = None


class PrescriptionCreate(BaseModel):
    """Fields required to create a new prescription."""

    medications: list[MedicationItem] = Field(..., min_length=1, max_length=20)
    diagnosis_id: str | None = None
    notes: str | None = None


class PrescriptionResponse(BaseModel):
    """Full prescription detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    medications: list[dict]
    diagnosis_id: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PrescriptionListResponse(BaseModel):
    """Paginated list of prescriptions."""

    items: list[PrescriptionResponse]
    total: int
    page: int
    page_size: int
