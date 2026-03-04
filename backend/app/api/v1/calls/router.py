"""Call log API routes -- VP-18 VoIP Screen Pop.

Endpoint map:
  GET  /calls             -- List call logs (paginated)
  GET  /calls/stream      -- SSE real-time incoming call stream
  GET  /calls/{id}        -- Get call log detail
  PUT  /calls/{id}/notes  -- Update call notes

Security:
  - All endpoints require calls:read or calls:write permission.
  - SSE token validated manually via decode_access_token.
  - PHI is NEVER logged.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.security import decode_access_token
from app.schemas.call_log import (
    CallLogListResponse,
    CallLogResponse,
    CallLogUpdateNotes,
)
from app.services.call_log_service import call_log_service

logger = logging.getLogger("dentalos.api.calls")

router = APIRouter(prefix="/calls", tags=["calls"])


# ─── SSE Stream ────────────────────────────────────────────────────────────


@router.get("/stream")
async def call_stream(
    token: str = Query(..., description="JWT access token for SSE auth"),
) -> StreamingResponse:
    """Server-Sent Events stream for real-time incoming call notifications.

    Subscribes to Redis channel ``dentalos:{tid}:calls:incoming``
    and yields SSE-formatted events for screen-pop.
    """
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    tid_raw: str | None = payload.get("tid")
    if not tid_raw:
        raise HTTPException(status_code=401, detail="Token missing tenant claim")

    tenant_id = tid_raw[3:] if tid_raw.startswith("tn_") else tid_raw

    role: str = payload.get("role", "")
    from app.auth.permissions import get_permissions_for_role

    permissions = get_permissions_for_role(role)
    if "calls:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing calls:read permission")

    channel = f"dentalos:{tenant_id}:calls:incoming"

    async def _event_generator() -> AsyncGenerator[str, None]:
        from app.core.redis import redis_client

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            yield ": keepalive\n\n"

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                else:
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
            "X-Accel-Buffering": "no",
        },
    )


# ─── Call Logs ─────────────────────────────────────────────────────────────


@router.get("", response_model=CallLogListResponse)
async def list_call_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    direction: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("calls:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CallLogListResponse:
    """List call logs with pagination and optional filters."""
    result = await call_log_service.list_call_logs(
        db, page=page, page_size=page_size, direction=direction, status=status,
    )
    return CallLogListResponse(
        items=[CallLogResponse.model_validate(c) for c in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{call_id}", response_model=CallLogResponse)
async def get_call_log(
    call_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("calls:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CallLogResponse:
    """Get a single call log by ID."""
    call = await call_log_service.get_call_log(db, call_id)
    return CallLogResponse.model_validate(call)


@router.put("/{call_id}/notes", response_model=CallLogResponse)
async def update_call_notes(
    call_id: uuid.UUID,
    body: CallLogUpdateNotes,
    current_user: AuthenticatedUser = Depends(require_permission("calls:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CallLogResponse:
    """Update notes on a call log entry."""
    call = await call_log_service.update_notes(db, call_id, body.notes)
    return CallLogResponse.model_validate(call)
