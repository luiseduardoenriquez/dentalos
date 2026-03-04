"""AI Virtual Receptionist staff-facing API routes -- VP-16.

Endpoint map (all JWT-protected):
  GET    /chatbot/conversations                          -- List conversations
  GET    /chatbot/conversations/{conversation_id}        -- Detail with messages
  POST   /chatbot/conversations/{conversation_id}/escalate -- Manual escalation
  POST   /chatbot/conversations/{conversation_id}/resolve  -- Mark resolved
  GET    /chatbot/config                                  -- Read chatbot config
  PUT    /chatbot/config                                  -- Update chatbot config

All read endpoints require 'chatbot:read' permission.
All write endpoints require 'chatbot:write' permission.

Security:
  - PHI (message content, patient names) is NEVER logged.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.chatbot import (
    ChatbotConfigResponse,
    ChatbotConfigUpdate,
    ChatbotConversationResponse,
    ChatbotMessageResponse,
    ConversationListResponse,
)
from app.services.chatbot_service import chatbot_service

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


# ── List conversations ───────────────────────────────────────────────────────


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="Listar conversaciones del chatbot",
)
async def list_conversations(
    status: str | None = Query(default=None, description="Filter by status: active, resolved, escalated"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("chatbot:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConversationListResponse:
    """Return a paginated list of chatbot conversations."""
    result = await chatbot_service.get_conversations(
        db=db,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ConversationListResponse(
        items=[ChatbotConversationResponse(**c) for c in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ── Conversation detail ─────────────────────────────────────────────────────


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatbotConversationResponse,
    summary="Detalle de conversacion con mensajes",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("chatbot:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ChatbotConversationResponse:
    """Fetch a single chatbot conversation with all messages."""
    result = await chatbot_service.get_conversation_detail(
        db=db,
        conversation_id=conversation_id,
    )
    return ChatbotConversationResponse(**result)


# ── Escalate conversation ────────────────────────────────────────────────────


@router.post(
    "/conversations/{conversation_id}/escalate",
    response_model=ChatbotConversationResponse,
    summary="Escalar conversacion a atencion humana",
)
async def escalate_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("chatbot:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ChatbotConversationResponse:
    """Manually escalate a chatbot conversation to human staff."""
    result = await chatbot_service.escalate_conversation(
        db=db,
        conversation_id=conversation_id,
    )
    return ChatbotConversationResponse(**result)


# ── Resolve conversation ─────────────────────────────────────────────────────


@router.post(
    "/conversations/{conversation_id}/resolve",
    response_model=ChatbotConversationResponse,
    summary="Marcar conversacion como resuelta",
)
async def resolve_conversation(
    conversation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_permission("chatbot:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ChatbotConversationResponse:
    """Mark a chatbot conversation as resolved."""
    result = await chatbot_service.resolve_conversation(
        db=db,
        conversation_id=conversation_id,
    )
    return ChatbotConversationResponse(**result)


# ── Read config ──────────────────────────────────────────────────────────────


@router.get(
    "/config",
    response_model=ChatbotConfigResponse,
    summary="Obtener configuracion del chatbot",
)
async def get_config(
    current_user: AuthenticatedUser = Depends(require_permission("chatbot:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ChatbotConfigResponse:
    """Return the current chatbot configuration for this tenant."""
    config = await chatbot_service.get_config(db=db)
    return ChatbotConfigResponse(**config)


# ── Update config ────────────────────────────────────────────────────────────


@router.put(
    "/config",
    response_model=ChatbotConfigResponse,
    summary="Actualizar configuracion del chatbot",
)
async def update_config(
    body: ChatbotConfigUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("chatbot:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ChatbotConfigResponse:
    """Update the chatbot configuration.

    Only provided (non-null) fields are merged into the existing config.
    """
    updates = body.model_dump(exclude_unset=True)
    config = await chatbot_service.update_config(
        db=db,
        updates=updates,
    )
    return ChatbotConfigResponse(**config)
