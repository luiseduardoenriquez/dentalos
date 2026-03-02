"""EPS verification request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EPSVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    verification_date: datetime
    eps_name: str | None = None
    eps_code: str | None = None
    affiliation_status: str | None = None
    regime: str | None = None
    copay_category: str | None = None
    created_at: datetime
