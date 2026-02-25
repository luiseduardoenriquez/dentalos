"""Treatment plan request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TreatmentPlanItemCreate(BaseModel):
    """Fields to add an item to a treatment plan."""

    cups_code: str = Field(..., min_length=4, max_length=10)
    cups_description: str = Field(..., min_length=1, max_length=500)
    tooth_number: int | None = None
    estimated_cost: int | None = Field(default=None, ge=0)
    priority_order: int = Field(default=0, ge=0)
    notes: str | None = None


class TreatmentPlanItemUpdate(BaseModel):
    """Fields that can be updated on a plan item."""

    estimated_cost: int | None = Field(default=None, ge=0)
    priority_order: int | None = Field(default=None, ge=0)
    notes: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in {"pending", "scheduled", "completed", "cancelled"}:
            raise ValueError("Estado de item inválido.")
        return v


class TreatmentPlanItemResponse(BaseModel):
    """Single plan item detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    treatment_plan_id: str
    cups_code: str
    cups_description: str
    tooth_number: int | None = None
    estimated_cost: int
    actual_cost: int
    priority_order: int
    status: str
    procedure_id: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class TreatmentPlanCreate(BaseModel):
    """Fields required to create a new treatment plan."""

    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    items: list[TreatmentPlanItemCreate] | None = None
    auto_from_odontogram: bool = False


class TreatmentPlanUpdate(BaseModel):
    """Fields that can be updated on an existing plan."""

    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in {"draft", "active", "completed", "cancelled"}:
            raise ValueError("Estado de plan inválido.")
        return v


class ApprovalRequest(BaseModel):
    """Request body for approving a treatment plan."""

    signature_image: str = Field(..., min_length=1)


class TreatmentPlanResponse(BaseModel):
    """Full treatment plan detail with items."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_id: str
    name: str
    description: str | None = None
    status: str
    total_cost_estimated: int
    total_cost_actual: int
    signature_id: str | None = None
    approved_at: datetime | None = None
    items: list[TreatmentPlanItemResponse] = []
    progress_percent: float = 0.0
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TreatmentPlanListResponse(BaseModel):
    """Paginated list of treatment plans."""

    items: list[TreatmentPlanResponse]
    total: int
    page: int
    page_size: int
