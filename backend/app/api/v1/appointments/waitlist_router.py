"""Waitlist API routes — AP-12 through AP-14.

Endpoint map:
  POST /waitlist                      — AP-12: Add patient to waitlist
  GET  /waitlist                      — AP-13: List waitlist entries (cursor)
  POST /waitlist/{entry_id}/notify    — AP-14: Notify a waitlist entry
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.waitlist import (
    WaitlistEntryCreate,
    WaitlistEntryResponse,
    WaitlistListResponse,
    WaitlistNotifyRequest,
)
from app.services.waitlist_service import waitlist_service

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


# ─── AP-12: Add to waitlist ───────────────────────────────────────────────────


@router.post("", response_model=WaitlistEntryResponse, status_code=201)
async def add_to_waitlist(
    body: WaitlistEntryCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("waitlist:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> WaitlistEntryResponse:
    """Add a patient to the appointment waitlist (AP-12).

    Validates that the patient is active and that no duplicate active entry
    already exists for the same patient and doctor combination. The entry
    status starts as 'waiting'.
    """
    result = await waitlist_service.add_to_waitlist(
        db=db,
        patient_id=body.patient_id,
        preferred_doctor_id=body.preferred_doctor_id,
        procedure_type=body.procedure_type,
        preferred_days=body.preferred_days,
        preferred_time_from=body.preferred_time_from,
        preferred_time_to=body.preferred_time_to,
        valid_until=body.valid_until.isoformat() if body.valid_until else None,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="waitlist_entry",
        resource_id=result["id"],
    )

    return WaitlistEntryResponse(**result)


# ─── AP-13: List waitlist ─────────────────────────────────────────────────────


@router.get("", response_model=WaitlistListResponse)
async def list_waitlist(
    status: str | None = Query(default=None, description="Filter by status: waiting, notified, booked, expired"),
    doctor_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(require_permission("waitlist:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> WaitlistListResponse:
    """Return a cursor-paginated list of waitlist entries (AP-13).

    Ordered by (created_at, id) descending. Pass the next_cursor from a
    previous response to advance through pages.
    """
    result = await waitlist_service.list_waitlist(
        db=db,
        status=status,
        doctor_id=doctor_id,
        cursor=cursor,
        page_size=page_size,
    )

    return WaitlistListResponse(**result)


# ─── AP-14: Notify waitlist entry ────────────────────────────────────────────


@router.post("/{entry_id}/notify", response_model=WaitlistEntryResponse)
async def notify_waitlist_entry(
    entry_id: str,
    body: WaitlistNotifyRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("waitlist:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> WaitlistEntryResponse:
    """Notify a waitlist patient that a slot is available (AP-14).

    Transitions the entry status from 'waiting' to 'notified' and increments
    the notification_count. The optional message field can carry a custom
    text to include in the outbound notification.
    """
    result = await waitlist_service.notify_entry(
        db=db,
        entry_id=entry_id,
        message=body.message,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="notify",
        resource_type="waitlist_entry",
        resource_id=entry_id,
    )

    return WaitlistEntryResponse(**result)
