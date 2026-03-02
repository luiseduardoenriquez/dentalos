"""Staff task service — delinquency and acceptance follow-up task automation.

Covers GAP-05 (Delinquency tracking) and GAP-06 (Quotation acceptance tracking).

Security invariants:
  - PHI is NEVER logged (no patient names, document numbers, phone numbers).
  - Only UUIDs are included in log messages.
  - Tenant settings govern threshold values; defaults apply when absent.
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import TaskErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.invoice import Invoice
from app.models.tenant.quotation import Quotation
from app.models.tenant.staff_task import StaffTask
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.staff_tasks")

# Valid status transitions — terminal states (completed, dismissed) have no
# outbound edges; once a task reaches them it cannot be re-opened.
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "completed", "dismissed"},
    "in_progress": {"completed", "dismissed"},
}

# Priority mapping for delinquency thresholds (days overdue → priority).
_DELINQUENCY_PRIORITY: dict[int, str] = {
    30: "normal",
    60: "high",
    90: "urgent",
}


class StaffTaskService:
    """Stateless staff task service."""

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create_task(
        self,
        *,
        db: AsyncSession,
        title: str,
        description: str | None = None,
        task_type: str = "manual",
        priority: str = "normal",
        assigned_to: uuid.UUID | None = None,
        patient_id: uuid.UUID | None = None,
        reference_id: uuid.UUID | None = None,
        reference_type: str | None = None,
        due_date: date | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new staff task and return it as a dict."""
        task = StaffTask(
            title=title,
            description=description,
            task_type=task_type,
            status="open",
            priority=priority,
            assigned_to=assigned_to,
            patient_id=patient_id,
            reference_id=reference_id,
            reference_type=reference_type,
            due_date=due_date,
            metadata=metadata,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        logger.info(
            "Staff task created: id=%s type=%s priority=%s",
            str(task.id)[:8],
            task_type,
            priority,
        )
        return self._task_to_dict(task)

    async def list_tasks(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        task_type: str | None = None,
        status: str | None = None,
        assigned_to: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Return a paginated list of staff tasks with optional filters."""
        offset = (page - 1) * page_size
        conditions: list[Any] = []

        if task_type is not None:
            conditions.append(StaffTask.task_type == task_type)
        if status is not None:
            conditions.append(StaffTask.status == status)
        if assigned_to is not None:
            conditions.append(StaffTask.assigned_to == assigned_to)

        base_query = select(StaffTask)
        if conditions:
            base_query = base_query.where(and_(*conditions))

        total_result = await db.execute(
            select(func.count(StaffTask.id)).where(
                and_(*conditions) if conditions else True
            )
        )
        total: int = total_result.scalar_one()

        rows_result = await db.execute(
            base_query
            .order_by(
                # Urgency first, then recency.
                StaffTask.priority.desc(),
                StaffTask.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        tasks = rows_result.scalars().all()

        return {
            "items": [self._task_to_dict(t) for t in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_task(
        self,
        *,
        db: AsyncSession,
        task_id: uuid.UUID,
        status: str | None = None,
        assigned_to: uuid.UUID | str | None = None,
        priority: str | None = None,
    ) -> dict[str, Any]:
        """Update task status, assignee, or priority.

        Status transitions are validated. Attempting a disallowed transition
        raises TASK_invalid_status_transition (422).
        Setting status to 'completed' automatically records completed_at.
        """
        task = await self._get_task(db, task_id)

        if status is not None and status != task.status:
            allowed = _VALID_TRANSITIONS.get(task.status, set())
            if status not in allowed:
                raise DentalOSError(
                    error=TaskErrors.INVALID_STATUS_TRANSITION,
                    message=(
                        f"Cannot transition task from '{task.status}' to '{status}'."
                    ),
                    status_code=422,
                    details={
                        "current_status": task.status,
                        "requested_status": status,
                        "allowed_transitions": sorted(allowed),
                    },
                )
            task.status = status
            if status == "completed":
                task.completed_at = datetime.now(UTC)

        if priority is not None:
            task.priority = priority

        if assigned_to is not None:
            if isinstance(assigned_to, str):
                assigned_to = uuid.UUID(assigned_to)
            task.assigned_to = assigned_to

        await db.flush()
        await db.refresh(task)
        logger.info(
            "Staff task updated: id=%s status=%s",
            str(task.id)[:8],
            task.status,
        )
        return self._task_to_dict(task)

    # ── Cron handlers ─────────────────────────────────────────────────────────

    async def check_delinquency(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
    ) -> int:
        """Daily cron: create tasks for overdue invoices past threshold.

        Algorithm:
          1. Read delinquency_thresholds_days from tenant settings
             (default [30, 60, 90]).
          2. For each threshold, find invoices where
             status='pending' AND due_date + threshold_days <= today
             AND balance > 0.
          3. Skip invoices that already have an open/in_progress delinquency
             task for the same reference_id + threshold.
          4. Auto-assign to first active receptionist if available.
          5. Return count of new tasks created.

        PHI rule: only UUIDs are logged; no names or financial values.
        """
        today = date.today()
        thresholds = await self._get_tenant_delinquency_thresholds(db)
        receptionist_id = await self._get_first_receptionist(db)

        created_count = 0

        for threshold_days in thresholds:
            cutoff = today - timedelta(days=threshold_days)
            priority = _DELINQUENCY_PRIORITY.get(threshold_days, "normal")

            # Find overdue invoices past the current threshold.
            overdue_result = await db.execute(
                select(Invoice.id, Invoice.patient_id).where(
                    and_(
                        Invoice.status == "pending",
                        Invoice.balance > 0,
                        Invoice.due_date <= cutoff,
                        Invoice.is_active.is_(True),
                    )
                )
            )
            overdue_rows = overdue_result.all()

            for invoice_id, patient_id in overdue_rows:
                # Check if a task already exists for this invoice + threshold.
                existing = await db.execute(
                    select(StaffTask.id).where(
                        and_(
                            StaffTask.task_type == "delinquency",
                            StaffTask.reference_id == invoice_id,
                            StaffTask.status.in_(["open", "in_progress"]),
                            # Use metadata to distinguish per-threshold duplicates.
                            StaffTask.metadata["threshold_days"].astext
                            == str(threshold_days),
                        )
                    ).limit(1)
                )
                if existing.scalar_one_or_none() is not None:
                    continue

                await self.create_task(
                    db=db,
                    title=(
                        f"Factura vencida ({threshold_days} días) — "
                        f"seguimiento de cobro"
                    ),
                    description=(
                        f"La factura lleva más de {threshold_days} días vencida "
                        "y tiene saldo pendiente. Contactar al paciente para "
                        "gestionar el pago."
                    ),
                    task_type="delinquency",
                    priority=priority,
                    assigned_to=receptionist_id,
                    patient_id=patient_id,
                    reference_id=invoice_id,
                    reference_type="invoice",
                    metadata={
                        "threshold_days": threshold_days,
                        "detected_on": today.isoformat(),
                    },
                )
                created_count += 1

        logger.info(
            "Delinquency check complete: tenant=%s thresholds=%s tasks_created=%d",
            tenant_id[:8],
            thresholds,
            created_count,
        )
        return created_count

    async def check_acceptance(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
    ) -> int:
        """Daily cron: create tasks for quotations pending acceptance too long.

        Algorithm:
          1. Read acceptance_followup_days from tenant settings (default 7).
          2. Find quotations where status IN ('sent', 'pending')
             AND created_at + followup_days <= today.
          3. Skip quotations that already have an open/in_progress acceptance
             task for the same reference_id.
          4. Return count of new tasks created.

        PHI rule: only UUIDs are logged.
        """
        today = date.today()
        followup_days = await self._get_tenant_acceptance_followup_days(db)
        cutoff_dt = datetime.now(UTC) - timedelta(days=followup_days)

        # Quotations in 'sent' status that have not been acted upon.
        pending_result = await db.execute(
            select(Quotation.id, Quotation.patient_id).where(
                and_(
                    Quotation.status.in_(["sent", "pending"]),
                    Quotation.created_at <= cutoff_dt,
                    Quotation.is_active.is_(True),
                )
            )
        )
        pending_rows = pending_result.all()

        created_count = 0
        for quotation_id, patient_id in pending_rows:
            # Check for existing open task.
            existing = await db.execute(
                select(StaffTask.id).where(
                    and_(
                        StaffTask.task_type == "acceptance",
                        StaffTask.reference_id == quotation_id,
                        StaffTask.status.in_(["open", "in_progress"]),
                    )
                ).limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            await self.create_task(
                db=db,
                title=(
                    f"Cotización sin aceptar ({followup_days} días) — "
                    "seguimiento de aprobación"
                ),
                description=(
                    f"La cotización lleva más de {followup_days} días enviada "
                    "sin respuesta del paciente. Contactar para confirmar o "
                    "ajustar el plan de tratamiento."
                ),
                task_type="acceptance",
                priority="normal",
                patient_id=patient_id,
                reference_id=quotation_id,
                reference_type="quotation",
                metadata={
                    "followup_days": followup_days,
                    "detected_on": today.isoformat(),
                },
            )
            created_count += 1

        logger.info(
            "Acceptance check complete: tenant=%s followup_days=%d tasks_created=%d",
            tenant_id[:8],
            followup_days,
            created_count,
        )
        return created_count

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def get_acceptance_rate(
        self,
        *,
        db: AsyncSession,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Return quotation acceptance rate analytics for the given date range.

        Calculates:
          - total non-draft quotations
          - accepted (approved) count
          - pending (sent/pending) count
          - expired count
          - acceptance rate = accepted / (total non-draft) if total > 0 else 0.0
          - average days from creation to approval (approved quotations only)
        """
        conditions: list[Any] = [
            Quotation.is_active.is_(True),
            Quotation.status != "draft",
        ]
        if date_from is not None:
            conditions.append(Quotation.created_at >= datetime(
                date_from.year, date_from.month, date_from.day, tzinfo=UTC
            ))
        if date_to is not None:
            # Inclusive upper bound: end of day_to.
            conditions.append(Quotation.created_at < datetime(
                date_to.year, date_to.month, date_to.day + 1, tzinfo=UTC
            ))

        result = await db.execute(
            select(
                func.count(Quotation.id).label("total"),
                func.count(Quotation.id).filter(
                    Quotation.status == "approved"
                ).label("accepted"),
                func.count(Quotation.id).filter(
                    Quotation.status.in_(["sent", "pending"])
                ).label("pending"),
                func.count(Quotation.id).filter(
                    Quotation.status == "expired"
                ).label("expired"),
                func.avg(
                    func.extract(
                        "epoch",
                        Quotation.approved_at - Quotation.created_at,
                    ) / 86400.0
                ).filter(
                    Quotation.status == "approved",
                    Quotation.approved_at.isnot(None),
                ).label("avg_days_to_accept"),
            ).where(and_(*conditions))
        )
        row = result.one()

        total: int = row.total or 0
        accepted: int = row.accepted or 0
        pending: int = row.pending or 0
        expired: int = row.expired or 0
        acceptance_rate: float = (accepted / total) if total > 0 else 0.0
        avg_days: float | None = (
            round(float(row.avg_days_to_accept), 1)
            if row.avg_days_to_accept is not None
            else None
        )

        return {
            "total_quotations": total,
            "accepted_count": accepted,
            "pending_count": pending,
            "expired_count": expired,
            "acceptance_rate": round(acceptance_rate, 4),
            "average_days_to_accept": avg_days,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_task(self, db: AsyncSession, task_id: uuid.UUID) -> StaffTask:
        """Fetch a StaffTask by ID or raise ResourceNotFoundError."""
        result = await db.execute(
            select(StaffTask).where(StaffTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise ResourceNotFoundError(
                error=TaskErrors.NOT_FOUND,
                resource_name="StaffTask",
            )
        return task

    async def _get_tenant_delinquency_thresholds(
        self, db: AsyncSession
    ) -> list[int]:
        """Read delinquency_thresholds_days from tenant settings.

        Falls back to [30, 60, 90] if not configured.
        This avoids a hard dependency on the settings service — if the query
        fails we use the default so the cron still runs.
        """
        try:
            from sqlalchemy import text

            result = await db.execute(
                text(
                    "SELECT settings->'billing'->'delinquency_thresholds_days' "
                    "FROM tenant_settings LIMIT 1"
                )
            )
            row = result.scalar_one_or_none()
            if row and isinstance(row, list):
                thresholds = [int(t) for t in row if isinstance(t, int | str)]
                if thresholds:
                    return sorted(thresholds)
        except Exception:
            logger.debug(
                "Could not read delinquency thresholds from settings, using defaults"
            )
        return [30, 60, 90]

    async def _get_tenant_acceptance_followup_days(
        self, db: AsyncSession
    ) -> int:
        """Read acceptance_followup_days from tenant settings. Default: 7."""
        try:
            from sqlalchemy import text

            result = await db.execute(
                text(
                    "SELECT settings->'billing'->'acceptance_followup_days' "
                    "FROM tenant_settings LIMIT 1"
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                return int(row)
        except Exception:
            logger.debug(
                "Could not read acceptance_followup_days from settings, using default"
            )
        return 7

    async def _get_first_receptionist(
        self, db: AsyncSession
    ) -> uuid.UUID | None:
        """Return the id of the first active receptionist for auto-assignment.

        Returns None when no receptionist exists (task will be unassigned).
        """
        result = await db.execute(
            select(User.id)
            .where(
                and_(
                    User.role == "receptionist",
                    User.is_active.is_(True),
                )
            )
            .order_by(User.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _task_to_dict(task: StaffTask) -> dict[str, Any]:
        """Serialise a StaffTask to a plain dict (UUIDs as strings)."""
        return {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "status": task.status,
            "priority": task.priority,
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
            "patient_id": str(task.patient_id) if task.patient_id else None,
            "reference_id": str(task.reference_id) if task.reference_id else None,
            "reference_type": task.reference_type,
            "due_date": task.due_date,
            "completed_at": task.completed_at,
            "metadata": task.metadata,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }


# Module-level singleton — import and use this everywhere.
staff_task_service = StaffTaskService()
