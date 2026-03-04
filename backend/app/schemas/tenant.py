"""Tenant management request/response schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ─── Superadmin: Request Schemas ────────────────────


class TenantCreateRequest(BaseModel):
    """Create a new tenant (superadmin only)."""

    name: str = Field(min_length=1, max_length=200)
    owner_email: EmailStr
    country_code: str = Field(pattern=r"^(CO|MX|CL|AR|PE|EC)$")
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    plan_id: str = Field(description="UUID of the plan to assign")

    @field_validator("owner_email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class TenantUpdateRequest(BaseModel):
    """Update tenant metadata (superadmin only)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    country_code: str | None = Field(default=None, pattern=r"^(CO|MX|CL|AR|PE|EC)$")
    timezone: str | None = Field(default=None, max_length=50)
    currency_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    address: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    plan_id: str | None = Field(default=None, description="UUID of a new plan")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v else v


# ─── Superadmin: Response Schemas ───────────────────


class PlanSummary(BaseModel):
    """Embedded plan info inside tenant detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    max_patients: int
    max_doctors: int
    max_users: int
    max_storage_mb: int
    features: dict[str, Any]
    price_cents: int
    currency: str


class TenantDetailResponse(BaseModel):
    """Full tenant detail (superadmin view)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    schema_name: str
    name: str
    country_code: str
    timezone: str
    currency_code: str
    locale: str
    owner_email: str
    owner_user_id: str | None
    phone: str | None
    address: str | None
    logo_url: str | None
    status: str
    onboarding_step: int
    settings: dict[str, Any]
    plan: PlanSummary
    member_count: int
    trial_ends_at: datetime | None
    suspended_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TenantListItem(BaseModel):
    """Single item in the admin tenants list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    country_code: str
    status: str
    plan_name: str
    owner_email: str
    member_count: int
    created_at: datetime


class TenantListResponse(BaseModel):
    """Paginated list of tenants."""

    items: list[TenantListItem]
    total: int
    page: int
    page_size: int


# ─── Settings: Request/Response Schemas ─────────────


class TenantSettingsResponse(BaseModel):
    """Current tenant settings (clinic_owner view)."""

    name: str
    phone: str | None
    address: str | None
    logo_url: str | None
    timezone: str
    currency_code: str
    country_code: str
    locale: str
    settings: dict[str, Any]


class TenantSettingsUpdate(BaseModel):
    """Updatable subset of tenant settings (clinic_owner)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    address: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=50)
    currency_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    locale: str | None = Field(default=None, max_length=10)
    settings: dict[str, Any] | None = Field(
        default=None,
        description="Partial settings to merge into existing JSONB",
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v else v


# ─── Add-ons ───────────────────────────────────────

ALLOWED_ADDONS = {"voice_dictation", "radiograph_ai"}


class AddonToggleRequest(BaseModel):
    """Toggle an add-on feature for the current tenant."""

    addon: str = Field(description="Add-on key to toggle")
    enabled: bool

    @field_validator("addon")
    @classmethod
    def validate_addon_key(cls, v: str) -> str:
        if v not in ALLOWED_ADDONS:
            raise ValueError(
                f"Invalid add-on: {v}. Allowed: {', '.join(sorted(ALLOWED_ADDONS))}"
            )
        return v


class AddonsResponse(BaseModel):
    """Current add-on state for a tenant."""

    addons: dict[str, bool]


# ─── Plan Usage / Limits ────────────────────────────


class PlanUsageResponse(BaseModel):
    """Current resource usage vs plan limits."""

    current_patients: int
    max_patients: int
    current_doctors: int
    max_doctors: int
    current_users: int
    max_users: int
    current_storage_mb: int
    max_storage_mb: int


class PlanLimitsResponse(BaseModel):
    """Plan limits and feature flags for the current tenant."""

    plan_name: str
    plan_price_monthly_cents: int
    max_patients: int
    max_doctors: int
    max_users: int
    max_storage_mb: int
    features: dict[str, Any]


# ─── Onboarding ─────────────────────────────────────


class OnboardingStepRequest(BaseModel):
    """Submit a single onboarding step."""

    step: int = Field(ge=0, le=4, description="Step number (0-4)")
    data: dict[str, Any] = Field(
        description="Step-specific data to merge into tenant settings"
    )


class OnboardingStepResponse(BaseModel):
    """Response after processing an onboarding step."""

    current_step: int
    completed: bool
    message: str


# ─── Plan Upgrade ──────────────────────────────────────────


class AvailablePlanItem(BaseModel):
    """Single plan available for selection in the upgrade dialog."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    price_cents: int
    currency: str
    pricing_model: str
    included_doctors: int
    max_patients: int
    max_doctors: int
    max_users: int
    max_storage_mb: int
    features: dict[str, Any]
    sort_order: int


class AvailablePlansResponse(BaseModel):
    """List of plans with the current plan identified."""

    current_plan_slug: str
    plans: list[AvailablePlanItem]


class ChangePlanRequest(BaseModel):
    """Request to switch the tenant's subscription plan."""

    plan_id: str = Field(description="UUID of the target plan")


class ChangePlanResponse(BaseModel):
    """Response after a successful plan change."""

    success: bool
    new_plan_name: str
    new_plan_slug: str
    message: str
