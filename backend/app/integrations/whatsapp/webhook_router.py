"""WhatsApp webhook routes -- INT-01 + VP-12.

GET  /webhooks/whatsapp -- Meta verification challenge
POST /webhooks/whatsapp -- Delivery statuses + inbound messages (signature-verified)

Security:
  - GET uses verify_token comparison for Meta webhook registration
  - POST validates X-Hub-Signature-256 header using app secret (HMAC-SHA256)
  - NO JWT auth -- webhooks use provider-specific signature verification
  - PHI is NEVER logged from webhook payloads
"""

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.whatsapp.webhook")

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


def _verify_signature(payload: bytes, signature: str) -> bool:
    """Verify X-Hub-Signature-256 using HMAC-SHA256.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header (format: "sha256=<hex>").

    Returns:
        True if signature is valid.
    """
    if not signature.startswith("sha256="):
        return False

    expected_sig = signature[7:]  # Strip "sha256=" prefix
    secret = settings.whatsapp_app_secret.encode("utf-8")
    computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed, expected_sig)


async def _resolve_tenant_id_for_webhook(phone_number_id: str) -> str | None:
    """Resolve the tenant_id for a WhatsApp phone_number_id.

    For MVP, we look up tenants that have this phone_number_id configured.
    Falls back to a single-tenant approach using the configured
    whatsapp_phone_number_id from settings.

    Returns the tenant schema name (e.g., 'tn_demodent') or None.
    """
    # MVP: if the webhook phone_number_id matches our configured one, use
    # a lookup from the public.tenants table. For single-tenant dev setups,
    # we query the first active tenant.
    if phone_number_id != settings.whatsapp_phone_number_id:
        logger.warning(
            "Webhook phone_number_id mismatch: received=%s configured=%s",
            phone_number_id,
            settings.whatsapp_phone_number_id,
        )
        return None

    try:
        from sqlalchemy import text

        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT id, schema_name FROM public.tenants "
                    "WHERE is_active = true "
                    "ORDER BY created_at ASC LIMIT 1"
                )
            )
            row = result.first()
            if row:
                return row[0], row[1]  # type: ignore[return-value]
    except Exception:
        logger.exception("Failed to resolve tenant for webhook")

    return None


async def _process_inbound_messages(value: dict[str, Any]) -> None:
    """Process inbound messages from a webhook payload value.

    For each inbound message:
    1. Extract phone number and message content
    2. Resolve tenant from phone_number_id
    3. Match phone to patient
    4. Find or create conversation
    5. Store inbound message
    6. Increment unread count
    7. Publish to Redis pub/sub for SSE
    """
    messages = value.get("messages", [])
    if not messages:
        return

    metadata = value.get("metadata", {})
    phone_number_id = metadata.get("phone_number_id", "")
    contacts = value.get("contacts", [])

    # Resolve tenant
    tenant_info = await _resolve_tenant_id_for_webhook(phone_number_id)
    if tenant_info is None:
        logger.warning("Could not resolve tenant for inbound WhatsApp message")
        return

    tenant_id, schema_name = tenant_info

    # Get the sender's phone number from contacts or message
    sender_phone = ""
    if contacts:
        sender_phone = contacts[0].get("wa_id", "")

    if not sender_phone and messages:
        sender_phone = messages[0].get("from", "")

    if not sender_phone:
        logger.warning("No sender phone in inbound WhatsApp webhook")
        return

    # Process each message in a tenant-scoped DB session
    from app.core.database import get_tenant_session
    from app.services.whatsapp_chat_service import whatsapp_chat_service

    try:
        async with get_tenant_session(schema_name) as db:
            # Match phone to patient
            patient_id = await whatsapp_chat_service.match_phone_to_patient(
                db, sender_phone
            )

            # Find or create conversation
            conversation = await whatsapp_chat_service.find_or_create_conversation(
                db, sender_phone, patient_id=patient_id
            )
            conversation_id = conversation["id"]

            for msg in messages:
                msg_type = msg.get("type", "text")
                wa_msg_id = msg.get("id", "")

                # Extract content based on message type
                content: str | None = None
                media_url: str | None = None
                media_type: str | None = None

                if msg_type == "text":
                    text_obj = msg.get("text", {})
                    content = text_obj.get("body", "")
                elif msg_type in ("image", "video", "audio", "document"):
                    media_obj = msg.get(msg_type, {})
                    media_url = media_obj.get("id", "")  # Meta media ID
                    media_type = media_obj.get("mime_type", msg_type)
                    content = media_obj.get("caption", "")
                elif msg_type == "location":
                    loc = msg.get("location", {})
                    content = (
                        f"Location: {loc.get('latitude', '')}, "
                        f"{loc.get('longitude', '')}"
                    )
                elif msg_type == "contacts":
                    content = "[Contact shared]"
                elif msg_type == "sticker":
                    sticker = msg.get("sticker", {})
                    media_url = sticker.get("id", "")
                    media_type = "sticker"
                    content = "[Sticker]"
                else:
                    content = f"[{msg_type} message]"

                # Store the inbound message
                stored = await whatsapp_chat_service.store_inbound_message(
                    db=db,
                    conversation_id=conversation_id,
                    content=content or "",
                    whatsapp_message_id=wa_msg_id,
                    media_url=media_url,
                    media_type=media_type,
                )

                # Increment unread count
                await whatsapp_chat_service.increment_unread(db, conversation_id)

                # Publish to Redis pub/sub for SSE clients
                try:
                    from app.core.redis import redis_client

                    channel = f"dentalos:{tenant_id}:whatsapp:new_message"
                    event_data = json.dumps(
                        {
                            "event": "new_message",
                            "conversation_id": conversation_id,
                            "message_id": stored["id"],
                            "direction": "inbound",
                            "content_preview": (content or "")[:100],
                            "phone_number": sender_phone,
                            "patient_id": str(patient_id) if patient_id else None,
                        },
                        default=str,
                    )
                    await redis_client.publish(channel, event_data)
                except Exception:
                    # Redis pub/sub is a performance enhancement, not critical
                    logger.warning("Failed to publish inbound message to Redis pub/sub")

            logger.info(
                "Processed %d inbound WhatsApp message(s) for conversation=%s",
                len(messages),
                conversation_id[:8],
            )

    except Exception:
        logger.exception("Failed to process inbound WhatsApp messages")


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    """Meta webhook verification challenge (GET).

    Meta sends this on webhook registration to verify ownership.
    We respond with hub.challenge if the verify_token matches.
    """
    if hub_mode != "subscribe":
        raise HTTPException(status_code=403, detail="Invalid mode")

    if not hmac.compare_digest(hub_verify_token, settings.whatsapp_verify_token):
        raise HTTPException(status_code=403, detail="Invalid verify token")

    logger.info("WhatsApp webhook verified successfully")
    return Response(content=hub_challenge, media_type="text/plain")


@router.post("")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> dict[str, str]:
    """Process WhatsApp webhook events (POST).

    Validates X-Hub-Signature-256, then processes:
    1. Delivery status updates (sent, delivered, read, failed)
    2. Inbound messages from patients (VP-12 bidirectional chat)

    Returns 200 immediately -- Meta retries on non-2xx.
    """
    body = await request.body()

    if not _verify_signature(body, x_hub_signature_256):
        logger.warning("WhatsApp webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Process entries
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # ── 1. Delivery status updates (existing INT-01 logic) ──────
            statuses = value.get("statuses", [])
            for status in statuses:
                msg_id = status.get("id", "unknown")
                msg_status = status.get("status", "unknown")
                # Log only message ID and status -- never recipient info (PHI)
                logger.info(
                    "WhatsApp delivery status: message_id=%s status=%s",
                    msg_id,
                    msg_status,
                )

            # ── 2. Inbound messages (VP-12 bidirectional chat) ──────────
            if value.get("messages"):
                try:
                    await _process_inbound_messages(value)
                except Exception:
                    # Never fail the webhook response -- Meta will retry
                    logger.exception("Error processing inbound WhatsApp messages")

    return {"status": "ok"}
