"""Family group service — management of patient family groups and consolidated billing.

Security invariants:
  - PHI (patient names, IDs) is NEVER logged.
  - Financial data in COP cents.
  - Soft-delete only — clinical data is never hard-deleted.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import FamilyErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.family import FamilyGroup, FamilyMember
from app.models.tenant.invoice import Invoice
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.family")


class FamilyService:
    """Stateless family group service."""

    # ── Group Lifecycle ────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        db: AsyncSession,
        name: str,
        primary_contact_patient_id: str,
    ) -> dict[str, Any]:
        """Create a family group and add the primary contact as first member.

        The primary contact is added with relationship='parent' as a sensible
        default for the administrative head of the family account.
        """
        primary_pid = uuid.UUID(primary_contact_patient_id)

        # Verify the primary contact patient exists
        await self._get_patient(db, primary_pid)

        group = FamilyGroup(
            name=name,
            primary_contact_patient_id=primary_pid,
            is_active=True,
        )
        db.add(group)
        await db.flush()
        await db.refresh(group)

        # Add primary contact as the first member automatically
        member = FamilyMember(
            family_group_id=group.id,
            patient_id=primary_pid,
            relationship="parent",
            is_active=True,
        )
        db.add(member)
        await db.flush()

        logger.info("Family group created: id=%s", str(group.id)[:8])
        return await self._group_to_dict(db, group)

    async def get(self, *, db: AsyncSession, family_id: str) -> dict[str, Any]:
        """Get a family group with its active members and their names."""
        group = await self._get_group(db, family_id)
        return await self._group_to_dict(db, group)

    # ── Member Management ──────────────────────────────────────────────────────

    async def add_member(
        self,
        *,
        db: AsyncSession,
        family_id: str,
        patient_id: str,
        relationship: str,
    ) -> dict[str, Any]:
        """Add a patient to a family group.

        Raises FamilyErrors.ALREADY_IN_FAMILY if the patient is already an
        active member of any family group (enforced by the UNIQUE constraint
        on family_members.patient_id for active records).
        """
        group = await self._get_group(db, family_id)
        pid = uuid.UUID(patient_id)

        # Verify the patient exists
        await self._get_patient(db, pid)

        # Check if patient is already in any family (active membership)
        existing = await db.execute(
            select(FamilyMember.id).where(
                FamilyMember.patient_id == pid,
                FamilyMember.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DentalOSError(
                error=FamilyErrors.ALREADY_IN_FAMILY,
                message="El paciente ya pertenece a un grupo familiar.",
                status_code=409,
            )

        member = FamilyMember(
            family_group_id=group.id,
            patient_id=pid,
            relationship=relationship,
            is_active=True,
        )
        db.add(member)
        await db.flush()

        logger.info(
            "Member added to family: family=%s",
            str(group.id)[:8],
        )
        return await self._group_to_dict(db, group)

    async def remove_member(
        self,
        *,
        db: AsyncSession,
        family_id: str,
        patient_id: str,
    ) -> dict[str, Any]:
        """Soft-remove a patient from a family group.

        Raises FamilyErrors.PRIMARY_CONTACT_REQUIRED if the caller attempts to
        remove the group's designated primary contact.
        """
        group = await self._get_group(db, family_id)
        pid = uuid.UUID(patient_id)

        if pid == group.primary_contact_patient_id:
            raise DentalOSError(
                error=FamilyErrors.PRIMARY_CONTACT_REQUIRED,
                message=(
                    "No se puede eliminar al contacto principal del grupo familiar. "
                    "Cambie el contacto principal antes de remover este miembro."
                ),
                status_code=409,
            )

        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.family_group_id == group.id,
                FamilyMember.patient_id == pid,
                FamilyMember.is_active.is_(True),
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise ResourceNotFoundError(
                error=FamilyErrors.MEMBER_NOT_FOUND,
                resource_name="FamilyMember",
            )

        member.is_active = False
        await db.flush()

        logger.info(
            "Member removed from family: family=%s",
            str(group.id)[:8],
        )
        return await self._group_to_dict(db, group)

    # ── Consolidated Billing ───────────────────────────────────────────────────

    async def get_family_billing(
        self, *, db: AsyncSession, family_id: str,
    ) -> dict[str, Any]:
        """Return a consolidated billing summary across all active family members.

        Aggregates invoices for each member: total_billed (sum of invoice totals),
        total_paid (sum of amount_paid), total_balance (sum of balance columns).
        Only considers non-cancelled, active invoices.
        """
        group = await self._get_group(db, family_id)

        # Collect active member patient IDs
        members_result = await db.execute(
            select(FamilyMember.patient_id).where(
                FamilyMember.family_group_id == group.id,
                FamilyMember.is_active.is_(True),
            )
        )
        member_patient_ids = [row[0] for row in members_result.all()]

        # For each member, resolve name and aggregate billing
        member_summaries: list[dict[str, Any]] = []
        grand_billed = 0
        grand_paid = 0
        grand_balance = 0

        for pid in member_patient_ids:
            patient = await self._get_patient(db, pid)
            patient_name = f"{patient.first_name} {patient.last_name}"

            billing_result = await db.execute(
                select(
                    func.coalesce(func.sum(Invoice.total), 0).label("total_billed"),
                    func.coalesce(func.sum(Invoice.amount_paid), 0).label("total_paid"),
                    func.coalesce(func.sum(Invoice.balance), 0).label("total_balance"),
                ).where(
                    Invoice.patient_id == pid,
                    Invoice.is_active.is_(True),
                    Invoice.status != "cancelled",
                )
            )
            billing_row = billing_result.one()

            member_billed = int(billing_row.total_billed)
            member_paid = int(billing_row.total_paid)
            member_balance = int(billing_row.total_balance)

            member_summaries.append({
                "patient_id": str(pid),
                "patient_name": patient_name,
                "total_billed": member_billed,
                "total_paid": member_paid,
                "total_balance": member_balance,
            })

            grand_billed += member_billed
            grand_paid += member_paid
            grand_balance += member_balance

        return {
            "family_id": group.id,
            "family_name": group.name,
            "members": member_summaries,
            "total_billed": grand_billed,
            "total_paid": grand_paid,
            "total_balance": grand_balance,
        }

    # ── Private Helpers ────────────────────────────────────────────────────────

    async def _get_group(self, db: AsyncSession, family_id: str) -> FamilyGroup:
        """Fetch an active family group or raise 404."""
        result = await db.execute(
            select(FamilyGroup).where(
                FamilyGroup.id == uuid.UUID(family_id),
                FamilyGroup.is_active.is_(True),
            )
        )
        group = result.scalar_one_or_none()
        if group is None:
            raise ResourceNotFoundError(
                error=FamilyErrors.NOT_FOUND,
                resource_name="FamilyGroup",
            )
        return group

    async def _get_patient(self, db: AsyncSession, patient_id: uuid.UUID) -> Patient:
        """Fetch an active patient or raise 404."""
        from app.core.error_codes import PatientErrors

        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            raise ResourceNotFoundError(
                error=PatientErrors.NOT_FOUND,
                resource_name="Patient",
            )
        return patient

    async def _group_to_dict(
        self, db: AsyncSession, group: FamilyGroup,
    ) -> dict[str, Any]:
        """Serialize a FamilyGroup with its active members to a dict."""
        members_result = await db.execute(
            select(FamilyMember, Patient.first_name, Patient.last_name)
            .join(Patient, FamilyMember.patient_id == Patient.id)
            .where(
                FamilyMember.family_group_id == group.id,
                FamilyMember.is_active.is_(True),
            )
            .order_by(FamilyMember.created_at)
        )
        rows = members_result.all()

        members = [
            {
                "patient_id": member.patient_id,
                "patient_name": f"{first_name} {last_name}",
                "relationship": member.relationship,
                "is_active": member.is_active,
            }
            for member, first_name, last_name in rows
        ]

        return {
            "id": group.id,
            "name": group.name,
            "primary_contact_patient_id": group.primary_contact_patient_id,
            "members": members,
            "is_active": group.is_active,
            "created_at": group.created_at,
        }


family_service = FamilyService()
