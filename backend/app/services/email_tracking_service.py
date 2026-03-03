"""Email open/click/unsubscribe tracking service — VP-17.

These methods are called by the public tracking endpoints that carry NO JWT.
They receive only a recipient_id (UUID) and the tenant schema name (encoded
in the URL path). The tenant session is opened by the router via
get_tenant_session().

Security invariants:
  - PHI is NEVER logged. recipient_id is the only identifier used in logs.
  - Unsubscribe is permanent and immediate — sets patients.email_unsubscribed.
  - Tracking pixel is a 1×1 transparent GIF so no browser rendering issues.
  - Click tracking redirects only to the destination URL stored by the caller;
    the `url` query parameter is validated to start with http(s).
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import MarketingErrors
from app.core.exceptions import DentalOSError
from app.models.tenant.email_campaign import EmailCampaign, EmailCampaignRecipient
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.marketing.tracking")

# ── 1×1 transparent GIF (43 bytes) ──────────────────────────────────────────
# Standard tracking pixel used by all major ESPs.
TRACKING_PIXEL = bytes(
    [
        0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
        0x01, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF,
        0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x01, 0x00,
        0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
        0x01, 0x00, 0x3B,
    ]
)

# ── Spanish unsubscribe confirmation HTML ────────────────────────────────────
_UNSUBSCRIBE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cancelaste tu suscripción</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }}
    .card {{
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,.08);
      padding: 48px 40px;
      max-width: 460px;
      text-align: center;
    }}
    .icon {{ font-size: 48px; margin-bottom: 16px; }}
    h1 {{ color: #1e293b; font-size: 22px; margin: 0 0 12px; }}
    p  {{ color: #64748b; font-size: 15px; line-height: 1.6; margin: 0 0 8px; }}
    .small {{ font-size: 13px; color: #94a3b8; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <h1>Suscripción cancelada</h1>
    <p>Has sido eliminado(a) exitosamente de nuestra lista de correos.</p>
    <p>Ya no recibirás emails de marketing de <strong>{clinic_name}</strong>.</p>
    <p class="small">
      Si esto fue un error, comunícate con la clínica directamente.
    </p>
  </div>
</body>
</html>"""


class EmailTrackingService:
    """Handles open pixel, click redirect, and unsubscribe for email campaigns.

    All methods are designed to be called from public (no-auth) endpoints.
    They never raise errors that would expose tenant details — on lookup
    failures they return gracefully (pixel / redirect / generic page).
    """

    # ── Open tracking ─────────────────────────────────────────────────────────

    async def handle_open_tracking(
        self,
        db: AsyncSession,
        recipient_id: uuid.UUID,
    ) -> bytes:
        """Record an email open and return the 1×1 transparent GIF.

        Always returns the GIF bytes, even if the recipient is not found, to
        avoid leaking information about whether the address exists.

        Side-effects (only when recipient found and status allows update):
          - Sets recipient.status = 'opened', recipient.opened_at = now.
          - Increments campaign.open_count by 1.
        """
        now = datetime.now(UTC)

        recipient = await self._get_recipient(db, recipient_id)
        if recipient is not None and recipient.status in ("sent", "pending"):
            recipient.status = "opened"
            recipient.opened_at = now

            # Increment counter on the parent campaign (best-effort)
            await db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(open_count=EmailCampaign.open_count + 1)
            )
            await db.flush()
            logger.debug(
                "Email open tracked: recipient=%s", str(recipient_id)[:8]
            )

        return TRACKING_PIXEL

    # ── Click tracking ────────────────────────────────────────────────────────

    async def handle_click_tracking(
        self,
        db: AsyncSession,
        recipient_id: uuid.UUID,
        url: str,
    ) -> str:
        """Record a link click and return the validated destination URL.

        The caller (router) issues a RedirectResponse with the returned URL.

        Args:
            url: The destination URL passed as a query parameter. Must start
                 with 'http://' or 'https://'; rejected strings fall back to '#'.

        Side-effects (only when recipient found):
          - Sets recipient.status = 'clicked', recipient.clicked_at = now.
          - Increments campaign.click_count by 1.
        """
        now = datetime.now(UTC)
        safe_url = self._sanitize_redirect_url(url)

        recipient = await self._get_recipient(db, recipient_id)
        if recipient is not None and recipient.status in ("sent", "pending", "opened"):
            recipient.status = "clicked"
            if recipient.clicked_at is None:
                recipient.clicked_at = now

            await db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(click_count=EmailCampaign.click_count + 1)
            )
            await db.flush()
            logger.debug(
                "Email click tracked: recipient=%s", str(recipient_id)[:8]
            )

        return safe_url

    # ── Unsubscribe ───────────────────────────────────────────────────────────

    async def handle_unsubscribe(
        self,
        db: AsyncSession,
        recipient_id: uuid.UUID,
    ) -> str:
        """Process an unsubscribe request and return the Spanish confirmation page.

        Side-effects (only when recipient found):
          - Sets recipient.status = 'unsubscribed'.
          - Sets patients.email_unsubscribed = true, email_unsubscribed_at = now.
          - Increments campaign.unsubscribe_count by 1.

        Always returns the HTML confirmation page regardless of lookup result
        so the patient always sees a confirmation (idempotent behaviour).
        """
        now = datetime.now(UTC)
        clinic_name = "la clínica"

        recipient = await self._get_recipient(db, recipient_id)
        if recipient is not None:
            # Idempotent: only update if not already unsubscribed
            if recipient.status != "unsubscribed":
                recipient.status = "unsubscribed"

                await db.execute(
                    update(Patient)
                    .where(Patient.id == recipient.patient_id)
                    .values(
                        email_unsubscribed=True,
                        email_unsubscribed_at=now,
                    )
                )
                await db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == recipient.campaign_id)
                    .values(
                        unsubscribe_count=EmailCampaign.unsubscribe_count + 1
                    )
                )
                await db.flush()
                logger.info(
                    "Email unsubscribe processed: recipient=%s",
                    str(recipient_id)[:8],
                )

        return _UNSUBSCRIBE_HTML.format(clinic_name=clinic_name)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_recipient(
        self,
        db: AsyncSession,
        recipient_id: uuid.UUID,
    ) -> EmailCampaignRecipient | None:
        """Load a recipient row. Returns None silently if not found."""
        result = await db.execute(
            select(EmailCampaignRecipient).where(
                EmailCampaignRecipient.id == recipient_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _sanitize_redirect_url(url: str) -> str:
        """Return url if it starts with http(s)://, else return '#'.

        Prevents open redirect abuse by only allowing absolute HTTP URLs.
        """
        stripped = (url or "").strip()
        if stripped.lower().startswith("http://") or stripped.lower().startswith(
            "https://"
        ):
            return stripped
        logger.warning(
            "Rejected unsafe redirect URL in click tracking: url_prefix=%s",
            stripped[:20] if stripped else "<empty>",
        )
        return "#"


# Module-level singleton
email_tracking_service = EmailTrackingService()
