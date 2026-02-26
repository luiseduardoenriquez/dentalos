"""Messaging API routes — MS-01 through MS-05.

Endpoint map:
  POST /messages/threads              — MS-01 Create thread
  GET  /messages/threads              — MS-02 List threads
  POST /messages/threads/{id}/messages — MS-03 Send message
  GET  /messages/threads/{id}/messages — MS-04 List messages
  POST /messages/threads/{id}/read    — MS-05 Mark thread read
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.messaging import (
    MessageListResponse,
    MessageResponse,
    MessageSend,
    ThreadCreate,
    ThreadListResponse,
    ThreadResponse,
)
from app.services.messaging_service import messaging_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    body: ThreadCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("messages:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ThreadResponse:
    """Create a new message thread with an initial message (MS-01)."""
    result = await messaging_service.create_thread(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        created_by_id=current_user.user_id,
        patient_id=body.patient_id,
        subject=body.subject,
        initial_message=body.initial_message,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="message_thread",
        resource_id=result["id"],
    )

    return ThreadResponse(**result)


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    patient_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("messages:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ThreadListResponse:
    """List message threads (MS-02)."""
    result = await messaging_service.list_threads(
        db=db,
        patient_id=patient_id,
        status=status,
        cursor=cursor,
        limit=limit,
    )
    return ThreadListResponse(
        data=[ThreadResponse(**t) for t in result["data"]],
        pagination=result["pagination"],
    )


@router.post(
    "/threads/{thread_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    thread_id: str,
    body: MessageSend,
    current_user: AuthenticatedUser = Depends(
        require_permission("messages:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> MessageResponse:
    """Send a message in an existing thread (MS-03)."""
    result = await messaging_service.send_message(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        thread_id=thread_id,
        sender_type="staff",
        sender_id=current_user.user_id,
        body=body.body,
    )
    return MessageResponse(**result)


@router.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("messages:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> MessageListResponse:
    """List messages in a thread (MS-04)."""
    result = await messaging_service.list_messages(
        db=db,
        thread_id=thread_id,
        cursor=cursor,
        limit=limit,
    )
    return MessageListResponse(
        data=[MessageResponse(**m) for m in result["data"]],
        pagination=result["pagination"],
    )


@router.post("/threads/{thread_id}/read")
async def mark_thread_read(
    thread_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("messages:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Mark a thread as read for the current user (MS-05)."""
    return await messaging_service.mark_thread_read(
        db=db,
        thread_id=thread_id,
        user_id=current_user.user_id,
    )
