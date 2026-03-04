"""AI Virtual Receptionist public web widget routes -- VP-16.

No authentication required. Uses the tenant slug for resolution.

Endpoint map:
  POST /public/{slug}/chatbot/message  -- Process a web widget message
  GET  /public/{slug}/chatbot/config   -- Public-safe chatbot config

Security:
  - PHI (message content, patient names) is NEVER logged.
  - Rate limited per IP to prevent abuse.
  - Chatbot must be enabled in tenant config to accept messages.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DentalOSError
from app.core.rate_limit import check_rate_limit
from app.core.tenant import validate_schema_name
from app.models.public.tenant import Tenant
from app.schemas.chatbot import (
    ChatbotMessageResponse,
    ChatbotPublicConfigResponse,
    ChatbotWebMessageInput,
)
from app.services.chatbot_service import chatbot_service

logger = logging.getLogger("dentalos.chatbot")

router = APIRouter(prefix="/public", tags=["chatbot-widget"])


# ─── Tenant Resolution ──────────────────────────────────────────────────────


async def _resolve_tenant_by_slug(slug: str, db: AsyncSession) -> Tenant:
    """Resolve an active tenant from a URL slug.

    Queries public.tenants and returns the Tenant ORM object.

    Raises:
        HTTPException (404) -- slug does not exist or tenant is not active.
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == slug,
            Tenant.status == "active",
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TENANT_not_found",
                "message": "No se encontro una clinica activa con ese enlace.",
                "details": {},
            },
        )
    return tenant


# ─── Process Web Widget Message ─────────────────────────────────────────────


@router.post(
    "/{slug}/chatbot/message",
    response_model=ChatbotMessageResponse,
    summary="Enviar mensaje al chatbot (widget web)",
)
async def send_widget_message(
    slug: str,
    body: ChatbotWebMessageInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process a message from the public web widget.

    Flow:
      1. Rate limit (30 per 10 minutes per IP).
      2. Resolve tenant by slug.
      3. Validate and set tenant schema search_path.
      4. Verify chatbot is enabled for this tenant.
      5. Handle message via chatbot_service.
      6. Return bot response.

    The session_id in the request body maps to an existing
    chatbot conversation id. If None, a new conversation is created.
    """
    # 1. Rate limit
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    await check_rate_limit(
        f"rl:chatbot_widget:{ip}",
        limit=30,
        window_seconds=600,
    )

    # 2. Resolve tenant
    tenant = await _resolve_tenant_by_slug(slug, db)

    # 3. Set search_path
    schema = tenant.schema_name
    if not validate_schema_name(schema):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TENANT_invalid_schema",
                "message": "Internal configuration error.",
                "details": {},
            },
        )
    await db.execute(text(f"SET search_path TO {schema}, public"))

    # 4. Verify chatbot is enabled
    config = await chatbot_service.get_config(db=db)
    if not config.get("enabled", False):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "CHATBOT_not_enabled",
                "message": "El chatbot no esta habilitado para esta clinica.",
                "details": {},
            },
        )

    # 5. Parse conversation_id from session_id
    import uuid

    conversation_id = None
    if body.session_id:
        try:
            conversation_id = uuid.UUID(body.session_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_failed",
                    "message": "session_id invalido.",
                    "details": {},
                },
            )

    # 6. Handle message
    result = await chatbot_service.handle_message(
        db=db,
        message=body.message,
        channel="web",
        patient_id=None,
        conversation_id=conversation_id,
        whatsapp_conversation_id=None,
    )

    # Include the conversation_id in the response so the widget can
    # send it back as session_id in subsequent requests
    response = result["response"]
    response["conversation_id"] = result["conversation_id"]
    return response


# ─── Public Config ───────────────────────────────────────────────────────────


@router.get(
    "/{slug}/chatbot/config",
    response_model=ChatbotPublicConfigResponse,
    summary="Configuracion publica del chatbot",
)
async def get_public_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ChatbotPublicConfigResponse:
    """Return the public-safe chatbot configuration.

    Only returns whether the chatbot is enabled and the greeting message.
    No authentication required.
    """
    tenant = await _resolve_tenant_by_slug(slug, db)

    schema = tenant.schema_name
    if not validate_schema_name(schema):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TENANT_invalid_schema",
                "message": "Internal configuration error.",
                "details": {},
            },
        )
    await db.execute(text(f"SET search_path TO {schema}, public"))

    config = await chatbot_service.get_config(db=db)

    return ChatbotPublicConfigResponse(
        enabled=config.get("enabled", False),
        greeting_message=config.get("greeting_message", ""),
    )
