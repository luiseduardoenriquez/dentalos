"""Twilio SMS webhook routes — INT-02.

POST /webhooks/twilio/status — Delivery status callbacks

Security:
  - Validates Twilio request signature (X-Twilio-Signature header)
  - Uses HMAC-SHA1 per Twilio's webhook signing spec
  - NO JWT auth — uses provider-specific signature verification
  - PHI (phone numbers) is NEVER logged
"""

import hashlib
import hmac
import logging
from base64 import b64encode
from urllib.parse import urljoin  # noqa: F401

from fastapi import APIRouter, Form, Header, HTTPException, Request

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.sms.webhook")

router = APIRouter(prefix="/webhooks/twilio", tags=["webhooks"])


def _build_twilio_signature(
    url: str, params: dict[str, str], auth_token: str
) -> str:
    """Compute Twilio request signature per their spec.

    1. Take the full URL of the request.
    2. Sort POST parameters alphabetically by name.
    3. Concatenate parameter names and values to the URL.
    4. HMAC-SHA1 with the auth token as key, base64-encode result.
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
    """Verify Twilio X-Twilio-Signature header."""
    if not settings.twilio_auth_token:
        return False
    expected = _build_twilio_signature(url, params, settings.twilio_auth_token)
    return hmac.compare_digest(expected, signature)


@router.post("/status")
async def twilio_status_callback(
    request: Request,
    x_twilio_signature: str = Header(..., alias="X-Twilio-Signature"),
    MessageSid: str = Form(""),
    MessageStatus: str = Form(""),
    ErrorCode: str | None = Form(None),
) -> dict[str, str]:
    """Process Twilio delivery status webhook.

    Twilio sends POST with form-encoded data and X-Twilio-Signature header.
    We verify the signature before processing.
    """
    # Reconstruct the full URL for signature verification
    url = str(request.url)

    # Get all form params for signature computation
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    if not _verify_twilio_signature(url, params, x_twilio_signature):
        logger.warning("Twilio webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Log only SID and status — never phone numbers (PHI)
    logger.info(
        "Twilio delivery status: sid=%s status=%s error_code=%s",
        MessageSid,
        MessageStatus,
        ErrorCode,
    )

    return {"status": "ok"}
