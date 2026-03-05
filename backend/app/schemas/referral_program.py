"""Patient referral program request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReferralCodeResponse(BaseModel):
    """Response schema for a patient's referral code."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    code: str
    is_active: bool
    uses_count: int
    max_uses: int | None = None
    created_at: datetime


class ReferralRewardResponse(BaseModel):
    """Response schema for a single referral reward."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    referrer_patient_id: str
    referred_patient_id: str
    reward_type: str
    reward_amount_cents: int
    status: str
    applied_to_invoice_id: str | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ReferralRewardListResponse(BaseModel):
    """Paginated list of referral rewards."""

    items: list[ReferralRewardResponse]
    total: int


class ReferralProgramStatsResponse(BaseModel):
    """Aggregate statistics for the referral program dashboard."""

    is_active: bool
    total_codes_generated: int
    total_referrals_made: int
    referrals_pending: int
    referrals_converted: int
    rewards_pending: int
    rewards_applied: int
    total_discount_given_cents: int
    reward_type: str
    reward_value_cents: int
    reward_description: str | None = None


class ReferralProgramToggleRequest(BaseModel):
    """Toggle the referral program on/off."""

    is_active: bool


class ProcessReferralCodeRequest(BaseModel):
    """Used internally when a new patient signs up with a referral code."""

    referral_code: str = Field(..., min_length=1, max_length=8)
