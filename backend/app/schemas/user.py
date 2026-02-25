"""User management request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Response Schemas ────────────────────────────────


class UserProfileResponse(BaseModel):
    """Full profile view returned to the authenticated user themselves."""

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
    created_at: datetime
    updated_at: datetime


class UserTeamMemberResponse(BaseModel):
    """Team member view returned to clinic_owner in list/detail endpoints."""

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
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Paginated list of team members."""

    items: list[UserTeamMemberResponse]
    total: int
    page: int
    page_size: int


# ─── Request Schemas ─────────────────────────────────


class UserProfileUpdate(BaseModel):
    """Fields the authenticated user can update on their own profile.

    professional_license and specialties are accepted here but are only
    applied when the calling user is a doctor — that validation lives in
    the service layer, not in this schema.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    avatar_url: str | None = Field(default=None, max_length=500)
    professional_license: str | None = Field(default=None, max_length=50)
    specialties: list[str] | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v

    @field_validator("avatar_url")
    @classmethod
    def strip_avatar_url(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v

    @field_validator("professional_license")
    @classmethod
    def strip_license(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v

    @field_validator("specialties")
    @classmethod
    def strip_specialties(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [s.strip() for s in v if s.strip()]
        return v


class UserTeamMemberUpdate(BaseModel):
    """Fields a clinic_owner can update on a team member.

    Changing role to clinic_owner is not allowed — enforced in the service.
    """

    role: str | None = Field(
        default=None,
        pattern=r"^(doctor|assistant|receptionist)$",
    )
    is_active: bool | None = None
