"""WhatsApp Business API service -- INT-01.

Uses Meta Cloud API to send template messages via WhatsApp.
PHI is NEVER included in WhatsApp messages -- only appointment IDs,
doctor names, and clinic names are allowed.

Security:
  - Access token stored in env, never logged
  - Message content is scrubbed for PHI before sending
  - All API calls use httpx with timeouts
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.whatsapp")

# Meta Cloud API base URL
META_API_BASE = "https://graph.facebook.com/v21.0"

# Fields that must NEVER appear in WhatsApp messages (PHI)
_PHI_FIELDS = {
    "document_number",
    "cedula",
    "phone",
    "email",
    "diagnosis",
    "clinical_notes",
}


def _scrub_phi(data: dict[str, Any]) -> dict[str, str]:
    """Remove PHI fields from template parameter data."""
    return {k: str(v) for k, v in data.items() if k not in _PHI_FIELDS}


class WhatsAppService:
    """Sends template messages via Meta WhatsApp Cloud API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=META_API_BASE,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Bearer {settings.whatsapp_access_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def is_configured(self) -> bool:
        """Check if WhatsApp integration is properly configured."""
        return bool(
            settings.whatsapp_access_token
            and settings.whatsapp_phone_number_id
        )

    async def send_template_message(
        self,
        *,
        to_phone: str,
        template_name: str,
        language_code: str = "es",
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a WhatsApp template message.

        Args:
            to_phone: Recipient phone in E.164 format (e.g., +573001234567).
            template_name: Pre-approved Meta template name.
            language_code: Template language code (default: "es" for Spanish).
            parameters: Template body parameters (PHI will be scrubbed).

        Returns:
            Meta API response dict with message_id.

        Raises:
            httpx.HTTPStatusError: On API failure.
        """
        if not self.is_configured():
            logger.warning("WhatsApp not configured, skipping message send")
            return {"status": "skipped", "reason": "not_configured"}

        # Scrub PHI from parameters
        clean_params = _scrub_phi(parameters) if parameters else {}

        # Build template components
        components: list[dict[str, Any]] = []
        if clean_params:
            body_params = [
                {"type": "text", "text": v}
                for v in clean_params.values()
            ]
            components.append({
                "type": "body",
                "parameters": body_params,
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }

        client = await self._get_client()
        response = await client.post(
            f"/{settings.whatsapp_phone_number_id}/messages",
            json=payload,
        )
        response.raise_for_status()

        result: dict[str, Any] = response.json()
        # Log only message ID, never recipient phone (PHI)
        msg_id = result.get("messages", [{}])[0].get("id", "unknown")
        logger.info(
            "WhatsApp template sent: message_id=%s template=%s",
            msg_id,
            template_name,
        )

        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton
whatsapp_service = WhatsAppService()
