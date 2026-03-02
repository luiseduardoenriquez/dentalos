"""RETHUS verification request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RETHUSVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    rethus_number: str | None = None
    verification_status: str  # pending / verified / failed / expired
    verified_at: datetime | None = None
    professional_name: str | None = None
    profession: str | None = None
    specialty: str | None = None


class RETHUSVerificationTrigger(BaseModel):
    rethus_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9]+$",
    )
