"""Dental lab order service -- VP-22 / Sprint 31-32.

Manages dental laboratory directories and work-order lifecycle for each tenant.

Status transition graph (LabOrder.status):
    pending → sent_to_lab → in_progress → ready → delivered
    (any state except delivered) → cancelled

Timestamp automation:
    → sent_to_lab  : sets sent_at
    → ready        : sets ready_at  + enqueues lab_order.ready notification
    → delivered    : sets delivered_at

Security invariants:
  - PHI (patient names, document numbers) is NEVER logged.
  - Delivered orders are immutable — no status changes allowed after delivery.
  - Orders already cancelled cannot be re-opened.
  - All monetary values in COP cents.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import LabOrderErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.lab_order import DentalLab, LabOrder
from app.schemas.lab_order import DentalLabCreate, DentalLabUpdate, LabOrderCreate, LabOrderUpdate
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.lab_orders")

# -- Transition table ---------------------------------------------------------

# Maps each status to the set of statuses it may advance to.
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"sent_to_lab", "cancelled"}),
    "sent_to_lab": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"ready", "cancelled"}),
    "ready": frozenset({"delivered", "cancelled"}),
    "delivered": frozenset(),   # terminal — no further transitions
    "cancelled": frozenset(),   # terminal — no further transitions
}


# -- Service class ------------------------------------------------------------


class LabOrderService:
    """Stateless dental lab order service.

    All methods receive the AsyncSession from the caller (injected via
    FastAPI Depends). No internal state is held between calls.
    """

    # ── Lab CRUD ──────────────────────────────────────────────────────────────

    async def create_lab(
        self,
        db: AsyncSession,
        data: DentalLabCreate,
    ) -> dict[str, Any]:
        """Create a new dental lab entry for the tenant.

        Args:
            db: Tenant-scoped AsyncSession.
            data: Validated DentalLabCreate payload.

        Returns:
            dict representation of the created DentalLab.
        """
        lab = DentalLab(
            name=data.name.strip(),
            contact_name=data.contact_name.strip() if data.contact_name else None,
            phone=data.phone.strip() if data.phone else None,
            email=data.email.strip() if data.email else None,
            address=data.address.strip() if data.address else None,
            city=data.city.strip() if data.city else None,
            notes=data.notes,
            is_active=True,
        )
        db.add(lab)
        await db.flush()
        await db.refresh(lab)

        logger.info("DentalLab created: lab=%s...", str(lab.id)[:8])
        return self._lab_to_dict(lab)

    async def list_labs(
        self,
        db: AsyncSession,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """Return all dental labs for the tenant.

        Args:
            db: Tenant-scoped AsyncSession.
            include_inactive: When True, includes deactivated labs.

        Returns:
            List of lab dicts ordered by name.
        """
        query = select(DentalLab)
        if not include_inactive:
            query = query.where(DentalLab.is_active.is_(True))
        query = query.order_by(DentalLab.name)

        result = await db.execute(query)
        labs = result.scalars().all()
        return [self._lab_to_dict(lab) for lab in labs]

    async def get_lab(
        self,
        db: AsyncSession,
        lab_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Return a single dental lab or raise ResourceNotFoundError.

        Args:
            db: Tenant-scoped AsyncSession.
            lab_id: UUID of the DentalLab to retrieve.

        Returns:
            dict representation of the DentalLab.

        Raises:
            ResourceNotFoundError: When the lab does not exist or is inactive.
        """
        lab = await self._get_lab_or_raise(db, lab_id)
        return self._lab_to_dict(lab)

    async def update_lab(
        self,
        db: AsyncSession,
        lab_id: uuid.UUID,
        data: DentalLabUpdate,
    ) -> dict[str, Any]:
        """Update mutable fields on a dental lab record.

        Args:
            db: Tenant-scoped AsyncSession.
            lab_id: UUID of the DentalLab to update.
            data: Validated DentalLabUpdate payload (only set fields applied).

        Returns:
            dict representation of the updated DentalLab.

        Raises:
            ResourceNotFoundError: When the lab does not exist.
        """
        lab = await self._get_lab_or_raise(db, lab_id)

        if data.name is not None:
            lab.name = data.name.strip()
        if data.contact_name is not None:
            lab.contact_name = data.contact_name.strip()
        if data.phone is not None:
            lab.phone = data.phone.strip()
        if data.email is not None:
            lab.email = data.email.strip()
        if data.address is not None:
            lab.address = data.address.strip()
        if data.city is not None:
            lab.city = data.city.strip()
        if data.notes is not None:
            lab.notes = data.notes
        if data.is_active is not None:
            lab.is_active = data.is_active

        await db.flush()
        await db.refresh(lab)

        logger.info("DentalLab updated: lab=%s...", str(lab.id)[:8])
        return self._lab_to_dict(lab)

    # ── Order CRUD ────────────────────────────────────────────────────────────

    async def create_order(
        self,
        db: AsyncSession,
        data: LabOrderCreate,
        created_by: uuid.UUID,
    ) -> dict[str, Any]:
        """Create a new lab work order with status=pending.

        Args:
            db: Tenant-scoped AsyncSession.
            data: Validated LabOrderCreate payload.
            created_by: UUID of the staff member creating the order.

        Returns:
            dict representation of the created LabOrder.
        """
        try:
            patient_uuid = uuid.UUID(data.patient_id)
        except ValueError:
            raise DentalOSError(
                error="VALIDATION_invalid_field",
                message="patient_id inválido.",
                status_code=400,
            )

        treatment_plan_uuid: uuid.UUID | None = None
        if data.treatment_plan_id is not None:
            try:
                treatment_plan_uuid = uuid.UUID(data.treatment_plan_id)
            except ValueError:
                raise DentalOSError(
                    error="VALIDATION_invalid_field",
                    message="treatment_plan_id inválido.",
                    status_code=400,
                )

        lab_uuid: uuid.UUID | None = None
        if data.lab_id is not None:
            try:
                lab_uuid = uuid.UUID(data.lab_id)
            except ValueError:
                raise DentalOSError(
                    error="VALIDATION_invalid_field",
                    message="lab_id inválido.",
                    status_code=400,
                )

        order = LabOrder(
            patient_id=patient_uuid,
            treatment_plan_id=treatment_plan_uuid,
            lab_id=lab_uuid,
            order_type=data.order_type,
            specifications=data.specifications,
            status="pending",
            due_date=data.due_date,
            cost_cents=data.cost_cents,
            notes=data.notes,
            created_by=created_by,
            is_active=True,
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        logger.info(
            "LabOrder created: order=%s... patient=%s...",
            str(order.id)[:8],
            str(patient_uuid)[:8],
        )
        return self._order_to_dict(order)

    async def update_order(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        data: LabOrderUpdate,
    ) -> dict[str, Any]:
        """Update mutable fields on a lab order.

        Orders in delivered or cancelled states cannot be modified.

        Args:
            db: Tenant-scoped AsyncSession.
            order_id: UUID of the LabOrder to update.
            data: Validated LabOrderUpdate payload.

        Returns:
            dict representation of the updated LabOrder.

        Raises:
            ResourceNotFoundError: When the order is not found.
            DentalOSError: When the order is in a terminal state.
        """
        order = await self._get_order_or_raise(db, order_id)

        if order.status in ("delivered", "cancelled"):
            raise DentalOSError(
                error=LabOrderErrors.INVALID_STATUS_TRANSITION,
                message="No se puede modificar una orden en estado final (entregada o cancelada).",
                status_code=409,
            )

        if data.lab_id is not None:
            try:
                order.lab_id = uuid.UUID(data.lab_id)
            except ValueError:
                raise DentalOSError(
                    error="VALIDATION_invalid_field",
                    message="lab_id inválido.",
                    status_code=400,
                )
        if data.order_type is not None:
            order.order_type = data.order_type
        if data.specifications is not None:
            order.specifications = data.specifications
        if data.due_date is not None:
            order.due_date = data.due_date
        if data.cost_cents is not None:
            order.cost_cents = data.cost_cents
        if data.notes is not None:
            order.notes = data.notes

        await db.flush()
        await db.refresh(order)

        logger.info("LabOrder updated: order=%s...", str(order.id)[:8])
        return self._order_to_dict(order)

    async def get_order(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Return a single lab order or raise ResourceNotFoundError.

        Args:
            db: Tenant-scoped AsyncSession.
            order_id: UUID of the LabOrder to retrieve.

        Returns:
            dict representation of the LabOrder.

        Raises:
            ResourceNotFoundError: When the order does not exist.
        """
        order = await self._get_order_or_raise(db, order_id)
        return self._order_to_dict(order)

    async def list_orders(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        lab_id: uuid.UUID | None = None,
        patient_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Return a paginated list of lab orders.

        Args:
            db: Tenant-scoped AsyncSession.
            page: 1-based page number.
            page_size: Items per page (max 100).
            status_filter: Optional status to filter by.
            lab_id: Optional lab UUID to filter by.
            patient_id: Optional patient UUID to filter by.

        Returns:
            dict with items, total, page, page_size.
        """
        query = select(LabOrder).where(LabOrder.is_active.is_(True))

        if status_filter is not None:
            query = query.where(LabOrder.status == status_filter)
        if lab_id is not None:
            query = query.where(LabOrder.lab_id == lab_id)
        if patient_id is not None:
            query = query.where(LabOrder.patient_id == patient_id)

        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Paginated results
        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(LabOrder.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        orders = result.scalars().all()

        return {
            "items": [self._order_to_dict(o) for o in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Status advancement ────────────────────────────────────────────────────

    async def advance_status(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        new_status: str,
        tenant_id: str = "",
    ) -> dict[str, Any]:
        """Advance a lab order to the specified status.

        Validates the transition is permitted, sets relevant timestamps,
        and (on → ready) enqueues a lab_order.ready notification.

        Args:
            db: Tenant-scoped AsyncSession.
            order_id: UUID of the LabOrder to advance.
            new_status: Target status string.
            tenant_id: Tenant identifier (used for notification envelope).

        Returns:
            dict representation of the updated LabOrder.

        Raises:
            ResourceNotFoundError: When the order is not found.
            DentalOSError: ALREADY_DELIVERED if currently delivered.
            DentalOSError: INVALID_STATUS_TRANSITION if the transition is not allowed.
        """
        order = await self._get_order_or_raise(db, order_id)

        if order.status == "delivered":
            raise DentalOSError(
                error=LabOrderErrors.ALREADY_DELIVERED,
                message="La orden ya fue entregada. No se puede cambiar su estado.",
                status_code=409,
            )

        allowed = _VALID_TRANSITIONS.get(order.status, frozenset())
        if new_status not in allowed:
            raise DentalOSError(
                error=LabOrderErrors.INVALID_STATUS_TRANSITION,
                message=(
                    f"Transición de estado inválida: '{order.status}' → '{new_status}'. "
                    f"Transiciones permitidas: {sorted(allowed) or 'ninguna'}."
                ),
                status_code=422,
            )

        now = datetime.now(UTC)

        # Set transition-specific timestamps
        if new_status == "sent_to_lab" and order.sent_at is None:
            order.sent_at = now
        elif new_status == "ready" and order.ready_at is None:
            order.ready_at = now
        elif new_status == "delivered" and order.delivered_at is None:
            order.delivered_at = now

        order.status = new_status
        await db.flush()
        await db.refresh(order)

        logger.info(
            "LabOrder status advanced: order=%s... status=%s",
            str(order.id)[:8],
            new_status,
        )

        # Notify staff that the order is ready for pickup
        if new_status == "ready":
            await self._enqueue_ready_notification(
                order=order,
                tenant_id=tenant_id,
            )

        return self._order_to_dict(order)

    # ── Overdue detection ─────────────────────────────────────────────────────

    async def get_overdue_orders(
        self,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Return all active lab orders that have passed their due date.

        An order is considered overdue when:
          - status is NOT in (delivered, cancelled)
          - due_date is NOT NULL and due_date < today

        Args:
            db: Tenant-scoped AsyncSession.

        Returns:
            List of overdue LabOrder dicts ordered by due_date ascending.
        """
        today = date.today()

        result = await db.execute(
            select(LabOrder)
            .where(
                and_(
                    LabOrder.is_active.is_(True),
                    LabOrder.status.not_in(["delivered", "cancelled"]),
                    LabOrder.due_date.is_not(None),
                    LabOrder.due_date < today,
                )
            )
            .order_by(LabOrder.due_date.asc())
        )
        orders = result.scalars().all()
        return [self._order_to_dict(o) for o in orders]

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_lab_or_raise(
        self,
        db: AsyncSession,
        lab_id: uuid.UUID,
    ) -> DentalLab:
        """Fetch a DentalLab or raise ResourceNotFoundError."""
        result = await db.execute(
            select(DentalLab).where(DentalLab.id == lab_id)
        )
        lab = result.scalar_one_or_none()
        if lab is None:
            raise ResourceNotFoundError(
                error=LabOrderErrors.LAB_NOT_FOUND,
                resource_name="DentalLab",
            )
        return lab

    async def _get_order_or_raise(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
    ) -> LabOrder:
        """Fetch a LabOrder or raise ResourceNotFoundError."""
        result = await db.execute(
            select(LabOrder).where(
                LabOrder.id == order_id,
                LabOrder.is_active.is_(True),
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise ResourceNotFoundError(
                error=LabOrderErrors.NOT_FOUND,
                resource_name="LabOrder",
            )
        return order

    async def _enqueue_ready_notification(
        self,
        order: LabOrder,
        tenant_id: str,
    ) -> None:
        """Publish a lab_order.ready job to the notifications queue.

        Called automatically when an order transitions to the 'ready' status
        so that clinic staff can be notified to pick up or schedule delivery.
        """
        try:
            message = QueueMessage(
                tenant_id=tenant_id,
                job_type="lab_order.ready",
                payload={
                    "order_id": str(order.id),
                    "patient_id": str(order.patient_id),
                    "order_type": order.order_type,
                    "lab_id": str(order.lab_id) if order.lab_id else None,
                    "due_date": order.due_date.isoformat() if order.due_date else None,
                },
                priority=5,
            )
            await publish_message("notifications", message)
            logger.debug(
                "lab_order.ready enqueued: order=%s...", str(order.id)[:8]
            )
        except Exception as exc:
            # Notification failures must not roll back the status transition
            logger.warning(
                "Failed to enqueue lab_order.ready notification: order=%s... error=%s",
                str(order.id)[:8],
                str(exc),
            )

    @staticmethod
    def _lab_to_dict(lab: DentalLab) -> dict[str, Any]:
        """Serialize a DentalLab ORM instance to a plain dict."""
        return {
            "id": str(lab.id),
            "name": lab.name,
            "contact_name": lab.contact_name,
            "phone": lab.phone,
            "email": lab.email,
            "address": lab.address,
            "city": lab.city,
            "notes": lab.notes,
            "is_active": lab.is_active,
            "created_at": lab.created_at,
            "updated_at": lab.updated_at,
        }

    @staticmethod
    def _order_to_dict(order: LabOrder) -> dict[str, Any]:
        """Serialize a LabOrder ORM instance to a plain dict."""
        return {
            "id": str(order.id),
            "patient_id": str(order.patient_id),
            "treatment_plan_id": (
                str(order.treatment_plan_id) if order.treatment_plan_id else None
            ),
            "lab_id": str(order.lab_id) if order.lab_id else None,
            "order_type": order.order_type,
            "specifications": order.specifications,
            "status": order.status,
            "due_date": order.due_date,
            "sent_at": order.sent_at,
            "ready_at": order.ready_at,
            "delivered_at": order.delivered_at,
            "cost_cents": order.cost_cents,
            "notes": order.notes,
            "created_by": str(order.created_by) if order.created_by else None,
            "is_active": order.is_active,
            "deleted_at": order.deleted_at,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }


# Module-level singleton
lab_order_service = LabOrderService()
