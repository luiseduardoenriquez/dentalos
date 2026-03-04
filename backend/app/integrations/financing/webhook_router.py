"""Financing provider webhook routes -- VP-11 / Sprint 29-30.

POST /webhooks/financing/addi         — Addi status notifications
POST /webhooks/financing/sistecredito — Sistecrédito status notifications

Security:
  - Validates provider-specific HMAC-SHA256 signatures
  - NO JWT auth -- webhooks use provider-specific signature verification
  - PHI is NEVER logged from webhook payloads
  - Only the first 8 characters of provider_reference are logged
  - tenant_id is extracted from the webhook payload (set at application creation)
"""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_tenant_session
from app.integrations.financing.addi_service import addi_service
from app.integrations.financing.sistecredito_service import sistecredito_service

logger = logging.getLogger("dentalos.integrations.financing.webhook")

router = APIRouter(prefix="/webhooks/financing", tags=["webhooks"])


# -- Inbound webhook payload schemas ------------------------------------------


class AddiWebhookPayload(BaseModel):
    """Payload received from Addi webhook notifications."""

    event_type: str
    application_id: str
    status: str
    approved_amount: int | None = None  # Full COP from Addi
    disbursed_at: str | None = None
    tenant_id: str  # DentalOS tenant ID, echoed back from external_reference metadata


class SistecreditoWebhookPayload(BaseModel):
    """Payload received from Sistecrédito webhook notifications."""

    evento: str
    id_credito: str
    estado: str
    valor_aprobado: int | None = None  # Full COP from Sistecrédito
    fecha_desembolso: str | None = None
    tenant_id: str  # DentalOS tenant ID, echoed back from referencia_externa metadata


# -- Addi webhook -------------------------------------------------------------


@router.post("/addi")
async def receive_addi_webhook(
    request: Request,
    x_addi_signature: str = Header(..., alias="X-Addi-Signature"),
) -> dict[str, str]:
    """Process Addi financing webhook notifications.

    Validates the HMAC-SHA256 signature from the X-Addi-Signature header,
    parses the application event, and updates the financing application status
    in the tenant database.

    Returns 200 immediately to acknowledge receipt. Addi retries on non-2xx.
    """
    body = await request.body()

    # Verify webhook signature (timing-safe HMAC-SHA256)
    if not addi_service.verify_webhook(body, x_addi_signature):
        logger.warning("Addi webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse the webhook payload
    try:
        payload = AddiWebhookPayload.model_validate_json(body)
    except Exception:
        logger.warning("Addi webhook payload parsing failed")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Log only safe, truncated identifiers -- never PHI or financial details
    logger.info(
        "Addi webhook received: event=%s ref=%s... status=%s",
        payload.event_type,
        payload.application_id[:8] if payload.application_id else "unknown",
        payload.status,
    )

    # Update application status in the tenant database
    try:
        approved_amount_cents: int | None = None
        if payload.approved_amount is not None:
            approved_amount_cents = payload.approved_amount * 100  # Convert COP to cents

        async with get_tenant_session(payload.tenant_id) as db:
            await _update_application_status(
                db=db,
                provider="addi",
                provider_reference=payload.application_id,
                new_status=payload.status,
                approved_amount_cents=approved_amount_cents,
                disbursed_at=payload.disbursed_at,
            )
    except ValueError:
        # Tenant not found — still return 200 to prevent Addi retry loops
        logger.error(
            "Addi webhook: tenant not found for ref=%s...",
            payload.application_id[:8],
        )
    except Exception:
        logger.exception(
            "Addi webhook processing failed: ref=%s...",
            payload.application_id[:8],
        )
        # Return 200 to prevent retry storms; failed updates can be reconciled manually
        # via the get_status polling endpoint

    return {"status": "ok"}


# -- Sistecrédito webhook -----------------------------------------------------


@router.post("/sistecredito")
async def receive_sistecredito_webhook(
    request: Request,
    x_sistecredito_signature: str = Header(..., alias="X-Sistecredito-Signature"),
) -> dict[str, str]:
    """Process Sistecrédito financing webhook notifications.

    Validates the HMAC-SHA256 signature from the X-Sistecredito-Signature header,
    parses the credit event, and updates the financing application status
    in the tenant database.

    Returns 200 immediately to acknowledge receipt. Sistecrédito retries on non-2xx.
    """
    body = await request.body()

    # Verify webhook signature (timing-safe HMAC-SHA256)
    if not sistecredito_service.verify_webhook(body, x_sistecredito_signature):
        logger.warning("Sistecrédito webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse the webhook payload
    try:
        payload = SistecreditoWebhookPayload.model_validate_json(body)
    except Exception:
        logger.warning("Sistecrédito webhook payload parsing failed")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Log only safe, truncated identifiers -- never PHI or financial details
    logger.info(
        "Sistecrédito webhook received: event=%s ref=%s... status=%s",
        payload.evento,
        payload.id_credito[:8] if payload.id_credito else "unknown",
        payload.estado,
    )

    # Update application status in the tenant database
    try:
        approved_amount_cents: int | None = None
        if payload.valor_aprobado is not None:
            approved_amount_cents = payload.valor_aprobado * 100  # Convert COP to cents

        async with get_tenant_session(payload.tenant_id) as db:
            await _update_application_status(
                db=db,
                provider="sistecredito",
                provider_reference=payload.id_credito,
                new_status=payload.estado,
                approved_amount_cents=approved_amount_cents,
                disbursed_at=payload.fecha_desembolso,
            )
    except ValueError:
        # Tenant not found — still return 200 to prevent Sistecrédito retry loops
        logger.error(
            "Sistecrédito webhook: tenant not found for ref=%s...",
            payload.id_credito[:8],
        )
    except Exception:
        logger.exception(
            "Sistecrédito webhook processing failed: ref=%s...",
            payload.id_credito[:8],
        )
        # Return 200 to prevent retry storms

    return {"status": "ok"}


# -- Shared DB update helper --------------------------------------------------


async def _update_application_status(
    db: Any,
    provider: str,
    provider_reference: str,
    new_status: str,
    approved_amount_cents: int | None,
    disbursed_at: str | None,
) -> None:
    """Update a financing application's status in the tenant database.

    Looks up the application by provider_reference, updates its status,
    and if the application is now disbursed, records the disbursement timestamp.

    Args:
        db: Tenant-scoped AsyncSession.
        provider: Provider name (addi, sistecredito).
        provider_reference: Provider-assigned application identifier.
        new_status: New application status from the webhook.
        approved_amount_cents: Approved amount in COP cents (null if not yet approved).
        disbursed_at: ISO datetime string when funds were disbursed (null if not yet).
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.tenant.financing import FinancingApplication

    result = await db.execute(
        select(FinancingApplication).where(
            FinancingApplication.provider == provider,
            FinancingApplication.provider_reference == provider_reference,
        )
    )
    application = result.scalar_one_or_none()

    if application is None:
        logger.warning(
            "Financing webhook: application not found: provider=%s ref=%s...",
            provider,
            provider_reference[:8],
        )
        return

    application.status = new_status

    if new_status == "approved" and application.approved_at is None:
        application.approved_at = datetime.now(UTC)

    if disbursed_at and application.disbursed_at is None:
        try:
            application.disbursed_at = datetime.fromisoformat(
                disbursed_at.replace("Z", "+00:00")
            )
        except ValueError:
            application.disbursed_at = datetime.now(UTC)

    if new_status in ("completed", "paid_off"):
        application.completed_at = datetime.now(UTC)

    await db.flush()

    logger.info(
        "Financing application updated: provider=%s ref=%s... status=%s",
        provider,
        provider_reference[:8],
        new_status,
    )
