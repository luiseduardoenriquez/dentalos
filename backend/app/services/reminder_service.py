"""Reminder configuration service.

Manages per-tenant appointment reminder settings. Each tenant has exactly one
ReminderConfig row that is auto-created with sensible defaults on first access.

Security invariants:
  - No PHI — reminder config contains only channel/timing rules, not patient data.
  - No hard deletion — config rows are updated in place (not clinical data, but
    kept consistent with overall soft-delete philosophy for audit purposes).
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant.reminder_config import ReminderConfig

logger = logging.getLogger("dentalos.reminder")


class ReminderService:
    """Manages per-tenant appointment reminder configuration.

    Provides get/update operations. The first call to get_config auto-creates
    the row with safe defaults if it does not yet exist (idempotent).
    """

    # ------------------------------------------------------------------
    # Get (auto-create on first access)
    # ------------------------------------------------------------------

    async def get_config(self, *, db: AsyncSession) -> dict[str, Any]:
        """Return the tenant's reminder configuration.

        Creates a default config row if none exists yet (idempotent).
        Default: single 24h SMS reminder, max 3 rules.
        """
        result = await db.execute(select(ReminderConfig).limit(1))
        config = result.scalar_one_or_none()

        if config is None:
            config = ReminderConfig(
                reminders=[{"hours_before": 24, "channels": ["sms"]}],
                default_channels=["sms"],
                max_reminders_allowed=3,
            )
            db.add(config)
            await db.flush()
            await db.refresh(config)
            logger.info("Reminder config auto-created with defaults")

        return self._to_dict(config)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_config(
        self,
        *,
        db: AsyncSession,
        reminders: list[dict] | None = None,
        default_channels: list[str] | None = None,
        max_reminders_allowed: int | None = None,
    ) -> dict[str, Any]:
        """Update the tenant's reminder configuration.

        Only the provided fields are updated; omitted fields are left unchanged.
        Ensures the config row exists before applying changes.
        """
        # Ensure the row exists
        await self.get_config(db=db)

        result = await db.execute(select(ReminderConfig).limit(1))
        config = result.scalar_one()

        if reminders is not None:
            config.reminders = reminders
        if default_channels is not None:
            config.default_channels = default_channels
        if max_reminders_allowed is not None:
            config.max_reminders_allowed = max_reminders_allowed

        await db.flush()
        await db.refresh(config)

        logger.info(
            "Reminder config updated: max_reminders=%d channels=%s",
            config.max_reminders_allowed,
            config.default_channels,
        )

        return self._to_dict(config)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _to_dict(self, config: ReminderConfig) -> dict[str, Any]:
        """Serialize a ReminderConfig ORM instance to a plain dict."""
        return {
            "id": str(config.id),
            "reminders": config.reminders or [],
            "default_channels": config.default_channels or [],
            "max_reminders_allowed": config.max_reminders_allowed,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }


# Module-level singleton — stateless, safe to share across requests.
reminder_service = ReminderService()
