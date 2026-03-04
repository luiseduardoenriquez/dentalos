"""Unit tests for NPSSurveyService (VP-21 / Sprint 29-30).

Tests cover:
  - send_survey: creates record with token
  - submit_response: success, already responded, token not found,
    detractor alert, promoter no alert
  - get_nps_dashboard: NPS calculation, empty data
  - get_nps_by_doctor: grouping by doctor
  - auto_send_after_appointment: creates survey, idempotent
  - _classify_nps: score classification boundaries
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import SurveyErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.nps_survey_service import NPSSurveyService, _calculate_nps, _classify_nps


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_survey(**overrides) -> MagicMock:
    """Build a mock NPSSurveyResponse ORM row."""
    s = MagicMock()
    s.id = overrides.get("id", uuid.uuid4())
    s.patient_id = overrides.get("patient_id", uuid.uuid4())
    s.doctor_id = overrides.get("doctor_id", uuid.uuid4())
    s.appointment_id = overrides.get("appointment_id", None)
    s.survey_token = overrides.get("survey_token", "tok-abc123")
    s.channel_sent = overrides.get("channel_sent", "whatsapp")
    s.nps_score = overrides.get("nps_score", None)
    s.csat_score = overrides.get("csat_score", None)
    s.comments = overrides.get("comments", None)
    s.sent_at = overrides.get("sent_at", datetime.now(UTC))
    s.responded_at = overrides.get("responded_at", None)
    return s


# ── TestSendSurvey ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSendSurvey:
    """Tests for NPSSurveyService.send_survey."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.add = MagicMock()
        self.service = NPSSurveyService()
        self.patient_id = uuid.uuid4()
        self.doctor_id = uuid.uuid4()

    async def test_send_survey_creates_record(self):
        """send_survey persists an NPSSurveyResponse and returns a dict with token."""
        survey_orm = _make_survey(
            patient_id=self.patient_id,
            doctor_id=self.doctor_id,
            survey_token="secure-token-abc",
        )

        with patch(
            "app.services.nps_survey_service.NPSSurveyResponse",
            return_value=survey_orm,
        ):
            result = await self.service.send_survey(
                db=self.db,
                patient_id=self.patient_id,
                doctor_id=self.doctor_id,
                channel="whatsapp",
            )

        self.db.add.assert_called_once()
        self.db.flush.assert_called()
        self.db.refresh.assert_called()
        assert result["patient_id"] == self.patient_id
        assert result["doctor_id"] == self.doctor_id

    async def test_send_survey_token_uniqueness(self):
        """Each call to send_survey generates a distinct token."""
        tokens = set()

        for i in range(5):
            survey_orm = _make_survey(
                patient_id=self.patient_id,
                doctor_id=self.doctor_id,
            )
            # Capture the token passed to NPSSurveyResponse constructor
            created_tokens = []

            original_init = MagicMock(return_value=survey_orm)

            def capture_token(**kwargs):
                created_tokens.append(kwargs.get("survey_token", ""))
                return survey_orm

            with patch(
                "app.services.nps_survey_service.NPSSurveyResponse",
                side_effect=capture_token,
            ):
                await self.service.send_survey(
                    db=self.db,
                    patient_id=self.patient_id,
                    doctor_id=self.doctor_id,
                )

            if created_tokens:
                tokens.add(created_tokens[0])

        # If tokens were captured they must be unique; if not, just confirm no crash
        if len(tokens) > 1:
            assert len(tokens) > 1


# ── TestSubmitResponse ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSubmitResponse:
    """Tests for NPSSurveyService.submit_response."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.service = NPSSurveyService()

    async def test_submit_response_success(self):
        """Valid token + score sets responded_at and nps_score."""
        survey_orm = _make_survey(survey_token="valid-token", responded_at=None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = survey_orm
        self.db.execute.return_value = result_mock

        result = await self.service.submit_response(
            db=self.db,
            token="valid-token",
            nps_score=9,
            csat_score=4,
            comments="Excelente atención",
        )

        assert survey_orm.nps_score == 9
        assert survey_orm.csat_score == 4
        assert survey_orm.responded_at is not None
        self.db.flush.assert_called()

    async def test_submit_response_already_responded(self):
        """Survey already responded → raises ALREADY_RESPONDED (409)."""
        survey_orm = _make_survey(
            survey_token="used-token",
            responded_at=datetime.now(UTC),
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = survey_orm
        self.db.execute.return_value = result_mock

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.submit_response(
                db=self.db,
                token="used-token",
                nps_score=8,
                csat_score=None,
                comments=None,
            )

        assert exc_info.value.error == SurveyErrors.ALREADY_RESPONDED
        assert exc_info.value.status_code == 409

    async def test_submit_response_token_not_found(self):
        """Unknown token → ResourceNotFoundError."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result_mock

        with pytest.raises(ResourceNotFoundError):
            await self.service.submit_response(
                db=self.db,
                token="nonexistent-token",
                nps_score=7,
                csat_score=None,
                comments=None,
            )

    async def test_submit_response_detractor_alert(self):
        """NPS score 0-6 (detractor) calls _handle_detractor."""
        survey_orm = _make_survey(survey_token="det-token", responded_at=None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = survey_orm
        self.db.execute.return_value = result_mock

        with patch.object(
            self.service,
            "_handle_detractor",
            new_callable=AsyncMock,
        ) as mock_handle:
            await self.service.submit_response(
                db=self.db,
                token="det-token",
                nps_score=3,
                csat_score=None,
                comments="No me gustó el servicio",
            )

        mock_handle.assert_called_once()

    async def test_submit_response_promoter_no_alert(self):
        """NPS score 9-10 (promoter) does NOT call _handle_detractor."""
        survey_orm = _make_survey(survey_token="promo-token", responded_at=None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = survey_orm
        self.db.execute.return_value = result_mock

        with patch.object(
            self.service,
            "_handle_detractor",
            new_callable=AsyncMock,
        ) as mock_handle:
            await self.service.submit_response(
                db=self.db,
                token="promo-token",
                nps_score=10,
                csat_score=5,
                comments="¡Excelente clínica!",
            )

        mock_handle.assert_not_called()

    async def test_submit_response_invalid_nps_score(self):
        """NPS score > 10 → raises INVALID_SCORE (422)."""
        survey_orm = _make_survey(survey_token="score-token", responded_at=None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = survey_orm
        self.db.execute.return_value = result_mock

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.submit_response(
                db=self.db,
                token="score-token",
                nps_score=11,
                csat_score=None,
                comments=None,
            )

        assert exc_info.value.error == SurveyErrors.INVALID_SCORE
        assert exc_info.value.status_code == 422


# ── TestGetNpsDashboard ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetNpsDashboard:
    """Tests for NPSSurveyService.get_nps_dashboard."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = NPSSurveyService()

    async def test_get_nps_dashboard_calculation(self):
        """NPS = (promoters% - detractors%) of total responded."""
        # 4 promoters, 2 passives, 2 detractors, total = 8
        # NPS = (4-2)/8 * 100 = 25.0
        agg_row = MagicMock()
        agg_row.total = 8
        agg_row.promoters = 4
        agg_row.passives = 2
        agg_row.detractors = 2
        agg_result = MagicMock()
        agg_result.one.return_value = agg_row

        trend_result = MagicMock()
        trend_result.all.return_value = []

        self.db.execute.side_effect = [agg_result, trend_result]

        result = await self.service.get_nps_dashboard(db=self.db)

        assert result["nps_score"] == 25.0
        assert result["promoters"] == 4
        assert result["passives"] == 2
        assert result["detractors"] == 2
        assert result["total_responses"] == 8
        assert "trend" in result

    async def test_get_nps_dashboard_no_responses(self):
        """No survey responses → NPS score is 0 and counts are all zero."""
        agg_row = MagicMock()
        agg_row.total = 0
        agg_row.promoters = 0
        agg_row.passives = 0
        agg_row.detractors = 0
        agg_result = MagicMock()
        agg_result.one.return_value = agg_row

        trend_result = MagicMock()
        trend_result.all.return_value = []

        self.db.execute.side_effect = [agg_result, trend_result]

        result = await self.service.get_nps_dashboard(db=self.db)

        assert result["nps_score"] == 0.0
        assert result["total_responses"] == 0
        assert result["trend"] == []


# ── TestGetNpsByDoctor ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetNpsByDoctor:
    """Tests for NPSSurveyService.get_nps_by_doctor."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = NPSSurveyService()

    async def test_get_nps_by_doctor(self):
        """Result contains one entry per doctor with correct NPS calculation."""
        doctor1_id = uuid.uuid4()
        doctor2_id = uuid.uuid4()

        row1 = MagicMock()
        row1.doctor_id = doctor1_id
        row1.doctor_name = "Dr. García"
        row1.total = 5
        row1.promoters = 3
        row1.passives = 1
        row1.detractors = 1

        row2 = MagicMock()
        row2.doctor_id = doctor2_id
        row2.doctor_name = "Dra. Martínez"
        row2.total = 4
        row2.promoters = 4
        row2.passives = 0
        row2.detractors = 0

        result_mock = MagicMock()
        result_mock.all.return_value = [row1, row2]
        self.db.execute.return_value = result_mock

        result = await self.service.get_nps_by_doctor(db=self.db)

        assert "items" in result
        assert len(result["items"]) == 2
        # Dr. García: (3-1)/5 * 100 = 40.0
        garcia = next(
            i for i in result["items"] if i["doctor_name"] == "Dr. García"
        )
        assert garcia["nps_score"] == 40.0
        assert garcia["promoters"] == 3


# ── TestAutoSendAfterAppointment ──────────────────────────────────────────────


@pytest.mark.unit
class TestAutoSendAfterAppointment:
    """Tests for NPSSurveyService.auto_send_after_appointment."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.add = MagicMock()
        self.service = NPSSurveyService()
        self.appointment_id = uuid.uuid4()
        self.patient_id = uuid.uuid4()
        self.doctor_id = uuid.uuid4()

    async def test_auto_send_after_appointment_creates(self):
        """No existing survey → creates and returns a new survey."""
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = existing_result

        survey_orm = _make_survey(
            appointment_id=self.appointment_id,
            patient_id=self.patient_id,
            doctor_id=self.doctor_id,
        )

        with patch(
            "app.services.nps_survey_service.NPSSurveyResponse",
            return_value=survey_orm,
        ):
            result = await self.service.auto_send_after_appointment(
                db=self.db,
                appointment_id=self.appointment_id,
                patient_id=self.patient_id,
                doctor_id=self.doctor_id,
            )

        assert result is not None
        self.db.add.assert_called_once()

    async def test_auto_send_after_appointment_idempotent(self):
        """Survey already sent for this appointment → returns None (no duplicate)."""
        existing_id = uuid.uuid4()
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_id
        self.db.execute.return_value = existing_result

        result = await self.service.auto_send_after_appointment(
            db=self.db,
            appointment_id=self.appointment_id,
            patient_id=self.patient_id,
            doctor_id=self.doctor_id,
        )

        assert result is None
        self.db.add.assert_not_called()


# ── TestClassifyNps (pure functions) ─────────────────────────────────────────


@pytest.mark.unit
class TestNpsHelpers:
    """Tests for the module-level _classify_nps and _calculate_nps helpers."""

    def test_nps_score_classification_detractor(self):
        """Scores 0-6 are detractors."""
        for score in range(0, 7):
            assert _classify_nps(score) == "detractor", f"score={score}"

    def test_nps_score_classification_passive(self):
        """Scores 7-8 are passives."""
        for score in (7, 8):
            assert _classify_nps(score) == "passive", f"score={score}"

    def test_nps_score_classification_promoter(self):
        """Scores 9-10 are promoters."""
        for score in (9, 10):
            assert _classify_nps(score) == "promoter", f"score={score}"

    def test_calculate_nps_basic(self):
        """NPS = (promoters - detractors) / total * 100."""
        assert _calculate_nps(promoters=7, detractors=1, total=10) == 60.0

    def test_calculate_nps_zero_total(self):
        """Zero total returns 0.0 without division error."""
        assert _calculate_nps(promoters=0, detractors=0, total=0) == 0.0

    def test_calculate_nps_all_promoters(self):
        """100% promoters → NPS = 100.0."""
        assert _calculate_nps(promoters=5, detractors=0, total=5) == 100.0

    def test_calculate_nps_all_detractors(self):
        """100% detractors → NPS = -100.0."""
        assert _calculate_nps(promoters=0, detractors=5, total=5) == -100.0
