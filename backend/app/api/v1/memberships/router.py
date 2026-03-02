"""Membership API routes — VP-01.

Endpoint map:
  POST /memberships/plans                              — Create plan
  GET  /memberships/plans                              — List plans
  PUT  /memberships/plans/{plan_id}                    — Update plan
  POST /memberships/subscriptions                      — Subscribe patient
  GET  /memberships/subscriptions                      — List subscriptions
  POST /memberships/subscriptions/{sub_id}/cancel      — Cancel subscription
  POST /memberships/subscriptions/{sub_id}/pause       — Pause subscription
  GET  /memberships/dashboard                          — Dashboard stats
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.membership import (
    MembershipDashboard,
    MembershipPlanCreate,
    MembershipPlanResponse,
    MembershipPlanUpdate,
    SubscriptionCreate,
    SubscriptionResponse,
)
from app.services.membership_service import membership_service

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.post("/plans", response_model=MembershipPlanResponse, status_code=201)
async def create_plan(
    body: MembershipPlanCreate,
    current_user: AuthenticatedUser = Depends(require_permission("memberships:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> MembershipPlanResponse:
    """Create a new membership plan."""
    result = await membership_service.create_plan(
        db=db, created_by=str(current_user.user_id), **body.model_dump(),
    )
    return MembershipPlanResponse(**result)


@router.get("/plans", response_model=list[MembershipPlanResponse])
async def list_plans(
    include_archived: bool = Query(default=False),
    current_user: AuthenticatedUser = Depends(require_permission("memberships:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[MembershipPlanResponse]:
    """List membership plans."""
    results = await membership_service.list_plans(db=db, include_archived=include_archived)
    return [MembershipPlanResponse(**r) for r in results]


@router.put("/plans/{plan_id}", response_model=MembershipPlanResponse)
async def update_plan(
    plan_id: str,
    body: MembershipPlanUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("memberships:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> MembershipPlanResponse:
    """Update a membership plan."""
    result = await membership_service.update_plan(
        db=db, plan_id=plan_id, **body.model_dump(exclude_unset=True),
    )
    return MembershipPlanResponse(**result)


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def subscribe_patient(
    body: SubscriptionCreate,
    current_user: AuthenticatedUser = Depends(require_permission("memberships:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SubscriptionResponse:
    """Subscribe a patient to a membership plan."""
    result = await membership_service.subscribe_patient(
        db=db,
        patient_id=body.patient_id,
        plan_id=body.plan_id,
        start_date=body.start_date,
        payment_method=body.payment_method,
        created_by=str(current_user.user_id),
    )
    return SubscriptionResponse(**result)


@router.get("/subscriptions")
async def list_subscriptions(
    status: str | None = Query(default=None, pattern=r"^(active|paused|cancelled|expired)$"),
    patient_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("memberships:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """List membership subscriptions."""
    return await membership_service.list_subscriptions(
        db=db, status=status, patient_id=patient_id, page=page, page_size=page_size,
    )


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("memberships:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SubscriptionResponse:
    """Cancel a membership subscription."""
    result = await membership_service.cancel_subscription(db=db, subscription_id=subscription_id)
    return SubscriptionResponse(**result)


@router.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionResponse)
async def pause_subscription(
    subscription_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("memberships:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SubscriptionResponse:
    """Pause a membership subscription."""
    result = await membership_service.pause_subscription(db=db, subscription_id=subscription_id)
    return SubscriptionResponse(**result)


@router.get("/dashboard", response_model=MembershipDashboard)
async def membership_dashboard(
    current_user: AuthenticatedUser = Depends(require_permission("memberships:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> MembershipDashboard:
    """Get membership dashboard statistics."""
    result = await membership_service.get_dashboard(db=db)
    return MembershipDashboard(**result)
