"""Membership plan and subscription schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class MembershipPlanCreate(BaseModel):
    """Create a new membership plan."""
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    monthly_price_cents: int = Field(ge=0)
    annual_price_cents: int | None = Field(default=None, ge=0)
    benefits: dict | None = None
    discount_percentage: int = Field(ge=0, le=100, default=0)


class MembershipPlanUpdate(BaseModel):
    """Update an existing membership plan."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    monthly_price_cents: int | None = Field(default=None, ge=0)
    annual_price_cents: int | None = Field(default=None, ge=0)
    benefits: dict | None = None
    discount_percentage: int | None = Field(default=None, ge=0, le=100)
    status: str | None = Field(default=None, pattern=r"^(active|archived)$")


class MembershipPlanResponse(BaseModel):
    """Membership plan details."""
    id: str
    name: str
    description: str | None = None
    monthly_price_cents: int
    annual_price_cents: int | None = None
    benefits: dict | None = None
    discount_percentage: int
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionCreate(BaseModel):
    """Subscribe a patient to a membership plan."""
    patient_id: str
    plan_id: str
    start_date: date
    payment_method: str | None = None


class SubscriptionResponse(BaseModel):
    """Membership subscription details."""
    id: str
    patient_id: str
    plan_id: str
    plan_name: str | None = None
    status: str
    start_date: date
    next_billing_date: date | None = None
    cancelled_at: datetime | None = None
    paused_at: datetime | None = None
    payment_method: str | None = None
    discount_percentage: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MembershipDashboard(BaseModel):
    """Aggregated membership dashboard stats."""
    active_count: int = 0
    paused_count: int = 0
    total_monthly_revenue_cents: int = 0
    churn_rate_percent: float = 0.0
