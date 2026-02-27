"""Google Calendar sync stub — INT-09.

This is a placeholder integration for future implementation.
Currently raises NotImplementedError on all operations.
The validate_config() method can be used to check if OAuth credentials are set.
"""

import logging

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.calendar.google")


class GoogleCalendarService:
    """Google Calendar sync stub."""

    def validate_config(self) -> bool:
        """Check if Google OAuth credentials are configured."""
        return bool(
            settings.google_client_id
            and settings.google_client_secret
        )

    async def get_auth_url(self, *, redirect_uri: str) -> str:
        """Generate OAuth2 authorization URL.

        Raises:
            NotImplementedError: Always — stub for future implementation.
        """
        raise NotImplementedError(
            "Google Calendar OAuth pending (INT-09). "
            "Configure google_client_id and google_client_secret."
        )

    async def exchange_code(self, *, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for tokens.

        Raises:
            NotImplementedError: Always — stub for future implementation.
        """
        raise NotImplementedError(
            "Google Calendar OAuth token exchange pending (INT-09)."
        )

    async def sync_appointment(
        self,
        *,
        tenant_id: str,
        user_id: str,
        appointment_id: str,
        summary: str,
        start_time: str,
        end_time: str,
    ) -> dict:
        """Sync an appointment to Google Calendar.

        Raises:
            NotImplementedError: Always — stub for future implementation.
        """
        raise NotImplementedError(
            "Google Calendar appointment sync pending (INT-09)."
        )


# Module-level singleton
google_calendar_service = GoogleCalendarService()
