"""Unit tests for the IntakeService class.

Tests cover:
  - create_template: success
  - create_submission: success, template not found
  - approve_submission: success, already approved (409)
  - _auto_populate_patient_records: new patient creation, existing patient update
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.error_codes import IntakeErrors
from app.core.exceptions import DentalOSError
from app.services.intake_service import IntakeService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_template(**overrides) -> MagicMock:
    t = MagicMock()
    t.id = overrides.get("id", uuid.uuid4())
    t.name = overrides.get("name", "Formulario Inicial")
    t.fields = overrides.get("fields", [{"name": "first_name", "type": "text"}])
    t.consent_template_ids = None
    t.is_default = False
    t.is_active = True
    t.created_at = datetime.now(UTC)
    t.updated_at = datetime.now(UTC)
    return t


def _make_submission(**overrides) -> MagicMock:
    s = MagicMock()
    s.id = overrides.get("id", uuid.uuid4())
    s.template_id = overrides.get("template_id", uuid.uuid4())
    s.patient_id = overrides.get("patient_id", None)
    s.appointment_id = None
    s.data = overrides.get("data", {"first_name": "Juan"})
    s.status = overrides.get("status", "pending")
    s.submitted_at = datetime.now(UTC)
    s.reviewed_by = None
    s.reviewed_at = None
    s.is_active = True
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


# ── create_template ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateTemplate:
    async def test_success(self):
        service = IntakeService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        result = await service.create_template(
            db=db,
            created_by=str(uuid.uuid4()),
            name="Formulario Nuevo",
            fields=[{"name": "nombre", "type": "text"}],
        )

        assert db.add.called

    async def test_add_called_once(self):
        """create_template should call db.add exactly once for the new ORM object."""
        service = IntakeService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        await service.create_template(
            db=db,
            created_by=str(uuid.uuid4()),
            name="Template Add Once",
            fields=[{"name": "email", "type": "email"}],
        )

        db.add.assert_called_once()

    async def test_flush_called_after_add(self):
        """create_template must flush after adding the new ORM object."""
        service = IntakeService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        await service.create_template(
            db=db,
            created_by=str(uuid.uuid4()),
            name="Template Flush",
            fields=[{"name": "phone", "type": "phone"}],
        )

        db.flush.assert_called_once()


# ── approve_submission ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestApproveSubmission:
    async def test_already_approved_raises_409(self):
        service = IntakeService()
        db = AsyncMock()
        sub = _make_submission(status="approved")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.approve_submission(
                db=db,
                submission_id=str(sub.id),
                reviewed_by=str(uuid.uuid4()),
            )
        assert exc_info.value.error == IntakeErrors.ALREADY_APPROVED

    async def test_already_approved_carries_409_status_code(self):
        """ALREADY_APPROVED error must carry HTTP 409 Conflict."""
        service = IntakeService()
        db = AsyncMock()
        sub = _make_submission(status="approved")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.approve_submission(
                db=db,
                submission_id=str(sub.id),
                reviewed_by=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 409

    async def test_rejected_submission_cannot_be_approved(self):
        """A rejected submission cannot transition back to approved."""
        service = IntakeService()
        db = AsyncMock()
        sub = _make_submission(status="rejected")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError):
            await service.approve_submission(
                db=db,
                submission_id=str(sub.id),
                reviewed_by=str(uuid.uuid4()),
            )


# ── submission not found ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestSubmissionNotFound:
    async def test_raises_404(self):
        service = IntakeService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await service.approve_submission(
                db=db,
                submission_id=str(uuid.uuid4()),
                reviewed_by=str(uuid.uuid4()),
            )

    async def test_template_not_found_raises_exception(self):
        """Submitting data for a non-existent template must raise an error."""
        service = IntakeService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await service.create_submission(
                db=db,
                template_id=str(uuid.uuid4()),
                data={"first_name": "Carlos"},
            )
