"""Loyalty points service -- award, redeem, expire, and query patient points.

Security invariants:
  - PHI is NEVER logged (patient names, document numbers).
  - All monetary values in COP cents.
  - Negative balance prevented by SELECT ... FOR UPDATE + application check
    (backed by CHECK constraint on the table as a safety net).
  - Transactions are append-only -- never updated or deleted.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import LoyaltyErrors
from app.core.exceptions import DentalOSError
from app.models.tenant.loyalty import LoyaltyPoints, LoyaltyTransaction
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.loyalty")

# Default: 100 points = 1000 cents (10 cents per point)
_DEFAULT_POINTS_TO_CURRENCY_RATIO = 10


class LoyaltyService:
    """Stateless loyalty points service.

    All methods receive the AsyncSession from the caller (injected via
    FastAPI Depends). No internal state is held between calls.
    """

    # -- Award Points ----------------------------------------------------------

    async def award_points(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        points: int,
        reason: str | None = None,
        reference_id: uuid.UUID | None = None,
        reference_type: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Award points to a patient, creating the balance row if needed.

        Uses SELECT ... FOR UPDATE to prevent race conditions on the
        balance row. Returns the updated PointsBalance dict.
        """
        now = datetime.now(UTC)

        # Get or create balance row with row-level lock
        row = await self._get_or_create_locked(db, patient_id)

        row.points_balance += points
        row.lifetime_points_earned += points
        row.last_activity_at = now

        # Append transaction
        txn = LoyaltyTransaction(
            patient_id=patient_id,
            type="earned",
            points=points,
            reason=reason,
            reference_id=reference_id,
            reference_type=reference_type,
            performed_by=performed_by,
        )
        db.add(txn)
        await db.flush()
        await db.refresh(row)

        logger.info(
            "Points awarded: patient=%s pts=%d balance=%d",
            str(patient_id)[:8],
            points,
            row.points_balance,
        )
        return self._balance_to_dict(row)

    # -- Redeem Points ---------------------------------------------------------

    async def redeem_points(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        points: int,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Redeem points from a patient's balance.

        Returns dict with 'balance' (PointsBalance) and 'discount_cents'.
        Raises LOYALTY_insufficient_points if balance is too low.
        """
        now = datetime.now(UTC)

        # Lock the row
        result = await db.execute(
            select(LoyaltyPoints)
            .where(LoyaltyPoints.patient_id == patient_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()

        if row is None or row.points_balance < points:
            current = row.points_balance if row else 0
            raise DentalOSError(
                error=LoyaltyErrors.INSUFFICIENT_POINTS,
                message=(
                    f"Puntos insuficientes. Disponible: {current}, "
                    f"solicitado: {points}."
                ),
                status_code=409,
                details={"available": current, "requested": points},
            )

        row.points_balance -= points
        row.lifetime_points_redeemed += points
        row.last_activity_at = now

        # Append transaction
        txn = LoyaltyTransaction(
            patient_id=patient_id,
            type="redeemed",
            points=points,
            reason=reason,
            performed_by=performed_by,
        )
        db.add(txn)
        await db.flush()
        await db.refresh(row)

        ratio = await self.get_points_to_currency_ratio(db)
        discount_cents = points * ratio

        logger.info(
            "Points redeemed: patient=%s pts=%d discount=%d balance=%d",
            str(patient_id)[:8],
            points,
            discount_cents,
            row.points_balance,
        )
        return {
            "balance": self._balance_to_dict(row),
            "discount_cents": discount_cents,
        }

    # -- Balance Query ---------------------------------------------------------

    async def get_balance(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Return the patient's current point balance.

        Creates a default zero-balance row if none exists (without locking,
        since this is a read path and the INSERT is idempotent on conflict).
        """
        result = await db.execute(
            select(LoyaltyPoints).where(
                LoyaltyPoints.patient_id == patient_id,
            )
        )
        row = result.scalar_one_or_none()

        if row is None:
            row = LoyaltyPoints(
                patient_id=patient_id,
                points_balance=0,
                lifetime_points_earned=0,
                lifetime_points_redeemed=0,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)

        return self._balance_to_dict(row)

    # -- Portal View -----------------------------------------------------------

    async def get_portal_loyalty(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get balance and recent transactions for the patient portal."""
        balance = await self.get_balance(db, patient_id)

        result = await db.execute(
            select(LoyaltyTransaction)
            .where(LoyaltyTransaction.patient_id == patient_id)
            .order_by(LoyaltyTransaction.created_at.desc())
            .limit(limit)
        )
        transactions = result.scalars().all()

        return {
            "balance": balance,
            "recent_transactions": [
                self._transaction_to_dict(t) for t in transactions
            ],
        }

    # -- Expiration ------------------------------------------------------------

    async def expire_inactive(
        self,
        db: AsyncSession,
        expiry_months: int = 12,
    ) -> int:
        """Expire points for patients inactive longer than expiry_months.

        Zeroes out the balance and creates an 'expired' transaction for
        each affected patient. Returns the count of patients expired.

        Intended to be called by the maintenance worker cron.
        """
        from dateutil.relativedelta import relativedelta

        cutoff = datetime.now(UTC) - relativedelta(months=expiry_months)

        result = await db.execute(
            select(LoyaltyPoints)
            .where(
                and_(
                    LoyaltyPoints.last_activity_at < cutoff,
                    LoyaltyPoints.points_balance > 0,
                )
            )
            .with_for_update()
        )
        rows = result.scalars().all()

        count = 0
        now = datetime.now(UTC)
        for row in rows:
            expired_points = row.points_balance
            txn = LoyaltyTransaction(
                patient_id=row.patient_id,
                type="expired",
                points=expired_points,
                reason=f"Inactividad > {expiry_months} meses",
            )
            db.add(txn)
            row.points_balance = 0
            row.last_activity_at = now
            count += 1

        if count > 0:
            await db.flush()
            logger.info("Expired loyalty points for %d patients", count)

        return count

    # -- Leaderboard -----------------------------------------------------------

    async def get_leaderboard(
        self,
        db: AsyncSession,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Top N patients by current points balance.

        Joins Patient table for display name. Returns dict suitable for
        LeaderboardResponse schema.
        """
        result = await db.execute(
            select(
                LoyaltyPoints.patient_id,
                (Patient.first_name + " " + Patient.last_name).label("patient_name"),
                LoyaltyPoints.points_balance,
                LoyaltyPoints.lifetime_points_earned,
            )
            .join(Patient, LoyaltyPoints.patient_id == Patient.id)
            .where(LoyaltyPoints.points_balance > 0)
            .order_by(LoyaltyPoints.points_balance.desc())
            .limit(limit)
        )
        rows = result.all()

        items = [
            {
                "patient_id": row.patient_id,
                "patient_name": row.patient_name or "",
                "points_balance": row.points_balance,
                "lifetime_earned": row.lifetime_points_earned,
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": len(items),
        }

    # -- Tenant Settings -------------------------------------------------------

    async def get_points_to_currency_ratio(
        self,
        db: AsyncSession,
    ) -> int:
        """Read the points-to-currency ratio from tenant settings JSONB.

        Looks up public.tenants.settings->'loyalty'->'points_to_currency_ratio'.
        Default: 10 (meaning 1 point = 10 cents, so 100 points = 1000 cents).
        """
        try:
            from sqlalchemy import text as sa_text

            result = await db.execute(
                sa_text(
                    "SELECT settings->'loyalty'->>'points_to_currency_ratio' "
                    "FROM public.tenants LIMIT 1"
                )
            )
            raw = result.scalar_one_or_none()
            if raw is not None:
                ratio = int(raw)
                if ratio > 0:
                    return ratio
        except Exception:
            logger.debug(
                "Could not read points_to_currency_ratio from tenant settings, "
                "using default"
            )
        return _DEFAULT_POINTS_TO_CURRENCY_RATIO

    # -- Private Helpers -------------------------------------------------------

    async def _get_or_create_locked(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
    ) -> LoyaltyPoints:
        """Get the LoyaltyPoints row with FOR UPDATE, creating if absent."""
        result = await db.execute(
            select(LoyaltyPoints)
            .where(LoyaltyPoints.patient_id == patient_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()

        if row is None:
            row = LoyaltyPoints(
                patient_id=patient_id,
                points_balance=0,
                lifetime_points_earned=0,
                lifetime_points_redeemed=0,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)
            # Re-lock the newly created row
            result = await db.execute(
                select(LoyaltyPoints)
                .where(LoyaltyPoints.patient_id == patient_id)
                .with_for_update()
            )
            row = result.scalar_one()

        return row

    def _balance_to_dict(self, row: LoyaltyPoints) -> dict[str, Any]:
        return {
            "patient_id": row.patient_id,
            "points_balance": row.points_balance,
            "lifetime_earned": row.lifetime_points_earned,
            "lifetime_redeemed": row.lifetime_points_redeemed,
            "last_activity_at": row.last_activity_at,
        }

    def _transaction_to_dict(self, txn: LoyaltyTransaction) -> dict[str, Any]:
        return {
            "id": txn.id,
            "patient_id": txn.patient_id,
            "type": txn.type,
            "points": txn.points,
            "reason": txn.reason,
            "reference_id": txn.reference_id,
            "reference_type": txn.reference_type,
            "created_at": txn.created_at,
        }


loyalty_service = LoyaltyService()
