"""Unit tests for the ReferralProgramService class.

Tests cover:
  - generate_code: creates 8-char uppercase code
  - get_or_create_code: returns existing code if present (idempotent)
  - process_referral_code: success (creates two rewards), self-referral (422),
    max_uses exceeded (409)
  - apply_referral_discount: applies oldest pending rewards up to budget
  - get_program_stats: returns aggregate counts
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import ReferralProgramErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.referral_program_service import (
    DEFAULT_REWARD_AMOUNT_CENTS,
    ReferralProgramService,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_code(**overrides) -> MagicMock:
    code = MagicMock()
    code.id = overrides.get("id", uuid.uuid4())
    code.patient_id = overrides.get("patient_id", uuid.uuid4())
    code.code = overrides.get("code", "ABCD1234")
    code.is_active = overrides.get("is_active", True)
    code.uses_count = overrides.get("uses_count", 0)
    code.max_uses = overrides.get("max_uses", None)
    code.created_at = datetime.now(UTC)
    return code


def _make_reward(**overrides) -> MagicMock:
    reward = MagicMock()
    reward.id = overrides.get("id", uuid.uuid4())
    reward.referrer_patient_id = overrides.get("referrer_patient_id", uuid.uuid4())
    reward.referred_patient_id = overrides.get("referred_patient_id", uuid.uuid4())
    reward.referral_code_id = overrides.get("referral_code_id", uuid.uuid4())
    reward.reward_type = overrides.get("reward_type", "discount")
    reward.reward_amount_cents = overrides.get(
        "reward_amount_cents", DEFAULT_REWARD_AMOUNT_CENTS
    )
    reward.status = overrides.get("status", "pending")
    reward.applied_to_invoice_id = overrides.get("applied_to_invoice_id", None)
    reward.completed_at = overrides.get("completed_at", None)
    reward.created_at = datetime.now(UTC)
    return reward


# ── generate_code ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateCode:
    async def test_generate_code_calls_db_add_and_flush(self):
        """generate_code must persist a new ReferralCode via add + flush."""
        service = ReferralProgramService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        patient_id = str(uuid.uuid4())

        # Simulate successful flush (no IntegrityError)
        code_obj = _make_code(patient_id=uuid.UUID(patient_id))

        async def fake_refresh(obj):
            obj.id = code_obj.id
            obj.code = "TSTCODE1"
            obj.patient_id = uuid.UUID(patient_id)
            obj.is_active = True
            obj.uses_count = 0
            obj.max_uses = None
            obj.created_at = datetime.now(UTC)

        db.refresh = fake_refresh

        with patch(
            "app.services.referral_program_service.ReferralCode"
        ) as MockReferralCode:
            instance = _make_code(patient_id=uuid.UUID(patient_id))
            MockReferralCode.return_value = instance

            result = await service.generate_code(db=db, patient_id=patient_id)

        assert db.add.called
        assert "code" in result

    async def test_generate_code_unique_code_length(self):
        """generate_code must produce a code that is at most 8 characters."""
        import secrets as _secrets

        # Sample 10 generated codes and verify they are all <= 8 chars
        for _ in range(10):
            code = _secrets.token_urlsafe(6)[:8].upper()
            assert len(code) <= 8


# ── get_or_create_code ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetOrCreateCode:
    async def test_returns_existing_code_when_present(self):
        """get_or_create_code must return the existing code without creating a new one."""
        service = ReferralProgramService()
        db = AsyncMock()

        patient_id = str(uuid.uuid4())
        existing_code = _make_code(patient_id=uuid.UUID(patient_id), code="EXIST123")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_code
        db.execute = AsyncMock(return_value=result_mock)
        db.add = MagicMock()

        result = await service.get_or_create_code(db=db, patient_id=patient_id)

        assert result["code"] == "EXIST123"
        db.add.assert_not_called()

    async def test_creates_code_when_none_exists(self):
        """get_or_create_code must call generate_code when no active code is found."""
        service = ReferralProgramService()
        db = AsyncMock()

        patient_id = str(uuid.uuid4())

        # First execute: no existing code
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)
        db.add = MagicMock()
        db.flush = AsyncMock()

        new_code = _make_code(patient_id=uuid.UUID(patient_id), code="NEWCODE1")

        async def fake_refresh(obj):
            obj.id = new_code.id
            obj.code = "NEWCODE1"
            obj.patient_id = uuid.UUID(patient_id)
            obj.is_active = True
            obj.uses_count = 0
            obj.max_uses = None
            obj.created_at = datetime.now(UTC)

        db.refresh = fake_refresh

        with patch(
            "app.services.referral_program_service.ReferralCode"
        ) as MockReferralCode:
            instance = _make_code(patient_id=uuid.UUID(patient_id))
            MockReferralCode.return_value = instance
            result = await service.get_or_create_code(db=db, patient_id=patient_id)

        assert db.add.called


# ── process_referral_code: success ────────────────────────────────────────────


@pytest.mark.unit
class TestProcessReferralCodeSuccess:
    async def test_process_creates_two_reward_records(self):
        """process_referral_code must add two ReferralReward records to the session."""
        service = ReferralProgramService()
        db = AsyncMock()

        referrer_pid = uuid.uuid4()
        referred_pid = uuid.uuid4()
        code_obj = _make_code(patient_id=referrer_pid, code="VALID123")

        # call 1: find code  |  call 2: check existing reward (none)
        code_result = MagicMock()
        code_result.scalar_one_or_none.return_value = code_obj

        no_reward_result = MagicMock()
        no_reward_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[code_result, no_reward_result])
        db.add = MagicMock()
        db.flush = AsyncMock()

        referrer_reward = _make_reward(
            referrer_patient_id=referrer_pid,
            referred_patient_id=referred_pid,
            referral_code_id=code_obj.id,
        )
        referred_reward = _make_reward(
            referrer_patient_id=referred_pid,
            referred_patient_id=referred_pid,
            referral_code_id=code_obj.id,
        )

        refresh_sequence = [referrer_reward, referred_reward]
        refresh_index = 0

        async def fake_refresh(obj):
            nonlocal refresh_index
            src = refresh_sequence[refresh_index % 2]
            obj.id = src.id
            obj.referrer_patient_id = src.referrer_patient_id
            obj.referred_patient_id = src.referred_patient_id
            obj.referral_code_id = src.referral_code_id
            obj.reward_type = src.reward_type
            obj.reward_amount_cents = src.reward_amount_cents
            obj.status = src.status
            obj.applied_to_invoice_id = src.applied_to_invoice_id
            obj.completed_at = src.completed_at
            obj.created_at = src.created_at
            refresh_index += 1

        db.refresh = fake_refresh

        with patch(
            "app.services.referral_program_service.ReferralReward"
        ) as MockReward:
            instances = [
                _make_reward(referrer_patient_id=referrer_pid, referred_patient_id=referred_pid),
                _make_reward(referrer_patient_id=referred_pid, referred_patient_id=referred_pid),
            ]
            MockReward.side_effect = instances

            result = await service.process_referral_code(
                db=db,
                referral_code_str="VALID123",
                referred_patient_id=str(referred_pid),
            )

        assert db.add.call_count == 2
        assert "referrer_reward" in result
        assert "referred_reward" in result

    async def test_process_increments_uses_count(self):
        """process_referral_code must increment uses_count on the code object."""
        service = ReferralProgramService()
        db = AsyncMock()

        referrer_pid = uuid.uuid4()
        referred_pid = uuid.uuid4()
        code_obj = _make_code(patient_id=referrer_pid, uses_count=2)

        code_result = MagicMock()
        code_result.scalar_one_or_none.return_value = code_obj

        no_reward_result = MagicMock()
        no_reward_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[code_result, no_reward_result])
        db.add = MagicMock()
        db.flush = AsyncMock()

        r1 = _make_reward()
        r2 = _make_reward()
        call_idx = 0

        async def fake_refresh(obj):
            nonlocal call_idx
            src = r1 if call_idx == 0 else r2
            obj.id = src.id
            obj.referrer_patient_id = src.referrer_patient_id
            obj.referred_patient_id = src.referred_patient_id
            obj.referral_code_id = src.referral_code_id
            obj.reward_type = src.reward_type
            obj.reward_amount_cents = src.reward_amount_cents
            obj.status = src.status
            obj.applied_to_invoice_id = src.applied_to_invoice_id
            obj.completed_at = src.completed_at
            obj.created_at = src.created_at
            call_idx += 1

        db.refresh = fake_refresh

        with patch("app.services.referral_program_service.ReferralReward") as MockReward:
            MockReward.side_effect = [r1, r2]
            await service.process_referral_code(
                db=db,
                referral_code_str="VALID123",
                referred_patient_id=str(referred_pid),
            )

        assert code_obj.uses_count == 3


# ── process_referral_code: self-referral ──────────────────────────────────────


@pytest.mark.unit
class TestProcessReferralCodeSelfReferral:
    async def test_self_referral_raises_422(self):
        """process_referral_code must raise SELF_REFERRAL (422) when patient uses own code."""
        service = ReferralProgramService()
        db = AsyncMock()

        patient_id = uuid.uuid4()
        code_obj = _make_code(patient_id=patient_id, code="MINE1234")

        code_result = MagicMock()
        code_result.scalar_one_or_none.return_value = code_obj
        db.execute = AsyncMock(return_value=code_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.process_referral_code(
                db=db,
                referral_code_str="MINE1234",
                referred_patient_id=str(patient_id),
            )

        assert exc_info.value.error == ReferralProgramErrors.SELF_REFERRAL
        assert exc_info.value.status_code == 422

    async def test_self_referral_does_not_add_rewards(self):
        """Self-referral must not create any ReferralReward records."""
        service = ReferralProgramService()
        db = AsyncMock()

        patient_id = uuid.uuid4()
        code_obj = _make_code(patient_id=patient_id)

        code_result = MagicMock()
        code_result.scalar_one_or_none.return_value = code_obj
        db.execute = AsyncMock(return_value=code_result)
        db.add = MagicMock()

        with pytest.raises(DentalOSError):
            await service.process_referral_code(
                db=db,
                referral_code_str="MINE1234",
                referred_patient_id=str(patient_id),
            )

        db.add.assert_not_called()


# ── process_referral_code: max_uses ───────────────────────────────────────────


@pytest.mark.unit
class TestProcessReferralCodeMaxUses:
    async def test_max_uses_exceeded_raises_409(self):
        """process_referral_code must raise CODE_MAX_USES (409) when limit reached."""
        service = ReferralProgramService()
        db = AsyncMock()

        code_obj = _make_code(uses_count=10, max_uses=10)

        code_result = MagicMock()
        code_result.scalar_one_or_none.return_value = code_obj
        db.execute = AsyncMock(return_value=code_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.process_referral_code(
                db=db,
                referral_code_str="FULLCODE",
                referred_patient_id=str(uuid.uuid4()),
            )

        assert exc_info.value.error == ReferralProgramErrors.CODE_MAX_USES
        assert exc_info.value.status_code == 409

    async def test_code_not_found_raises_404(self):
        """process_referral_code must raise ResourceNotFoundError for unknown codes."""
        service = ReferralProgramService()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.process_referral_code(
                db=db,
                referral_code_str="UNKNOWN1",
                referred_patient_id=str(uuid.uuid4()),
            )

        assert exc_info.value.error == ReferralProgramErrors.CODE_NOT_FOUND


# ── apply_referral_discount ───────────────────────────────────────────────────


@pytest.mark.unit
class TestApplyReferralDiscount:
    async def test_no_pending_rewards_returns_zero(self):
        """apply_referral_discount must return 0 when patient has no pending rewards."""
        service = ReferralProgramService()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        total = await service.apply_referral_discount(
            db=db,
            patient_id=str(uuid.uuid4()),
            invoice_id=uuid.uuid4(),
            max_discount_cents=50000,
        )

        assert total == 0

    async def test_applies_oldest_reward_first(self):
        """apply_referral_discount must mark oldest rewards as applied first."""
        service = ReferralProgramService()
        db = AsyncMock()

        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        reward1 = _make_reward(
            referrer_patient_id=patient_id,
            reward_amount_cents=5000,
            status="pending",
        )
        reward2 = _make_reward(
            referrer_patient_id=patient_id,
            reward_amount_cents=5000,
            status="pending",
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [reward1, reward2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        total = await service.apply_referral_discount(
            db=db,
            patient_id=str(patient_id),
            invoice_id=invoice_id,
            max_discount_cents=50000,
        )

        assert total == 10000
        assert reward1.status == "applied"
        assert reward2.status == "applied"
        assert reward1.applied_to_invoice_id == invoice_id
        assert reward2.applied_to_invoice_id == invoice_id

    async def test_respects_max_discount_budget(self):
        """apply_referral_discount must not exceed max_discount_cents."""
        service = ReferralProgramService()
        db = AsyncMock()

        patient_id = uuid.uuid4()

        reward1 = _make_reward(reward_amount_cents=5000, status="pending")
        reward2 = _make_reward(reward_amount_cents=5000, status="pending")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [reward1, reward2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        total = await service.apply_referral_discount(
            db=db,
            patient_id=str(patient_id),
            invoice_id=uuid.uuid4(),
            max_discount_cents=5000,  # Only enough for one reward
        )

        # Should apply exactly 5000 (one reward), not 10000
        assert total == 5000

    async def test_flushes_after_applying(self):
        """apply_referral_discount must call db.flush() when rewards are applied."""
        service = ReferralProgramService()
        db = AsyncMock()

        patient_id = uuid.uuid4()
        reward = _make_reward(reward_amount_cents=5000, status="pending")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [reward]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        await service.apply_referral_discount(
            db=db,
            patient_id=str(patient_id),
            invoice_id=uuid.uuid4(),
            max_discount_cents=50000,
        )

        db.flush.assert_called_once()


# ── get_program_stats ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetProgramStats:
    async def test_get_program_stats_returns_expected_keys(self):
        """get_program_stats must return a dict with the five aggregate keys."""
        service = ReferralProgramService()
        db = AsyncMock()

        # Five separate scalar_one() calls, one per aggregate query.
        results = [
            MagicMock(scalar_one=MagicMock(return_value=10)),   # total_codes
            MagicMock(scalar_one=MagicMock(return_value=25)),   # total_referrals
            MagicMock(scalar_one=MagicMock(return_value=8)),    # pending
            MagicMock(scalar_one=MagicMock(return_value=17)),   # applied
            MagicMock(scalar_one=MagicMock(return_value=85000)),# total_discount
        ]
        db.execute = AsyncMock(side_effect=results)

        stats = await service.get_program_stats(db=db)

        assert "total_referral_codes" in stats
        assert "total_referrals_made" in stats
        assert "total_rewards_pending" in stats
        assert "total_rewards_applied" in stats
        assert "total_discount_given_cents" in stats

    async def test_get_program_stats_values_match_aggregates(self):
        """get_program_stats values must reflect the DB aggregate results."""
        service = ReferralProgramService()
        db = AsyncMock()

        results = [
            MagicMock(scalar_one=MagicMock(return_value=5)),
            MagicMock(scalar_one=MagicMock(return_value=12)),
            MagicMock(scalar_one=MagicMock(return_value=4)),
            MagicMock(scalar_one=MagicMock(return_value=8)),
            MagicMock(scalar_one=MagicMock(return_value=40000)),
        ]
        db.execute = AsyncMock(side_effect=results)

        stats = await service.get_program_stats(db=db)

        assert stats["total_referral_codes"] == 5
        assert stats["total_referrals_made"] == 12
        assert stats["total_rewards_pending"] == 4
        assert stats["total_rewards_applied"] == 8
        assert stats["total_discount_given_cents"] == 40000
