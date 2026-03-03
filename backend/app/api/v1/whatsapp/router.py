"""WhatsApp bidirectional chat API routes -- VP-12.

Endpoint map:
  GET    /messaging/conversations            -- List conversations (paginated)
  GET    /messaging/conversations/stream     -- SSE real-time stream
  GET    /messaging/conversations/{id}/messages -- List messages (paginated)
  POST   /messaging/conversations/{id}/send  -- Send message
  PUT    /messaging/conversations/{id}/assign -- Assign conversation
  PUT    /messaging/conversations/{id}/archive -- Archive conversation
  GET    /messaging/quick-replies            -- List quick replies

SSE endpoint uses Redis pub/sub for real-time message delivery.
JWT is passed via query param for SSE (EventSource does not support headers).

Security:
  - All endpoints require whatsapp:read or whatsapp:write permission.
  - SSE token validated manually via decode_access_token.
  - PHI is NEVER logged.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.security import decode_access_token
from app.schemas.whatsapp_chat import (
    AssignRequest,
    ConversationListResponse,
    ConversationResponse,
    MessageListResponse,
    MessageResponse,
    QuickReplyResponse,
    SendMessageRequest,
)
from app.services.whatsapp_chat_service import whatsapp_chat_service

logger = logging.getLogger("dentalos.api.whatsapp")

router = APIRouter(prefix="/messaging", tags=["whatsapp-chat"])


# ─── SSE Stream (must be defined BEFORE the {conversation_id} routes) ────────


@router.get("/conversations/stream")
async def conversation_stream(
    token: str = Query(..., description="JWT access token for SSE auth"),
) -> StreamingResponse:
    """Server-Sent Events stream for real-time WhatsApp messages.

    Subscribes to Redis pub/sub channel ``dentalos:{tid}:whatsapp:new_message``
    and yields SSE-formatted events whenever a new inbound message arrives.

    EventSource does not support Authorization headers, so the JWT is passed
    via the ``token`` query parameter and validated manually.
    """
    # Manual JWT validation (no FastAPI Depends for SSE query-param auth)
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    tid_raw: str | None = payload.get("tid")
    if not tid_raw:
        raise HTTPException(status_code=401, detail="Token missing tenant claim")

    tenant_id = tid_raw[3:] if tid_raw.startswith("tn_") else tid_raw

    # Check permission
    role: str = payload.get("role", "")
    from app.auth.permissions import get_permissions_for_role

    permissions = get_permissions_for_role(role)
    if "whatsapp:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing whatsapp:read permission")

    channel = f"dentalos:{tenant_id}:whatsapp:new_message"

    async def _event_generator() -> AsyncGenerator[str, None]:
        """Subscribe to Redis pub/sub and yield SSE events."""
        from app.core.redis import redis_client

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            # Send initial keepalive so the client knows the connection is alive
            yield ": keepalive\n\n"

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message["type"] == "message":
                    data = message["data"]
                    # data may be bytes or str depending on Redis config
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                else:
                    # Send periodic keepalive to prevent proxy/LB timeout
                    yield ": keepalive\n\n"
                    await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ─── Conversations ───────────────────────────────────────────────────────────


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(
        require_permission("whatsapp:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConversationListResponse:
    """List WhatsApp conversations with pagination and filters."""
    result = await whatsapp_chat_service.get_conversations(
        db=db,
        page=page,
        page_size=page_size,
        status_filter=status,
        assigned_to=assigned_to,
    )
    return ConversationListResponse(
        items=[ConversationResponse(**c) for c in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── Messages ────────────────────────────────────────────────────────────────


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
)
async def list_messages(
    conversation_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("whatsapp:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> MessageListResponse:
    """List messages in a conversation.

    Also resets the unread count to 0 (staff opened the conversation).
    """
    result = await whatsapp_chat_service.get_messages(
        db=db,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
    )
    return MessageListResponse(
        items=[MessageResponse(**m) for m in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post(
    "/conversations/{conversation_id}/send",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    current_user: AuthenticatedUser = Depends(
        require_permission("whatsapp:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> MessageResponse:
    """Send a WhatsApp message in a conversation."""
    result = await whatsapp_chat_service.send_message(
        db=db,
        conversation_id=conversation_id,
        content=body.content,
        sent_by=current_user.user_id,
        media_url=body.media_url,
    )
    return MessageResponse(**result)


# ─── Conversation Actions ────────────────────────────────────────────────────


@router.put(
    "/conversations/{conversation_id}/assign",
    response_model=ConversationResponse,
)
async def assign_conversation(
    conversation_id: str,
    body: AssignRequest,
    current_user: AuthenticatedUser = Depends(
        require_permission("whatsapp:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConversationResponse:
    """Assign a conversation to a staff member."""
    result = await whatsapp_chat_service.assign_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=body.user_id,
    )
    return ConversationResponse(**result)


@router.put(
    "/conversations/{conversation_id}/archive",
    response_model=ConversationResponse,
)
async def archive_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("whatsapp:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConversationResponse:
    """Archive a conversation."""
    result = await whatsapp_chat_service.archive_conversation(
        db=db,
        conversation_id=conversation_id,
    )
    return ConversationResponse(**result)


# ─── Quick Replies ───────────────────────────────────────────────────────────


@router.get("/quick-replies", response_model=list[QuickReplyResponse])
async def list_quick_replies(
    current_user: AuthenticatedUser = Depends(
        require_permission("whatsapp:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[QuickReplyResponse]:
    """List all active quick reply templates."""
    items = await whatsapp_chat_service.get_quick_replies(db=db)
    return [QuickReplyResponse(**qr) for qr in items]
