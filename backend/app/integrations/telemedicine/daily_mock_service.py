"""Mock Daily.co video provider for local development and testing.

Returns deterministic fake data so that the telemedicine flow can be exercised
end-to-end without real Daily.co credentials. Automatically used when
settings.daily_api_key is empty (dev/test environments).

Security:
  - No real API calls are made.
  - end_session() always returns True (idempotent no-op).
  - get_recording() always returns None (recordings require real sessions).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from app.integrations.telemedicine.base import TelemedicineProviderBase
from app.integrations.telemedicine.schemas import RoomResult

logger = logging.getLogger("dentalos.integrations.daily.mock")


class DailyMockService(TelemedicineProviderBase):
    """Fake Daily.co video service for development and test environments."""

    def is_configured(self) -> bool:
        """Mock is always considered configured."""
        return True

    async def create_room(
        self,
        *,
        room_name: str,
        max_participants: int = 2,
        exp_minutes: int = 120,
    ) -> RoomResult:
        """Return a deterministic mock room result.

        The provider_session_id is derived from room_name via SHA-256 so that
        the same room name always produces the same mock session ID, enabling
        idempotency testing.

        Args:
            room_name: Opaque room identifier.
            max_participants: Ignored in mock.
            exp_minutes: Ignored in mock.

        Returns:
            RoomResult with mock Daily.co-style URL.
        """
        # Deterministic session ID based on room_name
        name_hash = hashlib.sha256(room_name.encode("utf-8")).hexdigest()[:16]
        provider_session_id = f"mock-session-{name_hash}"

        room_url = f"https://dentalos.daily.co/mock-{uuid.uuid4().hex[:8]}"

        result = RoomResult(
            room_name=room_name,
            room_url=room_url,
            provider_session_id=provider_session_id,
            created_at=datetime.now(UTC),
        )

        logger.info(
            "Mock Daily.co room created: name=%s...",
            room_name[:12] if len(room_name) >= 12 else room_name,
        )

        return result

    async def get_room_url(
        self,
        *,
        room_name: str,
        is_owner: bool = False,
    ) -> str:
        """Return a deterministic mock join URL.

        The fake token is derived from room_name and is_owner flag so it is
        stable across calls (useful for snapshot tests).

        Args:
            room_name: Room identifier.
            is_owner: Whether the participant is the moderator.

        Returns:
            Mock join URL with fake token query parameter.
        """
        token_seed = f"{room_name}:{'owner' if is_owner else 'participant'}"
        fake_token = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()[:32]
        join_url = f"https://dentalos.daily.co/{room_name}?t={fake_token}"

        logger.info(
            "Mock Daily.co join URL generated: room=%s... is_owner=%s",
            room_name[:12] if len(room_name) >= 12 else room_name,
            is_owner,
        )

        return join_url

    async def end_session(self, *, room_name: str) -> bool:
        """No-op mock — always returns True.

        Args:
            room_name: Room identifier (ignored).

        Returns:
            True always.
        """
        logger.info(
            "Mock Daily.co room ended (no-op): %s...",
            room_name[:12] if len(room_name) >= 12 else room_name,
        )
        return True

    async def get_recording(self, *, room_name: str) -> str | None:
        """Always returns None — mock sessions have no cloud recordings.

        Args:
            room_name: Room identifier (ignored).

        Returns:
            None always.
        """
        return None

    async def close(self) -> None:
        """No-op for mock service."""


# Module-level singleton
daily_mock_service = DailyMockService()
