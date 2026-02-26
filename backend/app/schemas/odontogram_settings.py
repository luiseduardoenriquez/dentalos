"""Odontogram configuration schemas (FE-S-04)."""

from pydantic import BaseModel, Field


class OdontogramSettingsResponse(BaseModel):
    """Current odontogram display configuration for a tenant."""

    default_view: str = "classic"
    default_zoom: str = "full"
    auto_save_dictation: bool = False
    condition_colors: dict[str, str] = Field(default_factory=dict)


class OdontogramSettingsUpdate(BaseModel):
    """Fields that can be updated in the odontogram configuration."""

    default_view: str | None = Field(
        default=None, pattern=r"^(classic|anatomic)$"
    )
    default_zoom: str | None = Field(
        default=None, pattern=r"^(full|quadrant)$"
    )
    auto_save_dictation: bool | None = None
    condition_colors: dict[str, str] | None = None
