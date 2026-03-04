"""Production Daily.co video provider implementation.

Integrates with the Daily.co REST API v1 to create private video rooms, generate
short-lived meeting tokens, delete rooms, and retrieve cloud recordings.

Security:
  - All API calls use Bearer token auth (daily_api_key from settings).
  - Room names must NOT contain PHI. Callers must pass opaque identifiers.
  - Recording URLs are signed by Daily.co and expire — never cached long-term.
  - Provider errors are re-raised as RuntimeError to preserve error boundaries.
  - No PHI is logged anywhere in this module.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.telemedicine.base import TelemedicineProviderBase
from app.integrations.telemedicine.schemas import RoomResult

logger = logging.getLogger("dentalos.integrations.daily")

# Daily.co REST API v1 path fragments
_ROOMS_PATH = "/rooms"
_MEETING_TOKENS_PATH = "/meeting-tokens"
_RECORDINGS_PATH = "/recordings"


class DailyService(TelemedicineProviderBase):
    """Production Daily.co video session service."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        """Return True if the Daily.co API key is set in settings."""
        return bool(settings.daily_api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client for Daily.co."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.daily_api_url,
                headers={
                    "Authorization": f"Bearer {settings.daily_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def create_room(
        self,
        *,
        room_name: str,
        max_participants: int = 2,
        exp_minutes: int = 120,
    ) -> RoomResult:
        """Create a private Daily.co room with cloud recording enabled.

        The room is created with privacy='private', which requires a meeting
        token for all participants. Cloud recording is enabled so that sessions
        can be retrieved later for clinical audit purposes.

        Args:
            room_name: Opaque room identifier (no PHI). Daily.co requires
                room names to match ^[a-zA-Z0-9_-]+$ with max length 255.
            max_participants: Maximum concurrent participants (default 2).
            exp_minutes: Room expiry in minutes from now (default 120).

        Returns:
            RoomResult with provider room details.

        Raises:
            RuntimeError: On Daily.co API error.
        """
        if not self.is_configured():
            raise RuntimeError("Daily.co integration is not configured — DAILY_API_KEY is missing")

        exp_timestamp = int(time.time()) + (exp_minutes * 60)

        client = await self._get_client()
        try:
            response = await client.post(
                _ROOMS_PATH,
                json={
                    "name": room_name,
                    "privacy": "private",
                    "properties": {
                        "max_participants": max_participants,
                        "exp": exp_timestamp,
                        "enable_recording": "cloud",
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Daily.co create_room failed: status=%d",
                exc.response.status_code,
            )
            raise RuntimeError(
                f"Daily.co API error creating room: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Daily.co create_room network error: %s", type(exc).__name__)
            raise RuntimeError("Daily.co API network error creating room") from exc

        data: dict[str, Any] = response.json()

        # Daily.co response shape: {id, name, url, privacy, config, ...}
        provider_session_id: str = data.get("id", room_name)
        room_url: str = data.get("url", f"https://dentalos.daily.co/{room_name}")

        from datetime import UTC, datetime

        created_at = datetime.now(UTC)

        logger.info(
            "Daily.co room created: name=%s...",
            room_name[:12] if len(room_name) >= 12 else room_name,
        )

        return RoomResult(
            room_name=room_name,
            room_url=room_url,
            provider_session_id=provider_session_id,
            created_at=created_at,
        )

    async def get_room_url(
        self,
        *,
        room_name: str,
        is_owner: bool = False,
    ) -> str:
        """Generate a short-lived meeting token and return the full join URL.

        Calls POST /meeting-tokens to obtain a signed token for the participant.
        The token is embedded as a query parameter in the returned join URL.
        Tokens expire after 2 hours (matching the default room expiry).

        Args:
            room_name: The existing Daily.co room name.
            is_owner: True → doctor (moderator); False → patient (participant).

        Returns:
            Full join URL with the meeting token.

        Raises:
            RuntimeError: On Daily.co API error.
        """
        if not self.is_configured():
            raise RuntimeError("Daily.co integration is not configured")

        # Meeting tokens expire in 2 hours (7200 seconds)
        exp_timestamp = int(time.time()) + 7200

        client = await self._get_client()
        try:
            response = await client.post(
                _MEETING_TOKENS_PATH,
                json={
                    "properties": {
                        "room_name": room_name,
                        "is_owner": is_owner,
                        "exp": exp_timestamp,
                    }
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Daily.co get_room_url token generation failed: status=%d",
                exc.response.status_code,
            )
            raise RuntimeError(
                f"Daily.co API error generating meeting token: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Daily.co get_room_url network error: %s", type(exc).__name__
            )
            raise RuntimeError("Daily.co API network error generating meeting token") from exc

        token_data: dict[str, Any] = response.json()
        token: str = token_data.get("token", "")

        if not token:
            raise RuntimeError("Daily.co returned empty meeting token")

        # Extract domain from API URL to build join URL
        # Daily.co room URL format: https://<domain>.daily.co/<room_name>?t=<token>
        # Domain is the subdomain registered for the account; by default 'dentalos'
        # The full room URL is already stored in the room — we just append the token.
        # For token-only URLs we construct from room_name and base domain.
        api_base = settings.daily_api_url  # https://api.daily.co/v1
        # Domain for room URLs is the account's Daily.co subdomain, not the API host.
        # We use the room name to derive: https://dentalos.daily.co/<room_name>?t=<token>
        # In production, accounts use a custom domain or 'dentalos' subdomain.
        join_url = f"https://dentalos.daily.co/{room_name}?t={token}"

        _ = api_base  # suppress unused variable warning

        logger.info(
            "Daily.co meeting token generated: room=%s... is_owner=%s",
            room_name[:12] if len(room_name) >= 12 else room_name,
            is_owner,
        )

        return join_url

    async def end_session(self, *, room_name: str) -> bool:
        """Delete a Daily.co room, preventing further joins.

        This is a hard delete on the Daily.co side. The VideoSession record
        in the tenant DB is updated separately by the service layer.

        Args:
            room_name: The room to delete.

        Returns:
            True if deleted successfully or the room was already gone (404).

        Raises:
            RuntimeError: On non-404 Daily.co API errors.
        """
        if not self.is_configured():
            raise RuntimeError("Daily.co integration is not configured")

        client = await self._get_client()
        try:
            response = await client.delete(f"{_ROOMS_PATH}/{room_name}")
            if response.status_code == 404:
                # Room already deleted — treat as success (idempotent)
                logger.info(
                    "Daily.co end_session: room not found (already deleted): %s...",
                    room_name[:12] if len(room_name) >= 12 else room_name,
                )
                return True
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Daily.co end_session failed: status=%d",
                exc.response.status_code,
            )
            raise RuntimeError(
                f"Daily.co API error deleting room: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Daily.co end_session network error: %s", type(exc).__name__
            )
            raise RuntimeError("Daily.co API network error deleting room") from exc

        logger.info(
            "Daily.co room deleted: %s...",
            room_name[:12] if len(room_name) >= 12 else room_name,
        )
        return True

    async def get_recording(self, *, room_name: str) -> str | None:
        """Retrieve the cloud recording download URL for a session.

        Queries GET /recordings?room_name={room_name} and returns the
        download_url of the most recent recording. Returns None if no
        recording is available yet (e.g. session just ended, processing
        is in progress).

        Args:
            room_name: The room to query recordings for.

        Returns:
            Recording download URL string, or None if unavailable.

        Raises:
            RuntimeError: On Daily.co API error (except 404 → returns None).
        """
        if not self.is_configured():
            raise RuntimeError("Daily.co integration is not configured")

        client = await self._get_client()
        try:
            response = await client.get(
                _RECORDINGS_PATH,
                params={"room_name": room_name},
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error(
                "Daily.co get_recording failed: status=%d",
                exc.response.status_code,
            )
            raise RuntimeError(
                f"Daily.co API error fetching recordings: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Daily.co get_recording network error: %s", type(exc).__name__
            )
            raise RuntimeError("Daily.co API network error fetching recordings") from exc

        data: dict[str, Any] = response.json()

        # Daily.co response: {total_count: N, data: [{id, room_name, download_url, ...}]}
        recordings: list[dict[str, Any]] = data.get("data", [])
        if not recordings:
            return None

        # Return the download_url from the first (most recent) recording
        download_url: str | None = recordings[0].get("download_url")
        return download_url or None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton — reused across requests for connection pooling
daily_service = DailyService()
