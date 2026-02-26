"""Referral service — create, list, and update patient referrals.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.patient import Patient
from app.models.tenant.referral import PatientReferral
from app.models.tenant.user import User
from app.services.notification_dispatch import dispatch_notification

logger = logging.getLogger("dentalos.referral")


def _referral_to_dict(
    r: PatientReferral,
    from_name: str | None = None,
    to_name: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "patient_id": str(r.patient_id),
        "from_doctor_id": str(r.from_doctor_id),
        "from_doctor_name": from_name,
        "to_doctor_id": str(r.to_doctor_id),
        "to_doctor_name": to_name,
        "reason": r.reason,
        "priority": r.priority,
        "specialty": r.specialty,
        "status": r.status,
        "notes": r.notes,
        "accepted_at": r.accepted_at,
        "completed_at": r.completed_at,
        "is_active": r.is_active,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


class ReferralService:
    """Stateless referral service."""

    async def create_referral(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        from_doctor_id: str,
        to_doctor_id: str,
        reason: str,
        priority: str = "normal",
        specialty: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a patient referral (P-15)."""
        pid = uuid.UUID(patient_id)
        from_id = uuid.UUID(from_doctor_id)
        to_id = uuid.UUID(to_doctor_id)

        # Validate from != to
        if from_id == to_id:
            raise DentalOSError(
                error="CLINICAL_invalid_referral",
                message="No puedes referir un paciente a ti mismo.",
                status_code=422,
            )

        # Validate patient exists
        patient_exists = (await db.execute(
            select(Patient.id).where(Patient.id == pid, Patient.is_active.is_(True))
        )).scalar_one_or_none()

        if patient_exists is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="El paciente no existe o esta inactivo.",
                status_code=404,
            )

        # Validate to_doctor exists
        to_doctor = (await db.execute(
            select(User).where(User.id == to_id, User.is_active.is_(True))
        )).scalar_one_or_none()

        if to_doctor is None:
            raise DentalOSError(
                error="CLINICAL_doctor_not_found",
                message="El doctor destino no existe o esta inactivo.",
                status_code=404,
            )

        referral = PatientReferral(
            patient_id=pid,
            from_doctor_id=from_id,
            to_doctor_id=to_id,
            reason=reason,
            priority=priority,
            specialty=specialty,
            notes=notes,
            status="pending",
            is_active=True,
        )
        db.add(referral)
        await db.flush()

        # Get from doctor name for response
        from_doctor = (await db.execute(
            select(User.name).where(User.id == from_id)
        )).scalar_one_or_none()

        logger.info("Referral created: referral=%s", str(referral.id)[:8])

        # Dispatch notification to receiving doctor
        await dispatch_notification(
            tenant_id=tenant_id,
            user_id=to_doctor_id,
            event_type="referral_received",
            data={
                "referral_id": str(referral.id),
                "from_doctor_name": from_doctor or "Doctor",
                "patient_id": patient_id,
                "priority": priority,
                "specialty": specialty,
            },
            priority=7 if priority == "urgent" else 5,
        )

        return _referral_to_dict(
            referral,
            from_name=from_doctor,
            to_name=to_doctor.name if to_doctor else None,
        )

    async def list_referrals(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List referrals for a patient (P-15)."""
        pid = uuid.UUID(patient_id)
        offset = (page - 1) * page_size

        total = (await db.execute(
            select(func.count(PatientReferral.id)).where(
                PatientReferral.patient_id == pid,
                PatientReferral.is_active.is_(True),
            )
        )).scalar_one()

        referrals = (await db.execute(
            select(PatientReferral)
            .where(
                PatientReferral.patient_id == pid,
                PatientReferral.is_active.is_(True),
            )
            .order_by(PatientReferral.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        # Resolve doctor names in batch
        doctor_ids = set()
        for r in referrals:
            doctor_ids.add(r.from_doctor_id)
            doctor_ids.add(r.to_doctor_id)

        name_map: dict[uuid.UUID, str] = {}
        if doctor_ids:
            doctors = (await db.execute(
                select(User.id, User.name).where(User.id.in_(doctor_ids))
            )).all()
            for uid, name in doctors:
                name_map[uid] = name

        items = [
            _referral_to_dict(
                r,
                from_name=name_map.get(r.from_doctor_id),
                to_name=name_map.get(r.to_doctor_id),
            )
            for r in referrals
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_referral_status(
        self,
        *,
        db: AsyncSession,
        referral_id: str,
        updater_id: str,
        status: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update referral status (P-15)."""
        rid = uuid.UUID(referral_id)

        result = await db.execute(
            select(PatientReferral).where(
                PatientReferral.id == rid,
                PatientReferral.is_active.is_(True),
            )
        )
        referral = result.scalar_one_or_none()

        if referral is None:
            raise ResourceNotFoundError(
                error="CLINICAL_referral_not_found",
                resource_name="PatientReferral",
            )

        # Validate status transition
        valid_transitions = {
            "pending": {"accepted", "declined"},
            "accepted": {"completed"},
        }
        allowed = valid_transitions.get(referral.status, set())
        if status not in allowed:
            raise DentalOSError(
                error="CLINICAL_invalid_status_transition",
                message=f"No se puede cambiar de '{referral.status}' a '{status}'.",
                status_code=409,
            )

        now = datetime.now(UTC)
        referral.status = status

        if notes is not None:
            referral.notes = notes

        if status == "accepted":
            referral.accepted_at = now
        elif status == "completed":
            referral.completed_at = now

        await db.flush()

        # Resolve doctor names
        doctor_ids = {referral.from_doctor_id, referral.to_doctor_id}
        name_map: dict[uuid.UUID, str] = {}
        doctors = (await db.execute(
            select(User.id, User.name).where(User.id.in_(doctor_ids))
        )).all()
        for uid, name in doctors:
            name_map[uid] = name

        logger.info("Referral updated: referral=%s status=%s", referral_id[:8], status)

        return _referral_to_dict(
            referral,
            from_name=name_map.get(referral.from_doctor_id),
            to_name=name_map.get(referral.to_doctor_id),
        )


# Module-level singleton
referral_service = ReferralService()
