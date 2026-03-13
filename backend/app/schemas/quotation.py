"""Quotation request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuotationItemCreate(BaseModel):
    """Fields for a quotation line item."""

    description: str = Field(..., min_length=1, max_length=500)
    cups_code: str | None = None
    service_id: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: int = Field(..., ge=0)
    discount: int = Field(default=0, ge=0)
    tooth_number: int | None = None
    treatment_plan_item_id: str | None = None


class QuotationItemResponse(BaseModel):
    """Single quotation item detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    quotation_id: str
    service_id: str | None = None
    description: str
    cups_code: str | None = None
    quantity: int
    unit_price: int
    discount: int
    line_total: int
    sort_order: int
    tooth_number: int | None = None
    treatment_plan_item_id: str | None = None
    created_at: datetime
    updated_at: datetime


class QuotationCreate(BaseModel):
    """Fields required to create a new quotation."""

    treatment_plan_id: str | None = None
    items: list[QuotationItemCreate] | None = None
    valid_until: date | None = None
    notes: str | None = None

    @field_validator("items")
    @classmethod
    def validate_items_or_plan(cls, v: list | None, info) -> list | None:
        if v is None and not info.data.get("treatment_plan_id"):
            raise ValueError(
                "Debe proporcionar un treatment_plan_id o items para crear la cotización."
            )
        return v


class QuotationApproveRequest(BaseModel):
    """Request body for approving a quotation."""

    signature_image: str = Field(..., min_length=1)


class QuotationResponse(BaseModel):
    """Full quotation detail with items."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    quotation_number: str
    patient_id: str
    created_by: str
    treatment_plan_id: str | None = None
    subtotal: int
    tax: int
    total: int
    valid_until: date | None = None
    status: str
    notes: str | None = None
    signature_id: str | None = None
    approved_at: datetime | None = None
    invoice_id: str | None = None
    items: list[QuotationItemResponse] = []
    days_until_expiry: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class QuotationListResponse(BaseModel):
    """Paginated list of quotations."""

    items: list[QuotationResponse]
    total: int
    page: int
    page_size: int


class QuotationShareRequest(BaseModel):
    """Request body for sharing a quotation via email or WhatsApp."""

    channel: str = Field(..., pattern=r"^(email|whatsapp)$")
    recipient_email: str | None = Field(
        default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    recipient_phone: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{7,15}$"
    )
    message: str | None = Field(default=None, max_length=500)

    @field_validator("recipient_email")
    @classmethod
    def validate_email_when_email_channel(cls, v: str | None, info) -> str | None:
        if info.data.get("channel") == "email" and not v:
            raise ValueError("Se requiere recipient_email para el canal email.")
        return v

    @field_validator("recipient_phone")
    @classmethod
    def validate_phone_when_whatsapp_channel(cls, v: str | None, info) -> str | None:
        if info.data.get("channel") == "whatsapp" and not v:
            raise ValueError("Se requiere recipient_phone para el canal whatsapp.")
        return v


class QuotationShareResponse(BaseModel):
    """Result of sharing a quotation."""

    shared: bool
    channel: str
    sent_to: str
