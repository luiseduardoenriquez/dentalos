"""Unit tests for the FamilyService class.

Tests cover:
  - create: primary contact auto-added as first member
  - add_member: success
  - add_member: already in family raises ALREADY_IN_FAMILY (409)
  - remove_member: soft-deletes (is_active = False)
  - remove_member: primary contact raises PRIMARY_CONTACT_REQUIRED (409)
  - get_family_billing: totals calculated across all members
  - get (family not found): raises FamilyErrors.NOT_FOUND
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import FamilyErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.family_service import FamilyService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_group(**overrides) -> MagicMock:
    group = MagicMock()
    group.id = overrides.get("id", uuid.uuid4())
    group.name = overrides.get("name", "Familia Perez")
    group.primary_contact_patient_id = overrides.get("primary_contact_patient_id", uuid.uuid4())
    group.is_active = overrides.get("is_active", True)
    group.created_at = datetime.now(UTC)
    return group


def _make_patient(**overrides) -> MagicMock:
    patient = MagicMock()
    patient.id = overrides.get("id", uuid.uuid4())
    patient.first_name = overrides.get("first_name", "Test")
    patient.last_name = overrides.get("last_name", "Patient")
    patient.is_active = True
    return patient


def _make_member(**overrides) -> MagicMock:
    member = MagicMock()
    member.id = overrides.get("id", uuid.uuid4())
    member.family_group_id = overrides.get("family_group_id", uuid.uuid4())
    member.patient_id = overrides.get("patient_id", uuid.uuid4())
    member.relationship = overrides.get("relationship", "parent")
    member.is_active = overrides.get("is_active", True)
    member.created_at = datetime.now(UTC)
    return member


# ── create ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateFamily:
    """Tests for FamilyService.create."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_create_family_adds_primary_contact(self, db):
        """Creating a family must auto-add primary contact as the first member."""
        primary_pid = uuid.uuid4()
        patient = _make_patient(id=primary_pid)
        group = _make_group(primary_contact_patient_id=primary_pid)

        # _get_patient result
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient

        # _group_to_dict -> members query
        members_result = MagicMock()
        members_result.all.return_value = [(MagicMock(), "Test", "Patient")]

        db.execute = AsyncMock(side_effect=[patient_result, members_result])

        with patch("app.services.family_service.FamilyGroup", return_value=group):
            with patch("app.services.family_service.FamilyMember") as mock_member_cls:
                mock_member = _make_member(patient_id=primary_pid)
                mock_member_cls.return_value = mock_member

                service = FamilyService()
                await service.create(
                    db=db,
                    name="Familia Perez",
                    primary_contact_patient_id=str(primary_pid),
                )

        # db.add called at least twice: once for group, once for member
        assert db.add.call_count >= 2

    async def test_create_family_flushes_twice(self, db):
        """Must flush after creating the group AND after creating the member."""
        primary_pid = uuid.uuid4()
        patient = _make_patient(id=primary_pid)
        group = _make_group(primary_contact_patient_id=primary_pid)

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient

        members_result = MagicMock()
        members_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[patient_result, members_result])

        with patch("app.services.family_service.FamilyGroup", return_value=group):
            with patch("app.services.family_service.FamilyMember"):
                service = FamilyService()
                await service.create(
                    db=db,
                    name="Familia Test",
                    primary_contact_patient_id=str(primary_pid),
                )

        assert db.flush.call_count >= 2


# ── add_member ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAddMember:
    """Tests for FamilyService.add_member."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_add_member_success(self, db):
        """Adding a new member must call db.add and flush."""
        family_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        group = _make_group(id=family_id)
        patient = _make_patient(id=patient_id)

        group_result = MagicMock()
        group_result.scalar_one_or_none.return_value = group

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient

        # No existing membership
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # _group_to_dict members query
        members_result = MagicMock()
        members_result.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[group_result, patient_result, existing_result, members_result]
        )

        with patch("app.services.family_service.FamilyMember"):
            service = FamilyService()
            await service.add_member(
                db=db,
                family_id=str(family_id),
                patient_id=str(patient_id),
                relationship="child",
            )

        db.add.assert_called()
        db.flush.assert_called()

    async def test_add_member_already_in_family_raises(self, db):
        """Patient already in an active family must raise ALREADY_IN_FAMILY (409)."""
        family_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        group = _make_group(id=family_id)
        patient = _make_patient(id=patient_id)

        group_result = MagicMock()
        group_result.scalar_one_or_none.return_value = group

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient

        # Existing active membership found
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = uuid.uuid4()

        db.execute = AsyncMock(
            side_effect=[group_result, patient_result, existing_result]
        )

        service = FamilyService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.add_member(
                db=db,
                family_id=str(family_id),
                patient_id=str(patient_id),
                relationship="child",
            )

        assert exc_info.value.error == FamilyErrors.ALREADY_IN_FAMILY
        assert exc_info.value.status_code == 409


# ── remove_member ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRemoveMember:
    """Tests for FamilyService.remove_member."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    async def test_remove_member_soft_deletes(self, db):
        """Remove must set member.is_active = False (soft delete)."""
        family_id = uuid.uuid4()
        primary_pid = uuid.uuid4()
        member_pid = uuid.uuid4()

        group = _make_group(id=family_id, primary_contact_patient_id=primary_pid)
        member = _make_member(patient_id=member_pid, family_group_id=family_id, is_active=True)

        group_result = MagicMock()
        group_result.scalar_one_or_none.return_value = group

        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = member

        # _group_to_dict members query
        members_result = MagicMock()
        members_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[group_result, member_result, members_result])

        service = FamilyService()
        await service.remove_member(
            db=db,
            family_id=str(family_id),
            patient_id=str(member_pid),
        )

        assert member.is_active is False
        db.flush.assert_called()

    async def test_remove_primary_contact_raises(self, db):
        """Removing the primary contact must raise PRIMARY_CONTACT_REQUIRED (409)."""
        primary_pid = uuid.uuid4()
        family_id = uuid.uuid4()

        group = _make_group(id=family_id, primary_contact_patient_id=primary_pid)

        group_result = MagicMock()
        group_result.scalar_one_or_none.return_value = group
        db.execute = AsyncMock(return_value=group_result)

        service = FamilyService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.remove_member(
                db=db,
                family_id=str(family_id),
                patient_id=str(primary_pid),
            )

        assert exc_info.value.error == FamilyErrors.PRIMARY_CONTACT_REQUIRED
        assert exc_info.value.status_code == 409


# ── get_family_billing ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetFamilyBilling:
    """Tests for FamilyService.get_family_billing."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_family_billing_aggregation(self, db):
        """Totals must be summed correctly across all family members."""
        family_id = uuid.uuid4()
        primary_pid = uuid.uuid4()
        member_pid = uuid.uuid4()

        group = _make_group(id=family_id, primary_contact_patient_id=primary_pid)
        patient1 = _make_patient(id=primary_pid, first_name="Ana", last_name="Perez")
        patient2 = _make_patient(id=member_pid, first_name="Luis", last_name="Perez")

        # _get_group
        group_result = MagicMock()
        group_result.scalar_one_or_none.return_value = group

        # members list
        members_result = MagicMock()
        members_result.all.return_value = [(primary_pid,), (member_pid,)]

        # patient1 billing
        billing_row1 = MagicMock()
        billing_row1.total_billed = 500_000
        billing_row1.total_paid = 300_000
        billing_row1.total_balance = 200_000
        billing_result1 = MagicMock()
        billing_result1.one.return_value = billing_row1

        # patient2 billing
        billing_row2 = MagicMock()
        billing_row2.total_billed = 200_000
        billing_row2.total_paid = 200_000
        billing_row2.total_balance = 0
        billing_result2 = MagicMock()
        billing_result2.one.return_value = billing_row2

        # patient1 lookup
        p1_result = MagicMock()
        p1_result.scalar_one_or_none.return_value = patient1

        # patient2 lookup
        p2_result = MagicMock()
        p2_result.scalar_one_or_none.return_value = patient2

        db.execute = AsyncMock(
            side_effect=[
                group_result,
                members_result,
                p1_result,
                billing_result1,
                p2_result,
                billing_result2,
            ]
        )

        service = FamilyService()
        result = await service.get_family_billing(db=db, family_id=str(family_id))

        assert result["total_billed"] == 700_000
        assert result["total_paid"] == 500_000
        assert result["total_balance"] == 200_000
        assert len(result["members"]) == 2


# ── get (family not found) ────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetFamilyNotFound:
    """Tests for FamilyService.get when family does not exist."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_family_not_found_raises(self, db):
        """Non-existent family ID must raise ResourceNotFoundError."""
        not_found_result = MagicMock()
        not_found_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=not_found_result)

        service = FamilyService()
        with pytest.raises(ResourceNotFoundError):
            await service.get(db=db, family_id=str(uuid.uuid4()))
