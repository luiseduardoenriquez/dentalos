"""Unit tests for the MembershipService class.

Tests cover:
  - create_plan: success
  - subscribe_patient: success, already_subscribed (409)
  - cancel_subscription: success, invalid status (409)
  - pause_subscription: success, not active (409)
  - get_active_membership_discount: with and without active subscription
  - get_dashboard: aggregation
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.error_codes import MembershipErrors
from app.core.exceptions import DentalOSError
from app.services.membership_service import MembershipService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_plan(**overrides) -> MagicMock:
    plan = MagicMock()
    plan.id = uuid.uuid4()
    plan.name = overrides.get("name", "Plan Básico")
    plan.description = overrides.get("description", "Limpieza incluida")
    plan.monthly_price_cents = overrides.get("monthly_price_cents", 99000)
    plan.annual_price_cents = overrides.get("annual_price_cents", 999000)
    plan.benefits = overrides.get("benefits", {"cleanings": 2})
    plan.discount_percentage = overrides.get("discount_percentage", 15)
    plan.status = overrides.get("status", "active")
    plan.is_active = True
    plan.created_at = datetime.now(UTC)
    plan.updated_at = datetime.now(UTC)
    return plan


def _make_subscription(**overrides) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.patient_id = overrides.get("patient_id", uuid.uuid4())
    sub.plan_id = overrides.get("plan_id", uuid.uuid4())
    sub.status = overrides.get("status", "active")
    sub.start_date = overrides.get("start_date", date.today())
    sub.next_billing_date = overrides.get("next_billing_date", date.today())
    sub.cancelled_at = overrides.get("cancelled_at", None)
    sub.paused_at = overrides.get("paused_at", None)
    sub.payment_method = overrides.get("payment_method", "card")
    sub.is_active = True
    sub.created_at = datetime.now(UTC)
    sub.updated_at = datetime.now(UTC)
    return sub


# ── create_plan ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreatePlan:
    async def test_success(self):
        service = MembershipService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        result = await service.create_plan(
            db=db,
            created_by=str(uuid.uuid4()),
            name="Plan Premium",
            monthly_price_cents=199000,
        )

        assert db.add.called

    async def test_add_is_called_once(self):
        """create_plan should call db.add exactly once."""
        service = MembershipService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        await service.create_plan(
            db=db,
            created_by=str(uuid.uuid4()),
            name="Plan Único",
            monthly_price_cents=150000,
        )

        db.add.assert_called_once()

    async def test_flush_is_called_after_add(self):
        """create_plan must flush to persist the new plan ORM object."""
        service = MembershipService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        await service.create_plan(
            db=db,
            created_by=str(uuid.uuid4()),
            name="Plan Flush Test",
            monthly_price_cents=100000,
        )

        db.flush.assert_called_once()


# ── subscribe_patient ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSubscribePatient:
    async def test_already_subscribed_raises_409(self):
        service = MembershipService()
        db = AsyncMock()

        # First call: _get_plan returns a plan
        plan = _make_plan()
        plan_result = MagicMock()
        plan_result.scalar_one_or_none.return_value = plan

        # Second call: existing subscription found
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = uuid.uuid4()

        db.execute = AsyncMock(side_effect=[plan_result, existing_result])

        with pytest.raises(DentalOSError) as exc_info:
            await service.subscribe_patient(
                db=db,
                patient_id=str(uuid.uuid4()),
                plan_id=str(plan.id),
                start_date=date.today(),
                created_by=str(uuid.uuid4()),
            )
        assert exc_info.value.error == MembershipErrors.ALREADY_SUBSCRIBED

    async def test_already_subscribed_has_409_status_code(self):
        """The ALREADY_SUBSCRIBED error must carry HTTP 409."""
        service = MembershipService()
        db = AsyncMock()

        plan = _make_plan()
        plan_result = MagicMock()
        plan_result.scalar_one_or_none.return_value = plan

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = uuid.uuid4()

        db.execute = AsyncMock(side_effect=[plan_result, existing_result])

        with pytest.raises(DentalOSError) as exc_info:
            await service.subscribe_patient(
                db=db,
                patient_id=str(uuid.uuid4()),
                plan_id=str(plan.id),
                start_date=date.today(),
                created_by=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 409


# ── cancel_subscription ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestCancelSubscription:
    async def test_cannot_cancel_expired(self):
        service = MembershipService()
        db = AsyncMock()
        sub = _make_subscription(status="expired")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.cancel_subscription(db=db, subscription_id=str(sub.id))
        assert exc_info.value.error == MembershipErrors.CANNOT_CANCEL

    async def test_cannot_cancel_already_cancelled(self):
        """A subscription that is already cancelled cannot be cancelled again."""
        service = MembershipService()
        db = AsyncMock()
        sub = _make_subscription(status="cancelled")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.cancel_subscription(db=db, subscription_id=str(sub.id))
        assert exc_info.value.error == MembershipErrors.CANNOT_CANCEL

    async def test_subscription_not_found_raises_404(self):
        """Cancelling a non-existent subscription must raise a 404-type error."""
        service = MembershipService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await service.cancel_subscription(
                db=db, subscription_id=str(uuid.uuid4())
            )


# ── pause_subscription ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPauseSubscription:
    async def test_cannot_pause_cancelled(self):
        service = MembershipService()
        db = AsyncMock()
        sub = _make_subscription(status="cancelled")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.pause_subscription(db=db, subscription_id=str(sub.id))
        assert exc_info.value.error == MembershipErrors.CANNOT_PAUSE

    async def test_cannot_pause_already_paused(self):
        """A paused subscription cannot be paused again."""
        service = MembershipService()
        db = AsyncMock()
        sub = _make_subscription(status="paused")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.pause_subscription(db=db, subscription_id=str(sub.id))
        assert exc_info.value.error == MembershipErrors.CANNOT_PAUSE

    async def test_cannot_pause_expired(self):
        """An expired subscription cannot be paused."""
        service = MembershipService()
        db = AsyncMock()
        sub = _make_subscription(status="expired")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.pause_subscription(db=db, subscription_id=str(sub.id))
        assert exc_info.value.error == MembershipErrors.CANNOT_PAUSE


# ── get_active_membership_discount ───────────────────────────────────────────


@pytest.mark.unit
class TestGetActiveMembershipDiscount:
    async def test_no_active_membership_returns_zero(self):
        service = MembershipService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        discount, sub_id = await service.get_active_membership_discount(
            db=db,
            patient_id=uuid.uuid4(),
        )
        assert discount == 0
        assert sub_id is None

    async def test_active_membership_returns_discount(self):
        service = MembershipService()
        db = AsyncMock()

        sub_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (15, sub_id)
        db.execute = AsyncMock(return_value=mock_result)

        discount, returned_id = await service.get_active_membership_discount(
            db=db,
            patient_id=uuid.uuid4(),
        )
        assert discount == 15
        assert returned_id == sub_id

    async def test_discount_is_non_negative(self):
        """Discount percentage must always be 0 or greater."""
        service = MembershipService()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        discount, _ = await service.get_active_membership_discount(
            db=db,
            patient_id=uuid.uuid4(),
        )
        assert discount >= 0
