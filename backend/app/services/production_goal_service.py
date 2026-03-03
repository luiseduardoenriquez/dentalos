"""Production goal configuration — VP-04.

Stores per-doctor and per-clinic production goals in clinic_settings JSONB.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("dentalos.production_goals")


class ProductionGoalService:
    """Manage production goal configuration for doctors and clinics.

    Goals are stored in the clinic_settings table under the `production_goals`
    JSONB key.  The structure is:
      {
        "monthly_target_cents": <int>,
        "doctor_goals": {
          "<doctor_id>": {"monthly_target_cents": <int>}
        }
      }
    """

    async def get_goals(
        self,
        *,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Return production goals from clinic_settings.

        Args:
            db: Tenant-scoped async database session.

        Returns:
            dict with monthly_target_cents and doctor_goals map.
            Returns safe defaults when no record exists yet.
        """
        result = await db.execute(
            text(
                "SELECT settings->'production_goals' FROM clinic_settings LIMIT 1"
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return {"monthly_target_cents": 0, "doctor_goals": {}}
        return (
            row
            if isinstance(row, dict)
            else {"monthly_target_cents": 0, "doctor_goals": {}}
        )

    async def update_goals(
        self,
        *,
        db: AsyncSession,
        monthly_target_cents: int | None = None,
        doctor_id: str | None = None,
        doctor_monthly_target_cents: int | None = None,
    ) -> dict[str, Any]:
        """Update production goals in clinic_settings JSONB.

        Merges partial updates into the existing goals structure.
        Caller may update the clinic-wide target, a specific doctor's target,
        or both in a single call.

        Args:
            db: Tenant-scoped async database session.
            monthly_target_cents: New clinic-wide monthly production goal in COP
                                  cents.  Pass None to leave unchanged.
            doctor_id: UUID string of the doctor whose goal is being set.  Must
                       be paired with doctor_monthly_target_cents.
            doctor_monthly_target_cents: Monthly production goal for the given
                                         doctor in COP cents.

        Returns:
            The full updated goals dict after persisting.
        """
        current = await self.get_goals(db=db)

        if monthly_target_cents is not None:
            current["monthly_target_cents"] = monthly_target_cents

        if doctor_id is not None and doctor_monthly_target_cents is not None:
            if "doctor_goals" not in current:
                current["doctor_goals"] = {}
            current["doctor_goals"][doctor_id] = {
                "monthly_target_cents": doctor_monthly_target_cents,
            }

        goals_json = json.dumps(current)
        await db.execute(
            text(
                "UPDATE clinic_settings"
                " SET settings = jsonb_set("
                "   COALESCE(settings, '{}'), '{production_goals}', :goals::jsonb"
                " )"
                " WHERE id = (SELECT id FROM clinic_settings LIMIT 1)"
            ),
            {"goals": goals_json},
        )
        await db.flush()

        logger.info("Production goals updated")
        return current


# Module-level singleton.
production_goal_service = ProductionGoalService()
