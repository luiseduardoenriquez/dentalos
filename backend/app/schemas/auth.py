"""Auth request/response schemas."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ─── Request Schemas ─────────────────────────────────


def _validate_password_strength(v: str) -> str:
    """Shared password strength validator."""
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    clinic_name: str = Field(min_length=1, max_length=200)
    country: str = Field(pattern=r"^(CO|MX|CL|AR|PE|EC)$")
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("name", "clinic_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class SelectTenantRequest(BaseModel):
    pre_auth_token: str
    tenant_id: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern=r"^(doctor|assistant|receptionist)$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class VerifyEmailRequest(BaseModel):
    token: str


# ─── Response Schemas ────────────────────────────────


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: str
    phone: str | None = None
    avatar_url: str | None = None
    professional_license: str | None = None
    specialties: list[str] | None = None
    is_active: bool
    email_verified: bool


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    country_code: str
    timezone: str
    currency_code: str
    status: str
    plan_name: str
    logo_url: str | None = None


class TenantListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    tenant_name: str
    tenant_slug: str
    role: str
    is_primary: bool


class LoginSuccessResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    tenant: TenantResponse


class LoginMultiTenantResponse(BaseModel):
    requires_tenant_selection: bool = True
    pre_auth_token: str
    tenants: list[TenantListItem]
    message: str = "Please select a clinic to continue."


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PlanLimits(BaseModel):
    max_patients: int
    max_doctors: int
    max_users: int
    max_storage_mb: int


class MeResponse(BaseModel):
    user: UserResponse
    tenant: TenantResponse
    permissions: list[str]
    feature_flags: dict
    plan_limits: PlanLimits


class MessageResponse(BaseModel):
    message: str
