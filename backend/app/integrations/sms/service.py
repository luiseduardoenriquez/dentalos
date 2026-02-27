"""Twilio SMS service — INT-02.

Sends SMS messages via Twilio REST API using httpx (not the Twilio SDK
to avoid adding a heavy dependency — httpx is already in deps).

Security:
  - PHI is NEVER included in SMS messages
  - Twilio auth token never logged
  - Country-based sender routing for LATAM numbers
"""

import logging
from base64 import b64encode
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.sms")

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class TwilioSMSService:
    """Sends SMS via Twilio REST API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # Basic auth: account_sid:auth_token
            credentials = b64encode(
                f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
            ).decode()
            self._client = httpx.AsyncClient(
                base_url=TWILIO_API_BASE,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Basic {credentials}",
                },
            )
        return self._client

    def is_configured(self) -> bool:
        """Check if Twilio integration is properly configured."""
        return bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        )

    def _get_from_number(self, to_phone: str) -> str:
        """Get the sender number based on recipient country.

        Routes to country-specific Twilio numbers if configured,
        falls back to the default number.
        """
        # For now, use the default from number
        # Future: add per-country routing based on +XX prefix
        return settings.twilio_from_number

    async def send_sms(
        self,
        *,
        to_phone: str,
        body: str,
    ) -> dict[str, Any]:
        """Send an SMS message via Twilio.

        Args:
            to_phone: Recipient phone in E.164 format (+573001234567).
            body: Message body (max 1600 chars). Must NOT contain PHI.

        Returns:
            Twilio API response with sid, status.
        """
        if not self.is_configured():
            logger.warning("Twilio not configured, skipping SMS send")
            return {"status": "skipped", "reason": "not_configured"}

        from_number = self._get_from_number(to_phone)

        client = await self._get_client()
        response = await client.post(
            f"/Accounts/{settings.twilio_account_sid}/Messages.json",
            data={
                "To": to_phone,
                "From": from_number,
                "Body": body[:1600],  # Twilio max
            },
        )
        response.raise_for_status()

        result = response.json()
        sid = result.get("sid", "unknown")
        # Log only SID — never phone numbers (PHI)
        logger.info("SMS sent: sid=%s status=%s", sid, result.get("status"))

        return result

    async def send_otp(
        self,
        *,
        to_phone: str,
        code: str,
    ) -> dict[str, Any]:
        """Send an OTP verification code via SMS.

        Uses a standardized message format. The code itself is not PHI.
        """
        body = f"Tu código de verificación DentalOS es: {code}. Válido por 10 minutos."
        return await self.send_sms(to_phone=to_phone, body=body)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton
twilio_sms_service = TwilioSMSService()
