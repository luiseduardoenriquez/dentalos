"""Orthodontics service -- case management, bonding, visits, and materials.

Business invariants enforced here:
  - Case status transitions follow VALID_TRANSITIONS from ortho schemas.
  - Bonding records and their teeth are bulk-inserted in a single flush.
  - Visit numbers are auto-assigned and unique within a case.
  - Material consumption decrements inventory quantity atomically (SELECT FOR UPDATE).
  - Inventory quantity never goes below zero on material consumption.
  - Clinical data is NEVER hard-deleted (Res. 1888 regulatory requirement).
  - Soft delete for OrthoCase, OrthoBondingRecord, OrthoVisit (is_active + deleted_at).
  - OrthoBondingTooth and OrthoCaseMaterial rows are immutable once written.
  - PHI (patient names, document numbers, clinical notes) is NEVER logged.
"""

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.error_codes import OrthoErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.odontogram_constants import VALID_FDI_ALL
from app.models.tenant.inventory import InventoryItem
from app.models.tenant.ortho import (
    OrthoBondingRecord,
    OrthoBondingTooth,
    OrthoCase,
    OrthoCaseMaterial,
    OrthoVisit,
)
from app.models.tenant.patient import Patient
from app.schemas.ortho import VALID_TRANSITIONS

logger = logging.getLogger("dentalos.ortho")


# ─── Serialization helpers ───────────────────────────────────────────────────


def _case_to_dict(case: OrthoCase) -> dict[str, Any]:
    """Serialize an OrthoCase ORM instance to a plain dict."""
    return {
        "id": str(case.id),
        "patient_id": str(case.patient_id),
        "doctor_id": str(case.doctor_id),
        "treatment_plan_id": str(case.treatment_plan_id) if case.treatment_plan_id else None,
        "case_number": case.case_number,
        "status": case.status,
        "angle_class": case.angle_class,
        "malocclusion_type": case.malocclusion_type,
        "appliance_type": case.appliance_type,
        "estimated_duration_months": case.estimated_duration_months,
        "actual_start_date": case.actual_start_date,
        "actual_end_date": case.actual_end_date,
        "total_cost_estimated": case.total_cost_estimated,
        "initial_payment": case.initial_payment,
        "monthly_payment": case.monthly_payment,
        "notes": case.notes,
        "is_active": case.is_active,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def _case_to_list_item(case: OrthoCase, visit_count: int) -> dict[str, Any]:
    """Serialize an OrthoCase to a condensed list-view dict."""
    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "status": case.status,
        "appliance_type": case.appliance_type,
        "doctor_id": str(case.doctor_id),
        "total_cost_estimated": case.total_cost_estimated,
        "visit_count": visit_count,
        "created_at": case.created_at,
    }


def _bonding_record_to_dict(record: OrthoBondingRecord) -> dict[str, Any]:
    """Serialize an OrthoBondingRecord ORM instance to a plain dict (with teeth)."""
    return {
        "id": str(record.id),
        "ortho_case_id": str(record.ortho_case_id),
        "recorded_by": str(record.recorded_by),
        "notes": record.notes,
        "teeth": [_tooth_to_dict(t) for t in (record.teeth or [])],
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _tooth_to_dict(tooth: OrthoBondingTooth) -> dict[str, Any]:
    """Serialize an OrthoBondingTooth ORM instance to a plain dict."""
    return {
        "id": str(tooth.id),
        "tooth_number": tooth.tooth_number,
        "bracket_status": tooth.bracket_status,
        "bracket_type": tooth.bracket_type,
        "slot_size": tooth.slot_size,
        "wire_type": tooth.wire_type,
        "band": tooth.band,
        "notes": tooth.notes,
    }


def _visit_to_dict(visit: OrthoVisit) -> dict[str, Any]:
    """Serialize an OrthoVisit ORM instance to a plain dict."""
    return {
        "id": str(visit.id),
        "ortho_case_id": str(visit.ortho_case_id),
        "visit_number": visit.visit_number,
        "doctor_id": str(visit.doctor_id),
        "visit_date": visit.visit_date,
        "wire_upper": visit.wire_upper,
        "wire_lower": visit.wire_lower,
        "elastics": visit.elastics,
        "adjustments": visit.adjustments,
        "next_visit_date": visit.next_visit_date,
        "payment_status": visit.payment_status,
        "payment_amount": visit.payment_amount,
        "payment_id": str(visit.payment_id) if visit.payment_id else None,
        "created_at": visit.created_at,
        "updated_at": visit.updated_at,
    }


def _material_to_dict(material: OrthoCaseMaterial) -> dict[str, Any]:
    """Serialize an OrthoCaseMaterial ORM instance to a plain dict."""
    return {
        "id": str(material.id),
        "ortho_case_id": str(material.ortho_case_id),
        "visit_id": str(material.visit_id) if material.visit_id else None,
        "inventory_item_id": str(material.inventory_item_id),
        "quantity_used": float(material.quantity_used),
        "notes": material.notes,
        "created_by": str(material.created_by),
        "created_at": material.created_at,
    }


# ─── Validation helpers ──────────────────────────────────────────────────────


async def _ensure_patient_active(db: AsyncSession, patient_id: uuid.UUID) -> None:
    """Validate that the patient exists and is active. Raises 404 if not."""
    result = await db.execute(
        select(Patient.id).where(
            Patient.id == patient_id,
            Patient.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise ResourceNotFoundError(
            error="PATIENT_not_found",
            resource_name="Patient",
        )


async def _get_active_case(
    db: AsyncSession,
    case_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> OrthoCase:
    """Fetch an active OrthoCase belonging to the given patient. Raises 404 if not found."""
    result = await db.execute(
        select(OrthoCase).where(
            OrthoCase.id == case_id,
            OrthoCase.patient_id == patient_id,
            OrthoCase.is_active.is_(True),
        )
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise ResourceNotFoundError(
            error=OrthoErrors.CASE_NOT_FOUND,
            resource_name="OrthoCase",
        )
    return case


def _next_case_number(existing_count: int) -> str:
    """Return the next case number string, e.g. 'ORT-0001', 'ORT-0002'."""
    return f"ORT-{existing_count + 1:04d}"


# ─── Ortho Service ────────────────────────────────────────────────────────────


class OrthoService:
    """Stateless orthodontics case management service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path for each method is already set by get_tenant_db().
    """

    async def create_case(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new orthodontic case for a patient.

        Auto-assigns a sequential case number (ORT-0001, ORT-0002, ...) scoped
        to the patient's existing cases in the current tenant schema.

        Args:
            db: Tenant-scoped async session.
            patient_id: UUID string of the patient.
            doctor_id: UUID string of the treating doctor.
            data: Dict with appliance_type and optional classification, cost,
                  duration, treatment_plan_id, and notes fields.

        Raises:
            ResourceNotFoundError (404) -- patient not found or inactive.
        """
        pid = uuid.UUID(patient_id)
        did = uuid.UUID(doctor_id)

        # 1. Validate patient exists and is active
        await _ensure_patient_active(db, pid)

        # 2. Count existing cases (all, including inactive) to generate number
        count_stmt = (
            select(func.count())
            .select_from(OrthoCase)
            .where(OrthoCase.patient_id == pid)
        )
        existing_count = (await db.execute(count_stmt)).scalar_one()
        case_number = _next_case_number(existing_count)

        # 3. Create OrthoCase
        treatment_plan_id_raw = data.get("treatment_plan_id")
        case = OrthoCase(
            patient_id=pid,
            doctor_id=did,
            treatment_plan_id=uuid.UUID(treatment_plan_id_raw) if treatment_plan_id_raw else None,
            case_number=case_number,
            status="planning",
            appliance_type=data["appliance_type"],
            angle_class=data.get("angle_class"),
            malocclusion_type=data.get("malocclusion_type"),
            estimated_duration_months=data.get("estimated_duration_months"),
            total_cost_estimated=data.get("total_cost_estimated", 0),
            initial_payment=data.get("initial_payment", 0),
            monthly_payment=data.get("monthly_payment", 0),
            notes=data.get("notes"),
            is_active=True,
        )
        db.add(case)
        await db.flush()

        logger.info(
            "OrthoCase created: patient=%s case=%s number=%s",
            str(pid)[:8],
            str(case.id)[:8],
            case_number,
        )

        return _case_to_dict(case)

    async def get_case(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        case_id: str,
    ) -> dict[str, Any]:
        """Fetch a single active orthodontic case.

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        case = await _get_active_case(db, cid, pid)
        return _case_to_dict(case)

    async def list_cases(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of active orthodontic cases for a patient.

        List view is condensed and includes a visit_count per case.
        Cases are ordered newest-first.
        """
        pid = uuid.UUID(patient_id)

        # Count total active cases
        count_stmt = (
            select(func.count())
            .select_from(OrthoCase)
            .where(
                OrthoCase.patient_id == pid,
                OrthoCase.is_active.is_(True),
            )
        )
        total = (await db.execute(count_stmt)).scalar_one()

        # Visit count subquery per case
        visit_count_subq = (
            select(
                OrthoVisit.ortho_case_id,
                func.count().label("visit_count"),
            )
            .where(OrthoVisit.is_active.is_(True))
            .group_by(OrthoVisit.ortho_case_id)
            .subquery()
        )

        offset = (page - 1) * page_size
        cases_stmt = (
            select(
                OrthoCase,
                func.coalesce(visit_count_subq.c.visit_count, 0).label("visit_count"),
            )
            .outerjoin(
                visit_count_subq,
                OrthoCase.id == visit_count_subq.c.ortho_case_id,
            )
            .where(
                OrthoCase.patient_id == pid,
                OrthoCase.is_active.is_(True),
            )
            .order_by(OrthoCase.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(cases_stmt)).all()

        items = [_case_to_list_item(row[0], row[1]) for row in rows]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_case(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        case_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply partial updates to an active orthodontic case.

        Only non-None fields in data are written. Status field changes must
        go through transition_case() instead.

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        case = await _get_active_case(db, cid, pid)

        # Update only non-None fields
        for field in (
            "angle_class",
            "malocclusion_type",
            "appliance_type",
            "estimated_duration_months",
            "total_cost_estimated",
            "initial_payment",
            "monthly_payment",
            "notes",
        ):
            value = data.get(field)
            if value is not None:
                setattr(case, field, value)

        await db.flush()
        await db.refresh(case)
        return _case_to_dict(case)

    async def transition_case(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        case_id: str,
        target_status: str,
    ) -> dict[str, Any]:
        """Transition an orthodontic case to a new status.

        Status transitions follow the VALID_TRANSITIONS map from the ortho schema:
          planning → bonding → active_treatment → retention → completed
          (any status) → cancelled

        Side effects:
          - Entering 'bonding': sets actual_start_date = today (UTC).
          - Entering 'completed' or 'cancelled': sets actual_end_date = today (UTC).

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
            DentalOSError (422) -- invalid status transition.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        case = await _get_active_case(db, cid, pid)

        current_status = case.status
        allowed = VALID_TRANSITIONS.get(current_status, frozenset())

        if target_status not in allowed:
            raise DentalOSError(
                error=OrthoErrors.INVALID_STATUS_TRANSITION,
                message=(
                    f"No se puede transicionar el caso de '{current_status}' "
                    f"a '{target_status}'. "
                    f"Transiciones permitidas: {', '.join(sorted(allowed)) or 'ninguna'}."
                ),
                status_code=422,
                details={
                    "current_status": current_status,
                    "target_status": target_status,
                    "allowed_transitions": sorted(allowed),
                },
            )

        today = datetime.now(UTC).date()

        if target_status == "bonding":
            case.actual_start_date = today

        if target_status in ("completed", "cancelled"):
            case.actual_end_date = today

        case.status = target_status
        await db.flush()
        await db.refresh(case)

        return _case_to_dict(case)

    async def create_bonding_record(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        recorded_by: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a bonding record with per-tooth bracket data in a single flush.

        Validates each tooth number against VALID_FDI_ALL before inserting.
        Uses bulk insert for OrthoBondingTooth rows to minimize DB round-trips
        (up to 32 rows = one per adult tooth).

        Args:
            db: Tenant-scoped async session.
            case_id: UUID string of the ortho case.
            patient_id: UUID string of the patient (ownership check).
            recorded_by: UUID string of the clinician recording the bonding.
            data: Dict with notes and teeth list (each with tooth_number and
                  bracket fields).

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
            DentalOSError (422) -- invalid FDI tooth number.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)
        uid = uuid.UUID(recorded_by)

        # 1. Validate case ownership
        await _get_active_case(db, cid, pid)

        # 2. Extract and validate tooth numbers
        teeth_data: list[dict[str, Any]] = data.get("teeth", [])
        tooth_numbers = [t["tooth_number"] for t in teeth_data]
        invalid = [tn for tn in tooth_numbers if tn not in VALID_FDI_ALL]
        if invalid:
            raise DentalOSError(
                error=OrthoErrors.INVALID_TOOTH_NUMBER,
                message=(
                    f"Numeros de diente invalidos: {invalid}. "
                    "Use la numeracion FDI."
                ),
                status_code=422,
                details={"invalid_teeth": invalid},
            )

        # 3. Create the bonding record header
        record = OrthoBondingRecord(
            ortho_case_id=cid,
            recorded_by=uid,
            notes=data.get("notes"),
            is_active=True,
        )
        db.add(record)
        await db.flush()  # assigns record.id

        # 4. Bulk insert OrthoBondingTooth rows (single round-trip)
        if teeth_data:
            tooth_rows = [
                {
                    "id": uuid.uuid4(),
                    "record_id": record.id,
                    "tooth_number": t["tooth_number"],
                    "bracket_status": t["bracket_status"],
                    "bracket_type": t.get("bracket_type"),
                    "slot_size": t.get("slot_size"),
                    "wire_type": t.get("wire_type"),
                    "band": t.get("band", False),
                    "notes": t.get("notes"),
                }
                for t in teeth_data
            ]
            await db.execute(insert(OrthoBondingTooth), tooth_rows)

        # 5. Reload to get teeth via selectin relationship
        await db.refresh(record, attribute_names=["teeth"])

        logger.info(
            "OrthoBondingRecord created: case=%s record=%s teeth=%d",
            str(cid)[:8],
            str(record.id)[:8],
            len(teeth_data),
        )

        return _bonding_record_to_dict(record)

    async def list_bonding_records(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of bonding records for an orthodontic case.

        List view is condensed: {id, recorded_by, tooth_count, created_at}.
        Records are ordered newest-first.

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        # Validate case ownership
        await _get_active_case(db, cid, pid)

        # Count total active bonding records
        count_stmt = (
            select(func.count())
            .select_from(OrthoBondingRecord)
            .where(
                OrthoBondingRecord.ortho_case_id == cid,
                OrthoBondingRecord.is_active.is_(True),
            )
        )
        total = (await db.execute(count_stmt)).scalar_one()

        # Tooth count subquery per record
        tooth_count_subq = (
            select(
                OrthoBondingTooth.record_id,
                func.count().label("tooth_count"),
            )
            .group_by(OrthoBondingTooth.record_id)
            .subquery()
        )

        offset = (page - 1) * page_size
        records_stmt = (
            select(
                OrthoBondingRecord,
                func.coalesce(tooth_count_subq.c.tooth_count, 0).label("tooth_count"),
            )
            .outerjoin(
                tooth_count_subq,
                OrthoBondingRecord.id == tooth_count_subq.c.record_id,
            )
            .where(
                OrthoBondingRecord.ortho_case_id == cid,
                OrthoBondingRecord.is_active.is_(True),
            )
            .order_by(OrthoBondingRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(records_stmt)).all()

        items = [
            {
                "id": str(row[0].id),
                "recorded_by": str(row[0].recorded_by),
                "tooth_count": row[1],
                "created_at": row[0].created_at,
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_bonding_record(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        record_id: str,
    ) -> dict[str, Any]:
        """Fetch a single bonding record with all tooth data.

        Raises:
            ResourceNotFoundError (404) -- case or record not found / inactive.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)
        rid = uuid.UUID(record_id)

        # Validate case ownership
        await _get_active_case(db, cid, pid)

        result = await db.execute(
            select(OrthoBondingRecord)
            .options(selectinload(OrthoBondingRecord.teeth))
            .where(
                OrthoBondingRecord.id == rid,
                OrthoBondingRecord.ortho_case_id == cid,
                OrthoBondingRecord.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()

        if record is None:
            raise ResourceNotFoundError(
                error=OrthoErrors.BONDING_NOT_FOUND,
                resource_name="OrthoBondingRecord",
            )

        return _bonding_record_to_dict(record)

    async def create_visit(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        doctor_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new adjustment visit within an orthodontic case.

        Auto-assigns the next sequential visit_number (MAX + 1) scoped to the
        case. If no visits exist yet, visit_number = 1.

        payment_amount defaults to case.monthly_payment if not provided in data.

        Args:
            db: Tenant-scoped async session.
            case_id: UUID string of the ortho case.
            patient_id: UUID string of the patient (ownership check).
            doctor_id: UUID string of the treating doctor.
            data: Dict with visit_date and optional wire, elastics, adjustments,
                  next_visit_date, and payment fields.

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)
        did = uuid.UUID(doctor_id)

        # 1. Validate case ownership and retrieve for monthly_payment default
        case = await _get_active_case(db, cid, pid)

        # 2. Auto-assign visit_number = MAX(visit_number) + 1 for this case
        max_stmt = (
            select(func.max(OrthoVisit.visit_number))
            .where(
                OrthoVisit.ortho_case_id == cid,
                OrthoVisit.is_active.is_(True),
            )
        )
        current_max = (await db.execute(max_stmt)).scalar_one_or_none()
        visit_number = (current_max or 0) + 1

        # 3. Resolve payment_amount: use provided value or default to monthly_payment
        payment_amount = data.get("payment_amount")
        if payment_amount is None:
            payment_amount = case.monthly_payment

        # 4. Create OrthoVisit
        visit = OrthoVisit(
            ortho_case_id=cid,
            visit_number=visit_number,
            doctor_id=did,
            visit_date=data["visit_date"],
            wire_upper=data.get("wire_upper"),
            wire_lower=data.get("wire_lower"),
            elastics=data.get("elastics"),
            adjustments=data.get("adjustments"),
            next_visit_date=data.get("next_visit_date"),
            payment_status="pending",
            payment_amount=payment_amount,
            is_active=True,
        )
        db.add(visit)
        await db.flush()

        logger.info(
            "OrthoVisit created: case=%s visit=%s number=%d",
            str(cid)[:8],
            str(visit.id)[:8],
            visit_number,
        )

        return _visit_to_dict(visit)

    async def list_visits(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of active visits for an orthodontic case.

        Visits are ordered by visit_number ascending (chronological order).

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        # Validate case ownership
        await _get_active_case(db, cid, pid)

        # Count total active visits
        count_stmt = (
            select(func.count())
            .select_from(OrthoVisit)
            .where(
                OrthoVisit.ortho_case_id == cid,
                OrthoVisit.is_active.is_(True),
            )
        )
        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        visits_stmt = (
            select(OrthoVisit)
            .where(
                OrthoVisit.ortho_case_id == cid,
                OrthoVisit.is_active.is_(True),
            )
            .order_by(OrthoVisit.visit_number.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(visits_stmt)
        visits = result.scalars().all()

        return {
            "items": [_visit_to_dict(v) for v in visits],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_visit(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        visit_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply partial updates to an active visit.

        Only non-None fields in data are written.

        Raises:
            ResourceNotFoundError (404) -- case or visit not found / inactive.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)
        vid = uuid.UUID(visit_id)

        # Validate case ownership
        await _get_active_case(db, cid, pid)

        # Fetch the visit
        result = await db.execute(
            select(OrthoVisit).where(
                OrthoVisit.id == vid,
                OrthoVisit.ortho_case_id == cid,
                OrthoVisit.is_active.is_(True),
            )
        )
        visit = result.scalar_one_or_none()
        if visit is None:
            raise ResourceNotFoundError(
                error=OrthoErrors.VISIT_NOT_FOUND,
                resource_name="OrthoVisit",
            )

        # Update only non-None fields
        for field in (
            "wire_upper",
            "wire_lower",
            "elastics",
            "adjustments",
            "next_visit_date",
            "payment_status",
            "payment_amount",
        ):
            value = data.get(field)
            if value is not None:
                setattr(visit, field, value)

        await db.flush()
        await db.refresh(visit)
        return _visit_to_dict(visit)

    async def add_material(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Record material consumption for an orthodontic case.

        Uses SELECT FOR UPDATE on InventoryItem to atomically verify and
        decrement quantity. Raises if the item has insufficient stock.

        Args:
            db: Tenant-scoped async session.
            case_id: UUID string of the ortho case.
            patient_id: UUID string of the patient (ownership check).
            user_id: UUID string of the user recording the consumption.
            data: Dict with inventory_item_id, quantity_used, and optional
                  visit_id and notes.

        Raises:
            ResourceNotFoundError (404) -- case or inventory item not found.
            DentalOSError (422) -- insufficient inventory quantity.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)
        uid = uuid.UUID(user_id)
        item_id = uuid.UUID(data["inventory_item_id"])
        quantity_used = Decimal(str(data["quantity_used"]))

        # 1. Validate case ownership
        await _get_active_case(db, cid, pid)

        # 2. Lock the inventory item for atomic quantity check and decrement
        item_result = await db.execute(
            select(InventoryItem)
            .where(
                InventoryItem.id == item_id,
                InventoryItem.is_active.is_(True),
            )
            .with_for_update()
        )
        item = item_result.scalar_one_or_none()
        if item is None:
            raise ResourceNotFoundError(
                error="INVENTORY_item_not_found",
                resource_name="InventoryItem",
            )

        # 3. Check sufficient quantity
        current_qty = Decimal(str(item.quantity))
        if current_qty < quantity_used:
            raise DentalOSError(
                error=OrthoErrors.INSUFFICIENT_INVENTORY,
                message=(
                    f"Inventario insuficiente para el item '{str(item_id)[:8]}'. "
                    f"Disponible: {current_qty}, requerido: {quantity_used}."
                ),
                status_code=422,
                details={
                    "inventory_item_id": str(item_id),
                    "available_quantity": float(current_qty),
                    "requested_quantity": float(quantity_used),
                },
            )

        # 4. Decrement inventory quantity
        item.quantity = current_qty - quantity_used

        # 5. Create OrthoCaseMaterial row
        visit_id_raw = data.get("visit_id")
        material = OrthoCaseMaterial(
            ortho_case_id=cid,
            visit_id=uuid.UUID(visit_id_raw) if visit_id_raw else None,
            inventory_item_id=item_id,
            quantity_used=quantity_used,
            notes=data.get("notes"),
            created_by=uid,
        )
        db.add(material)
        await db.flush()

        logger.info(
            "OrthoCaseMaterial added: case=%s item=%s qty=%s",
            str(cid)[:8],
            str(item_id)[:8],
            quantity_used,
        )

        return _material_to_dict(material)

    async def list_materials(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of materials consumed for a case.

        Items ordered by created_at desc (most recent first).
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        # Validate case ownership
        await _get_active_case(db, cid, pid)

        # Count total
        count_stmt = (
            select(func.count())
            .select_from(OrthoCaseMaterial)
            .where(OrthoCaseMaterial.ortho_case_id == cid)
        )
        total = (await db.execute(count_stmt)).scalar_one()

        # Fetch page
        offset = (page - 1) * page_size
        materials_stmt = (
            select(OrthoCaseMaterial)
            .where(OrthoCaseMaterial.ortho_case_id == cid)
            .order_by(OrthoCaseMaterial.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(materials_stmt)).scalars().all()

        return {
            "items": [_material_to_dict(m) for m in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_case_summary(
        self,
        *,
        db: AsyncSession,
        case_id: str,
        patient_id: str,
    ) -> dict[str, Any]:
        """Return aggregated financial and visit statistics for a case.

        Computes:
          - total_visits: count of all active visits.
          - visits_paid: count of visits with payment_status = 'paid'.
          - visits_pending: count of visits with payment_status = 'pending'.
          - total_collected: sum of payment_amount for paid visits (cents COP).
          - total_expected: initial_payment + monthly_payment * total_visits.
          - balance_remaining: total_expected - total_collected.
          - materials_count: total material consumption records.
          - last_visit_date: most recent active visit_date.
          - next_visit_date: earliest upcoming next_visit_date from active visits.

        Raises:
            ResourceNotFoundError (404) -- case not found, inactive, or belongs
                                           to a different patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(case_id)

        ortho_case = await _get_active_case(db, cid, pid)

        # Query visit aggregates in one pass
        visit_agg_stmt = select(
            func.count().label("total_visits"),
            func.count(
                case((OrthoVisit.payment_status == "paid", OrthoVisit.id))
            ).label("visits_paid"),
            func.coalesce(
                func.sum(
                    case(
                        (OrthoVisit.payment_status == "paid", OrthoVisit.payment_amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_collected"),
            func.max(OrthoVisit.visit_date).label("last_visit_date"),
            func.min(OrthoVisit.next_visit_date).label("next_visit_date"),
        ).where(
            OrthoVisit.ortho_case_id == cid,
            OrthoVisit.is_active.is_(True),
        )
        visit_row = (await db.execute(visit_agg_stmt)).one()

        total_visits: int = visit_row.total_visits or 0
        visits_paid: int = int(visit_row.visits_paid or 0)
        visits_pending: int = total_visits - visits_paid
        total_collected: int = int(visit_row.total_collected or 0)
        last_visit_date = visit_row.last_visit_date
        next_visit_date = visit_row.next_visit_date

        # Materials count
        materials_count_stmt = (
            select(func.count())
            .select_from(OrthoCaseMaterial)
            .where(OrthoCaseMaterial.ortho_case_id == cid)
        )
        materials_count: int = (await db.execute(materials_count_stmt)).scalar_one()

        # Financial summary
        total_expected: int = ortho_case.initial_payment + (ortho_case.monthly_payment * total_visits)
        balance_remaining: int = total_expected - total_collected

        return {
            "case_id": str(cid),
            "status": ortho_case.status,
            "total_visits": total_visits,
            "visits_paid": visits_paid,
            "visits_pending": visits_pending,
            "total_collected": total_collected,
            "total_expected": total_expected,
            "balance_remaining": balance_remaining,
            "materials_count": materials_count,
            "last_visit_date": last_visit_date,
            "next_visit_date": next_visit_date,
        }


# ─── Singleton ───────────────────────────────────────────────────────────────

ortho_service = OrthoService()
