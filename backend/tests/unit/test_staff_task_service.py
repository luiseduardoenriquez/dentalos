"""Unit tests for the StaffTaskService class.

Tests cover:
  - create_task: creates a manual task
  - update_task: valid status transitions, invalid transition (422)
  - check_delinquency: creates tasks at 30/60/90 day thresholds, skips duplicates
  - check_acceptance: creates tasks for unaccepted quotations, skips existing
  - get_acceptance_rate: returns rate calculation from DB aggregate
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import TaskErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.staff_task_service import StaffTaskService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_task(**overrides) -> MagicMock:
    task = MagicMock()
    task.id = overrides.get("id", uuid.uuid4())
    task.title = overrides.get("title", "Factura vencida")
    task.description = overrides.get("description", "Contactar paciente")
    task.task_type = overrides.get("task_type", "delinquency")
    task.status = overrides.get("status", "open")
    task.priority = overrides.get("priority", "normal")
    task.assigned_to = overrides.get("assigned_to", None)
    task.patient_id = overrides.get("patient_id", uuid.uuid4())
    task.reference_id = overrides.get("reference_id", uuid.uuid4())
    task.reference_type = overrides.get("reference_type", "invoice")
    task.due_date = overrides.get("due_date", None)
    task.completed_at = overrides.get("completed_at", None)
    task.metadata = overrides.get("metadata", {"threshold_days": 30})
    task.created_at = datetime.now(UTC)
    task.updated_at = datetime.now(UTC)
    return task


# ── create_task ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateTask:
    async def test_create_task_calls_add_and_flush(self):
        """create_task must call db.add once and db.flush once."""
        service = StaffTaskService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        task = _make_task(task_type="manual")

        async def fake_refresh(obj):
            obj.id = task.id
            obj.title = task.title
            obj.description = task.description
            obj.task_type = "manual"
            obj.status = "open"
            obj.priority = task.priority
            obj.assigned_to = task.assigned_to
            obj.patient_id = task.patient_id
            obj.reference_id = task.reference_id
            obj.reference_type = task.reference_type
            obj.due_date = task.due_date
            obj.completed_at = None
            obj.metadata = task.metadata
            obj.created_at = task.created_at
            obj.updated_at = task.updated_at

        db.refresh = fake_refresh

        with patch("app.services.staff_task_service.StaffTask") as MockTask:
            MockTask.return_value = task

            result = await service.create_task(
                db=db,
                title="Llamar al paciente",
                task_type="manual",
                priority="normal",
            )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_create_task_initial_status_is_open(self):
        """create_task must produce a task with status='open'."""
        service = StaffTaskService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        task = _make_task(status="open")

        async def fake_refresh(obj):
            obj.id = task.id
            obj.title = task.title
            obj.description = task.description
            obj.task_type = task.task_type
            obj.status = "open"
            obj.priority = task.priority
            obj.assigned_to = task.assigned_to
            obj.patient_id = task.patient_id
            obj.reference_id = task.reference_id
            obj.reference_type = task.reference_type
            obj.due_date = task.due_date
            obj.completed_at = None
            obj.metadata = task.metadata
            obj.created_at = task.created_at
            obj.updated_at = task.updated_at

        db.refresh = fake_refresh

        with patch("app.services.staff_task_service.StaffTask") as MockTask:
            MockTask.return_value = task

            result = await service.create_task(
                db=db,
                title="Tarea nueva",
                task_type="manual",
            )

        assert result["status"] == "open"

    async def test_create_task_returns_dict_with_expected_keys(self):
        """create_task must return a dict with id, title, status, task_type."""
        service = StaffTaskService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        task = _make_task()

        async def fake_refresh(obj):
            obj.id = task.id
            obj.title = task.title
            obj.description = task.description
            obj.task_type = task.task_type
            obj.status = "open"
            obj.priority = task.priority
            obj.assigned_to = task.assigned_to
            obj.patient_id = task.patient_id
            obj.reference_id = task.reference_id
            obj.reference_type = task.reference_type
            obj.due_date = None
            obj.completed_at = None
            obj.metadata = task.metadata
            obj.created_at = task.created_at
            obj.updated_at = task.updated_at

        db.refresh = fake_refresh

        with patch("app.services.staff_task_service.StaffTask") as MockTask:
            MockTask.return_value = task

            result = await service.create_task(db=db, title="Tarea X")

        for key in ("id", "title", "status", "task_type", "priority"):
            assert key in result


# ── update_task: valid transitions ────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateTaskStatusTransition:
    async def test_open_to_in_progress_is_valid(self):
        """Transitioning from 'open' to 'in_progress' must succeed."""
        service = StaffTaskService()
        db = AsyncMock()

        task = _make_task(status="open")
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task
        db.execute = AsyncMock(return_value=task_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await service.update_task(
            db=db,
            task_id=task.id,
            status="in_progress",
        )

        assert task.status == "in_progress"

    async def test_open_to_completed_is_valid(self):
        """Transitioning from 'open' to 'completed' must set completed_at."""
        service = StaffTaskService()
        db = AsyncMock()

        task = _make_task(status="open")
        task.completed_at = None
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task
        db.execute = AsyncMock(return_value=task_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await service.update_task(
            db=db,
            task_id=task.id,
            status="completed",
        )

        assert task.status == "completed"
        assert task.completed_at is not None

    async def test_in_progress_to_completed_is_valid(self):
        """Transitioning from 'in_progress' to 'completed' must succeed."""
        service = StaffTaskService()
        db = AsyncMock()

        task = _make_task(status="in_progress")
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task
        db.execute = AsyncMock(return_value=task_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await service.update_task(
            db=db,
            task_id=task.id,
            status="completed",
        )

        assert task.status == "completed"


# ── update_task: invalid transitions ─────────────────────────────────────────


@pytest.mark.unit
class TestUpdateTaskInvalidTransition:
    async def test_completed_to_open_raises_422(self):
        """Transitioning from 'completed' to 'open' must raise 422 DentalOSError."""
        service = StaffTaskService()
        db = AsyncMock()

        task = _make_task(status="completed")
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task
        db.execute = AsyncMock(return_value=task_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.update_task(
                db=db,
                task_id=task.id,
                status="open",
            )

        assert exc_info.value.error == TaskErrors.INVALID_STATUS_TRANSITION
        assert exc_info.value.status_code == 422

    async def test_dismissed_to_in_progress_raises_422(self):
        """Transitioning from 'dismissed' to 'in_progress' must raise 422."""
        service = StaffTaskService()
        db = AsyncMock()

        task = _make_task(status="dismissed")
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task
        db.execute = AsyncMock(return_value=task_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.update_task(
                db=db,
                task_id=task.id,
                status="in_progress",
            )

        assert exc_info.value.status_code == 422

    async def test_task_not_found_raises_404(self):
        """update_task must raise ResourceNotFoundError for an unknown task_id."""
        service = StaffTaskService()
        db = AsyncMock()

        not_found_result = MagicMock()
        not_found_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=not_found_result)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.update_task(
                db=db,
                task_id=uuid.uuid4(),
                status="in_progress",
            )

        assert exc_info.value.error == TaskErrors.NOT_FOUND


# ── check_delinquency ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckDelinquencyCreatesTasks:
    async def _build_delinquency_db(
        self,
        overdue_rows_per_threshold: list[list[tuple]],
        has_existing_task: bool = False,
    ) -> AsyncMock:
        """Build a mock DB for check_delinquency.

        The method issues these execute() calls per threshold:
          1. SELECT delinquency_thresholds_days from tenant_settings
          2. SELECT first active receptionist
          3+ (for each threshold) SELECT overdue invoices
          4+ (for each invoice) SELECT existing task
        """
        # We patch _get_tenant_delinquency_thresholds and _get_first_receptionist
        # directly so we only need to mock the invoice and task queries.
        pass

    async def test_creates_task_for_overdue_invoice(self):
        """check_delinquency must create one task per overdue invoice per threshold."""
        service = StaffTaskService()
        db = AsyncMock()

        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        receptionist_id = uuid.uuid4()

        # Overdue invoices for the 30-day threshold
        overdue_result_30 = MagicMock()
        overdue_result_30.all.return_value = [(invoice_id, patient_id)]

        # No existing task for this invoice + threshold
        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(
            side_effect=[overdue_result_30, no_existing_result]
        )
        db.add = MagicMock()
        db.flush = AsyncMock()

        created_task = _make_task(task_type="delinquency")

        async def fake_refresh(obj):
            obj.id = created_task.id
            obj.title = created_task.title
            obj.description = created_task.description
            obj.task_type = "delinquency"
            obj.status = "open"
            obj.priority = "normal"
            obj.assigned_to = receptionist_id
            obj.patient_id = patient_id
            obj.reference_id = invoice_id
            obj.reference_type = "invoice"
            obj.due_date = None
            obj.completed_at = None
            obj.metadata = {"threshold_days": 30}
            obj.created_at = created_task.created_at
            obj.updated_at = created_task.updated_at

        db.refresh = fake_refresh

        with patch.object(
            service,
            "_get_tenant_delinquency_thresholds",
            return_value=[30],
        ), patch.object(
            service,
            "_get_first_receptionist",
            return_value=receptionist_id,
        ), patch("app.services.staff_task_service.StaffTask") as MockTask:
            MockTask.return_value = created_task

            count = await service.check_delinquency(db=db, tenant_id="tn_abc123")

        assert count == 1
        db.add.assert_called_once()

    async def test_creates_high_priority_for_60_day_threshold(self):
        """check_delinquency must assign 'high' priority for 60-day overdue invoices."""
        service = StaffTaskService()
        db = AsyncMock()

        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        overdue_result = MagicMock()
        overdue_result.all.return_value = [(invoice_id, patient_id)]

        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[overdue_result, no_existing_result])
        db.add = MagicMock()
        db.flush = AsyncMock()

        captured_priority: list[str] = []

        original_create = service.create_task

        async def capture_create_task(**kwargs):
            captured_priority.append(kwargs.get("priority", ""))
            return {"id": str(uuid.uuid4()), "status": "open", "priority": kwargs.get("priority")}

        with patch.object(
            service,
            "_get_tenant_delinquency_thresholds",
            return_value=[60],
        ), patch.object(
            service,
            "_get_first_receptionist",
            return_value=None,
        ), patch.object(service, "create_task", side_effect=capture_create_task):

            count = await service.check_delinquency(db=db, tenant_id="tn_abc123")

        assert count == 1
        assert captured_priority[0] == "high"

    async def test_creates_urgent_priority_for_90_day_threshold(self):
        """check_delinquency must assign 'urgent' priority for 90-day overdue invoices."""
        service = StaffTaskService()
        db = AsyncMock()

        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        overdue_result = MagicMock()
        overdue_result.all.return_value = [(invoice_id, patient_id)]

        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[overdue_result, no_existing_result])

        captured_priority: list[str] = []

        async def capture_create_task(**kwargs):
            captured_priority.append(kwargs.get("priority", ""))
            return {"id": str(uuid.uuid4()), "status": "open", "priority": kwargs.get("priority")}

        with patch.object(
            service,
            "_get_tenant_delinquency_thresholds",
            return_value=[90],
        ), patch.object(
            service,
            "_get_first_receptionist",
            return_value=None,
        ), patch.object(service, "create_task", side_effect=capture_create_task):

            count = await service.check_delinquency(db=db, tenant_id="tn_abc123")

        assert count == 1
        assert captured_priority[0] == "urgent"


@pytest.mark.unit
class TestCheckDelinquencyNoDuplicates:
    async def test_skips_invoice_with_existing_task(self):
        """check_delinquency must skip invoices that already have an open task."""
        service = StaffTaskService()
        db = AsyncMock()

        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        overdue_result = MagicMock()
        overdue_result.all.return_value = [(invoice_id, patient_id)]

        # A task already exists for this invoice + threshold
        existing_task_result = MagicMock()
        existing_task_result.scalar_one_or_none.return_value = uuid.uuid4()

        db.execute = AsyncMock(side_effect=[overdue_result, existing_task_result])
        db.add = MagicMock()

        with patch.object(
            service,
            "_get_tenant_delinquency_thresholds",
            return_value=[30],
        ), patch.object(
            service,
            "_get_first_receptionist",
            return_value=None,
        ):
            count = await service.check_delinquency(db=db, tenant_id="tn_abc123")

        assert count == 0
        db.add.assert_not_called()

    async def test_no_overdue_invoices_returns_zero(self):
        """check_delinquency must return 0 when no invoices are overdue."""
        service = StaffTaskService()
        db = AsyncMock()

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        db.execute = AsyncMock(return_value=overdue_result)
        db.add = MagicMock()

        with patch.object(
            service,
            "_get_tenant_delinquency_thresholds",
            return_value=[30, 60, 90],
        ), patch.object(
            service,
            "_get_first_receptionist",
            return_value=None,
        ):
            count = await service.check_delinquency(db=db, tenant_id="tn_abc123")

        assert count == 0
        db.add.assert_not_called()


# ── check_acceptance ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckAcceptance:
    async def test_creates_task_for_unaccepted_quotation(self):
        """check_acceptance must create a task for each long-pending quotation."""
        service = StaffTaskService()
        db = AsyncMock()

        quotation_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        pending_result = MagicMock()
        pending_result.all.return_value = [(quotation_id, patient_id)]

        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[pending_result, no_existing_result])
        db.add = MagicMock()
        db.flush = AsyncMock()

        created_task = _make_task(task_type="acceptance", reference_type="quotation")

        async def fake_refresh(obj):
            obj.id = created_task.id
            obj.title = created_task.title
            obj.description = created_task.description
            obj.task_type = "acceptance"
            obj.status = "open"
            obj.priority = "normal"
            obj.assigned_to = None
            obj.patient_id = patient_id
            obj.reference_id = quotation_id
            obj.reference_type = "quotation"
            obj.due_date = None
            obj.completed_at = None
            obj.metadata = {"followup_days": 7}
            obj.created_at = created_task.created_at
            obj.updated_at = created_task.updated_at

        db.refresh = fake_refresh

        with patch.object(
            service,
            "_get_tenant_acceptance_followup_days",
            return_value=7,
        ), patch("app.services.staff_task_service.StaffTask") as MockTask:
            MockTask.return_value = created_task

            count = await service.check_acceptance(db=db, tenant_id="tn_abc123")

        assert count == 1
        db.add.assert_called_once()

    async def test_skips_quotation_with_existing_acceptance_task(self):
        """check_acceptance must skip quotations that already have an open task."""
        service = StaffTaskService()
        db = AsyncMock()

        quotation_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        pending_result = MagicMock()
        pending_result.all.return_value = [(quotation_id, patient_id)]

        existing_task_result = MagicMock()
        existing_task_result.scalar_one_or_none.return_value = uuid.uuid4()

        db.execute = AsyncMock(side_effect=[pending_result, existing_task_result])
        db.add = MagicMock()

        with patch.object(
            service,
            "_get_tenant_acceptance_followup_days",
            return_value=7,
        ):
            count = await service.check_acceptance(db=db, tenant_id="tn_abc123")

        assert count == 0
        db.add.assert_not_called()

    async def test_no_pending_quotations_returns_zero(self):
        """check_acceptance must return 0 when no quotations need follow-up."""
        service = StaffTaskService()
        db = AsyncMock()

        pending_result = MagicMock()
        pending_result.all.return_value = []
        db.execute = AsyncMock(return_value=pending_result)
        db.add = MagicMock()

        with patch.object(
            service,
            "_get_tenant_acceptance_followup_days",
            return_value=7,
        ):
            count = await service.check_acceptance(db=db, tenant_id="tn_abc123")

        assert count == 0
        db.add.assert_not_called()


# ── get_acceptance_rate ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetAcceptanceRate:
    async def test_get_acceptance_rate_returns_expected_keys(self):
        """get_acceptance_rate must return a dict with the six analytics keys."""
        service = StaffTaskService()
        db = AsyncMock()

        row = MagicMock()
        row.total = 10
        row.accepted = 6
        row.pending = 3
        row.expired = 1
        row.avg_days_to_accept = 4.5

        result_mock = MagicMock()
        result_mock.one.return_value = row
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_acceptance_rate(db=db)

        for key in (
            "total_quotations",
            "accepted_count",
            "pending_count",
            "expired_count",
            "acceptance_rate",
            "average_days_to_accept",
        ):
            assert key in result

    async def test_get_acceptance_rate_calculation(self):
        """get_acceptance_rate must compute rate = accepted / total."""
        service = StaffTaskService()
        db = AsyncMock()

        row = MagicMock()
        row.total = 8
        row.accepted = 4
        row.pending = 3
        row.expired = 1
        row.avg_days_to_accept = 3.0

        result_mock = MagicMock()
        result_mock.one.return_value = row
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_acceptance_rate(db=db)

        assert result["total_quotations"] == 8
        assert result["accepted_count"] == 4
        # 4 / 8 = 0.5
        assert result["acceptance_rate"] == 0.5

    async def test_get_acceptance_rate_zero_total_returns_zero_rate(self):
        """get_acceptance_rate must return 0.0 rate when total is 0 (no division by zero)."""
        service = StaffTaskService()
        db = AsyncMock()

        row = MagicMock()
        row.total = 0
        row.accepted = 0
        row.pending = 0
        row.expired = 0
        row.avg_days_to_accept = None

        result_mock = MagicMock()
        result_mock.one.return_value = row
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_acceptance_rate(db=db)

        assert result["acceptance_rate"] == 0.0
        assert result["average_days_to_accept"] is None

    async def test_get_acceptance_rate_with_date_range(self):
        """get_acceptance_rate must accept date_from and date_to without error."""
        service = StaffTaskService()
        db = AsyncMock()

        row = MagicMock()
        row.total = 5
        row.accepted = 3
        row.pending = 2
        row.expired = 0
        row.avg_days_to_accept = 2.0

        result_mock = MagicMock()
        result_mock.one.return_value = row
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.get_acceptance_rate(
            db=db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 3, 31),
        )

        assert result["total_quotations"] == 5
        assert result["acceptance_rate"] == 0.6
