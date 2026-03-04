"""Twilio Voice webhook routes -- VP-18 VoIP Screen Pop.

POST /webhooks/twilio/voice/{tenant_slug}/incoming  -- Incoming call webhook
POST /webhooks/twilio/voice/{tenant_slug}/status     -- Call status callback

Security:
  - Validates Twilio request signature (X-Twilio-Signature HMAC-SHA1)
  - NO JWT auth — uses provider-specific signature verification
  - PHI (phone numbers) is NEVER logged

Tenant resolution:
  - slug path parameter → public.tenants lookup → schema_name
  - Scoped DB session opened via get_tenant_session(schema_name)
"""

import hashlib
import hmac
import logging
from base64 import b64encode

from fastapi import APIRouter, Form, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.twilio_voice.webhook")

router = APIRouter(prefix="/webhooks/twilio/voice", tags=["webhooks"])


# ─── Signature helpers ────────────────────────────────────────────────────────


def _build_twilio_signature(
    url: str, params: dict[str, str], auth_token: str
) -> str:
    """Compute Twilio request signature (HMAC-SHA1).

    Algorithm per Twilio docs:
    1. Take the full URL of the request (including query string).
    2. Sort all POST parameters alphabetically (case-sensitive).
    3. Append each parameter name and value to the URL string.
    4. Sign with HMAC-SHA1 using auth_token as the key and base64-encode.
    """
    sorted_params = sorted(params.items())
    data_string = url + "".join(f"{k}{v}" for k, v in sorted_params)
    signature = hmac.new(
        auth_token.encode("utf-8"),
        data_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return b64encode(signature).decode("utf-8")


def _verify_twilio_signature(
    url: str, params: dict[str, str], signature: str
) -> bool:
    """Verify Twilio X-Twilio-Signature header using constant-time comparison."""
    if not settings.twilio_auth_token:
        return False
    expected = _build_twilio_signature(url, params, settings.twilio_auth_token)
    return hmac.compare_digest(expected, signature)


# ─── Tenant resolution ────────────────────────────────────────────────────────


async def _resolve_tenant_by_slug(slug: str) -> tuple[str, str] | None:
    """Resolve a tenant slug to (tenant_id, schema_name).

    Queries public.tenants by slug.  Returns None if not found or not active.
    """
    try:
        from sqlalchemy import text

        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT id::text, schema_name "
                    "FROM public.tenants "
                    "WHERE slug = :slug AND status = 'active' "
                    "LIMIT 1"
                ),
                {"slug": slug},
            )
            row = result.first()
            if row:
                return row[0], row[1]
    except Exception:
        logger.exception(
            "Tenant resolution failed for slug — voice webhook aborted"
        )
    return None


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/{tenant_slug}/incoming")
async def incoming_call_webhook(
    tenant_slug: str,
    request: Request,
    x_twilio_signature: str = Header(..., alias="X-Twilio-Signature"),
    CallSid: str = Form(""),
    From: str = Form(""),
    To: str = Form(""),
    CallStatus: str = Form("ringing"),
) -> PlainTextResponse:
    """Handle an incoming Twilio Voice call.

    Webhook flow:
    1. Verify HMAC-SHA1 signature.
    2. Resolve tenant by slug from public.tenants.
    3. Open tenant-scoped DB session.
    4. Match caller phone number to an active patient.
    5. Create call_log row with direction='inbound'.
    6. Publish screen-pop event to Redis channel.
    7. Return TwiML to Twilio so the call is handled correctly.

    PHI: phone numbers are NEVER logged — only call SID and tenant slug.
    """
    url = str(request.url)
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    if not _verify_twilio_signature(url, params, x_twilio_signature):
        logger.warning(
            "Twilio Voice incoming webhook signature verification failed: "
            "slug=%s sid=%s",
            tenant_slug,
            CallSid,
        )
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Log only non-PHI fields
    logger.info(
        "Incoming call webhook: sid=%s slug=%s status=%s",
        CallSid,
        tenant_slug,
        CallStatus,
    )

    # Resolve tenant
    tenant_info = await _resolve_tenant_by_slug(tenant_slug)
    if tenant_info is None:
        logger.warning("Unknown tenant slug in voice webhook: slug=%s", tenant_slug)
        # Still return valid TwiML so Twilio doesn't retry aggressively
        return PlainTextResponse(
            content=(
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response>"
                '<Say language="es-MX">Lo sentimos, esta línea no está disponible.</Say>'
                "</Response>"
            ),
            media_type="application/xml",
        )

    tenant_id, schema_name = tenant_info

    # Process asynchronously in tenant-scoped DB session
    try:
        from app.core.database import get_tenant_session
        from app.services.call_log_service import call_log_service

        async with get_tenant_session(schema_name) as db:
            # Match caller to a patient record (exact phone match)
            patient_id = await call_log_service.match_phone_to_patient(db, From)

            # Create call log
            call = await call_log_service.create_call_log(
                db,
                phone_number=From,
                direction="inbound",
                twilio_call_sid=CallSid if CallSid else None,
                patient_id=patient_id,
            )

            # Publish screen-pop event to Redis
            try:
                await call_log_service.publish_incoming_call(
                    tenant_id,
                    {
                        "call_id": str(call.id),
                        "direction": "inbound",
                        "patient_id": str(patient_id) if patient_id else None,
                        "call_status": CallStatus,
                    },
                )
            except Exception:
                # Redis pub/sub is a performance enhancement, not critical
                logger.warning(
                    "Failed to publish incoming call event to Redis: sid=%s",
                    CallSid,
                )

    except Exception:
        logger.exception(
            "Error processing incoming call log: sid=%s slug=%s",
            CallSid,
            tenant_slug,
        )

    # Always return valid TwiML to Twilio regardless of DB/Redis outcome
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Say language="es-MX">Bienvenido a la clínica</Say>'
        "</Response>"
    )
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/{tenant_slug}/status")
async def call_status_webhook(
    tenant_slug: str,
    request: Request,
    x_twilio_signature: str = Header(..., alias="X-Twilio-Signature"),
    CallSid: str = Form(""),
    CallStatus: str = Form(""),
    CallDuration: str | None = Form(None),
) -> dict[str, str]:
    """Handle Twilio call status callback.

    Updates the call_log row with the final status and duration.
    PHI (phone numbers) is NEVER logged.
    """
    url = str(request.url)
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    if not _verify_twilio_signature(url, params, x_twilio_signature):
        logger.warning(
            "Twilio Voice status webhook signature verification failed: "
            "slug=%s sid=%s",
            tenant_slug,
            CallSid,
        )
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Log only non-PHI fields
    logger.info(
        "Call status update: sid=%s slug=%s status=%s duration=%s",
        CallSid,
        tenant_slug,
        CallStatus,
        CallDuration,
    )

    # Status mapping: Twilio uses 'completed', 'no-answer', 'busy', 'failed',
    # 'canceled'; our schema CHECK allows 'ringing','in_progress','completed',
    # 'missed','voicemail'.  Map unknown statuses to the closest equivalent.
    _STATUS_MAP: dict[str, str] = {
        "completed": "completed",
        "in-progress": "in_progress",
        "ringing": "ringing",
        "queued": "ringing",
        "no-answer": "missed",
        "busy": "missed",
        "failed": "missed",
        "canceled": "missed",
    }
    mapped_status = _STATUS_MAP.get(CallStatus, "missed")

    duration_seconds: int | None = None
    if CallDuration:
        try:
            duration_seconds = int(CallDuration)
        except ValueError:
            pass

    if not CallSid:
        return {"status": "ok"}

    # Resolve tenant and update call log
    tenant_info = await _resolve_tenant_by_slug(tenant_slug)
    if tenant_info is None:
        logger.warning(
            "Unknown tenant slug in voice status callback: slug=%s", tenant_slug
        )
        return {"status": "ok"}

    _tenant_id, schema_name = tenant_info

    try:
        from app.core.database import get_tenant_session
        from app.services.call_log_service import call_log_service

        async with get_tenant_session(schema_name) as db:
            await call_log_service.update_call_status(
                db,
                twilio_call_sid=CallSid,
                status=mapped_status,
                duration_seconds=duration_seconds,
            )
    except Exception:
        logger.exception(
            "Error updating call status: sid=%s slug=%s",
            CallSid,
            tenant_slug,
        )

    return {"status": "ok"}
