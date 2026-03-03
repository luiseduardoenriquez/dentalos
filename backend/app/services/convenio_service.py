"""Convenio service — corporate agreement management and discount lookup.

Security invariants:
  - PHI is NEVER logged.
  - Soft-delete only; clinical data is never hard-deleted.
"""

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ConvenioErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.convenio import Convenio, ConvenioPatient

logger = logging.getLogger("dentalos.convenio")


class ConvenioService:
    """Stateless convenio service."""

    # ── Convenio CRUD ─────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        db: AsyncSession,
        data: dict[str, Any],
        created_by: str,
    ) -> dict[str, Any]:
        """Create a new corporate agreement."""
        convenio = Convenio(
            company_name=data["company_name"],
            contact_info=data.get("contact_info"),
            discount_rules=data.get("discount_rules"),
            valid_from=data["valid_from"],
            valid_until=data.get("valid_until"),
            is_active=True,
            created_by=uuid.UUID(created_by),
        )
        db.add(convenio)
        await db.flush()
        await db.refresh(convenio)
        logger.info("Convenio created: id=%s", str(convenio.id)[:8])
        return self._to_dict(convenio)

    async def list_convenios(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of active convenios."""
        offset = (page - 1) * page_size
        conditions = [Convenio.is_active.is_(True), Convenio.deleted_at.is_(None)]

        total = (
            await db.execute(select(func.count(Convenio.id)).where(*conditions))
        ).scalar_one()

        result = await db.execute(
            select(Convenio)
            .where(*conditions)
            .order_by(Convenio.company_name)
            .offset(offset)
            .limit(page_size)
        )
        items = [self._to_dict(c) for c in result.scalars().all()]

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update(
        self,
        *,
        db: AsyncSession,
        convenio_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update mutable fields on an existing convenio."""
        convenio = await self._get(db, convenio_id)
        for key, value in data.items():
            if value is not None and hasattr(convenio, key):
                setattr(convenio, key, value)
        await db.flush()
        await db.refresh(convenio)
        logger.info("Convenio updated: id=%s", str(convenio.id)[:8])
        return self._to_dict(convenio)

    # ── Patient Linking ───────────────────────────────────────────────────────

    async def link_patient(
        self,
        *,
        db: AsyncSession,
        convenio_id: str,
        patient_id: str,
        employee_id: str | None = None,
    ) -> dict[str, Any]:
        """Link a patient to a convenio.

        Raises ConvenioErrors.PATIENT_ALREADY_LINKED on duplicate.
        """
        convenio = await self._get(db, convenio_id)
        pid = uuid.UUID(patient_id)

        # Check for an existing active link
        existing = (
            await db.execute(
                select(ConvenioPatient.id).where(
                    ConvenioPatient.convenio_id == convenio.id,
                    ConvenioPatient.patient_id == pid,
                    ConvenioPatient.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            raise DentalOSError(
                error=ConvenioErrors.PATIENT_ALREADY_LINKED,
                message="El paciente ya está vinculado a este convenio.",
                status_code=409,
            )

        link = ConvenioPatient(
            convenio_id=convenio.id,
            patient_id=pid,
            employee_id=employee_id,
            is_active=True,
        )
        try:
            db.add(link)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise DentalOSError(
                error=ConvenioErrors.PATIENT_ALREADY_LINKED,
                message="El paciente ya está vinculado a este convenio.",
                status_code=409,
            )

        await db.refresh(link)
        logger.info(
            "Patient linked to convenio: convenio=%s", str(convenio.id)[:8]
        )
        return {
            "id": str(link.id),
            "convenio_id": str(link.convenio_id),
            "patient_id": str(link.patient_id),
            "employee_id": link.employee_id,
            "is_active": link.is_active,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
        }

    # ── Discount Lookup (used by invoice_service) ─────────────────────────────

    async def get_active_convenio_discount(
        self,
        *,
        db: AsyncSession,
        patient_id: uuid.UUID,
    ) -> tuple[int, uuid.UUID | None]:
        """Return (discount_percentage, convenio_id) or (0, None).

        A convenio is active when today falls within
        valid_from .. COALESCE(valid_until, '9999-12-31').
        """
        today = date.today()
        result = await db.execute(
            select(Convenio.id, Convenio.discount_rules)
            .join(
                ConvenioPatient,
                and_(
                    ConvenioPatient.convenio_id == Convenio.id,
                    ConvenioPatient.patient_id == patient_id,
                    ConvenioPatient.is_active.is_(True),
                ),
            )
            .where(
                Convenio.is_active.is_(True),
                Convenio.deleted_at.is_(None),
                Convenio.valid_from <= today,
                (Convenio.valid_until >= today) | (Convenio.valid_until.is_(None)),
            )
            .order_by(Convenio.valid_from.desc())
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return 0, None

        convenio_id, discount_rules = row
        discount_pct = 0
        if isinstance(discount_rules, dict):
            discount_pct = int(discount_rules.get("value", 0))

        return discount_pct, convenio_id

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get(self, db: AsyncSession, convenio_id: str) -> Convenio:
        result = await db.execute(
            select(Convenio).where(
                Convenio.id == uuid.UUID(convenio_id),
                Convenio.is_active.is_(True),
                Convenio.deleted_at.is_(None),
            )
        )
        convenio = result.scalar_one_or_none()
        if convenio is None:
            raise ResourceNotFoundError(
                error=ConvenioErrors.NOT_FOUND,
                resource_name="Convenio",
            )
        return convenio

    def _to_dict(self, convenio: Convenio) -> dict[str, Any]:
        return {
            "id": convenio.id,
            "company_name": convenio.company_name,
            "contact_info": convenio.contact_info,
            "discount_rules": convenio.discount_rules,
            "valid_from": convenio.valid_from,
            "valid_until": convenio.valid_until,
            "is_active": convenio.is_active,
            "created_at": convenio.created_at,
            "updated_at": convenio.updated_at,
        }


convenio_service = ConvenioService()
