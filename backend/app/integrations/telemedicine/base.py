"""Abstract base class for the Telemedicine video provider service.

Defines the contract that both the production service (Daily.co) and the mock
service must implement. This enables seamless swapping between real and fake
backends via dependency injection or feature flags.

Security:
  - PHI (patient names, document numbers) is NEVER passed to or returned from
    these methods. Room names must be opaque identifiers only.
  - Recording URLs (when returned) must be stored and transmitted over TLS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.telemedicine.schemas import RoomResult


class TelemedicineProviderBase(ABC):
    """Contract for telemedicine video session operations."""

    @abstractmethod
    async def create_room(
        self,
        *,
        room_name: str,
        max_participants: int = 2,
        exp_minutes: int = 120,
    ) -> RoomResult:
        """Create a new video room on the provider.

        Args:
            room_name: Opaque room identifier (e.g. 'dentalos-abc12345-def67890').
                Must be URL-safe and contain NO PHI.
            max_participants: Maximum number of concurrent participants allowed.
                Defaults to 2 (doctor + patient).
            exp_minutes: Minutes from now before the room expires automatically.
                Defaults to 120 (2 hours).

        Returns:
            RoomResult with room_name, room_url, provider_session_id, created_at.

        Raises:
            RuntimeError: If the provider API call fails.
        """
        ...

    @abstractmethod
    async def get_room_url(
        self,
        *,
        room_name: str,
        is_owner: bool = False,
    ) -> str:
        """Generate a participant join URL with a short-lived meeting token.

        Owners (is_owner=True) receive moderator privileges: they can mute
        participants, end the meeting, and access recording controls.
        Patients (is_owner=False) join as regular participants.

        Args:
            room_name: The room identifier previously returned by create_room().
            is_owner: If True, the token grants moderator/owner privileges.
                Doctors receive is_owner=True; patients receive is_owner=False.

        Returns:
            Fully-qualified join URL including the meeting token as a query
            parameter (e.g. 'https://dentalos.daily.co/abc123?t=<token>').

        Raises:
            RuntimeError: If the provider API call fails.
        """
        ...

    @abstractmethod
    async def end_session(self, *, room_name: str) -> bool:
        """Permanently delete a video room on the provider.

        Once deleted, the room_name can no longer be joined. Calling this
        method is idempotent — if the room does not exist it should still
        return True rather than raising.

        Args:
            room_name: The room identifier to delete.

        Returns:
            True if the room was deleted (or already did not exist).

        Raises:
            RuntimeError: If the provider API call fails with a non-404 error.
        """
        ...

    @abstractmethod
    async def get_recording(self, *, room_name: str) -> str | None:
        """Retrieve the cloud recording download URL for a completed session.

        Daily.co cloud recordings are available a few minutes after a session
        ends. Returns None if no recording is available yet or if cloud
        recording was not enabled.

        Args:
            room_name: The room identifier to query recordings for.

        Returns:
            Recording download URL string, or None if unavailable.

        Raises:
            RuntimeError: If the provider API call fails.
        """
        ...
