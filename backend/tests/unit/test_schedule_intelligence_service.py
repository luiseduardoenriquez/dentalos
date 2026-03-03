"""Unit tests for the ScheduleIntelligenceService class.

Tests cover:
  - predict_no_shows: score bounds (0-100), low risk, high risk
  - _risk_level: classification thresholds
  - find_gaps: identifies unfilled slots
  - get_utilization: percentage calculation
  - get_intelligence: parallel execution via asyncio.gather
"""

import asyncio
import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.schedule_intelligence_service import (
    ScheduleIntelligenceService,
    _risk_level,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_appointment_row(**overrides) -> MagicMock:
    row = MagicMock()
    row.appointment_id = overrides.get("appointment_id", uuid.uuid4())
    row.patient_id = overrides.get("patient_id", uuid.uuid4())
    row.start_time = overrides.get(
        "start_time", datetime.combine(date.today(), time(9, 0), tzinfo=UTC)
    )
    row.appt_type = overrides.get("appt_type", "consultation")
    row.doctor_id = overrides.get("doctor_id", uuid.uuid4())
    row.first_name = "Test"
    row.last_name = "Patient"
    return row


def _make_schedule_row(**overrides) -> MagicMock:
    row = MagicMock()
    row.doctor_id = overrides.get("doctor_id", uuid.uuid4())
    row.work_start = overrides.get("work_start", time(8, 0))
    row.work_end = overrides.get("work_end", time(16, 0))
    row.breaks = overrides.get("breaks", [])
    row.doctor_name = overrides.get("doctor_name", "Dr. Test")
    return row


# ── _risk_level ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRiskLevel:
    """Tests for the _risk_level() module-level function."""

    def test_score_zero_is_low(self):
        assert _risk_level(0) == "low"

    def test_score_30_is_low(self):
        assert _risk_level(30) == "low"

    def test_score_31_is_medium(self):
        assert _risk_level(31) == "medium"

    def test_score_60_is_medium(self):
        assert _risk_level(60) == "medium"

    def test_score_61_is_high(self):
        assert _risk_level(61) == "high"

    def test_score_100_is_high(self):
        assert _risk_level(100) == "high"


# ── predict_no_shows ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPredictNoShowScoreBounds:
    """Tests for ScheduleIntelligenceService.predict_no_shows."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_predict_no_show_score_bounds(self, db):
        """Score must always be between 0 and 100 inclusive."""
        target_date = date.today()
        doc_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        appt_row = _make_appointment_row(patient_id=patient_id, doctor_id=doc_id)

        appt_result = MagicMock()
        appt_result.all.return_value = [appt_row]

        # clinic-wide rates
        empty_result = MagicMock()
        empty_result.one.return_value = MagicMock(total=0, no_shows=0)
        empty_result.all.return_value = []

        # patient rate / recency
        patient_hist = MagicMock()
        patient_hist.one.return_value = MagicMock(total=5, no_shows=1)

        recency_result = MagicMock()
        recency_result.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[
                appt_result,        # appointments fetch
                empty_result,       # clinic dow rate
                empty_result,       # clinic time rates
                empty_result,       # clinic type rates
                patient_hist,       # patient history
                recency_result,     # recency
            ]
        )

        service = ScheduleIntelligenceService()
        results = await service.predict_no_shows(db, target_date, doc_id)

        assert isinstance(results, list)
        for item in results:
            assert 0 <= item["risk_score"] <= 100

    async def test_predict_no_show_low_risk(self, db):
        """Patient with 0% no-show rate -> low risk (score <= 30)."""
        target_date = date.today()
        patient_id = uuid.uuid4()
        appt_row = _make_appointment_row(patient_id=patient_id)

        appt_result = MagicMock()
        appt_result.all.return_value = [appt_row]

        # 0% no-show history
        patient_hist = MagicMock()
        patient_hist.one.return_value = MagicMock(total=10, no_shows=0)

        empty_one = MagicMock()
        empty_one.one.return_value = MagicMock(total=0, no_shows=0)
        empty_one.all.return_value = []

        recency_result = MagicMock()
        recency_result.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[
                appt_result,
                empty_one,    # clinic dow
                empty_one,    # clinic time
                empty_one,    # clinic type
                patient_hist,
                recency_result,
            ]
        )

        service = ScheduleIntelligenceService()
        results = await service.predict_no_shows(db, target_date)

        assert len(results) == 1
        assert results[0]["risk_level"] == "low"

    async def test_predict_no_show_high_risk(self, db):
        """Patient with 80% no-show rate -> high risk (score > 60)."""
        target_date = date.today()
        patient_id = uuid.uuid4()
        appt_row = _make_appointment_row(patient_id=patient_id)

        appt_result = MagicMock()
        appt_result.all.return_value = [appt_row]

        # 80% no-show history for patient
        patient_hist = MagicMock()
        patient_hist.one.return_value = MagicMock(total=10, no_shows=8)

        # 80% clinic-wide no-show rate for day of week
        clinic_dow = MagicMock()
        clinic_dow.one.return_value = MagicMock(total=50, no_shows=40)

        empty_time = MagicMock()
        empty_time.all.return_value = []

        recency_result = MagicMock()
        recency_result.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[
                appt_result,
                clinic_dow,
                empty_time,    # clinic time
                empty_time,    # clinic type
                patient_hist,
                recency_result,
            ]
        )

        service = ScheduleIntelligenceService()
        results = await service.predict_no_shows(db, target_date)

        assert len(results) == 1
        assert results[0]["risk_level"] == "high"

    async def test_predict_no_show_returns_empty_when_no_appointments(self, db):
        """No appointments for the day -> empty list returned."""
        appt_result = MagicMock()
        appt_result.all.return_value = []
        db.execute = AsyncMock(return_value=appt_result)

        service = ScheduleIntelligenceService()
        results = await service.predict_no_shows(db, date.today())

        assert results == []


# ── find_gaps ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestFindGaps:
    """Tests for ScheduleIntelligenceService.find_gaps."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_find_gaps_identifies_unfilled_slots(self, db):
        """Doctor with 8-16h working hours and one 9-10h appointment has gaps."""
        target_date = date.today()
        doc_id = uuid.uuid4()

        sched_row = _make_schedule_row(
            doctor_id=doc_id,
            work_start=time(8, 0),
            work_end=time(16, 0),
            breaks=[],
        )

        sched_result = MagicMock()
        sched_result.all.return_value = [sched_row]

        # One appointment from 9:00 to 10:00
        appt_row = MagicMock()
        appt_row.doctor_id = doc_id
        appt_row.start_time = datetime.combine(target_date, time(9, 0), tzinfo=UTC)
        appt_row.end_time = datetime.combine(target_date, time(10, 0), tzinfo=UTC)

        appt_result = MagicMock()
        appt_result.all.return_value = [appt_row]

        # Suggestion queries (waitlist, treatment plan)
        wl_result = MagicMock()
        wl_result.all.return_value = []
        tp_result = MagicMock()
        tp_result.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[sched_result, appt_result, wl_result, tp_result]
        )

        service = ScheduleIntelligenceService()
        gaps = await service.find_gaps(db, target_date, doc_id)

        assert len(gaps) >= 1
        # Verify gap structure
        for gap in gaps:
            assert "slot_start" in gap
            assert "slot_end" in gap
            assert gap["slot_end"] > gap["slot_start"]

    async def test_find_gaps_empty_when_no_schedules(self, db):
        """No doctor schedules -> empty gaps list."""
        sched_result = MagicMock()
        sched_result.all.return_value = []
        db.execute = AsyncMock(return_value=sched_result)

        service = ScheduleIntelligenceService()
        gaps = await service.find_gaps(db, date.today())

        assert gaps == []


# ── get_utilization ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetUtilization:
    """Tests for ScheduleIntelligenceService.get_utilization."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_utilization_calculation(self, db):
        """180 completed minutes / 480 available minutes = 37.5%."""
        target_date = date.today()
        doc_id = uuid.uuid4()

        sched_row = _make_schedule_row(
            doctor_id=doc_id,
            # 8h working = 480 minutes
            work_start=time(8, 0),
            work_end=time(16, 0),
            breaks=[],
        )

        sched_result = MagicMock()
        sched_result.all.return_value = [sched_row]

        # 180 completed minutes
        appt_row = MagicMock()
        appt_row.doctor_id = doc_id
        appt_row.completed_minutes = 180

        appt_result = MagicMock()
        appt_result.all.return_value = [appt_row]

        db.execute = AsyncMock(side_effect=[sched_result, appt_result])

        service = ScheduleIntelligenceService()
        metrics = await service.get_utilization(db, target_date, doc_id)

        assert len(metrics) == 1
        metric = metrics[0]
        assert metric["available_minutes"] == 480
        assert metric["completed_minutes"] == 180
        # 180/480*100 = 37.5
        assert metric["utilization_pct"] == 37.5

    async def test_utilization_zero_when_no_schedules(self, db):
        """No schedules -> empty utilization list."""
        sched_result = MagicMock()
        sched_result.all.return_value = []
        db.execute = AsyncMock(return_value=sched_result)

        service = ScheduleIntelligenceService()
        metrics = await service.get_utilization(db, date.today())

        assert metrics == []


# ── get_intelligence ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetIntelligence:
    """Tests for ScheduleIntelligenceService.get_intelligence."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_intelligence_parallel_execution(self, db):
        """get_intelligence must use asyncio.gather to run queries in parallel."""
        target_date = date.today()
        service = ScheduleIntelligenceService()

        gather_calls = []

        async def mock_gather(*coros):
            gather_calls.append(len(coros))
            results = [await c for c in coros]
            return results

        with patch.object(service, "predict_no_shows", new_callable=AsyncMock, return_value=[]):
            with patch.object(service, "find_gaps", new_callable=AsyncMock, return_value=[]):
                with patch.object(service, "get_utilization", new_callable=AsyncMock, return_value=[]):
                    with patch("app.services.schedule_intelligence_service.asyncio.gather", side_effect=mock_gather):
                        result = await service.get_intelligence(db, target_date)

        # asyncio.gather was called with 3 coroutines
        assert gather_calls == [3]
        assert "no_show_risks" in result
        assert "gaps" in result
        assert "utilization" in result
