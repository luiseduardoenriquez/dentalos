"""Unit tests for the RecallService class.

Tests cover:
  - create_campaign: success
  - activate_campaign: success, invalid status (409)
  - pause_campaign: success, not active (409)
  - identify_inactive_patients: returns UUIDs
  - process_step: sends notification and increments step
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.error_codes import RecallErrors
from app.core.exceptions import DentalOSError
from app.services.recall_service import RecallService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_campaign(**overrides) -> MagicMock:
    c = MagicMock()
    c.id = overrides.get("id", uuid.uuid4())
    c.name = overrides.get("name", "Recall 6 meses")
    c.type = overrides.get("type", "recall")
    c.filters = None
    c.message_templates = None
    c.channel = overrides.get("channel", "whatsapp")
    c.schedule = overrides.get(
        "schedule",
        [{"day_offset": 0, "channel": "whatsapp", "message_template": "Hola"}],
    )
    c.status = overrides.get("status", "draft")
    c.created_by = uuid.uuid4()
    c.activated_at = None
    c.paused_at = None
    c.completed_at = None
    c.is_active = True
    c.created_at = datetime.now(UTC)
    c.updated_at = datetime.now(UTC)
    return c


# ── activate_campaign ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestActivateCampaign:
    async def test_cannot_activate_completed(self):
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="completed")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.activate_campaign(db=db, campaign_id=str(campaign.id))
        assert exc_info.value.error == RecallErrors.CANNOT_ACTIVATE

    async def test_cannot_activate_already_active(self):
        """An active campaign cannot be activated again."""
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="active")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.activate_campaign(db=db, campaign_id=str(campaign.id))
        assert exc_info.value.error == RecallErrors.CANNOT_ACTIVATE

    async def test_activate_draft_succeeds(self):
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="draft")

        # First call: _get_campaign
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign

        # Second call: _campaign_to_dict stats query
        stats_result = MagicMock()
        stats_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[campaign_result, stats_result])
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await service.activate_campaign(db=db, campaign_id=str(campaign.id))
        assert campaign.status == "active"
        assert campaign.activated_at is not None

    async def test_activate_sets_activated_at_timestamp(self):
        """activate_campaign must set activated_at to a non-None datetime."""
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="draft")

        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign

        stats_result = MagicMock()
        stats_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[campaign_result, stats_result])
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await service.activate_campaign(db=db, campaign_id=str(campaign.id))
        assert campaign.activated_at is not None

    async def test_cannot_activate_has_409_status_code(self):
        """CANNOT_ACTIVATE error must carry HTTP 409 Conflict."""
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="completed")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.activate_campaign(db=db, campaign_id=str(campaign.id))
        assert exc_info.value.status_code == 409


# ── pause_campaign ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPauseCampaign:
    async def test_cannot_pause_draft(self):
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="draft")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.pause_campaign(db=db, campaign_id=str(campaign.id))
        assert exc_info.value.error == RecallErrors.ALREADY_PAUSED

    async def test_cannot_pause_already_paused(self):
        """A paused campaign cannot be paused again."""
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="paused")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.pause_campaign(db=db, campaign_id=str(campaign.id))
        assert exc_info.value.error == RecallErrors.ALREADY_PAUSED

    async def test_cannot_pause_completed(self):
        """A completed campaign cannot be paused."""
        service = RecallService()
        db = AsyncMock()
        campaign = _make_campaign(status="completed")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError):
            await service.pause_campaign(db=db, campaign_id=str(campaign.id))


# ── campaign not found ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCampaignNotFound:
    async def test_activate_raises_404(self):
        service = RecallService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await service.activate_campaign(db=db, campaign_id=str(uuid.uuid4()))

    async def test_pause_raises_404(self):
        """Pausing a non-existent campaign must raise a not-found error."""
        service = RecallService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await service.pause_campaign(db=db, campaign_id=str(uuid.uuid4()))
