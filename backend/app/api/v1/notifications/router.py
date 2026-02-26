"""Notification API routes — N-01 through N-04, U-09.

Endpoint map:
  GET  /notifications                          — N-01: List notifications (cursor-paginated)
  POST /notifications/{notification_id}/read   — N-02: Mark single notification as read
  POST /notifications/read-all                 — N-03: Mark all notifications as read
  GET  /notifications/preferences              — N-04: Get notification preferences
  PUT  /notifications/preferences              — U-09: Update notification preferences
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.notifications import (
    MarkAllReadRequest,
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationResponse,
    UpdatePreferencesRequest,
)
from app.services.notification_service import notification_service

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


# ─── N-01: List notifications ────────────────────────────────────────────────


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    status: str | None = Query(default=None, description="Filter: read, unread, all"),
    type: str | None = Query(default=None, description="Filter by notification type"),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("notifications:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> NotificationListResponse:
    """List notifications for the current user with cursor-based pagination."""
    result = await notification_service.list_notifications(
        db=db,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant.tenant_id,
        status=status,
        notification_type=type,
        cursor=cursor,
        limit=limit,
    )
    return NotificationListResponse(**result)


# ─── N-02: Mark single notification as read ──────────────────────────────────


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
async def mark_notification_read(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("notifications:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> NotificationResponse:
    """Mark a single notification as read. Idempotent."""
    result = await notification_service.mark_read(
        db=db,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant.tenant_id,
        notification_id=notification_id,
    )
    return NotificationResponse(**result)


# ─── N-03: Mark all notifications as read ────────────────────────────────────


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    body: MarkAllReadRequest | None = None,
    current_user: AuthenticatedUser = Depends(
        require_permission("notifications:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> MarkAllReadResponse:
    """Mark all unread notifications as read. Optionally filter by type."""
    type_filter = body.type if body else None
    result = await notification_service.mark_all_read(
        db=db,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant.tenant_id,
        type_filter=type_filter,
    )
    return MarkAllReadResponse(**result)


# ─── N-04: Get notification preferences ──────────────────────────────────────


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    current_user: AuthenticatedUser = Depends(
        require_permission("notifications:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> NotificationPreferenceResponse:
    """Get the current user's notification channel preferences."""
    result = await notification_service.get_preferences(
        db=db,
        user_id=current_user.user_id,
    )
    return NotificationPreferenceResponse(**result)


# ─── U-09: Update notification preferences ──────────────────────────────────


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: AuthenticatedUser = Depends(
        require_permission("notifications:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> NotificationPreferenceResponse:
    """Update notification channel preferences for the current user."""
    updates = [u.model_dump() for u in body.preferences]
    result = await notification_service.update_preferences(
        db=db,
        user_id=current_user.user_id,
        updates=updates,
    )
    return NotificationPreferenceResponse(**result)
