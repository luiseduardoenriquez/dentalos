"""RETHUS professional registry verification service — VP-07.

Orchestrates RETHUS lookups by resolving the correct adapter (production or
mock), persisting results onto the User record, and exposing a periodic
re-verification method used by the maintenance worker.

PHI rules:
  - user_id (UUID) is safe to log as an identifier.
  - professional names are PHI-adjacent — NEVER written to logs.
  - rethus_number is a registry identifier, not PHI, but is treated carefully.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import RETHUSErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.integrations.rethus.base import RETHUSServiceBase
from app.integrations.rethus.mock_service import rethus_mock_service
from app.integrations.rethus.service import rethus_service
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.rethus_verification")

# Re-verify professionals verified more than 30 days ago.
_REVERIFY_THRESHOLD_DAYS = 30


def _get_adapter() -> RETHUSServiceBase:
    """Return the appropriate RETHUS adapter based on configuration.

    Uses the production service when credentials are present; falls back to
    the mock service for development and CI environments.
    """
    if rethus_service.is_configured():
        return rethus_service
    return rethus_mock_service


class RETHUSVerificationService:
    """Orchestrates RETHUS registry verification for user accounts.

    All methods are stateless and accept an AsyncSession injected by the
    FastAPI dependency system or the maintenance worker.
    """

    async def verify_user(
        self,
        *,
        db: AsyncSession,
        user_id: UUID | str,
        rethus_number: str,
    ) -> dict[str, Any]:
        """Trigger a RETHUS verification for a user and persist the result.

        Calls the RETHUS adapter, maps the response onto the User record, and
        commits the changes.  Returns a dict matching RETHUSVerificationResponse.

        Args:
            db: Tenant-scoped async database session.
            user_id: UUID of the user to verify (str or UUID accepted).
            rethus_number: The RETHUS registry number to verify.

        Returns:
            dict with verification status and professional details (no PHI logged).

        Raises:
            ResourceNotFoundError: If the user does not exist in this tenant.
            DentalOSError: If the RETHUS adapter returns an unexpected error.
        """
        user_id_str = str(user_id)
        logger.info("RETHUS verification requested: user_id=%s", user_id_str)

        user = await self._get_user(db=db, user_id=user_id_str)

        adapter = _get_adapter()
        try:
            result = await adapter.verify_professional(rethus_number=rethus_number)
        except Exception as exc:
            logger.error(
                "RETHUS adapter error for user_id=%s: %s",
                user_id_str,
                type(exc).__name__,
            )
            # Persist failed status without losing the rethus_number attempt.
            user.rethus_number = rethus_number
            user.rethus_verification_status = "failed"
            user.rethus_verified_at = None
            await db.flush()
            raise DentalOSError(
                error=RETHUSErrors.SERVICE_UNAVAILABLE,
                message="RETHUS verification service is currently unavailable.",
                status_code=503,
            ) from exc

        if result.found:
            user.rethus_number = rethus_number
            user.rethus_verification_status = "verified"
            user.rethus_verified_at = datetime.now(UTC)
            logger.info(
                "RETHUS verification succeeded: user_id=%s",
                user_id_str,
            )
        else:
            user.rethus_number = rethus_number
            user.rethus_verification_status = "failed"
            user.rethus_verified_at = None
            logger.warning(
                "RETHUS number not found in registry: user_id=%s",
                user_id_str,
            )

        await db.flush()

        return self._to_dict(
            user=user,
            professional_name=result.full_name if result.found else None,
            profession=result.profession if result.found else None,
            specialty=result.specialty if result.found else None,
        )

    async def check_status(
        self,
        *,
        db: AsyncSession,
        user_id: UUID | str,
    ) -> dict[str, Any]:
        """Return the current RETHUS verification status for a user.

        Args:
            db: Tenant-scoped async database session.
            user_id: UUID of the user to check.

        Returns:
            dict with current verification status (no PHI logged).

        Raises:
            ResourceNotFoundError: If the user does not exist in this tenant.
        """
        user_id_str = str(user_id)
        user = await self._get_user(db=db, user_id=user_id_str)
        return self._to_dict(user=user)

    async def periodic_reverify(self, *, db: AsyncSession) -> dict[str, Any]:
        """Re-verify all clinical users whose RETHUS status has aged past 30 days.

        Intended to be called by the maintenance worker on a scheduled basis.
        Errors on individual users are logged and swallowed so one failure does
        not abort the entire batch.

        Args:
            db: Tenant-scoped async database session.

        Returns:
            Summary dict with counts of processed, succeeded, and failed users.
        """
        threshold = datetime.now(UTC) - timedelta(days=_REVERIFY_THRESHOLD_DAYS)

        stmt = select(User).where(
            User.role.in_(["doctor", "assistant"]),
            User.rethus_verification_status == "verified",
            User.rethus_verified_at < threshold,
            User.rethus_number.is_not(None),
            User.is_active.is_(True),
        )
        result = await db.execute(stmt)
        users = result.scalars().all()

        processed = 0
        succeeded = 0
        failed = 0

        for user in users:
            processed += 1
            user_id_str = str(user.id)
            try:
                await self.verify_user(
                    db=db,
                    user_id=user.id,
                    rethus_number=user.rethus_number,  # type: ignore[arg-type]
                )
                succeeded += 1
            except Exception as exc:
                failed += 1
                logger.error(
                    "Periodic RETHUS re-verification failed for user_id=%s: %s",
                    user_id_str,
                    type(exc).__name__,
                )

        logger.info(
            "Periodic RETHUS re-verification complete: "
            "processed=%d succeeded=%d failed=%d",
            processed,
            succeeded,
            failed,
        )

        return {"processed": processed, "succeeded": succeeded, "failed": failed}

    # ─── Private helpers ──────────────────────────────────────────────────────

    async def _get_user(self, *, db: AsyncSession, user_id: str) -> User:
        """Fetch a User by ID or raise ResourceNotFoundError."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ResourceNotFoundError(
                error=RETHUSErrors.NOT_FOUND,
                resource_name="User",
            )
        return user

    @staticmethod
    def _to_dict(
        *,
        user: User,
        professional_name: str | None = None,
        profession: str | None = None,
        specialty: str | None = None,
    ) -> dict[str, Any]:
        """Map a User record to the RETHUSVerificationResponse dict contract."""
        return {
            "user_id": str(user.id),
            "rethus_number": user.rethus_number,
            "verification_status": user.rethus_verification_status,
            "verified_at": user.rethus_verified_at,
            # Professional details are only populated when explicitly provided
            # (i.e. fresh from the adapter). For check_status calls these are None
            # since we do not re-surface PHI from storage.
            "professional_name": professional_name,
            "profession": profession,
            "specialty": specialty,
        }


# Module-level singleton.
rethus_verification_service = RETHUSVerificationService()
