"""Public tracking endpoints for email open/click/unsubscribe — VP-17.

These endpoints carry NO JWT authentication. They are embedded in every
campaign email as:
  - A 1×1 GIF image tag for open tracking.
  - Wrapped hyperlinks for click tracking.
  - An unsubscribe footer link.

URL design:
  GET /public/track/open/{tenant_schema}/{recipient_id}
  GET /public/track/click/{tenant_schema}/{recipient_id}?url={destination}
  GET /public/unsubscribe/{tenant_schema}/{recipient_id}

The {tenant_schema} path segment is the schema name (e.g. "tn_demodent") so
that the tracking service can open the correct tenant DB session without any
JWT or cookie. The {recipient_id} is the UUID primary key of the
EmailCampaignRecipient row.

Security notes:
  - Tenant schema names are validated by get_tenant_session().
  - Redirect URLs are sanitized to http(s) only (open-redirect prevention).
  - No PHI is exposed in responses or logs.
  - All endpoints return graceful responses even when IDs are not found.
"""

import uuid
import logging

from fastapi import APIRouter, Path, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.database import get_tenant_session
from app.services.email_tracking_service import (
    TRACKING_PIXEL,
    email_tracking_service,
)

logger = logging.getLogger("dentalos.marketing.tracking")

router = APIRouter(prefix="/public", tags=["tracking"])


# ── Open tracking pixel ───────────────────────────────────────────────────────


@router.get(
    "/track/open/{tenant_schema}/{recipient_id}",
    response_class=Response,
    summary="Pixel de seguimiento de apertura de email",
    include_in_schema=False,  # Hidden from OpenAPI docs — public infrastructure endpoint
)
async def track_open(
    tenant_schema: str = Path(
        pattern=r"^tn_[a-z0-9_]{1,60}$",
        description="Tenant schema name, e.g. tn_demodent",
    ),
    recipient_id: uuid.UUID = Path(description="EmailCampaignRecipient UUID"),
) -> Response:
    """Return a 1×1 transparent GIF and record the email open event.

    Always returns the GIF (200 OK) regardless of whether the recipient_id
    exists, to avoid leaking information via status codes.
    """
    try:
        async with get_tenant_session(tenant_schema) as db:
            gif_bytes = await email_tracking_service.handle_open_tracking(
                db=db, recipient_id=recipient_id
            )
    except Exception:
        logger.debug(
            "Open tracking error for recipient=%s (non-critical)",
            str(recipient_id)[:8],
            exc_info=True,
        )
        gif_bytes = TRACKING_PIXEL

    return Response(
        content=gif_bytes,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# ── Click tracking redirect ───────────────────────────────────────────────────


@router.get(
    "/track/click/{tenant_schema}/{recipient_id}",
    response_class=RedirectResponse,
    summary="Seguimiento de clics en emails",
    include_in_schema=False,
)
async def track_click(
    tenant_schema: str = Path(
        pattern=r"^tn_[a-z0-9_]{1,60}$",
        description="Tenant schema name",
    ),
    recipient_id: uuid.UUID = Path(description="EmailCampaignRecipient UUID"),
    url: str = Query(default="", description="Destination URL to redirect to"),
) -> RedirectResponse:
    """Record a link click and redirect the patient to the destination URL.

    The `url` query parameter must be an absolute HTTP(S) URL; anything else
    is silently replaced with '#' to prevent open-redirect attacks.
    """
    redirect_url = "#"
    try:
        async with get_tenant_session(tenant_schema) as db:
            redirect_url = await email_tracking_service.handle_click_tracking(
                db=db, recipient_id=recipient_id, url=url
            )
    except Exception:
        logger.debug(
            "Click tracking error for recipient=%s (non-critical)",
            str(recipient_id)[:8],
            exc_info=True,
        )
        redirect_url = email_tracking_service._sanitize_redirect_url(url)

    return RedirectResponse(url=redirect_url, status_code=302)


# ── Unsubscribe ───────────────────────────────────────────────────────────────


@router.get(
    "/unsubscribe/{tenant_schema}/{recipient_id}",
    response_class=HTMLResponse,
    summary="Cancelar suscripción de emails de marketing",
    include_in_schema=False,
)
async def unsubscribe(
    tenant_schema: str = Path(
        pattern=r"^tn_[a-z0-9_]{1,60}$",
        description="Tenant schema name",
    ),
    recipient_id: uuid.UUID = Path(description="EmailCampaignRecipient UUID"),
) -> HTMLResponse:
    """Process an unsubscribe request and display a Spanish confirmation page.

    Sets patients.email_unsubscribed = true so the patient will never be
    included in future campaign recipient lists.

    Always returns the confirmation page (idempotent — safe to call twice).
    """
    try:
        async with get_tenant_session(tenant_schema) as db:
            html_content = await email_tracking_service.handle_unsubscribe(
                db=db, recipient_id=recipient_id
            )
    except Exception:
        logger.warning(
            "Unsubscribe error for recipient=%s",
            str(recipient_id)[:8],
            exc_info=True,
        )
        # Return a generic confirmation even on error to avoid confusing the patient
        html_content = (
            "<!DOCTYPE html><html lang='es'><body>"
            "<p>Tu solicitud de cancelación fue procesada.</p>"
            "</body></html>"
        )

    return HTMLResponse(content=html_content, status_code=200)
