"""Mercado Pago IPN (Instant Payment Notification) webhook router.

POST /webhooks/mercadopago/ipn — receives and processes MP IPN callbacks.

Two notification types are handled:
  - ``payment``                  — invoice payment, triggers reconciliation job
  - ``subscription_preapproval`` — recurring subscription status change

Security model:
  - NO JWT auth — MP webhooks are authenticated via HMAC-SHA256 signature
  - Signature is verified before any payload parsing
  - PHI is NEVER logged (no amounts, no payer info, no invoice references)
  - Only truncated payment/subscription IDs are written to logs
  - Always returns 200 OK — MP retries on non-2xx responses

IPN flow:
  1. MP delivers a minimal notification with resource type and ID
  2. We verify the x-signature header using HMAC-SHA256
  3. We fetch the full resource from the MP API to get status + external_reference
  4. We route to the correct tenant from external_reference (format: "{tid}:{resource_id}")
  5. We enqueue a RabbitMQ job for async DB reconciliation by the notifications worker

Reference:
  https://www.mercadopago.com/developers/en/docs/your-integrations/notifications/ipn
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.queue import publish_message
from app.integrations.payments.mercadopago import mercadopago_service
from app.integrations.payments.mercadopago_schemas import MercadoPagoIPNPayload
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.integrations.mercadopago.webhook")

router = APIRouter(prefix="/webhooks/mercadopago", tags=["webhooks"])


def _extract_tenant_id(external_reference: str) -> str:
    """Extract the tenant identifier from an MP external_reference string.

    DentalOS sets external_reference to ``{tenant_id}:{resource_id}`` when
    creating preferences and subscriptions. This lets us route the IPN to the
    correct tenant schema without any unauthenticated DB lookup.

    Args:
        external_reference: The external_reference value from the MP resource.

    Returns:
        The tenant_id portion, or ``"unknown"`` when the format is unexpected.
    """
    if ":" in external_reference:
        return external_reference.split(":", 1)[0]
    return "unknown"


@router.post("/ipn")
async def receive_mercadopago_ipn(
    request: Request,
    x_signature: str | None = Header(default=None, alias="x-signature"),
) -> dict[str, str]:
    """Process a Mercado Pago IPN notification.

    Verifies the webhook signature, parses the notification type, fetches
    the full resource from the MP API, and enqueues an async reconciliation
    job via RabbitMQ.

    Returns 200 immediately on all valid (signature-verified) requests.
    Non-200 responses cause MP to retry delivery up to 5 times.

    Notification types handled:
      - ``payment``                  → enqueues ``payment.mp_reconcile``
      - ``subscription_preapproval`` → enqueues ``membership.mp_subscription_update``

    Args:
        request: The raw FastAPI request (used to read body bytes for sig check).
        x_signature: The ``x-signature`` header from Mercado Pago. When absent
            (e.g. in early-stage dev environments where MP doesn't yet sign),
            we skip verification only if the webhook secret is also unconfigured.
            In production the secret is always required.

    Returns:
        {"status": "ok"} on success.

    Raises:
        HTTPException 403: When signature verification fails.
        HTTPException 400: When the IPN payload cannot be parsed.
        HTTPException 422: When the notification type is not recognized.
    """
    body = await request.body()

    # -------------------------------------------------------------------
    # 1. Signature verification
    # -------------------------------------------------------------------
    if x_signature is None:
        # MP should always send x-signature; absence is suspicious
        logger.warning("MP IPN received without x-signature header")
        raise HTTPException(status_code=403, detail="Missing x-signature header")

    if not mercadopago_service.verify_webhook(body, x_signature):
        logger.warning("MP IPN signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    # -------------------------------------------------------------------
    # 2. Parse notification envelope
    # -------------------------------------------------------------------
    try:
        notification = MercadoPagoIPNPayload.model_validate_json(body)
    except Exception:
        logger.warning("MP IPN payload could not be parsed")
        raise HTTPException(status_code=400, detail="Invalid IPN payload")

    notification_type = notification.type
    resource_id: str = str(notification.data.get("id", ""))

    # Safe log — no PHI, only type and truncated resource ID
    logger.info(
        "MP IPN received: type=%s resource_id=%s... live_mode=%s",
        notification_type,
        resource_id[:8] if resource_id else "unknown",
        notification.live_mode,
    )

    # -------------------------------------------------------------------
    # 3. Route by notification type
    # -------------------------------------------------------------------
    if notification_type == "payment":
        await _handle_payment_notification(resource_id)

    elif notification_type == "subscription_preapproval":
        await _handle_subscription_notification(resource_id)

    else:
        # Unknown type — log and acknowledge to avoid MP retries for unsupported types
        logger.info(
            "MP IPN: unhandled notification type=%s resource_id=%s... — acknowledged",
            notification_type,
            resource_id[:8] if resource_id else "unknown",
        )

    # MP requires a 200 response to stop retry attempts
    return {"status": "ok"}


async def _handle_payment_notification(payment_id: str) -> None:
    """Handle a ``payment`` IPN notification.

    Fetches the full payment resource from the MP API to obtain status,
    status_detail, and the external_reference that encodes the tenant + invoice.
    Only ``approved`` payments trigger a reconciliation job; other statuses
    are logged and acknowledged.

    PHI policy: payer_email from the MP response is NEVER written to logs.

    Args:
        payment_id: Mercado Pago payment ID from the IPN data envelope.
    """
    if not payment_id:
        logger.warning("MP IPN payment notification missing payment_id")
        return

    try:
        status_result = await mercadopago_service.get_payment_status(
            payment_id=payment_id
        )
    except Exception as exc:
        # Log the exception type only — no raw MP API responses in logs
        logger.error(
            "MP IPN: failed to fetch payment status for payment_id=%s... error=%s",
            payment_id[:8],
            type(exc).__name__,
        )
        return

    # Only reconcile payments that have been approved by MP
    if status_result.status != "approved":
        logger.info(
            "MP IPN: payment not approved, skipping reconciliation. "
            "payment_id=%s... status=%s status_detail=%s",
            payment_id[:8],
            status_result.status,
            status_result.status_detail,
        )
        return

    # Publish reconciliation job to RabbitMQ.
    # The notifications worker is responsible for:
    #   1. Looking up the invoice by external_reference
    #   2. Creating an immutable Payment record
    #   3. Updating the invoice amount_paid / balance / status
    #   4. Optionally sending a payment confirmation notification

    # We cannot derive tenant_id here without an extra API call to get
    # external_reference — that field is on the payment resource but we
    # only requested status. Pass the payment_id to the worker and let it
    # re-fetch or look up via its own DB index.
    #
    # The worker must call GET /v1/payments/{id} to get external_reference
    # and derive tenant_id from it (format: "{tenant_id}:{invoice_id}").
    await publish_message(
        "notifications",
        QueueMessage(
            tenant_id="system",  # Worker resolves tenant from external_reference
            job_type="payment.mp_reconcile",
            payload={
                "provider": "mercadopago",
                "payment_id": payment_id,
                "amount_cents": status_result.amount_cents,
                "status": status_result.status,
                "status_detail": status_result.status_detail,
            },
            priority=9,  # Highest priority — financial reconciliation is time-critical
        ),
    )

    logger.info(
        "MP IPN: payment reconciliation job enqueued for payment_id=%s...",
        payment_id[:8],
    )


async def _handle_subscription_notification(subscription_id: str) -> None:
    """Handle a ``subscription_preapproval`` IPN notification.

    Enqueues an async job for the notifications worker to update the
    MembershipSubscription record in the tenant schema. The worker resolves
    the tenant from the subscription's external_reference field.

    Args:
        subscription_id: Mercado Pago preapproval ID from the IPN data envelope.
    """
    if not subscription_id:
        logger.warning("MP IPN subscription notification missing subscription_id")
        return

    # Publish status update job to RabbitMQ.
    # The notifications worker is responsible for:
    #   1. Fetching the preapproval resource from MP to get status + external_reference
    #   2. Parsing tenant_id from external_reference
    #   3. Updating MembershipSubscription.status in the tenant schema
    #   4. Optionally sending a membership status notification to the patient
    await publish_message(
        "notifications",
        QueueMessage(
            tenant_id="system",  # Worker resolves tenant from external_reference
            job_type="membership.mp_subscription_update",
            payload={
                "provider": "mercadopago",
                "subscription_id": subscription_id,
            },
            priority=7,  # High priority — membership status affects patient access
        ),
    )

    logger.info(
        "MP IPN: subscription update job enqueued for subscription_id=%s...",
        subscription_id[:8] if subscription_id else "unknown",
    )
