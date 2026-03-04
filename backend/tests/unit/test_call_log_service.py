"""Unit tests for CallLogService (VP-18 VoIP Screen Pop / Sprint 31-32).

Tests cover:
  - match_phone_to_patient: found, not found, +57 prefix
  - create_call_log: db.add called, returns CallLog with correct fields
  - update_call_status: completed sets ended_at, not found returns None
  - update_notes: updates notes, not found raises ResourceNotFoundError
  - get_call_log: returns CallLog, not found raises ResourceNotFoundError
  - list_call_logs: paginated result, direction filter
  - publish_screen_pop: verifies Redis publish called with correct channel
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.services.call_log_service import CallLogService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_call_log(**overrides) -> MagicMock:
    """Build a mock CallLog ORM row."""
    call = MagicMock()
    call.id = overrides.get("id", uuid.uuid4())
    call.phone_number = overrides.get("phone_number", "+573001234567")
    call.direction = overrides.get("direction", "inbound")
    call.status = overrides.get("status", "ringing")
    call.twilio_call_sid = overrides.get("twilio_call_sid", f"CA{uuid.uuid4().hex[:30]}")
    call.patient_id = overrides.get("patient_id", None)
    call.staff_id = overrides.get("staff_id", None)
    call.notes = overrides.get("notes", None)
    call.duration_seconds = overrides.get("duration_seconds", None)
    call.started_at = overrides.get("started_at", datetime.now(UTC))
    call.ended_at = overrides.get("ended_at", None)
    call.is_active = overrides.get("is_active", True)
    call.created_at = overrides.get("created_at", datetime.now(UTC))
    call.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return call


def _make_patient(**overrides) -> MagicMock:
    """Build a mock Patient ORM row (minimal)."""
    p = MagicMock()
    p.id = overrides.get("id", uuid.uuid4())
    p.phone = overrides.get("phone", "+573001234567")
    p.is_active = overrides.get("is_active", True)
    return p


# ── TestMatchPhoneToPatient ───────────────────────────────────────────────────


@pytest.mark.unit
class TestMatchPhoneToPatient:
    """Tests for CallLogService.match_phone_to_patient."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = CallLogService()

    async def test_match_phone_to_patient_found(self):
        """Patient with matching phone is found — returns patient UUID."""
        patient_id = uuid.uuid4()
        result = MagicMock()
        result.scalar_one_or_none.return_value = patient_id
        self.db.execute.return_value = result

        found = await self.service.match_phone_to_patient(
            self.db, "+573001234567"
        )

        assert found == patient_id
        self.db.execute.assert_called_once()

    async def test_match_phone_to_patient_not_found(self):
        """No patient with that phone — returns None."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        found = await self.service.match_phone_to_patient(
            self.db, "+573009999999"
        )

        assert found is None

    async def test_match_phone_to_patient_normalized(self):
        """Phone with +57 prefix is passed directly and matched."""
        patient_id = uuid.uuid4()
        result = MagicMock()
        result.scalar_one_or_none.return_value = patient_id
        self.db.execute.return_value = result

        found = await self.service.match_phone_to_patient(
            self.db, "+573001234567"
        )

        # Verify db.execute was called (query was built and run)
        assert found == patient_id
        self.db.execute.assert_called_once()


# ── TestCreateCallLog ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateCallLog:
    """Tests for CallLogService.create_call_log."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.add = MagicMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = CallLogService()

    async def test_create_call_log(self):
        """create_call_log calls db.add and db.flush, returns a CallLog-like object."""
        call_sid = f"CA{uuid.uuid4().hex[:30]}"
        patient_id = uuid.uuid4()

        with patch(
            "app.services.call_log_service.CallLog",
            return_value=_make_call_log(
                direction="inbound",
                status="ringing",
                twilio_call_sid=call_sid,
                patient_id=patient_id,
            ),
        ):
            result = await self.service.create_call_log(
                self.db,
                phone_number="+573001234567",
                direction="inbound",
                twilio_call_sid=call_sid,
                patient_id=patient_id,
            )

        self.db.add.assert_called_once()
        self.db.flush.assert_called_once()
        self.db.refresh.assert_called_once()
        assert result.direction == "inbound"
        assert result.status == "ringing"


# ── TestUpdateCallStatus ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateCallStatus:
    """Tests for CallLogService.update_call_status."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = CallLogService()

    async def test_update_call_status_completed(self):
        """Status=completed sets ended_at on the call log."""
        call = _make_call_log(status="ringing", ended_at=None)
        result = MagicMock()
        result.scalar_one_or_none.return_value = call
        self.db.execute.return_value = result

        updated = await self.service.update_call_status(
            self.db,
            twilio_call_sid=call.twilio_call_sid,
            status="completed",
            duration_seconds=120,
        )

        assert updated.status == "completed"
        assert updated.ended_at is not None
        assert updated.duration_seconds == 120

    async def test_update_call_status_not_found(self):
        """Unknown Twilio SID returns None (caller decides what to do)."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        updated = await self.service.update_call_status(
            self.db,
            twilio_call_sid="CA_nonexistent",
            status="completed",
        )

        assert updated is None

    async def test_update_call_status_missed(self):
        """Status=missed also sets ended_at."""
        call = _make_call_log(status="ringing", ended_at=None)
        result = MagicMock()
        result.scalar_one_or_none.return_value = call
        self.db.execute.return_value = result

        updated = await self.service.update_call_status(
            self.db,
            twilio_call_sid=call.twilio_call_sid,
            status="missed",
        )

        assert updated.status == "missed"
        assert updated.ended_at is not None


# ── TestUpdateNotes ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateNotes:
    """Tests for CallLogService.update_notes."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = CallLogService()

    async def test_update_notes(self):
        """Notes field is updated when the call log exists."""
        call = _make_call_log(notes=None)
        result = MagicMock()
        result.scalar_one_or_none.return_value = call
        self.db.execute.return_value = result

        updated = await self.service.update_notes(
            self.db, call.id, "Paciente preguntó por descuento"
        )

        assert updated.notes == "Paciente preguntó por descuento"
        self.db.flush.assert_called_once()
        self.db.refresh.assert_called_once()

    async def test_update_notes_not_found(self):
        """Unknown call_id raises ResourceNotFoundError."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        with pytest.raises(ResourceNotFoundError):
            await self.service.update_notes(
                self.db, uuid.uuid4(), "Nota irrelevante"
            )


# ── TestGetCallLog ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetCallLog:
    """Tests for CallLogService.get_call_log."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = CallLogService()

    async def test_get_call_log(self):
        """Known call_id returns the CallLog object."""
        call = _make_call_log()
        result = MagicMock()
        result.scalar_one_or_none.return_value = call
        self.db.execute.return_value = result

        retrieved = await self.service.get_call_log(self.db, call.id)

        assert retrieved.id == call.id
        assert retrieved.direction == call.direction

    async def test_get_call_log_not_found(self):
        """Unknown call_id raises ResourceNotFoundError."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        with pytest.raises(ResourceNotFoundError):
            await self.service.get_call_log(self.db, uuid.uuid4())


# ── TestListCallLogs ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListCallLogs:
    """Tests for CallLogService.list_call_logs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = CallLogService()

    async def test_list_call_logs(self):
        """Returns paginated result with items, total, page, page_size."""
        calls = [_make_call_log() for _ in range(3)]

        # First execute call returns total count, second returns items
        count_result = MagicMock()
        count_result.scalar.return_value = 3

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = calls

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.list_call_logs(self.db, page=1, page_size=20)

        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 3

    async def test_list_call_logs_with_direction_filter(self):
        """Direction filter limits items to only those with matching direction."""
        inbound_calls = [_make_call_log(direction="inbound") for _ in range(2)]

        count_result = MagicMock()
        count_result.scalar.return_value = 2

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = inbound_calls

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.list_call_logs(
            self.db, page=1, page_size=20, direction="inbound"
        )

        assert result["total"] == 2
        for item in result["items"]:
            assert item.direction == "inbound"


# ── TestPublishScreenPop ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestPublishScreenPop:
    """Tests for CallLogService.publish_screen_pop and publish_incoming_call."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = CallLogService()
        self.tenant_id = "abc123"

    async def test_publish_screen_pop(self):
        """publish_screen_pop publishes to the correct Redis channel."""
        call = _make_call_log(
            patient_id=uuid.uuid4(),
            direction="inbound",
            started_at=datetime.now(UTC),
        )

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch(
            "app.services.call_log_service.redis_client",
            mock_redis,
        ):
            await self.service.publish_screen_pop(
                self.tenant_id,
                call,
                patient_name="Dr. García",
            )

        mock_redis.publish.assert_called_once()
        channel_arg = mock_redis.publish.call_args[0][0]
        assert channel_arg == f"dentalos:{self.tenant_id}:calls:incoming"

    async def test_publish_incoming_call_payload_format(self):
        """publish_incoming_call sends valid JSON on the correct Redis channel."""
        call_data = {
            "call_id": str(uuid.uuid4()),
            "direction": "inbound",
            "patient_id": str(uuid.uuid4()),
            "call_status": "ringing",
        }

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch(
            "app.services.call_log_service.redis_client",
            mock_redis,
        ):
            await self.service.publish_incoming_call(self.tenant_id, call_data)

        mock_redis.publish.assert_called_once()
        channel_arg, payload_arg = mock_redis.publish.call_args[0]

        assert channel_arg == f"dentalos:{self.tenant_id}:calls:incoming"

        # Payload must be valid JSON
        parsed = json.loads(payload_arg)
        assert parsed["direction"] == "inbound"
