"""Unit tests for TelemedicineService (GAP-09 / Sprint 29-30).

Tests cover:
  - create_session: success, addon required, session already active,
    appointment not found
  - get_session: success, not found
  - get_patient_join_url: success, wrong patient
  - end_session: success, calculates duration, calls provider
  - link_to_clinical_record: creates audit entry
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import TelemedicineErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.telemedicine_service import TelemedicineService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_video_session(**overrides) -> MagicMock:
    """Build a mock VideoSession ORM row."""
    s = MagicMock()
    s.id = overrides.get("id", uuid.uuid4())
    s.appointment_id = overrides.get("appointment_id", uuid.uuid4())
    s.provider = overrides.get("provider", "daily")
    s.provider_session_id = overrides.get("provider_session_id", "room-abc123")
    s.status = overrides.get("status", "created")
    s.join_url_doctor = overrides.get(
        "join_url_doctor", "https://daily.co/room/doc-token-xyz"
    )
    s.join_url_patient = overrides.get(
        "join_url_patient", "https://daily.co/room/pat-token-abc"
    )
    s.started_at = overrides.get("started_at", None)
    s.ended_at = overrides.get("ended_at", None)
    s.duration_seconds = overrides.get("duration_seconds", None)
    s.recording_url = overrides.get("recording_url", None)
    s.created_at = overrides.get("created_at", datetime.now(UTC))
    return s


def _make_appointment_row(**overrides) -> MagicMock:
    """Build a mock Appointment row returned from a query."""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.status = overrides.get("status", "confirmed")
    row.patient_id = overrides.get("patient_id", uuid.uuid4())
    return row


def _make_room_result(**overrides) -> MagicMock:
    """Build a mock provider room creation result."""
    r = MagicMock()
    r.provider_session_id = overrides.get("provider_session_id", "room-xyz")
    r.room_url = overrides.get("room_url", "https://daily.co/room/room-xyz")
    return r


# ── TestCreateSession ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateSession:
    """Tests for TelemedicineService.create_session."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.add = MagicMock()
        self.service = TelemedicineService()
        self.appointment_id = str(uuid.uuid4())
        self.tenant_id = "tn_test1234"
        self.tenant_settings = {"telemedicine_config": {"enabled": True}}

    async def test_create_session_success(self):
        """Full flow: add-on gate → no existing session → confirmed appointment → create."""
        # No existing session
        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None

        # Confirmed appointment row
        appt_row = _make_appointment_row(
            id=uuid.UUID(self.appointment_id), status="confirmed"
        )
        appt_result = MagicMock()
        appt_result.one_or_none.return_value = appt_row

        self.db.execute.side_effect = [no_existing_result, appt_result]

        session_orm = _make_video_session(
            appointment_id=uuid.UUID(self.appointment_id)
        )

        mock_provider = AsyncMock()
        mock_provider.create_room = AsyncMock(return_value=_make_room_result())
        mock_provider.get_room_url = AsyncMock(
            side_effect=[
                "https://daily.co/room/doc",
                "https://daily.co/room/pat",
            ]
        )

        with patch(
            "app.services.telemedicine_service._get_provider",
            return_value=mock_provider,
        ), patch(
            "app.services.telemedicine_service.VideoSession",
            return_value=session_orm,
        ):
            result = await self.service.create_session(
                db=self.db,
                appointment_id=self.appointment_id,
                tenant_id=self.tenant_id,
                tenant_settings=self.tenant_settings,
            )

        self.db.add.assert_called_once()
        self.db.flush.assert_called()
        assert result["provider"] == "daily"
        assert result["join_url_doctor"] == "https://daily.co/room/doc-token-xyz"

    async def test_create_session_addon_required(self):
        """Telemedicine add-on not enabled → raises ADD_ON_REQUIRED (402)."""
        disabled_settings: dict = {}

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.create_session(
                db=self.db,
                appointment_id=self.appointment_id,
                tenant_id=self.tenant_id,
                tenant_settings=disabled_settings,
            )

        assert exc_info.value.error == TelemedicineErrors.ADD_ON_REQUIRED
        assert exc_info.value.status_code == 402

    async def test_create_session_addon_explicitly_disabled(self):
        """Add-on config with enabled=False → raises ADD_ON_REQUIRED."""
        disabled_settings = {"telemedicine_config": {"enabled": False}}

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.create_session(
                db=self.db,
                appointment_id=self.appointment_id,
                tenant_id=self.tenant_id,
                tenant_settings=disabled_settings,
            )

        assert exc_info.value.error == TelemedicineErrors.ADD_ON_REQUIRED

    async def test_create_session_already_active(self):
        """Existing active session → raises SESSION_ALREADY_ACTIVE (409)."""
        existing_session = _make_video_session(status="active")
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_session
        self.db.execute.return_value = existing_result

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.create_session(
                db=self.db,
                appointment_id=self.appointment_id,
                tenant_id=self.tenant_id,
                tenant_settings=self.tenant_settings,
            )

        assert exc_info.value.error == TelemedicineErrors.SESSION_ALREADY_ACTIVE
        assert exc_info.value.status_code == 409

    async def test_create_session_appointment_not_found(self):
        """Appointment does not exist → raises ResourceNotFoundError."""
        no_existing_result = MagicMock()
        no_existing_result.scalar_one_or_none.return_value = None

        appt_result = MagicMock()
        appt_result.one_or_none.return_value = None

        self.db.execute.side_effect = [no_existing_result, appt_result]

        with pytest.raises(ResourceNotFoundError):
            await self.service.create_session(
                db=self.db,
                appointment_id=self.appointment_id,
                tenant_id=self.tenant_id,
                tenant_settings=self.tenant_settings,
            )


# ── TestGetSession ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetSession:
    """Tests for TelemedicineService.get_session."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = TelemedicineService()
        self.appointment_id = str(uuid.uuid4())

    async def test_get_session_success(self):
        """Existing session by appointment_id → returns serialized dict."""
        session = _make_video_session(
            appointment_id=uuid.UUID(self.appointment_id),
            status="active",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = session
        self.db.execute.return_value = result_mock

        result = await self.service.get_session(
            db=self.db,
            appointment_id=self.appointment_id,
        )

        assert result["status"] == "active"
        assert result["provider"] == "daily"
        assert "join_url_doctor" in result

    async def test_get_session_not_found(self):
        """No session for appointment → raises SESSION_NOT_FOUND (404)."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result_mock

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.get_session(
                db=self.db,
                appointment_id=self.appointment_id,
            )

        assert exc_info.value.error == TelemedicineErrors.SESSION_NOT_FOUND
        assert exc_info.value.status_code == 404


# ── TestGetPatientJoinUrl ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetPatientJoinUrl:
    """Tests for TelemedicineService.get_patient_join_url."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = TelemedicineService()
        self.appointment_id = str(uuid.uuid4())
        self.patient_id = str(uuid.uuid4())

    async def test_get_patient_join_url_success(self):
        """Patient owns the appointment → returns join_url and session_id."""
        session = _make_video_session(
            appointment_id=uuid.UUID(self.appointment_id),
            join_url_patient="https://daily.co/room/pat-token",
        )
        row = (session, uuid.UUID(self.patient_id))
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = row
        self.db.execute.return_value = result_mock

        result = await self.service.get_patient_join_url(
            db=self.db,
            appointment_id=self.appointment_id,
            patient_id=self.patient_id,
        )

        assert result["join_url"] == "https://daily.co/room/pat-token"
        assert "session_id" in result

    async def test_get_patient_join_url_wrong_patient(self):
        """Appointment belongs to a different patient → raises SESSION_NOT_FOUND."""
        different_patient_id = uuid.uuid4()
        session = _make_video_session(appointment_id=uuid.UUID(self.appointment_id))
        row = (session, different_patient_id)
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = row
        self.db.execute.return_value = result_mock

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.get_patient_join_url(
                db=self.db,
                appointment_id=self.appointment_id,
                patient_id=self.patient_id,
            )

        assert exc_info.value.error == TelemedicineErrors.SESSION_NOT_FOUND
        assert exc_info.value.status_code == 404

    async def test_get_patient_join_url_no_session(self):
        """No active session found → raises SESSION_NOT_FOUND (404)."""
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = None
        self.db.execute.return_value = result_mock

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.get_patient_join_url(
                db=self.db,
                appointment_id=self.appointment_id,
                patient_id=self.patient_id,
            )

        assert exc_info.value.error == TelemedicineErrors.SESSION_NOT_FOUND


# ── TestEndSession ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestEndSession:
    """Tests for TelemedicineService.end_session."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = TelemedicineService()
        self.session_id = str(uuid.uuid4())

    async def test_end_session_success(self):
        """Ending a session updates status to 'ended' and sets ended_at."""
        started_at = datetime.now(UTC) - timedelta(minutes=30)
        session = _make_video_session(
            id=uuid.UUID(self.session_id),
            status="active",
            started_at=started_at,
            provider_session_id=None,  # no room to end
        )
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = session
        self.db.execute.return_value = session_result

        mock_provider = AsyncMock()
        mock_provider.end_session = AsyncMock()
        mock_provider.get_recording = AsyncMock(return_value=None)

        with patch(
            "app.services.telemedicine_service._get_provider",
            return_value=mock_provider,
        ):
            result = await self.service.end_session(
                db=self.db,
                session_id=self.session_id,
            )

        assert session.status == "ended"
        assert session.ended_at is not None
        self.db.flush.assert_called()

    async def test_end_session_calculates_duration(self):
        """Duration is calculated from started_at to now in seconds."""
        started_at = datetime.now(UTC) - timedelta(minutes=45)
        session = _make_video_session(
            id=uuid.UUID(self.session_id),
            status="active",
            started_at=started_at,
            provider_session_id=None,
        )
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = session
        self.db.execute.return_value = session_result

        mock_provider = AsyncMock()
        mock_provider.end_session = AsyncMock()
        mock_provider.get_recording = AsyncMock(return_value=None)

        with patch(
            "app.services.telemedicine_service._get_provider",
            return_value=mock_provider,
        ):
            await self.service.end_session(
                db=self.db,
                session_id=self.session_id,
            )

        # Duration should be approximately 45 minutes = 2700 seconds
        assert session.duration_seconds is not None
        assert session.duration_seconds >= 2600  # allow a few seconds of tolerance

    async def test_end_session_calls_provider(self):
        """Provider end_session is called when provider_session_id is set."""
        session = _make_video_session(
            id=uuid.UUID(self.session_id),
            status="active",
            provider_session_id="room-abc",
            started_at=None,
        )
        # appointment lookup for room name reconstruction
        appt_id_result = MagicMock()
        appt_id_result.scalar_one_or_none.return_value = session.appointment_id

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = session

        self.db.execute.side_effect = [session_result, appt_id_result]

        mock_provider = AsyncMock()
        mock_provider.end_session = AsyncMock()
        mock_provider.get_recording = AsyncMock(return_value=None)

        with patch(
            "app.services.telemedicine_service._get_provider",
            return_value=mock_provider,
        ):
            await self.service.end_session(
                db=self.db,
                session_id=self.session_id,
            )

        mock_provider.end_session.assert_called_once()

    async def test_end_session_not_found(self):
        """Session not found → raises SESSION_NOT_FOUND (404)."""
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = session_result

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.end_session(
                db=self.db,
                session_id=self.session_id,
            )

        assert exc_info.value.error == TelemedicineErrors.SESSION_NOT_FOUND
        assert exc_info.value.status_code == 404


# ── TestLinkToClinicalRecord ──────────────────────────────────────────────────


@pytest.mark.unit
class TestLinkToClinicalRecord:
    """Tests for TelemedicineService.link_to_clinical_record."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = TelemedicineService()
        self.session_id = str(uuid.uuid4())

    async def test_link_to_clinical_record(self):
        """Existing session → returns confirmation dict with linked=True."""
        appt_id = uuid.uuid4()
        session = _make_video_session(
            id=uuid.UUID(self.session_id),
            appointment_id=appt_id,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = session
        self.db.execute.return_value = result_mock

        result = await self.service.link_to_clinical_record(
            db=self.db,
            session_id=self.session_id,
        )

        assert result["linked"] is True
        assert result["session_id"] == str(session.id)
        assert result["appointment_id"] == str(appt_id)

    async def test_link_to_clinical_record_not_found(self):
        """Session not found → raises SESSION_NOT_FOUND (404)."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result_mock

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.link_to_clinical_record(
                db=self.db,
                session_id=self.session_id,
            )

        assert exc_info.value.error == TelemedicineErrors.SESSION_NOT_FOUND
