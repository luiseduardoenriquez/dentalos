"""Patient referral program service -- multi-step reward logic.

Handles referral code generation, referral processing, reward tracking,
and discount application during invoice creation.

Distinct from referral_service.py which handles doctor-to-doctor clinical referrals.

Security invariants:
  - PHI is NEVER logged (no patient names, emails, phones).
  - All monetary values in COP cents.
  - Soft-delete only for clinical/financial data.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ReferralProgramErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.patient_referral_program import ReferralCode, ReferralReward

logger = logging.getLogger("dentalos.referral_program")

# Default reward amount: 5000 COP ($5) per referral for each party
DEFAULT_REWARD_AMOUNT_CENTS = 5000


class ReferralProgramService:
    """Stateless patient referral program service."""

    # -- Code Generation -----------------------------------------------------------

    async def generate_code(
        self, *, db: AsyncSession, patient_id: str,
    ) -> dict[str, Any]:
        """Generate a unique 8-char alphanumeric referral code for a patient.

        Retries up to 3 times on UNIQUE constraint violation.
        """
        pid = uuid.UUID(patient_id)
        max_retries = 3

        for attempt in range(max_retries):
            code = secrets.token_urlsafe(6)[:8].upper()
            referral_code = ReferralCode(
                patient_id=pid,
                code=code,
                is_active=True,
                uses_count=0,
            )
            db.add(referral_code)
            try:
                await db.flush()
                await db.refresh(referral_code)
                logger.info(
                    "Referral code generated: id=%s attempt=%d",
                    str(referral_code.id)[:8],
                    attempt + 1,
                )
                return self._code_to_dict(referral_code)
            except IntegrityError:
                await db.rollback()
                if attempt == max_retries - 1:
                    raise DentalOSError(
                        error="SYSTEM_internal_error",
                        message="No se pudo generar un codigo de referido unico.",
                        status_code=500,
                    )
                logger.warning("Referral code collision, retrying (attempt %d)", attempt + 1)

        # Should not reach here, but satisfy type checker
        raise DentalOSError(
            error="SYSTEM_internal_error",
            message="No se pudo generar un codigo de referido unico.",
            status_code=500,
        )

    async def get_or_create_code(
        self, *, db: AsyncSession, patient_id: str,
    ) -> dict[str, Any]:
        """Get existing active referral code for patient, or create one.

        Used by portal endpoint so the patient always sees their code.
        """
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(ReferralCode).where(
                ReferralCode.patient_id == pid,
                ReferralCode.is_active.is_(True),
            ).order_by(ReferralCode.created_at.desc()).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            return self._code_to_dict(existing)

        return await self.generate_code(db=db, patient_id=patient_id)

    # -- Referral Processing -------------------------------------------------------

    async def process_referral_code(
        self,
        *,
        db: AsyncSession,
        referral_code_str: str,
        referred_patient_id: str,
    ) -> dict[str, Any]:
        """Process a referral code when a new patient books with it.

        Steps:
          1. Find ReferralCode by code string
          2. Validate: exists, is_active, max_uses not exceeded
          3. Check referred_patient_id != referrer (self-referral)
          4. Check no existing reward for this referred_patient_id (duplicate)
          5. Increment uses_count
          6. Create TWO ReferralReward records (one for referrer, one for referred)
          7. Return dict with both rewards
        """
        referred_pid = uuid.UUID(referred_patient_id)

        # 1. Find code
        result = await db.execute(
            select(ReferralCode).where(
                ReferralCode.code == referral_code_str.strip().upper(),
            )
        )
        code_obj = result.scalar_one_or_none()

        if code_obj is None:
            raise ResourceNotFoundError(
                error=ReferralProgramErrors.CODE_NOT_FOUND,
                resource_name="ReferralCode",
            )

        # 2a. Check is_active
        if not code_obj.is_active:
            raise DentalOSError(
                error=ReferralProgramErrors.CODE_EXPIRED,
                message="El codigo de referido ya no esta activo.",
                status_code=409,
            )

        # 2b. Check max_uses
        if code_obj.max_uses is not None and code_obj.uses_count >= code_obj.max_uses:
            raise DentalOSError(
                error=ReferralProgramErrors.CODE_MAX_USES,
                message="El codigo de referido ha alcanzado el limite de usos.",
                status_code=409,
            )

        # 3. Self-referral check
        if code_obj.patient_id == referred_pid:
            raise DentalOSError(
                error=ReferralProgramErrors.SELF_REFERRAL,
                message="No se puede usar su propio codigo de referido.",
                status_code=422,
            )

        # 4. Check no existing reward for this referred patient
        existing_reward = await db.execute(
            select(ReferralReward.id).where(
                ReferralReward.referred_patient_id == referred_pid,
            ).limit(1)
        )
        if existing_reward.scalar_one_or_none() is not None:
            raise DentalOSError(
                error=ReferralProgramErrors.ALREADY_REFERRED,
                message="Este paciente ya fue referido anteriormente.",
                status_code=409,
            )

        # 5. Increment uses_count
        code_obj.uses_count = code_obj.uses_count + 1

        # 6. Create two reward records
        referrer_reward = ReferralReward(
            referrer_patient_id=code_obj.patient_id,
            referred_patient_id=referred_pid,
            referral_code_id=code_obj.id,
            reward_type="discount",
            reward_amount_cents=DEFAULT_REWARD_AMOUNT_CENTS,
            status="pending",
        )
        referred_reward = ReferralReward(
            referrer_patient_id=referred_pid,
            referred_patient_id=referred_pid,
            referral_code_id=code_obj.id,
            reward_type="discount",
            reward_amount_cents=DEFAULT_REWARD_AMOUNT_CENTS,
            status="pending",
        )
        db.add(referrer_reward)
        db.add(referred_reward)
        await db.flush()
        await db.refresh(referrer_reward)
        await db.refresh(referred_reward)

        logger.info(
            "Referral processed: code_id=%s uses=%d",
            str(code_obj.id)[:8],
            code_obj.uses_count,
        )

        return {
            "referrer_reward": self._reward_to_dict(referrer_reward),
            "referred_reward": self._reward_to_dict(referred_reward),
        }

    # -- Referral Completion -------------------------------------------------------

    async def complete_referral(
        self, *, db: AsyncSession, referred_patient_id: str,
    ) -> list[dict[str, Any]]:
        """Mark referral rewards as complete when referred patient completes first appointment.

        Sets completed_at timestamp on all pending rewards for this referred patient.
        Rewards remain status='pending' until applied to an invoice.
        """
        referred_pid = uuid.UUID(referred_patient_id)

        result = await db.execute(
            select(ReferralReward).where(
                ReferralReward.referred_patient_id == referred_pid,
                ReferralReward.status == "pending",
                ReferralReward.completed_at.is_(None),
            )
        )
        rewards = list(result.scalars().all())

        now = datetime.now(UTC)
        for reward in rewards:
            reward.completed_at = now

        await db.flush()
        logger.info(
            "Referral completed: referred_patient=%s rewards_updated=%d",
            referred_patient_id[:8],
            len(rewards),
        )

        return [self._reward_to_dict(r) for r in rewards]

    # -- Reward Queries ------------------------------------------------------------

    async def get_pending_rewards(
        self, *, db: AsyncSession, patient_id: str,
    ) -> list[dict[str, Any]]:
        """Get all pending (unapplied) rewards for a patient.

        Returns rewards where the patient is the referrer_patient_id
        (i.e., rewards they earned) and status is still 'pending'.
        """
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(ReferralReward).where(
                ReferralReward.referrer_patient_id == pid,
                ReferralReward.status == "pending",
            ).order_by(ReferralReward.created_at.asc())
        )
        return [self._reward_to_dict(r) for r in result.scalars().all()]

    async def get_patient_rewards(
        self, *, db: AsyncSession, patient_id: str,
    ) -> dict[str, Any]:
        """List all rewards for a patient (for portal view).

        Includes rewards where the patient is either the referrer or the referred.
        """
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(ReferralReward).where(
                ReferralReward.referrer_patient_id == pid,
            ).order_by(ReferralReward.created_at.desc())
        )
        rewards = [self._reward_to_dict(r) for r in result.scalars().all()]

        return {
            "items": rewards,
            "total": len(rewards),
        }

    # -- Discount Application (called during invoice creation) ---------------------

    async def apply_referral_discount(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: uuid.UUID,
        max_discount_cents: int,
    ) -> int:
        """Apply referral discount(s) to an invoice.

        Called during invoice creation. Applies oldest pending rewards first,
        up to max_discount_cents total.

        Returns total discount applied in cents.
        """
        pid = uuid.UUID(patient_id)

        # Get oldest pending rewards for this patient
        result = await db.execute(
            select(ReferralReward).where(
                ReferralReward.referrer_patient_id == pid,
                ReferralReward.status == "pending",
            ).order_by(ReferralReward.created_at.asc())
        )
        pending_rewards = list(result.scalars().all())

        if not pending_rewards:
            return 0

        total_applied = 0
        for reward in pending_rewards:
            remaining_budget = max_discount_cents - total_applied
            if remaining_budget <= 0:
                break

            # Apply this reward (up to remaining budget)
            discount_from_reward = min(reward.reward_amount_cents, remaining_budget)
            total_applied += discount_from_reward

            reward.status = "applied"
            reward.applied_to_invoice_id = invoice_id

        await db.flush()

        if total_applied > 0:
            logger.info(
                "Referral discount applied: patient=%s invoice=%s amount=%d",
                patient_id[:8],
                str(invoice_id)[:8],
                total_applied,
            )

        return total_applied

    # -- Referral Notifications ----------------------------------------------------

    async def notify_referrer_on_completion(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        event: str,  # "booked" or "completed"
    ) -> None:
        """Notify the referrer when their referred patient books/completes an appointment.

        Looks up the referral reward for the referred patient to identify the
        referrer, then dispatches a notification to the referrer via the
        notifications queue.
        """
        referred_pid = uuid.UUID(patient_id)

        stmt = (
            select(ReferralReward)
            .where(
                ReferralReward.referred_patient_id == referred_pid,
                # Only notify the actual referrer (not the self-reward row)
                ReferralReward.referrer_patient_id != referred_pid,
            )
            .order_by(ReferralReward.created_at.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        referral = result.scalar_one_or_none()

        if not referral:
            return

        event_label = (
            "agendó una cita" if event == "booked" else "completó su cita"
        )

        try:
            from app.core.queue import publish_message

            await publish_message(
                queue="notifications",
                job_type="notification.dispatch",
                tenant_id=tenant_id,
                payload={
                    "event_type": f"referral.{event}",
                    "user_id": str(referral.referrer_patient_id),
                    "data": {
                        "title": "Tu referido avanzó",
                        "body": (
                            f"El paciente que referiste {event_label}. "
                            "¡Gracias por confiar en nosotros!"
                        ),
                        "metadata": {
                            "referral_reward_id": str(referral.id),
                            "referred_patient_id": patient_id,
                            "event": event,
                        },
                    },
                },
            )
            logger.info(
                "Referral notification sent: reward_id=%s event=%s",
                str(referral.id)[:8],
                event,
            )
        except Exception:
            logger.warning(
                "Failed to send referral notification: patient_id=%s",
                patient_id[:8],
            )

    # -- Stats (clinic_owner dashboard) --------------------------------------------

    async def get_program_stats(
        self, *, db: AsyncSession, tenant_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aggregate referral program statistics for the clinic dashboard."""
        total_codes = (await db.execute(
            select(func.count(ReferralCode.id)).where(
                ReferralCode.is_active.is_(True),
            )
        )).scalar_one()

        # Count distinct referred patients (each referral = 2 reward rows)
        total_referrals = (await db.execute(
            select(func.count(func.distinct(ReferralReward.referred_patient_id)))
        )).scalar_one()

        # Referrals pending = referred patients where NO reward is applied yet
        referrals_converted = (await db.execute(
            select(func.count(func.distinct(ReferralReward.referred_patient_id))).where(
                ReferralReward.status == "applied",
            )
        )).scalar_one()

        referrals_pending = total_referrals - referrals_converted

        pending = (await db.execute(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.status == "pending",
            )
        )).scalar_one()

        applied = (await db.execute(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.status == "applied",
            )
        )).scalar_one()

        total_discount = (await db.execute(
            select(func.coalesce(func.sum(ReferralReward.reward_amount_cents), 0)).where(
                ReferralReward.status == "applied",
            )
        )).scalar_one()

        # Program active state from tenant settings
        settings = tenant_settings or {}
        is_active = settings.get("referral_program_active", True)

        return {
            "is_active": is_active,
            "total_codes_generated": total_codes,
            "total_referrals_made": total_referrals,
            "referrals_pending": referrals_pending,
            "referrals_converted": referrals_converted,
            "rewards_pending": pending,
            "rewards_applied": applied,
            "total_discount_given_cents": total_discount,
            "reward_type": "discount",
            "reward_value_cents": DEFAULT_REWARD_AMOUNT_CENTS,
            "reward_description": (
                f"Descuento de ${DEFAULT_REWARD_AMOUNT_CENTS // 100:,} COP "
                f"para referidor y referido en su primera cita"
            ),
        }

    # -- Portal-specific Methods ---------------------------------------------------

    async def get_portal_referral_data(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_slug: str,
        base_url: str,
    ) -> dict[str, Any]:
        """Build the portal referral view with code, URL, and pending reward count.

        Always creates a code if one doesn't exist (portal patients expect to see their code).
        """
        code_data = await self.get_or_create_code(db=db, patient_id=patient_id)

        pid = uuid.UUID(patient_id)
        pending_count = (await db.execute(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.referrer_patient_id == pid,
                ReferralReward.status == "pending",
            )
        )).scalar_one()

        referral_url = f"{base_url.rstrip('/')}/{tenant_slug}?ref={code_data['code']}"

        return {
            "referral_code": code_data["code"],
            "referral_url": referral_url,
            "uses_count": code_data["uses_count"],
            "pending_rewards": pending_count,
            "reward_description": (
                f"Descuento de ${DEFAULT_REWARD_AMOUNT_CENTS // 100:,} COP "
                f"para ti y tu referido en la primera cita"
            ),
        }

    async def get_portal_rewards(
        self, *, db: AsyncSession, patient_id: str,
    ) -> dict[str, Any]:
        """List rewards for a patient using portal-friendly Spanish field names."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(ReferralReward).where(
                ReferralReward.referrer_patient_id == pid,
            ).order_by(ReferralReward.created_at.desc())
        )
        rewards = [self._reward_to_portal_dict(r) for r in result.scalars().all()]

        return {
            "items": rewards,
            "total": len(rewards),
        }

    # -- Dashboard (staff) ---------------------------------------------------------

    async def get_dashboard_data(
        self, *, db: AsyncSession,
    ) -> dict[str, Any]:
        """Aggregate dashboard data: stats + top 10 referrers with names.

        Does a local import of Patient to avoid circular dependency at module level.
        """
        from app.models.tenant.patient import Patient

        # Stats
        total_referrals = (await db.execute(
            select(func.count(func.distinct(ReferralReward.referred_patient_id)))
        )).scalar_one()

        successful = (await db.execute(
            select(func.count(func.distinct(ReferralReward.referred_patient_id))).where(
                ReferralReward.status == "applied",
            )
        )).scalar_one()

        conversion_rate = (successful / total_referrals) if total_referrals > 0 else 0.0

        total_rewards_cents = (await db.execute(
            select(func.coalesce(func.sum(ReferralReward.reward_amount_cents), 0)).where(
                ReferralReward.status == "applied",
            )
        )).scalar_one()

        active_referrers = (await db.execute(
            select(func.count(func.distinct(ReferralCode.patient_id))).where(
                ReferralCode.is_active.is_(True),
                ReferralCode.uses_count > 0,
            )
        )).scalar_one()

        stats = {
            "total_referrals": total_referrals,
            "successful_referrals": successful,
            "conversion_rate": round(conversion_rate, 4),
            "total_rewards_cents": total_rewards_cents,
            "active_referrers": active_referrers,
        }

        # Top 10 referrers
        top_q = (
            select(
                ReferralCode.patient_id,
                func.concat(Patient.first_name, " ", Patient.last_name).label("patient_name"),
                ReferralCode.uses_count.label("referral_count"),
                func.count(
                    func.distinct(
                        ReferralReward.referred_patient_id
                    )
                ).filter(ReferralReward.status == "applied").label("successful_count"),
                func.coalesce(
                    func.sum(ReferralReward.reward_amount_cents).filter(
                        ReferralReward.status == "applied"
                    ), 0
                ).label("rewards_earned_cents"),
            )
            .join(Patient, Patient.id == ReferralCode.patient_id)
            .outerjoin(ReferralReward, ReferralReward.referral_code_id == ReferralCode.id)
            .where(ReferralCode.is_active.is_(True), ReferralCode.uses_count > 0)
            .group_by(ReferralCode.patient_id, Patient.first_name, Patient.last_name, ReferralCode.uses_count)
            .order_by(ReferralCode.uses_count.desc())
            .limit(10)
        )
        rows = (await db.execute(top_q)).all()

        top_referrers = []
        for row in rows:
            rc = row.referral_count
            sc = row.successful_count
            top_referrers.append({
                "patient_id": str(row.patient_id),
                "patient_name": row.patient_name or "Paciente",
                "referral_count": rc,
                "successful_count": sc,
                "rewards_earned_cents": row.rewards_earned_cents,
                "conversion_rate": round((sc / rc) if rc > 0 else 0.0, 4),
            })

        return {
            "stats": stats,
            "top_referrers": top_referrers,
        }

    # -- Staff: patient summary (read-only) ----------------------------------------

    async def get_patient_referral_summary(
        self, *, db: AsyncSession, patient_id: str,
    ) -> dict[str, Any]:
        """Get a patient's referral code + reward counts for staff view.

        Does NOT create a code — staff viewing shouldn't trigger code generation.
        """
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(ReferralCode).where(
                ReferralCode.patient_id == pid,
                ReferralCode.is_active.is_(True),
            ).order_by(ReferralCode.created_at.desc()).limit(1)
        )
        code_obj = result.scalar_one_or_none()

        # Reward counts
        pending = (await db.execute(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.referrer_patient_id == pid,
                ReferralReward.status == "pending",
            )
        )).scalar_one()

        applied = (await db.execute(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.referrer_patient_id == pid,
                ReferralReward.status == "applied",
            )
        )).scalar_one()

        total_referrals = (await db.execute(
            select(func.count(func.distinct(ReferralReward.referred_patient_id))).where(
                ReferralReward.referrer_patient_id == pid,
                ReferralReward.referrer_patient_id != ReferralReward.referred_patient_id,
            )
        )).scalar_one()

        return {
            "referral_code": code_obj.code if code_obj else None,
            "code_is_active": code_obj.is_active if code_obj else False,
            "uses_count": code_obj.uses_count if code_obj else 0,
            "total_referrals_made": total_referrals,
            "rewards_pending": pending,
            "rewards_applied": applied,
        }

    # -- Private Helpers -----------------------------------------------------------

    def _code_to_dict(self, code: ReferralCode) -> dict[str, Any]:
        return {
            "id": str(code.id),
            "patient_id": str(code.patient_id),
            "code": code.code,
            "is_active": code.is_active,
            "uses_count": code.uses_count,
            "max_uses": code.max_uses,
            "created_at": code.created_at,
        }

    def _reward_to_dict(self, reward: ReferralReward) -> dict[str, Any]:
        return {
            "id": str(reward.id),
            "referrer_patient_id": str(reward.referrer_patient_id),
            "referred_patient_id": str(reward.referred_patient_id),
            "reward_type": reward.reward_type,
            "reward_amount_cents": reward.reward_amount_cents,
            "status": reward.status,
            "applied_to_invoice_id": (
                str(reward.applied_to_invoice_id) if reward.applied_to_invoice_id else None
            ),
            "completed_at": reward.completed_at,
            "created_at": reward.created_at,
        }

    def _reward_to_portal_dict(self, reward: ReferralReward) -> dict[str, Any]:
        """Map reward to portal-friendly shape with Spanish enum values."""
        type_map = {"discount": "descuento", "credit": "credito", "gift": "regalo"}
        status_map = {"pending": "pendiente", "applied": "aplicado", "expired": "expirado"}

        return {
            "id": str(reward.id),
            "created_at": reward.created_at,
            "reward_type": type_map.get(reward.reward_type, reward.reward_type),
            "amount_cents": reward.reward_amount_cents,
            "status": status_map.get(reward.status, reward.status),
            "applied_at": reward.completed_at,
            "expires_at": None,
            "description": (
                f"Descuento de ${reward.reward_amount_cents // 100:,} COP por referido"
            ),
        }


# Module-level singleton
referral_program_service = ReferralProgramService()
