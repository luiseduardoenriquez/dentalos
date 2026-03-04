"""Twilio Voice service -- VP-18 VoIP Screen Pop.

Wraps Twilio REST API for outbound calls and call lookups.
Uses httpx with Basic auth (account_sid:auth_token) — same pattern as the
SMS service.

Security: PHI (phone numbers) is NEVER logged.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.twilio_voice")

TWILIO_API_URL = "https://api.twilio.com/2010-04-01"


class TwilioVoiceService:
    """Twilio Voice REST API client.

    All methods are async and use httpx under the hood.  The singleton
    instance ``twilio_voice_service`` is imported by the webhook router and
    the calls API router.
    """

    def is_configured(self) -> bool:
        """Return True if all required Twilio Voice settings are present."""
        return bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_voice_number
        )

    async def initiate_call(
        self,
        *,
        to_number: str,
        from_number: str | None = None,
        twiml_url: str | None = None,
    ) -> dict | None:
        """Initiate an outbound call via Twilio REST API.

        Args:
            to_number:   E.164 formatted destination phone number.
            from_number: Caller ID to use.  Defaults to
                         settings.twilio_voice_number when not provided.
            twiml_url:   URL that Twilio will request for TwiML instructions.
                         Defaults to settings.twilio_voice_webhook_url.

        Returns:
            Parsed JSON response from Twilio, or None if not configured.
        """
        if not self.is_configured():
            logger.warning("Twilio Voice not configured — skipping initiate_call")
            return None

        caller_id = from_number or settings.twilio_voice_number
        instructions_url = twiml_url or settings.twilio_voice_webhook_url

        url = (
            f"{TWILIO_API_URL}/Accounts/{settings.twilio_account_sid}/Calls.json"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={
                    "To": to_number,
                    "From": caller_id,
                    "Url": instructions_url,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_call(self, call_sid: str) -> dict | None:
        """Fetch call details from Twilio by call SID.

        Returns:
            Parsed JSON from Twilio's Calls resource, or None if not configured.
        """
        if not self.is_configured():
            logger.warning("Twilio Voice not configured — skipping get_call")
            return None

        url = (
            f"{TWILIO_API_URL}/Accounts/{settings.twilio_account_sid}"
            f"/Calls/{call_sid}.json"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()


# Module-level singleton — import this in routers and services.
twilio_voice_service = TwilioVoiceService()
