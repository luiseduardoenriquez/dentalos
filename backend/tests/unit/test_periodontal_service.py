"""Unit tests for the PeriodontalService class.

Tests cover:
  - create_record: bulk insert with 32 teeth x 6 sites
  - create_record: sparse input (5 measurements only)
  - create_record: invalid tooth number raises INVALID_TOOTH_NUMBER
  - create_record: invalid site raises INVALID_SITE
  - compare_records: pocket_depth decreased -> improved
  - compare_records: pocket_depth increased -> worsened
  - compare_records: same values -> unchanged
  - list_records: paginated response
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import PeriodontalErrors
from app.core.exceptions import DentalOSError
from app.services.periodontal_service import PeriodontalService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_record(**overrides) -> MagicMock:
    record = MagicMock()
    record.id = overrides.get("id", uuid.uuid4())
    record.patient_id = overrides.get("patient_id", uuid.uuid4())
    record.recorded_by = overrides.get("recorded_by", uuid.uuid4())
    record.dentition_type = overrides.get("dentition_type", "adult")
    record.source = overrides.get("source", "manual")
    record.notes = overrides.get("notes", None)
    record.is_active = True
    record.created_at = overrides.get("created_at", datetime.now(UTC))
    record.updated_at = datetime.now(UTC)
    record.measurements = overrides.get("measurements", [])
    return record


def _make_measurement(tooth_number: int, site: str, pocket_depth: int | None = None) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tooth_number = tooth_number
    m.site = site
    m.pocket_depth = pocket_depth
    m.recession = None
    m.clinical_attachment_level = None
    m.bleeding_on_probing = False
    m.plaque_index = None
    m.mobility = None
    m.furcation = None
    return m


def _full_mouth_measurements() -> list[dict]:
    """Generate measurements for all 32 adult FDI teeth x 6 sites = 192 rows."""
    sites = ["mesial_buccal", "buccal", "distal_buccal", "mesial_lingual", "lingual", "distal_lingual"]
    # Adult teeth: 11-18, 21-28, 31-38, 41-48
    teeth = list(range(11, 19)) + list(range(21, 29)) + list(range(31, 39)) + list(range(41, 49))
    rows = []
    for tooth in teeth:
        for site in sites:
            rows.append({"tooth_number": tooth, "site": site, "pocket_depth": 3})
    return rows


# ── create_record ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateRecord:
    """Tests for PeriodontalService.create_record."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_create_record_bulk_insert(self, db):
        """32 teeth x 6 sites = 192 measurements triggers a bulk insert."""
        patient_id = uuid.uuid4()
        recorded_by = uuid.uuid4()

        # Patient exists
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        record = _make_record(patient_id=patient_id, measurements=[])

        with patch("app.services.periodontal_service.PeriodontalRecord", return_value=record):
            service = PeriodontalService()
            measurements = _full_mouth_measurements()
            await service.create_record(
                db=db,
                patient_id=str(patient_id),
                recorded_by=str(recorded_by),
                data={"measurements": measurements, "dentition_type": "adult"},
            )

        # db.execute called (for patient check and bulk insert)
        assert db.execute.call_count >= 2

    async def test_create_record_sparse_input(self, db):
        """Only 5 measurements must succeed without error."""
        patient_id = uuid.uuid4()
        recorded_by = uuid.uuid4()

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        record = _make_record(patient_id=patient_id, measurements=[])

        with patch("app.services.periodontal_service.PeriodontalRecord", return_value=record):
            service = PeriodontalService()
            measurements = [
                {"tooth_number": 11, "site": "mesial_buccal", "pocket_depth": 3},
                {"tooth_number": 11, "site": "buccal", "pocket_depth": 2},
                {"tooth_number": 12, "site": "distal_buccal", "pocket_depth": 4},
                {"tooth_number": 21, "site": "lingual", "pocket_depth": 3},
                {"tooth_number": 31, "site": "mesial_lingual", "pocket_depth": 5},
            ]
            # Should not raise
            await service.create_record(
                db=db,
                patient_id=str(patient_id),
                recorded_by=str(recorded_by),
                data={"measurements": measurements},
            )

    async def test_create_record_invalid_tooth_raises(self, db):
        """Tooth 99 is invalid FDI -> must raise INVALID_TOOTH_NUMBER (422)."""
        patient_id = uuid.uuid4()

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        service = PeriodontalService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.create_record(
                db=db,
                patient_id=str(patient_id),
                recorded_by=str(uuid.uuid4()),
                data={
                    "measurements": [
                        {"tooth_number": 99, "site": "buccal", "pocket_depth": 3}
                    ]
                },
            )

        assert exc_info.value.error == PeriodontalErrors.INVALID_TOOTH_NUMBER
        assert exc_info.value.status_code == 422

    async def test_create_record_invalid_site_raises(self, db):
        """Site 'invalid' is not a valid perio site -> must raise INVALID_SITE (422)."""
        patient_id = uuid.uuid4()

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        service = PeriodontalService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.create_record(
                db=db,
                patient_id=str(patient_id),
                recorded_by=str(uuid.uuid4()),
                data={
                    "measurements": [
                        {"tooth_number": 11, "site": "invalid_site", "pocket_depth": 3}
                    ]
                },
            )

        assert exc_info.value.error == PeriodontalErrors.INVALID_SITE
        assert exc_info.value.status_code == 422


# ── compare_records ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCompareRecords:
    """Tests for PeriodontalService.compare_records."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    def _setup_two_records(self, db, patient_id, m_a_depth, m_b_depth):
        """Helper to set up two records sharing one (tooth, site) pair."""
        ra_id = uuid.uuid4()
        rb_id = uuid.uuid4()

        m_a = _make_measurement(11, "buccal", m_a_depth)
        m_b = _make_measurement(11, "buccal", m_b_depth)

        record_a = _make_record(id=ra_id, patient_id=patient_id, measurements=[m_a])
        record_b = _make_record(id=rb_id, patient_id=patient_id, measurements=[m_b])

        # Give each record a real UUID so dict lookup works
        record_a.id = ra_id
        record_b.id = rb_id

        records_result = MagicMock()
        records_result.scalars.return_value.all.return_value = [record_a, record_b]
        db.execute = AsyncMock(return_value=records_result)

        return str(ra_id), str(rb_id)

    async def test_compare_records_improved(self, db):
        """Pocket depth b < a -> status 'improved'."""
        patient_id = uuid.uuid4()
        ra_id, rb_id = self._setup_two_records(db, patient_id, m_a_depth=5, m_b_depth=3)

        service = PeriodontalService()
        result = await service.compare_records(
            db=db,
            patient_id=str(patient_id),
            record_a_id=ra_id,
            record_b_id=rb_id,
        )

        assert len(result["deltas"]) >= 1
        delta = result["deltas"][0]
        assert delta["status"] == "improved"
        assert delta["pocket_depth_delta"] == -2  # 3 - 5

    async def test_compare_records_worsened(self, db):
        """Pocket depth b > a -> status 'worsened'."""
        patient_id = uuid.uuid4()
        ra_id, rb_id = self._setup_two_records(db, patient_id, m_a_depth=3, m_b_depth=5)

        service = PeriodontalService()
        result = await service.compare_records(
            db=db,
            patient_id=str(patient_id),
            record_a_id=ra_id,
            record_b_id=rb_id,
        )

        delta = result["deltas"][0]
        assert delta["status"] == "worsened"
        assert delta["pocket_depth_delta"] == 2  # 5 - 3

    async def test_compare_records_unchanged(self, db):
        """Same pocket depth b == a -> status 'unchanged'."""
        patient_id = uuid.uuid4()
        ra_id, rb_id = self._setup_two_records(db, patient_id, m_a_depth=4, m_b_depth=4)

        service = PeriodontalService()
        result = await service.compare_records(
            db=db,
            patient_id=str(patient_id),
            record_a_id=ra_id,
            record_b_id=rb_id,
        )

        delta = result["deltas"][0]
        assert delta["status"] == "unchanged"
        assert delta["pocket_depth_delta"] == 0


# ── list_records ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListRecords:
    """Tests for PeriodontalService.list_records."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_list_records_pagination(self, db):
        """Paginated response must include total, page, page_size, items."""
        patient_id = uuid.uuid4()

        total_result = MagicMock()
        total_result.scalar_one.return_value = 3

        record = _make_record(patient_id=patient_id)
        records_row = MagicMock()
        records_row.__getitem__ = lambda self, idx: [record, 5][idx]

        records_result = MagicMock()
        records_result.all.return_value = [(record, 5)]

        db.execute = AsyncMock(side_effect=[total_result, records_result])

        service = PeriodontalService()
        result = await service.list_records(
            db=db,
            patient_id=str(patient_id),
            page=1,
            page_size=20,
        )

        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert isinstance(result["items"], list)

    async def test_list_records_empty(self, db):
        """Empty patient history returns empty items list."""
        patient_id = uuid.uuid4()

        total_result = MagicMock()
        total_result.scalar_one.return_value = 0

        records_result = MagicMock()
        records_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[total_result, records_result])

        service = PeriodontalService()
        result = await service.list_records(db=db, patient_id=str(patient_id))

        assert result["total"] == 0
        assert result["items"] == []
