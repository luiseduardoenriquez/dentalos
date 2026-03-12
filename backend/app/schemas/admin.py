"""Admin/superadmin request and response schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Auth Schemas ─────────────────────────────────────


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    name: str
    totp_required: bool = False


class AdminTOTPSetupRequest(BaseModel):
    pass


class AdminTOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str | None = None


class AdminTOTPVerifyRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


# ─── Tenant Management Schemas ────────────────────────


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    plan_name: str
    status: str
    user_count: int
    patient_count: int
    created_at: str


class TenantListResponse(BaseModel):
    items: list[TenantSummary]
    total: int
    page: int
    page_size: int


class TenantDetailResponse(BaseModel):
    id: str
    name: str
    slug: str
    schema_name: str
    owner_email: str
    owner_user_id: str | None = None
    country_code: str
    timezone: str
    currency_code: str
    locale: str
    plan_id: str
    plan_name: str
    status: str
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None
    onboarding_step: int
    settings: dict
    addons: dict
    trial_ends_at: str | None = None
    suspended_at: str | None = None
    cancelled_at: str | None = None
    user_count: int
    created_at: str
    updated_at: str


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    owner_email: EmailStr
    plan_id: str
    country_code: str = Field(default="CO", min_length=2, max_length=2)
    timezone: str = Field(default="America/Bogota", max_length=50)
    currency_code: str = Field(default="COP", min_length=3, max_length=3)

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.strip().upper()


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    plan_id: str | None = None
    settings: dict | None = None
    is_active: bool | None = None


# ─── Plan Management Schemas ─────────────────────────


class PlanResponse(BaseModel):
    id: str
    name: str
    slug: str
    price_cents: int
    max_patients: int
    max_doctors: int
    features: dict
    is_active: bool


class PlanUpdateRequest(BaseModel):
    price_cents: int | None = None
    max_patients: int | None = None
    max_doctors: int | None = None
    features: dict | None = None
    is_active: bool | None = None


# ─── Analytics Schemas ────────────────────────────────


class PlatformAnalyticsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    total_patients: int
    mrr_cents: int
    mau: int
    churn_rate: float


# ─── Feature Flag Schemas ────────────────────────────


class FeatureFlagResponse(BaseModel):
    id: str
    flag_name: str
    scope: str | None = None
    plan_filter: str | None = None
    tenant_id: str | None = None
    enabled: bool
    description: str | None = None


class FeatureFlagUpdateRequest(BaseModel):
    enabled: bool | None = None
    scope: str | None = None
    plan_filter: str | None = None
    tenant_id: str | None = None
    description: str | None = None


class FeatureFlagCreateRequest(BaseModel):
    flag_name: str = Field(min_length=1, max_length=100)
    enabled: bool = False
    scope: str | None = None
    plan_filter: str | None = None
    tenant_id: str | None = None
    description: str | None = None


# ─── System Health Schemas ────────────────────────────


class SystemHealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool
    rabbitmq: bool
    storage: bool
    timestamp: str


# ─── Impersonation Schemas ────────────────────────────


class ImpersonateRequest(BaseModel):
    pass


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    impersonated_as: str = "clinic_owner"
