"""Unit tests for the LoyaltyService class.

Tests cover:
  - award_points: creates transaction, balance increases
  - award_points: creates record if none exists
  - redeem_points: balance decreases, transaction created
  - redeem_points: insufficient balance raises 409
  - redeem_points: correct discount_cents calculation
  - expire_inactive: zeroes balance and creates 'expired' transaction
  - get_leaderboard: sorted by points_balance desc
  - get_balance: returns default (0) when no record exists
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import LoyaltyErrors
from app.core.exceptions import DentalOSError
from app.services.loyalty_service import LoyaltyService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_loyalty_row(**overrides) -> MagicMock:
    row = MagicMock()
    row.patient_id = overrides.get("patient_id", uuid.uuid4())
    row.points_balance = overrides.get("points_balance", 0)
    row.lifetime_points_earned = overrides.get("lifetime_points_earned", 0)
    row.lifetime_points_redeemed = overrides.get("lifetime_points_redeemed", 0)
    row.last_activity_at = overrides.get("last_activity_at", datetime.now(UTC))
    return row


def _make_transaction(**overrides) -> MagicMock:
    txn = MagicMock()
    txn.id = overrides.get("id", uuid.uuid4())
    txn.patient_id = overrides.get("patient_id", uuid.uuid4())
    txn.type = overrides.get("type", "earned")
    txn.points = overrides.get("points", 100)
    txn.reason = overrides.get("reason", None)
    txn.reference_id = None
    txn.reference_type = None
    txn.created_at = datetime.now(UTC)
    return txn


# ── award_points ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAwardPoints:
    """Tests for LoyaltyService.award_points."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_award_points_creates_transaction(self, db):
        """Awarding points must persist a LoyaltyTransaction via db.add."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=50)

        locked_result = MagicMock()
        locked_result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=locked_result)

        with patch("app.services.loyalty_service.LoyaltyTransaction") as mock_txn_cls:
            mock_txn = MagicMock()
            mock_txn_cls.return_value = mock_txn

            service = LoyaltyService()
            with patch.object(service, "get_points_to_currency_ratio", new_callable=AsyncMock, return_value=10):
                await service.award_points(db=db, patient_id=patient_id, points=100)

        # db.add called at least once (the transaction)
        db.add.assert_called()

    async def test_award_points_increases_balance(self, db):
        """Balance must be incremented by the awarded points."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=50, lifetime_points_earned=50)

        locked_result = MagicMock()
        locked_result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=locked_result)

        service = LoyaltyService()
        with patch("app.services.loyalty_service.LoyaltyTransaction"):
            with patch.object(service, "get_points_to_currency_ratio", new_callable=AsyncMock, return_value=10):
                await service.award_points(db=db, patient_id=patient_id, points=100)

        assert row.points_balance == 150
        assert row.lifetime_points_earned == 150

    async def test_award_points_creates_record_if_none_exists(self, db):
        """When no LoyaltyPoints row exists, it must be created before awarding."""
        patient_id = uuid.uuid4()

        # First call (locked select): no row
        no_row_result = MagicMock()
        no_row_result.scalar_one_or_none.return_value = None

        # Second call (re-lock after insert)
        new_row = _make_loyalty_row(patient_id=patient_id, points_balance=0)
        locked_result = MagicMock()
        locked_result.scalar_one.return_value = new_row

        db.execute = AsyncMock(side_effect=[no_row_result, locked_result])

        with patch("app.services.loyalty_service.LoyaltyPoints") as mock_lp_cls:
            mock_lp_cls.return_value = new_row
            with patch("app.services.loyalty_service.LoyaltyTransaction"):
                service = LoyaltyService()
                with patch.object(service, "get_points_to_currency_ratio", new_callable=AsyncMock, return_value=10):
                    await service.award_points(db=db, patient_id=patient_id, points=50)

        # db.add called (at minimum for the new balance row)
        db.add.assert_called()


# ── redeem_points ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRedeemPoints:
    """Tests for LoyaltyService.redeem_points."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_redeem_points_success(self, db):
        """Successful redemption decreases balance and creates a transaction."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=500, lifetime_points_redeemed=0)

        locked_result = MagicMock()
        locked_result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=locked_result)

        with patch("app.services.loyalty_service.LoyaltyTransaction"):
            service = LoyaltyService()
            with patch.object(service, "get_points_to_currency_ratio", new_callable=AsyncMock, return_value=10):
                result = await service.redeem_points(db=db, patient_id=patient_id, points=100)

        assert row.points_balance == 400
        assert row.lifetime_points_redeemed == 100
        assert "discount_cents" in result

    async def test_redeem_points_insufficient_raises(self, db):
        """Requesting more points than available must raise INSUFFICIENT_POINTS (409)."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=50)

        locked_result = MagicMock()
        locked_result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=locked_result)

        service = LoyaltyService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.redeem_points(db=db, patient_id=patient_id, points=200)

        assert exc_info.value.error == LoyaltyErrors.INSUFFICIENT_POINTS
        assert exc_info.value.status_code == 409

    async def test_redeem_points_no_row_raises(self, db):
        """No balance row at all (None) must raise INSUFFICIENT_POINTS."""
        patient_id = uuid.uuid4()

        locked_result = MagicMock()
        locked_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=locked_result)

        service = LoyaltyService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.redeem_points(db=db, patient_id=patient_id, points=100)

        assert exc_info.value.error == LoyaltyErrors.INSUFFICIENT_POINTS

    async def test_redeem_returns_discount_cents(self, db):
        """discount_cents = points * ratio (default 10)."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=1000, lifetime_points_redeemed=0)

        locked_result = MagicMock()
        locked_result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=locked_result)

        with patch("app.services.loyalty_service.LoyaltyTransaction"):
            service = LoyaltyService()
            with patch.object(service, "get_points_to_currency_ratio", new_callable=AsyncMock, return_value=10):
                result = await service.redeem_points(db=db, patient_id=patient_id, points=200)

        # 200 points * 10 cents/point = 2000 cents
        assert result["discount_cents"] == 2000


# ── expire_inactive ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestExpireInactive:
    """Tests for LoyaltyService.expire_inactive."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_expire_inactive(self, db):
        """Inactive patient balance must be zeroed and 'expired' transaction created."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=300)

        locked_result = MagicMock()
        locked_result.scalars.return_value.all.return_value = [row]
        db.execute = AsyncMock(return_value=locked_result)

        with patch("app.services.loyalty_service.LoyaltyTransaction") as mock_txn_cls:
            mock_txn = MagicMock()
            mock_txn_cls.return_value = mock_txn

            service = LoyaltyService()
            count = await service.expire_inactive(db=db, expiry_months=12)

        assert count == 1
        assert row.points_balance == 0
        db.add.assert_called()

    async def test_expire_inactive_zero_patients_returns_zero(self, db):
        """No inactive patients -> returns 0 and makes no changes."""
        locked_result = MagicMock()
        locked_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=locked_result)

        service = LoyaltyService()
        count = await service.expire_inactive(db=db, expiry_months=12)

        assert count == 0
        db.add.assert_not_called()


# ── get_leaderboard ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetLeaderboard:
    """Tests for LoyaltyService.get_leaderboard."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_leaderboard(self, db):
        """Leaderboard returns items sorted by points_balance desc."""
        row1 = MagicMock()
        row1.patient_id = uuid.uuid4()
        row1.patient_name = "Ana Lopez"
        row1.points_balance = 500
        row1.lifetime_points_earned = 600

        row2 = MagicMock()
        row2.patient_id = uuid.uuid4()
        row2.patient_name = "Juan Perez"
        row2.points_balance = 300
        row2.lifetime_points_earned = 350

        result = MagicMock()
        result.all.return_value = [row1, row2]
        db.execute = AsyncMock(return_value=result)

        service = LoyaltyService()
        leaderboard = await service.get_leaderboard(db=db, limit=10)

        assert leaderboard["total"] == 2
        items = leaderboard["items"]
        assert len(items) == 2
        # First item must have higher balance
        assert items[0]["points_balance"] >= items[1]["points_balance"]


# ── get_balance ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetBalance:
    """Tests for LoyaltyService.get_balance."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_get_balance_returns_default_when_no_record(self, db):
        """No existing row creates a default 0-balance record."""
        patient_id = uuid.uuid4()

        no_row_result = MagicMock()
        no_row_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_row_result)

        new_row = _make_loyalty_row(patient_id=patient_id, points_balance=0)

        with patch("app.services.loyalty_service.LoyaltyPoints", return_value=new_row):
            service = LoyaltyService()
            result = await service.get_balance(db=db, patient_id=patient_id)

        assert result["points_balance"] == 0
        db.add.assert_called_once()

    async def test_get_balance_returns_existing_row(self, db):
        """Existing row must be returned as-is without creating a new record."""
        patient_id = uuid.uuid4()
        row = _make_loyalty_row(patient_id=patient_id, points_balance=750)

        row_result = MagicMock()
        row_result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=row_result)

        service = LoyaltyService()
        result = await service.get_balance(db=db, patient_id=patient_id)

        assert result["points_balance"] == 750
        db.add.assert_not_called()
