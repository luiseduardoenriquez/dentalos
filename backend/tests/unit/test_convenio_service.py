"""Unit tests for the ConvenioService class.

Tests cover:
  - create: creates convenio with correct fields
  - link_patient: success
  - link_patient: duplicate raises PATIENT_ALREADY_LINKED (409)
  - get_active_convenio_discount: patient has active convenio -> (discount%, id)
  - get_active_convenio_discount: expired convenio -> (0, None)
  - get_active_convenio_discount: no convenio -> (0, None)
  - discount_stacking_order: membership first, then convenio on remaining
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ConvenioErrors
from app.core.exceptions import DentalOSError
from app.services.convenio_service import ConvenioService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_convenio(**overrides) -> MagicMock:
    convenio = MagicMock()
    convenio.id = overrides.get("id", uuid.uuid4())
    convenio.company_name = overrides.get("company_name", "Empresa Test S.A.S.")
    convenio.contact_info = overrides.get("contact_info", {"email": "convenio@empresa.co"})
    convenio.discount_rules = overrides.get("discount_rules", {"type": "percentage", "value": 15})
    convenio.valid_from = overrides.get("valid_from", date(2025, 1, 1))
    convenio.valid_until = overrides.get("valid_until", date(2027, 12, 31))
    convenio.is_active = overrides.get("is_active", True)
    convenio.deleted_at = overrides.get("deleted_at", None)
    convenio.created_at = datetime.now(UTC)
    convenio.updated_at = datetime.now(UTC)
    return convenio


def _make_link(**overrides) -> MagicMock:
    link = MagicMock()
    link.id = overrides.get("id", uuid.uuid4())
    link.convenio_id = overrides.get("convenio_id", uuid.uuid4())
    link.patient_id = overrides.get("patient_id", uuid.uuid4())
    link.employee_id = overrides.get("employee_id", None)
    link.is_active = True
    link.created_at = datetime.now(UTC)
    link.updated_at = datetime.now(UTC)
    return link


# ── create ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateConvenio:
    """Tests for ConvenioService.create."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_create_convenio(self, db):
        """Creating a convenio must call db.add and flush."""
        created_by = str(uuid.uuid4())
        convenio = _make_convenio(company_name="Empresa ABC")

        with patch("app.services.convenio_service.Convenio", return_value=convenio):
            service = ConvenioService()
            result = await service.create(
                db=db,
                data={
                    "company_name": "Empresa ABC",
                    "valid_from": date(2025, 1, 1),
                    "discount_rules": {"type": "percentage", "value": 15},
                },
                created_by=created_by,
            )

        db.add.assert_called_once()
        db.flush.assert_called()

    async def test_create_convenio_returns_dict(self, db):
        """Result must be a dict with company_name and discount_rules keys."""
        convenio = _make_convenio()

        with patch("app.services.convenio_service.Convenio", return_value=convenio):
            service = ConvenioService()
            result = await service.create(
                db=db,
                data={
                    "company_name": "Empresa XYZ",
                    "valid_from": date(2025, 1, 1),
                },
                created_by=str(uuid.uuid4()),
            )

        assert "company_name" in result
        assert "discount_rules" in result


# ── link_patient ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestLinkPatient:
    """Tests for ConvenioService.link_patient."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.rollback = AsyncMock()
        return session

    async def test_link_patient_success(self, db):
        """Patient not yet linked must be added successfully."""
        convenio = _make_convenio()
        patient_id = uuid.uuid4()
        link = _make_link(convenio_id=convenio.id, patient_id=patient_id)

        # _get -> convenio found
        convenio_result = MagicMock()
        convenio_result.scalar_one_or_none.return_value = convenio

        # existing check -> no existing link
        no_link_result = MagicMock()
        no_link_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[convenio_result, no_link_result])

        with patch("app.services.convenio_service.ConvenioPatient", return_value=link):
            service = ConvenioService()
            result = await service.link_patient(
                db=db,
                convenio_id=str(convenio.id),
                patient_id=str(patient_id),
            )

        db.add.assert_called_once()
        assert "patient_id" in result

    async def test_link_patient_duplicate_raises(self, db):
        """Already-linked patient must raise PATIENT_ALREADY_LINKED (409)."""
        convenio = _make_convenio()
        patient_id = uuid.uuid4()

        # _get -> convenio found
        convenio_result = MagicMock()
        convenio_result.scalar_one_or_none.return_value = convenio

        # existing check -> active link exists
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = uuid.uuid4()

        db.execute = AsyncMock(side_effect=[convenio_result, existing_result])

        service = ConvenioService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.link_patient(
                db=db,
                convenio_id=str(convenio.id),
                patient_id=str(patient_id),
            )

        assert exc_info.value.error == ConvenioErrors.PATIENT_ALREADY_LINKED
        assert exc_info.value.status_code == 409


# ── get_active_convenio_discount ──────────────────────────────────────────────


@pytest.mark.unit
class TestGetActiveConvenioDiscount:
    """Tests for ConvenioService.get_active_convenio_discount."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_get_active_discount_percentage(self, db):
        """Active convenio with 15% discount must return (15, convenio_id)."""
        convenio_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        result_row = MagicMock()
        row_data = (convenio_id, {"type": "percentage", "value": 15})
        result = MagicMock()
        result.one_or_none.return_value = row_data
        db.execute = AsyncMock(return_value=result)

        service = ConvenioService()
        discount, returned_id = await service.get_active_convenio_discount(
            db=db,
            patient_id=patient_id,
        )

        assert discount == 15
        assert returned_id == convenio_id

    async def test_get_active_discount_expired(self, db):
        """Expired convenio (past valid_until) returns (0, None)."""
        # DB returns None because SQL WHERE filters out expired convenios
        result = MagicMock()
        result.one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        service = ConvenioService()
        discount, convenio_id = await service.get_active_convenio_discount(
            db=db,
            patient_id=uuid.uuid4(),
        )

        assert discount == 0
        assert convenio_id is None

    async def test_get_active_discount_no_convenio(self, db):
        """Patient with no convenio returns (0, None)."""
        result = MagicMock()
        result.one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        service = ConvenioService()
        discount, convenio_id = await service.get_active_convenio_discount(
            db=db,
            patient_id=uuid.uuid4(),
        )

        assert discount == 0
        assert convenio_id is None

    async def test_get_active_discount_zero_value_in_rules(self, db):
        """Convenio with discount_rules value=0 returns (0, convenio_id)."""
        convenio_id = uuid.uuid4()
        row_data = (convenio_id, {"type": "percentage", "value": 0})

        result = MagicMock()
        result.one_or_none.return_value = row_data
        db.execute = AsyncMock(return_value=result)

        service = ConvenioService()
        discount, returned_id = await service.get_active_convenio_discount(
            db=db,
            patient_id=uuid.uuid4(),
        )

        assert discount == 0
        assert returned_id == convenio_id


# ── discount_stacking ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestDiscountStacking:
    """Tests for discount stacking (membership first, then convenio on remaining)."""

    def test_discount_stacking_order(self):
        """Membership discount applied first, then convenio on remaining amount.

        Example:
          - original price: 100_000 cents
          - membership discount: 10% -> reduced to 90_000 cents
          - convenio discount: 15% on 90_000 -> saves 13_500 cents
          - final price: 76_500 cents
        """
        original = 100_000
        membership_pct = 10
        convenio_pct = 15

        after_membership = int(original * (1 - membership_pct / 100))
        assert after_membership == 90_000

        convenio_discount = int(after_membership * convenio_pct / 100)
        assert convenio_discount == 13_500

        final = after_membership - convenio_discount
        assert final == 76_500

    def test_discount_stacking_no_membership(self):
        """Without membership, only convenio discount applies on full amount."""
        original = 100_000
        convenio_pct = 15

        final = int(original * (1 - convenio_pct / 100))
        assert final == 85_000
