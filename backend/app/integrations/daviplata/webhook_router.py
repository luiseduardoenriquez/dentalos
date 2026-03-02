"""Daviplata webhook routes -- GAP-01 / Sprint 25-26.

POST /webhooks/daviplata -- Payment status notifications (signature-verified)

Security:
  - Validates X-Daviplata-Signature header using HMAC-SHA256
  - NO JWT auth -- webhooks use provider-specific signature verification
  - PHI is NEVER logged from webhook payloads
  - Only the first 8 characters of payment_id are logged for traceability
"""

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.queue import publish_message
from app.integrations.daviplata.schemas import DaviplataWebhookPayload
from app.integrations.daviplata.service import daviplata_service
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.integrations.daviplata.webhook")

router = APIRouter(prefix="/webhooks/daviplata", tags=["webhooks"])


@router.post("")
async def receive_daviplata_webhook(
    request: Request,
    x_daviplata_signature: str = Header(..., alias="X-Daviplata-Signature"),
) -> dict[str, str]:
    """Process Daviplata payment webhook notifications.

    Validates the HMAC-SHA256 signature from the X-Daviplata-Signature header,
    parses the payment event, and enqueues it for async reconciliation by
    payment_qr_service.

    Returns 200 immediately to acknowledge receipt. Daviplata retries on non-2xx.
    """
    body = await request.body()

    # Verify webhook signature (timing-safe HMAC-SHA256)
    if not daviplata_service.verify_webhook_signature(body, x_daviplata_signature):
        logger.warning("Daviplata webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse the webhook payload
    try:
        payload = DaviplataWebhookPayload.model_validate_json(body)
    except Exception:
        logger.warning("Daviplata webhook payload parsing failed")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Log only safe, truncated identifiers -- never amounts or references
    logger.info(
        "Daviplata webhook received: event_type=%s payment_id=%s... status=%s",
        payload.event_type,
        payload.payment_id[:8] if payload.payment_id else "unknown",
        payload.status,
    )

    # Only reconcile completed payments
    if payload.status == "completed":
        # Extract tenant_id from reference (format: "{tenant_short}:{invoice_id}")
        tenant_id = payload.reference.split(":", 1)[0] if ":" in payload.reference else "unknown"

        await publish_message(
            "notifications",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="payment.qr_reconcile",
                payload={
                    "provider": "daviplata",
                    "payment_id": payload.payment_id,
                    "amount_cents": payload.amount_cents,
                    "reference": payload.reference,
                },
                priority=8,  # High priority -- financial reconciliation
            ),
        )

    return {"status": "ok"}
