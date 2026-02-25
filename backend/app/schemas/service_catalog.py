"""Service catalog (price list) request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Request Schemas ──────────────────────────────────────────────────────────


class ServiceCatalogUpdate(BaseModel):
    """Fields a clinic can update on a service catalog entry.

    Only name, default_price, category, and is_active are editable.
    cups_code is immutable after creation.
    """

    name: str | None = Field(default=None, max_length=300)
    default_price: int | None = Field(default=None, ge=0)
    category: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError(
                    "El nombre del servicio no puede estar en blanco."
                )
            return stripped
        return v

    @field_validator("category")
    @classmethod
    def strip_category(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


# ─── Response Schemas ─────────────────────────────────────────────────────────


class ServiceCatalogResponse(BaseModel):
    """Full service catalog entry — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    cups_code: str
    name: str
    default_price: int
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceCatalogListResponse(BaseModel):
    """Cursor-paginated list of service catalog entries."""

    items: list[ServiceCatalogResponse]
    next_cursor: str | None = None
    has_more: bool
