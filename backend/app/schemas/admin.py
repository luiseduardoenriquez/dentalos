"""Admin/superadmin request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


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
