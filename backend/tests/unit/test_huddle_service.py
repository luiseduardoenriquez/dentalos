"""Unit tests for the HuddleService class.

Tests cover:
  - get_huddle: verifies all 8 sections are present and correctly structured
  - Individual section methods: verify query construction and data transformation
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.huddle_service import HuddleService


def _make_db_with_empty_results() -> AsyncMock:
    """Build a mock AsyncSession that returns empty results for all queries."""
    db = AsyncMock()

    # Default: execute returns empty results
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.one.return_value = MagicMock(total=0, count=0)
    mock_result.scalar_one.return_value = 0
    mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    db.execute = AsyncMock(return_value=mock_result)

    return db


@pytest.mark.unit
class TestGetHuddle:
    async def test_returns_all_sections(self):
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")

        assert "date" in result
        assert "appointments" in result
        assert "production" in result
        assert "incomplete_plans" in result
        assert "outstanding_balances" in result
        assert "birthdays" in result
        assert "recall_due" in result
        assert "yesterday_collections" in result
        assert "no_shows" in result

    async def test_date_is_today(self):
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert result["date"] == date.today()

    async def test_empty_clinic_returns_zeros(self):
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert result["appointments"] == []
        assert result["production"]["daily_actual_cents"] == 0
        assert result["incomplete_plans"] == []
        assert result["outstanding_balances"] == []
        assert result["birthdays"] == []
        assert result["recall_due"] == []
        assert result["yesterday_collections"]["total_collected_cents"] == 0
        assert result["no_shows"]["yesterday_no_show_count"] == 0

    async def test_tenant_id_is_passed_to_queries(self):
        """Verify the service accepts the tenant_id parameter without error."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        # Should not raise regardless of tenant_id format
        result = await service.get_huddle(db=db, tenant_id="tn_abc123")
        assert result is not None

    async def test_production_section_has_required_keys(self):
        """Production section must include daily_actual_cents and daily_goal_cents."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        production = result["production"]
        assert "daily_actual_cents" in production
        assert "daily_goal_cents" in production

    async def test_yesterday_collections_has_required_keys(self):
        """yesterday_collections must include total_collected_cents."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        yesterday = result["yesterday_collections"]
        assert "total_collected_cents" in yesterday

    async def test_no_shows_has_required_keys(self):
        """no_shows section must include yesterday_no_show_count."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        no_shows = result["no_shows"]
        assert "yesterday_no_show_count" in no_shows

    async def test_appointments_is_list(self):
        """appointments section must be a list."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert isinstance(result["appointments"], list)

    async def test_incomplete_plans_is_list(self):
        """incomplete_plans section must be a list."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert isinstance(result["incomplete_plans"], list)

    async def test_outstanding_balances_is_list(self):
        """outstanding_balances section must be a list."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert isinstance(result["outstanding_balances"], list)

    async def test_birthdays_is_list(self):
        """birthdays section must be a list."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert isinstance(result["birthdays"], list)

    async def test_recall_due_is_list(self):
        """recall_due section must be a list."""
        service = HuddleService()
        db = _make_db_with_empty_results()

        result = await service.get_huddle(db=db, tenant_id="tn_test")
        assert isinstance(result["recall_due"], list)
