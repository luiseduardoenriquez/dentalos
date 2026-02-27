"""WhatsApp webhook routes -- INT-01.

GET  /webhooks/whatsapp -- Meta verification challenge
POST /webhooks/whatsapp -- Delivery status updates (signature-verified)

Security:
  - GET uses verify_token comparison for Meta webhook registration
  - POST validates X-Hub-Signature-256 header using app secret (HMAC-SHA256)
  - NO JWT auth -- webhooks use provider-specific signature verification
  - PHI is NEVER logged from webhook payloads
"""

import hashlib
import hmac
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

    Validates X-Hub-Signature-256, then processes delivery status updates.
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

    return {"status": "ok"}
