"""Unit tests for the RETHUSVerificationService class.

Tests cover:
  - verify_user: success (found), not found in registry, user not in DB
  - check_status: returns current status dict
  - periodic_reverify: processes multiple users, swallows individual errors
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import RETHUSErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.rethus_verification_service import RETHUSVerificationService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.role = overrides.get("role", "doctor")
    user.rethus_number = overrides.get("rethus_number", "RETHUS-12345")
    user.rethus_verification_status = overrides.get(
        "rethus_verification_status", "pending"
    )
    user.rethus_verified_at = overrides.get("rethus_verified_at", None)
    user.is_active = overrides.get("is_active", True)
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_adapter_result(*, found: bool = True) -> MagicMock:
    result = MagicMock()
    result.found = found
    result.full_name = "Dr. Carlos Perez" if found else None
    result.profession = "Odontologia" if found else None
    result.specialty = "Ortodoncia" if found else None
    return result


# ── verify_user: success ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestVerifyUserSuccess:
    async def test_verify_user_sets_status_to_verified(self):
        """verify_user must set rethus_verification_status='verified' when found."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user(rethus_verification_status="pending")

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        adapter_result = _make_adapter_result(found=True)

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(return_value=adapter_result)
            mock_get_adapter.return_value = mock_adapter

            result = await service.verify_user(
                db=db,
                user_id=uuid.uuid4(),
                rethus_number="RETHUS-12345",
            )

        assert user.rethus_verification_status == "verified"
        assert user.rethus_verified_at is not None

    async def test_verify_user_returns_dict_with_expected_keys(self):
        """verify_user must return a dict matching the RETHUSVerificationResponse contract."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        adapter_result = _make_adapter_result(found=True)

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(return_value=adapter_result)
            mock_get_adapter.return_value = mock_adapter

            result = await service.verify_user(
                db=db,
                user_id=uuid.uuid4(),
                rethus_number="RETHUS-12345",
            )

        assert "user_id" in result
        assert "rethus_number" in result
        assert "verification_status" in result
        assert "verified_at" in result
        assert "professional_name" in result

    async def test_verify_user_flushes_db(self):
        """verify_user must call db.flush() to persist changes."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        adapter_result = _make_adapter_result(found=True)

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(return_value=adapter_result)
            mock_get_adapter.return_value = mock_adapter

            await service.verify_user(
                db=db,
                user_id=uuid.uuid4(),
                rethus_number="RETHUS-12345",
            )

        db.flush.assert_called()


# ── verify_user: adapter returns not found ────────────────────────────────────


@pytest.mark.unit
class TestVerifyUserNotFound:
    async def test_verify_user_not_found_sets_status_to_failed(self):
        """verify_user must set status='failed' when adapter returns found=False."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user(rethus_verification_status="pending")

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        adapter_result = _make_adapter_result(found=False)

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(return_value=adapter_result)
            mock_get_adapter.return_value = mock_adapter

            result = await service.verify_user(
                db=db,
                user_id=uuid.uuid4(),
                rethus_number="RETHUS-99999",
            )

        assert user.rethus_verification_status == "failed"
        assert user.rethus_verified_at is None

    async def test_verify_user_not_found_professional_name_is_none(self):
        """When adapter returns not found, professional_name in result must be None."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        adapter_result = _make_adapter_result(found=False)

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(return_value=adapter_result)
            mock_get_adapter.return_value = mock_adapter

            result = await service.verify_user(
                db=db,
                user_id=uuid.uuid4(),
                rethus_number="RETHUS-99999",
            )

        assert result["professional_name"] is None

    async def test_verify_user_db_user_missing_raises_404(self):
        """verify_user must raise ResourceNotFoundError when user does not exist."""
        service = RETHUSVerificationService()
        db = AsyncMock()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=user_result)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.verify_user(
                db=db,
                user_id=uuid.uuid4(),
                rethus_number="RETHUS-12345",
            )

        assert exc_info.value.error == RETHUSErrors.NOT_FOUND

    async def test_verify_user_adapter_exception_raises_503(self):
        """When the adapter raises, verify_user must raise 503 DentalOSError."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(
                side_effect=ConnectionError("RETHUS unreachable")
            )
            mock_get_adapter.return_value = mock_adapter

            with pytest.raises(DentalOSError) as exc_info:
                await service.verify_user(
                    db=db,
                    user_id=uuid.uuid4(),
                    rethus_number="RETHUS-12345",
                )

        assert exc_info.value.status_code == 503
        assert exc_info.value.error == RETHUSErrors.SERVICE_UNAVAILABLE


# ── check_status ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckStatus:
    async def test_check_status_returns_dict(self):
        """check_status must return a dict with verification_status and user_id."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user(rethus_verification_status="verified")

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)

        result = await service.check_status(db=db, user_id=uuid.uuid4())

        assert result["verification_status"] == "verified"
        assert "user_id" in result

    async def test_check_status_professional_name_is_none(self):
        """check_status must not return professional_name (PHI safety)."""
        service = RETHUSVerificationService()
        db = AsyncMock()
        user = _make_user(rethus_verification_status="verified")

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=user_result)

        result = await service.check_status(db=db, user_id=uuid.uuid4())

        assert result["professional_name"] is None

    async def test_check_status_user_not_found_raises_404(self):
        """check_status must raise ResourceNotFoundError when user is absent."""
        service = RETHUSVerificationService()
        db = AsyncMock()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=user_result)

        with pytest.raises(ResourceNotFoundError):
            await service.check_status(db=db, user_id=uuid.uuid4())


# ── periodic_reverify ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPeriodicReverify:
    async def test_periodic_reverify_returns_summary_dict(self):
        """periodic_reverify must return a dict with processed/succeeded/failed keys."""
        service = RETHUSVerificationService()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        summary = await service.periodic_reverify(db=db)

        assert "processed" in summary
        assert "succeeded" in summary
        assert "failed" in summary

    async def test_periodic_reverify_empty_batch(self):
        """periodic_reverify with no eligible users returns zeros."""
        service = RETHUSVerificationService()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        summary = await service.periodic_reverify(db=db)

        assert summary["processed"] == 0
        assert summary["succeeded"] == 0
        assert summary["failed"] == 0

    async def test_periodic_reverify_processes_multiple_users(self):
        """periodic_reverify must call verify_user once per eligible user."""
        service = RETHUSVerificationService()
        db = AsyncMock()

        user1 = _make_user(
            rethus_verification_status="verified",
            rethus_verified_at=datetime.now(UTC) - timedelta(days=40),
        )
        user2 = _make_user(
            rethus_verification_status="verified",
            rethus_verified_at=datetime.now(UTC) - timedelta(days=35),
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [user1, user2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock

        verify_calls: list[str] = []

        async def fake_verify_user(**kwargs):
            verify_calls.append(str(kwargs["user_id"]))
            # Return a valid dict to simulate success
            u = kwargs.get("user_id")
            return {
                "user_id": str(u),
                "rethus_number": "RETHUS-X",
                "verification_status": "verified",
                "verified_at": datetime.now(UTC),
                "professional_name": None,
                "profession": None,
                "specialty": None,
            }

        # The inner execute call (the SELECT) returns users; subsequent execute
        # calls inside verify_user also need to return user objects.
        user_result_mock = MagicMock()
        user_result_mock.scalar_one_or_none.side_effect = [user1, user2]

        db.execute = AsyncMock(side_effect=[result_mock, user_result_mock, user_result_mock])
        db.flush = AsyncMock()

        adapter_result = _make_adapter_result(found=True)

        with patch(
            "app.services.rethus_verification_service._get_adapter"
        ) as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.verify_professional = AsyncMock(return_value=adapter_result)
            mock_get_adapter.return_value = mock_adapter

            summary = await service.periodic_reverify(db=db)

        assert summary["processed"] == 2

    async def test_periodic_reverify_swallows_individual_errors(self):
        """periodic_reverify must not abort the batch when one user fails."""
        service = RETHUSVerificationService()
        db = AsyncMock()

        user1 = _make_user(rethus_number="RETHUS-FAIL")
        user2 = _make_user(rethus_number="RETHUS-OK")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [user1, user2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock

        call_count = 0

        async def mock_verify_user(*, db, user_id, rethus_number):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DentalOSError(
                    error=RETHUSErrors.SERVICE_UNAVAILABLE,
                    message="Service down",
                    status_code=503,
                )
            return {
                "user_id": str(user_id),
                "rethus_number": rethus_number,
                "verification_status": "verified",
                "verified_at": datetime.now(UTC),
                "professional_name": None,
                "profession": None,
                "specialty": None,
            }

        db.execute = AsyncMock(return_value=result_mock)

        with patch.object(service, "verify_user", side_effect=mock_verify_user):
            summary = await service.periodic_reverify(db=db)

        assert summary["processed"] == 2
        assert summary["failed"] == 1
        assert summary["succeeded"] == 1
