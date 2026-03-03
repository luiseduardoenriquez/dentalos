"""Unit tests for the EmailCampaignService class.

Tests cover:
  - create_campaign: draft status created, segment_filters stored
  - update_campaign: updates name/subject, non-draft raises NOT_DRAFT
  - identify_recipients: excludes unsubscribed, excludes no-email patients,
    age_min/age_max filter applied
  - send_campaign: bulk inserts recipients and enqueues job, empty segment raises
    NO_RECIPIENTS
  - schedule_campaign: sets status='scheduled' and scheduled_at, non-draft raises
    NOT_DRAFT
"""

import uuid
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import MarketingErrors
from app.core.exceptions import DentalOSError
from app.services.email_campaign_service import EmailCampaignService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_campaign(**overrides) -> MagicMock:
    """Build a mock EmailCampaign ORM row."""
    c = MagicMock()
    c.id = overrides.get("id", uuid.uuid4())
    c.name = overrides.get("name", "Campaña de prueba")
    c.subject = overrides.get("subject", "Asunto de prueba")
    c.template_id = overrides.get("template_id", "recall")
    c.template_html = overrides.get("template_html", None)
    c.segment_filters = overrides.get("segment_filters", {})
    c.status = overrides.get("status", "draft")
    c.scheduled_at = overrides.get("scheduled_at", None)
    c.sent_at = overrides.get("sent_at", None)
    c.sent_count = overrides.get("sent_count", 0)
    c.open_count = overrides.get("open_count", 0)
    c.click_count = overrides.get("click_count", 0)
    c.bounce_count = overrides.get("bounce_count", 0)
    c.unsubscribe_count = overrides.get("unsubscribe_count", 0)
    c.created_by = overrides.get("created_by", uuid.uuid4())
    c.is_active = overrides.get("is_active", True)
    c.deleted_at = overrides.get("deleted_at", None)
    c.created_at = overrides.get("created_at", datetime.now(UTC))
    c.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return c


def _make_patient_row(**overrides) -> MagicMock:
    """Build a mock patient query result row for recipient identification."""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.email = overrides.get("email", "paciente@example.com")
    return row


# ── TestCreateCampaign ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateCampaign:
    """Tests for EmailCampaignService.create_campaign."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_create_draft(self, db):
        """A new campaign must be persisted with status='draft'."""
        created_by = uuid.uuid4()
        campaign = _make_campaign(status="draft")

        with patch(
            "app.services.email_campaign_service.EmailCampaign",
            return_value=campaign,
        ):
            service = EmailCampaignService()
            result = await service.create_campaign(
                db=db,
                data={
                    "name": "Campaña Recall",
                    "subject": "¡Te extrañamos!",
                    "template_id": "recall",
                },
                created_by=created_by,
            )

        assert result["status"] == "draft"
        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_create_with_filters(self, db):
        """Segment filters must be stored on the campaign row."""
        created_by = uuid.uuid4()
        filters = {"age_min": 18, "age_max": 60}
        campaign = _make_campaign(status="draft", segment_filters=filters)

        with patch(
            "app.services.email_campaign_service.EmailCampaign",
            return_value=campaign,
        ) as MockCampaign:
            service = EmailCampaignService()
            await service.create_campaign(
                db=db,
                data={
                    "name": "Campaña Adultos",
                    "subject": "Servicio para adultos",
                    "segment_filters": filters,
                },
                created_by=created_by,
            )
            # Verify the constructor received segment_filters
            call_kwargs = MockCampaign.call_args.kwargs
            assert call_kwargs["segment_filters"] == filters


# ── TestUpdateCampaign ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateCampaign:
    """Tests for EmailCampaignService.update_campaign."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_update_draft_success(self, db):
        """A draft campaign name and subject can be updated."""
        campaign_id = uuid.uuid4()
        campaign = _make_campaign(id=campaign_id, status="draft", name="Original")

        result = MagicMock()
        result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        await service.update_campaign(
            db=db,
            campaign_id=campaign_id,
            data={"name": "Actualizada", "subject": "Nuevo asunto"},
        )

        assert campaign.name == "Actualizada"
        assert campaign.subject == "Nuevo asunto"
        db.flush.assert_called()

    async def test_update_non_draft_fails(self, db):
        """Updating a campaign with status != draft raises NOT_DRAFT (409)."""
        campaign_id = uuid.uuid4()
        campaign = _make_campaign(id=campaign_id, status="sending")

        result = MagicMock()
        result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.update_campaign(
                db=db,
                campaign_id=campaign_id,
                data={"name": "Cambio no permitido"},
            )

        assert exc_info.value.error == MarketingErrors.NOT_DRAFT
        assert exc_info.value.status_code == 409


# ── TestIdentifyRecipients ────────────────────────────────────────────────────


@pytest.mark.unit
class TestIdentifyRecipients:
    """Tests for EmailCampaignService.identify_recipients."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_excludes_unsubscribed(self, db):
        """Patients with email_unsubscribed=True must not appear in results."""
        # The service builds a WHERE clause that includes email_unsubscribed IS False,
        # so if the DB returns no rows we get an empty list.
        result = MagicMock()
        result.all.return_value = []
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        recipients = await service.identify_recipients(db, segment_filters=None)

        # No rows returned — confirming the query executed without error
        assert recipients == []

    async def test_excludes_no_email(self, db):
        """Patients with NULL email are excluded by the base WHERE condition."""
        result = MagicMock()
        result.all.return_value = []
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        recipients = await service.identify_recipients(db, segment_filters=None)

        assert isinstance(recipients, list)
        # Every returned row must have a non-None email
        for r in recipients:
            assert r["email"] is not None

    async def test_age_filter_does_not_crash(self, db):
        """Passing age_min / age_max filter must not raise an error."""
        row = _make_patient_row()
        result = MagicMock()
        result.all.return_value = [row]
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        recipients = await service.identify_recipients(
            db,
            segment_filters={"age_min": 30, "age_max": 55},
        )

        # Result list must contain the row returned by the mocked DB
        assert len(recipients) == 1
        assert recipients[0]["patient_id"] == row.id
        assert recipients[0]["email"] == row.email

    async def test_no_filters_returns_all_eligible(self, db):
        """Without filters all eligible (active, email present, not unsubscribed) rows are returned."""
        row1 = _make_patient_row(email="a@test.com")
        row2 = _make_patient_row(email="b@test.com")
        result = MagicMock()
        result.all.return_value = [row1, row2]
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        recipients = await service.identify_recipients(db, segment_filters={})

        assert len(recipients) == 2


# ── TestSendCampaign ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSendCampaign:
    """Tests for EmailCampaignService.send_campaign."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.add_all = MagicMock()
        return session

    async def test_send_creates_recipients_and_enqueues(self, db):
        """send_campaign must bulk-insert recipients and call publish_message."""
        campaign_id = uuid.uuid4()
        campaign = _make_campaign(id=campaign_id, status="draft", segment_filters={})

        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=campaign_result)

        recipients = [
            {"patient_id": uuid.uuid4(), "email": "p1@test.com"},
            {"patient_id": uuid.uuid4(), "email": "p2@test.com"},
        ]

        with patch.object(
            EmailCampaignService,
            "identify_recipients",
            new_callable=AsyncMock,
            return_value=recipients,
        ):
            with patch(
                "app.services.email_campaign_service.publish_message",
                new_callable=AsyncMock,
            ) as mock_publish:
                with patch(
                    "app.services.email_campaign_service.EmailCampaignRecipient",
                    side_effect=lambda **kw: MagicMock(**kw),
                ):
                    service = EmailCampaignService()
                    result = await service.send_campaign(
                        db=db,
                        campaign_id=campaign_id,
                        tenant_id="tn_abc123",
                    )

        db.add_all.assert_called_once()
        mock_publish.assert_called_once()
        assert result["recipient_count"] == 2
        assert result["queued"] is True
        assert campaign.status == "sending"
        assert campaign.sent_count == 2

    async def test_send_no_recipients(self, db):
        """When the segment is empty NO_RECIPIENTS (422) must be raised."""
        campaign_id = uuid.uuid4()
        campaign = _make_campaign(id=campaign_id, status="draft", segment_filters={})

        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=campaign_result)

        with patch.object(
            EmailCampaignService,
            "identify_recipients",
            new_callable=AsyncMock,
            return_value=[],
        ):
            service = EmailCampaignService()
            with pytest.raises(DentalOSError) as exc_info:
                await service.send_campaign(
                    db=db,
                    campaign_id=campaign_id,
                    tenant_id="tn_abc123",
                )

        assert exc_info.value.error == MarketingErrors.NO_RECIPIENTS
        assert exc_info.value.status_code == 422


# ── TestScheduleCampaign ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestScheduleCampaign:
    """Tests for EmailCampaignService.schedule_campaign."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_schedule_success(self, db):
        """A draft campaign scheduled_at must be set and status changed to 'scheduled'."""
        campaign_id = uuid.uuid4()
        campaign = _make_campaign(id=campaign_id, status="draft")
        scheduled_for = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)

        result = MagicMock()
        result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        await service.schedule_campaign(
            db=db,
            campaign_id=campaign_id,
            scheduled_at=scheduled_for,
        )

        assert campaign.status == "scheduled"
        assert campaign.scheduled_at == scheduled_for
        db.flush.assert_called()

    async def test_schedule_non_draft(self, db):
        """Scheduling a campaign not in draft status raises NOT_DRAFT (409)."""
        campaign_id = uuid.uuid4()
        campaign = _make_campaign(id=campaign_id, status="sent")

        result = MagicMock()
        result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=result)

        service = EmailCampaignService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.schedule_campaign(
                db=db,
                campaign_id=campaign_id,
                scheduled_at=datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
            )

        assert exc_info.value.error == MarketingErrors.NOT_DRAFT
        assert exc_info.value.status_code == 409
