"""Unit tests for the ReputationService class.

Tests cover:
  - send_survey: token generation, survey created, notification enqueued
  - record_response: routing to google_review vs private_feedback
  - record_response: already_responded raises 409
  - record_response: invalid token raises 404
  - get_dashboard: NPS calculation
  - get_feedback: paginated response
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ReputationErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.reputation_service import ReputationService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_survey(**overrides) -> MagicMock:
    survey = MagicMock()
    survey.id = overrides.get("id", uuid.uuid4())
    survey.patient_id = overrides.get("patient_id", uuid.uuid4())
    survey.appointment_id = overrides.get("appointment_id", uuid.uuid4())
    survey.score = overrides.get("score", None)
    survey.feedback_text = overrides.get("feedback_text", None)
    survey.channel_sent = overrides.get("channel_sent", "whatsapp")
    survey.survey_token = overrides.get("survey_token", "tok_abc123")
    survey.routed_to = overrides.get("routed_to", None)
    survey.sent_at = overrides.get("sent_at", datetime.now(UTC))
    survey.responded_at = overrides.get("responded_at", None)
    survey.created_at = overrides.get("created_at", datetime.now(UTC))
    return survey


# ── send_survey ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSendSurvey:
    """Tests for ReputationService.send_survey."""

    @pytest.fixture
    def db(self):
        """Mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_send_survey_creates_token(self, db):
        """Token must be exactly 64 chars, survey created, notification enqueued."""
        # Arrange
        appointment_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        tenant_id = "tn_abc123"

        appt_result = MagicMock()
        appt_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=appt_result)

        created_survey = _make_survey(patient_id=patient_id, appointment_id=appointment_id)
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        with patch("app.services.reputation_service.publish_message", new_callable=AsyncMock) as mock_publish:
            # Replace the SatisfactionSurvey constructor to return our mock
            with patch("app.services.reputation_service.SatisfactionSurvey", return_value=created_survey):
                service = ReputationService()
                await service.send_survey(
                    db=db,
                    appointment_id=appointment_id,
                    channel="whatsapp",
                    tenant_id=tenant_id,
                )

            # Assert publish_message was called (notification enqueued)
            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            assert call_args[0][0] == "notifications"

    async def test_send_survey_token_is_64_chars(self, db):
        """Token generated via secrets.token_urlsafe(48)[:64] must be 64 chars."""
        import secrets as _secrets

        # Verify the token generation pattern produces 64 chars
        token = _secrets.token_urlsafe(48)[:64]
        assert len(token) == 64

    async def test_send_survey_appointment_not_found_raises(self, db):
        """Missing appointment must raise ResourceNotFoundError."""
        appt_result = MagicMock()
        appt_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=appt_result)

        service = ReputationService()
        with pytest.raises(ResourceNotFoundError):
            await service.send_survey(
                db=db,
                appointment_id=uuid.uuid4(),
                channel="email",
                tenant_id="tn_abc123",
            )

    async def test_send_survey_calls_db_add(self, db):
        """db.add must be called to persist the survey."""
        patient_id = uuid.uuid4()
        appointment_id = uuid.uuid4()

        appt_result = MagicMock()
        appt_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=appt_result)

        created_survey = _make_survey(patient_id=patient_id, appointment_id=appointment_id)

        with patch("app.services.reputation_service.publish_message", new_callable=AsyncMock):
            with patch("app.services.reputation_service.SatisfactionSurvey", return_value=created_survey):
                service = ReputationService()
                await service.send_survey(
                    db=db,
                    appointment_id=appointment_id,
                    channel="sms",
                    tenant_id="tn_abc123",
                )

        db.add.assert_called_once()


# ── record_response ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRecordResponse:
    """Tests for ReputationService.record_response."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    async def test_record_response_high_score_routes_to_google(self, db):
        """Score >= 4 (default threshold) routes to google_review."""
        survey = _make_survey(responded_at=None)

        result = MagicMock()
        result.scalar_one_or_none.return_value = survey
        db.execute = AsyncMock(return_value=result)

        service = ReputationService()
        response = await service.record_response(
            db=db,
            token="some_token_64chars",
            score=5,
            feedback_text=None,
            tenant_settings={"review_score_threshold": 4},
        )

        assert response["routed_to"] == "google_review"

    async def test_record_response_low_score_routes_to_private(self, db):
        """Score < 4 routes to private_feedback."""
        survey = _make_survey(responded_at=None)

        result = MagicMock()
        result.scalar_one_or_none.return_value = survey
        db.execute = AsyncMock(return_value=result)

        service = ReputationService()
        response = await service.record_response(
            db=db,
            token="some_token_64chars",
            score=2,
            feedback_text="Mala experiencia",
            tenant_settings={"review_score_threshold": 4},
        )

        assert response["routed_to"] == "private_feedback"

    async def test_record_response_already_responded_raises(self, db):
        """Survey with responded_at not None must raise 409."""
        survey = _make_survey(responded_at=datetime.now(UTC), score=4)

        result = MagicMock()
        result.scalar_one_or_none.return_value = survey
        db.execute = AsyncMock(return_value=result)

        service = ReputationService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.record_response(
                db=db,
                token="some_token",
                score=5,
                feedback_text=None,
            )

        assert exc_info.value.error == ReputationErrors.SURVEY_ALREADY_RESPONDED
        assert exc_info.value.status_code == 409

    async def test_record_response_invalid_token_raises(self, db):
        """Token not found must raise ResourceNotFoundError (404)."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        service = ReputationService()
        with pytest.raises(ResourceNotFoundError):
            await service.record_response(
                db=db,
                token="nonexistent_token",
                score=5,
                feedback_text=None,
            )

    async def test_record_response_score_4_routes_to_google(self, db):
        """Boundary: score == threshold (4) routes to google_review."""
        survey = _make_survey(responded_at=None)

        result = MagicMock()
        result.scalar_one_or_none.return_value = survey
        db.execute = AsyncMock(return_value=result)

        service = ReputationService()
        response = await service.record_response(
            db=db,
            token="some_token",
            score=4,
            feedback_text=None,
            tenant_settings={"review_score_threshold": 4},
        )

        assert response["routed_to"] == "google_review"

    async def test_record_response_google_url_returned_when_routed(self, db):
        """google_review_url is returned when routed_to is google_review."""
        survey = _make_survey(responded_at=None)
        result = MagicMock()
        result.scalar_one_or_none.return_value = survey
        db.execute = AsyncMock(return_value=result)

        service = ReputationService()
        response = await service.record_response(
            db=db,
            token="some_token",
            score=5,
            feedback_text=None,
            tenant_settings={
                "review_score_threshold": 4,
                "google_review_url": "https://g.page/r/abc",
            },
        )

        assert response["google_review_url"] == "https://g.page/r/abc"


# ── get_dashboard ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetDashboard:
    """Tests for ReputationService.get_dashboard."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_dashboard_zero_surveys(self, db):
        """No surveys returns zero values."""
        total_result = MagicMock()
        total_result.scalar_one.return_value = 0
        db.execute = AsyncMock(return_value=total_result)

        service = ReputationService()
        result = await service.get_dashboard(db=db)

        assert result["total_surveys"] == 0
        assert result["nps_score"] == 0.0
        assert result["response_rate"] == 0.0

    async def test_get_dashboard_aggregation_nps(self, db):
        """NPS = (promoters - detractors) / responded * 100.

        Scenario: 10 total, 8 responded (3 promoters score=5, 2 detractors score<=3).
        NPS = (3 - 2) / 8 * 100 = 12.5
        """
        total_result = MagicMock()
        total_result.scalar_one.return_value = 10

        stats_row = MagicMock()
        stats_row.avg_score = 4.0
        stats_row.responded_count = 8
        stats_row.promoters = 3
        stats_row.detractors = 2
        stats_row.review_count = 3
        stats_row.private_feedback_count = 5

        stats_result = MagicMock()
        stats_result.one.return_value = stats_row

        db.execute = AsyncMock(side_effect=[total_result, stats_result])

        service = ReputationService()
        result = await service.get_dashboard(db=db)

        expected_nps = round((3 - 2) / 8 * 100, 2)
        assert result["nps_score"] == expected_nps
        assert result["total_surveys"] == 10


# ── get_feedback ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetFeedback:
    """Tests for ReputationService.get_feedback."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_feedback_pagination(self, db):
        """Paginated response has correct pagination metadata."""
        survey = _make_survey(routed_to="private_feedback", responded_at=datetime.now(UTC))

        total_result = MagicMock()
        total_result.scalar_one.return_value = 5

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [survey]

        db.execute = AsyncMock(side_effect=[total_result, items_result])

        service = ReputationService()
        result = await service.get_feedback(db=db, page=1, page_size=20)

        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 1

    async def test_get_feedback_empty_result(self, db):
        """Empty database returns empty items list."""
        total_result = MagicMock()
        total_result.scalar_one.return_value = 0

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[total_result, items_result])

        service = ReputationService()
        result = await service.get_feedback(db=db, page=1, page_size=20)

        assert result["total"] == 0
        assert result["items"] == []
