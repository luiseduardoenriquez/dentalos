"""Treatment plan service — create, manage, approve, and track treatment plans.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - Approval requires digital signature (via digital_signature_service).
  - All monetary values in COP cents.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import TreatmentPlanErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError, TreatmentPlanError
from app.core.pdf import render_pdf
from app.models.tenant.patient import Patient
from app.models.tenant.service_catalog import ServiceCatalog
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.services.digital_signature_service import digital_signature_service

logger = logging.getLogger("dentalos.treatment_plan")


def _item_to_dict(item: TreatmentPlanItem) -> dict[str, Any]:
    """Serialize a TreatmentPlanItem ORM instance to a plain dict."""
    return {
        "id": str(item.id),
        "treatment_plan_id": str(item.treatment_plan_id),
        "cups_code": item.cups_code,
        "cups_description": item.cups_description,
        "tooth_number": item.tooth_number,
        "estimated_cost": item.estimated_cost,
        "actual_cost": item.actual_cost,
        "priority_order": item.priority_order,
        "status": item.status,
        "procedure_id": str(item.procedure_id) if item.procedure_id else None,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _plan_to_dict(plan: TreatmentPlan) -> dict[str, Any]:
    """Serialize a TreatmentPlan ORM instance to a plain dict."""
    items = [_item_to_dict(i) for i in plan.items] if plan.items else []

    # Compute progress
    total_non_cancelled = sum(1 for i in items if i["status"] != "cancelled")
    completed_count = sum(1 for i in items if i["status"] == "completed")
    progress = (completed_count / total_non_cancelled * 100) if total_non_cancelled > 0 else 0.0

    return {
        "id": str(plan.id),
        "patient_id": str(plan.patient_id),
        "doctor_id": str(plan.doctor_id),
        "name": plan.name,
        "description": plan.description,
        "status": plan.status,
        "total_cost_estimated": plan.total_cost_estimated,
        "total_cost_actual": plan.total_cost_actual,
        "signature_id": str(plan.signature_id) if plan.signature_id else None,
        "approved_at": plan.approved_at,
        "items": items,
        "progress_percent": round(progress, 1),
        "is_active": plan.is_active,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


class TreatmentPlanService:
    """Stateless treatment plan service."""

    async def create_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        name: str,
        description: str | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new treatment plan with optional items.

        Raises:
            DentalOSError (404) — patient not found or inactive.
        """
        pid = uuid.UUID(patient_id)

        # Validate patient
        patient_result = await db.execute(
            select(Patient.id).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        if patient_result.scalar_one_or_none() is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="El paciente no existe o está inactivo.",
                status_code=404,
            )

        plan = TreatmentPlan(
            patient_id=pid,
            doctor_id=uuid.UUID(doctor_id),
            name=name,
            description=description,
            status="draft",
            total_cost_estimated=0,
            total_cost_actual=0,
            is_active=True,
        )
        db.add(plan)
        await db.flush()

        # Add items if provided
        total_estimated = 0
        if items:
            for idx, item_data in enumerate(items):
                # Auto-lookup price from service catalog if not provided
                estimated_cost = item_data.get("estimated_cost")
                if estimated_cost is None:
                    estimated_cost = await self._lookup_price(db=db, cups_code=item_data["cups_code"])

                plan_item = TreatmentPlanItem(
                    treatment_plan_id=plan.id,
                    cups_code=item_data["cups_code"],
                    cups_description=item_data["cups_description"],
                    tooth_number=item_data.get("tooth_number"),
                    estimated_cost=estimated_cost,
                    actual_cost=0,
                    priority_order=item_data.get("priority_order", idx),
                    status="pending",
                    notes=item_data.get("notes"),
                )
                db.add(plan_item)
                total_estimated += estimated_cost

        plan.total_cost_estimated = total_estimated
        await db.flush()

        # Reload with items relationship
        await db.refresh(plan)

        logger.info("Plan created: patient=%s plan=%s", patient_id[:8], str(plan.id)[:8])

        return _plan_to_dict(plan)

    async def get_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single treatment plan with items."""
        result = await db.execute(
            select(TreatmentPlan).where(
                TreatmentPlan.id == uuid.UUID(plan_id),
                TreatmentPlan.patient_id == uuid.UUID(patient_id),
                TreatmentPlan.is_active.is_(True),
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None
        return _plan_to_dict(plan)

    async def list_plans(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        """Paginated list of treatment plans for a patient."""
        pid = uuid.UUID(patient_id)
        offset = (page - 1) * page_size

        count_stmt = (
            select(func.count(TreatmentPlan.id))
            .where(TreatmentPlan.patient_id == pid, TreatmentPlan.is_active.is_(True))
        )
        list_stmt = (
            select(TreatmentPlan)
            .where(TreatmentPlan.patient_id == pid, TreatmentPlan.is_active.is_(True))
            .order_by(TreatmentPlan.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        if status_filter:
            count_stmt = count_stmt.where(TreatmentPlan.status == status_filter)
            list_stmt = list_stmt.where(TreatmentPlan.status == status_filter)

        total = (await db.execute(count_stmt)).scalar_one()
        plans = (await db.execute(list_stmt)).scalars().all()

        return {
            "items": [_plan_to_dict(p) for p in plans],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update plan metadata. Only allowed on draft plans.

        Raises:
            ResourceNotFoundError (404) — plan not found.
            TreatmentPlanError (409) — plan is not in draft status.
        """
        plan = await self._get_plan_or_raise(db, patient_id, plan_id)

        if plan.status != "draft":
            raise TreatmentPlanError(
                error=TreatmentPlanErrors.INVALID_STATUS_TRANSITION,
                message="Solo se pueden editar planes en estado borrador.",
                status_code=409,
            )

        if name is not None:
            plan.name = name
        if description is not None:
            plan.description = description

        await db.flush()
        await db.refresh(plan)

        return _plan_to_dict(plan)

    async def add_item(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
        cups_code: str,
        cups_description: str,
        tooth_number: int | None = None,
        estimated_cost: int | None = None,
        priority_order: int = 0,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add an item to a treatment plan."""
        plan = await self._get_plan_or_raise(db, patient_id, plan_id)

        if estimated_cost is None:
            estimated_cost = await self._lookup_price(db=db, cups_code=cups_code)

        item = TreatmentPlanItem(
            treatment_plan_id=plan.id,
            cups_code=cups_code,
            cups_description=cups_description,
            tooth_number=tooth_number,
            estimated_cost=estimated_cost,
            actual_cost=0,
            priority_order=priority_order,
            status="pending",
            notes=notes,
        )
        db.add(item)

        # Update plan total
        plan.total_cost_estimated += estimated_cost
        await db.flush()
        await db.refresh(plan)

        logger.info("Item added to plan=%s cups=%s", plan_id[:8], cups_code)

        return _plan_to_dict(plan)

    async def update_item(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
        item_id: str,
        estimated_cost: int | None = None,
        priority_order: int | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Update a plan item."""
        plan = await self._get_plan_or_raise(db, patient_id, plan_id)
        item = await self._get_item_or_raise(db, plan.id, item_id)

        old_cost = item.estimated_cost

        if estimated_cost is not None:
            item.estimated_cost = estimated_cost
            plan.total_cost_estimated += (estimated_cost - old_cost)
        if priority_order is not None:
            item.priority_order = priority_order
        if notes is not None:
            item.notes = notes
        if status is not None:
            item.status = status

        await db.flush()
        await db.refresh(plan)

        return _plan_to_dict(plan)

    async def complete_item(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
        item_id: str,
        procedure_id: str,
        actual_cost: int,
    ) -> dict[str, Any]:
        """Mark a plan item as completed and link the procedure.

        Auto-completes the plan when all items are completed/cancelled.
        """
        plan = await self._get_plan_or_raise(db, patient_id, plan_id)
        item = await self._get_item_or_raise(db, plan.id, item_id)

        if item.status == "completed":
            raise TreatmentPlanError(
                error=TreatmentPlanErrors.ITEM_ALREADY_COMPLETED,
                message="Este item ya fue completado.",
                status_code=409,
            )

        item.status = "completed"
        item.procedure_id = uuid.UUID(procedure_id)
        item.actual_cost = actual_cost

        # Update plan actual cost
        plan.total_cost_actual += actual_cost

        await db.flush()

        # Check if all items are completed/cancelled → auto-complete plan
        await db.refresh(plan)
        all_done = all(i.status in ("completed", "cancelled") for i in plan.items)
        if all_done and plan.status == "active":
            plan.status = "completed"
            await db.flush()

        await db.refresh(plan)

        logger.info("Item completed: plan=%s item=%s", plan_id[:8], item_id[:8])

        return _plan_to_dict(plan)

    async def approve_plan(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        plan_id: str,
        signer_id: str,
        signature_image_b64: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Approve a plan with a digital signature. Transitions draft → active.

        Raises:
            TreatmentPlanError (409) — plan already approved.
        """
        plan = await self._get_plan_or_raise(db, patient_id, plan_id)

        if plan.status != "draft":
            raise TreatmentPlanError(
                error=TreatmentPlanErrors.ALREADY_APPROVED,
                message="Este plan ya fue aprobado.",
                status_code=409,
            )

        # Create digital signature
        sig_result = await digital_signature_service.create_signature(
            db=db,
            tenant_id=tenant_id,
            signer_id=signer_id,
            document_type="treatment_plan",
            document_id=str(plan.id),
            signer_type="patient",
            signature_image_b64=signature_image_b64,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        plan.signature_id = uuid.UUID(sig_result["id"])
        plan.approved_at = datetime.now(UTC)
        plan.status = "active"
        await db.flush()
        await db.refresh(plan)

        logger.info("Plan approved: plan=%s", plan_id[:8])

        return _plan_to_dict(plan)

    async def cancel_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
    ) -> dict[str, Any]:
        """Cancel a treatment plan."""
        plan = await self._get_plan_or_raise(db, patient_id, plan_id)

        if plan.status in ("completed", "cancelled"):
            raise TreatmentPlanError(
                error=TreatmentPlanErrors.ALREADY_CANCELLED,
                message="Este plan ya fue completado o cancelado.",
                status_code=409,
            )

        plan.status = "cancelled"
        # Cancel all pending/scheduled items
        for item in plan.items:
            if item.status in ("pending", "scheduled"):
                item.status = "cancelled"

        await db.flush()
        await db.refresh(plan)

        return _plan_to_dict(plan)

    async def generate_pdf(
        self,
        *,
        plan_data: dict[str, Any],
        clinic_name: str = "DentalOS",
        watermark: str | None = None,
    ) -> bytes:
        """Generate a PDF for a treatment plan."""
        return await render_pdf(
            template_name="treatment_plan_es.html",
            context={
                "plan": plan_data,
                "clinic_name": clinic_name,
            },
            watermark=watermark,
        )

    # ─── Private helpers ─────────────────────────────────────────────────

    async def _get_plan_or_raise(
        self,
        db: AsyncSession,
        patient_id: str,
        plan_id: str,
    ) -> TreatmentPlan:
        """Fetch a plan or raise 404."""
        result = await db.execute(
            select(TreatmentPlan).where(
                TreatmentPlan.id == uuid.UUID(plan_id),
                TreatmentPlan.patient_id == uuid.UUID(patient_id),
                TreatmentPlan.is_active.is_(True),
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ResourceNotFoundError(
                error=TreatmentPlanErrors.NOT_FOUND,
                resource_name="TreatmentPlan",
            )
        return plan

    async def _get_item_or_raise(
        self,
        db: AsyncSession,
        plan_id: uuid.UUID,
        item_id: str,
    ) -> TreatmentPlanItem:
        """Fetch a plan item or raise 404."""
        result = await db.execute(
            select(TreatmentPlanItem).where(
                TreatmentPlanItem.id == uuid.UUID(item_id),
                TreatmentPlanItem.treatment_plan_id == plan_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise ResourceNotFoundError(
                error=TreatmentPlanErrors.ITEM_NOT_FOUND,
                resource_name="TreatmentPlanItem",
            )
        return item

    async def _lookup_price(
        self,
        *,
        db: AsyncSession,
        cups_code: str,
    ) -> int:
        """Look up default price from service catalog. Returns 0 if not found."""
        result = await db.execute(
            select(ServiceCatalog.default_price).where(
                ServiceCatalog.cups_code == cups_code,
                ServiceCatalog.is_active.is_(True),
            )
        )
        price = result.scalar_one_or_none()
        return price if price is not None else 0


# Module-level singleton
treatment_plan_service = TreatmentPlanService()
