"""Loyalty points program request/response schemas.

All monetary values are in cents. Points are dimensionless integers.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PointsBalance(BaseModel):
    """Current loyalty point balance for a patient."""

    patient_id: UUID
    points_balance: int
    lifetime_earned: int
    lifetime_redeemed: int
    last_activity_at: datetime | None = None


class TransactionResponse(BaseModel):
    """A single loyalty point transaction record."""

    id: UUID
    patient_id: UUID
    type: str
    points: int
    reason: str | None = None
    reference_id: UUID | None = None
    reference_type: str | None = None
    created_at: datetime


class RedeemRequest(BaseModel):
    """Request to redeem loyalty points for a patient."""

    patient_id: str
    points: int = Field(gt=0)
    reason: str | None = None


class RedeemResponse(BaseModel):
    """Response after redeeming loyalty points."""

    balance: PointsBalance
    discount_cents: int


class LeaderboardEntry(BaseModel):
    """A single entry in the loyalty leaderboard."""

    patient_id: UUID
    patient_name: str
    points_balance: int
    lifetime_earned: int


class PortalLoyaltyResponse(BaseModel):
    """Patient portal view of loyalty balance and recent transactions."""

    balance: PointsBalance
    recent_transactions: list[TransactionResponse]


class LeaderboardResponse(BaseModel):
    """Loyalty leaderboard with top patients by points."""

    items: list[LeaderboardEntry]
    total: int
