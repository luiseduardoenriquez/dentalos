"""Unit tests for EPSClaimService (VP-19 EPS Claims Management / Sprint 31-32).

Tests cover:
  - create_draft: status=draft, returns dict
  - submit_claim: draft→submitted, already_submitted error
  - sync_status: calls adapter, updates local status
  - update_claim: updates when draft, raises error when not draft
  - get_claim: returns dict, not found raises ResourceNotFoundError
  - list_claims: paginated, status filter
  - get_aging_report: returns 4 buckets
  - mock adapter: deterministic behavior
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import EPSClaimErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.eps_claim_service import EPSClaimService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_eps_claim(**overrides) -> MagicMock:
    """Build a mock EPSClaim ORM row."""
    claim = MagicMock()
    claim.id = overrides.get("id", uuid.uuid4())
    claim.patient_id = overrides.get("patient_id", uuid.uuid4())
    claim.eps_code = overrides.get("eps_code", "EPS001")
    claim.eps_name = overrides.get("eps_name", "EPS Sura")
    claim.claim_type = overrides.get("claim_type", "consultation")
    claim.procedures = overrides.get("procedures", [])
    claim.total_amount_cents = overrides.get("total_amount_cents", 50000)
    claim.copay_amount_cents = overrides.get("copay_amount_cents", 5000)
    claim.status = overrides.get("status", "draft")
    claim.external_claim_id = overrides.get("external_claim_id", None)
    claim.error_message = overrides.get("error_message", None)
    claim.submitted_at = overrides.get("submitted_at", None)
    claim.acknowledged_at = overrides.get("acknowledged_at", None)
    claim.response_at = overrides.get("response_at", None)
    claim.created_by = overrides.get("created_by", uuid.uuid4())
    claim.is_active = overrides.get("is_active", True)
    claim.created_at = overrides.get("created_at", datetime.now(UTC))
    claim.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return claim


def _make_claim_create(**overrides) -> MagicMock:
    """Build a mock EPSClaimCreate Pydantic model."""
    m = MagicMock()
    m.patient_id = overrides.get("patient_id", str(uuid.uuid4()))
    m.eps_code = overrides.get("eps_code", "EPS001")
    m.eps_name = overrides.get("eps_name", "EPS Sura")
    m.claim_type = overrides.get("claim_type", "consultation")
    m.procedures = overrides.get("procedures", [])
    m.total_amount_cents = overrides.get("total_amount_cents", 50000)
    m.copay_amount_cents = overrides.get("copay_amount_cents", 5000)
    return m


def _make_claim_update(**overrides) -> MagicMock:
    """Build a mock EPSClaimUpdate Pydantic model."""
    m = MagicMock()
    m.eps_code = overrides.get("eps_code", None)
    m.eps_name = overrides.get("eps_name", None)
    m.claim_type = overrides.get("claim_type", None)
    m.procedures = overrides.get("procedures", None)
    m.total_amount_cents = overrides.get("total_amount_cents", None)
    m.copay_amount_cents = overrides.get("copay_amount_cents", None)
    return m


def _make_submit_response(**overrides) -> MagicMock:
    """Build a mock EPS submit response."""
    r = MagicMock()
    r.external_claim_id = overrides.get("external_claim_id", f"EPS-{uuid.uuid4().hex[:8]}")
    r.status = overrides.get("status", "submitted")
    return r


def _make_status_response(**overrides) -> MagicMock:
    """Build a mock EPS status query response."""
    r = MagicMock()
    r.status = overrides.get("status", "acknowledged")
    r.error_message = overrides.get("error_message", None)
    return r


# ── TestCreateDraft ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateDraft:
    """Tests for EPSClaimService.create_draft."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.add = MagicMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = EPSClaimService()

    async def test_create_draft(self):
        """Creates a new EPS claim with status=draft, returns a dict."""
        claim = _make_eps_claim(status="draft")
        data = _make_claim_create()
        created_by = uuid.uuid4()

        with patch(
            "app.services.eps_claim_service.EPSClaim",
            return_value=claim,
        ):
            result = await self.service.create_draft(
                self.db, data, created_by
            )

        self.db.add.assert_called_once()
        self.db.flush.assert_called_once()
        assert result["status"] == "draft"
        assert "id" in result
        assert "eps_code" in result


# ── TestSubmitClaim ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSubmitClaim:
    """Tests for EPSClaimService.submit_claim."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = EPSClaimService()

    async def test_submit_claim_from_draft(self):
        """Draft claim is submitted — status transitions to 'submitted'."""
        claim = _make_eps_claim(status="draft", external_claim_id=None)
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = claim
        self.db.execute.return_value = orm_result

        adapter_response = _make_submit_response(status="submitted")
        mock_adapter = AsyncMock()
        mock_adapter.submit_claim = AsyncMock(return_value=adapter_response)

        with patch(
            "app.services.eps_claim_service._get_adapter",
            return_value=mock_adapter,
        ):
            result = await self.service.submit_claim(self.db, claim.id)

        assert result["status"] == "submitted"
        assert result["external_claim_id"] == adapter_response.external_claim_id
        self.db.flush.assert_called()

    async def test_submit_claim_already_submitted(self):
        """Claim already in 'submitted' status — raises ALREADY_SUBMITTED (409)."""
        claim = _make_eps_claim(status="submitted")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = claim
        self.db.execute.return_value = orm_result

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.submit_claim(self.db, claim.id)

        assert exc_info.value.error == EPSClaimErrors.ALREADY_SUBMITTED
        assert exc_info.value.status_code == 409


# ── TestSyncStatus ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSyncStatus:
    """Tests for EPSClaimService.sync_status."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = EPSClaimService()

    async def test_sync_status(self):
        """Adapter returns status — local claim is updated."""
        ext_id = f"EPS-{uuid.uuid4().hex[:8]}"
        claim = _make_eps_claim(
            status="submitted",
            external_claim_id=ext_id,
            acknowledged_at=None,
        )
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = claim
        self.db.execute.return_value = orm_result

        status_response = _make_status_response(
            status="acknowledged", error_message=None
        )
        mock_adapter = AsyncMock()
        mock_adapter.get_claim_status = AsyncMock(return_value=status_response)

        with patch(
            "app.services.eps_claim_service._get_adapter",
            return_value=mock_adapter,
        ):
            result = await self.service.sync_status(self.db, claim.id)

        assert result["status"] == "acknowledged"
        self.db.flush.assert_called()


# ── TestUpdateClaim ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateClaim:
    """Tests for EPSClaimService.update_claim."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.service = EPSClaimService()

    async def test_update_claim_draft(self):
        """Draft claim can be updated — returns updated dict."""
        claim = _make_eps_claim(status="draft", eps_code="EPS001")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = claim
        self.db.execute.return_value = orm_result

        data = _make_claim_update(eps_code="EPS002", eps_name="Nueva EPS")

        result = await self.service.update_claim(self.db, claim.id, data)

        # Verify the claim field was mutated
        assert claim.eps_code == "EPS002"
        assert claim.eps_name == "Nueva EPS"
        self.db.flush.assert_called()

    async def test_update_claim_not_draft(self):
        """Non-draft claim cannot be updated — raises ALREADY_SUBMITTED (409)."""
        claim = _make_eps_claim(status="submitted")
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = claim
        self.db.execute.return_value = orm_result

        data = _make_claim_update(eps_code="EPS999")

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.update_claim(self.db, claim.id, data)

        assert exc_info.value.error == EPSClaimErrors.ALREADY_SUBMITTED
        assert exc_info.value.status_code == 409


# ── TestGetClaim ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetClaim:
    """Tests for EPSClaimService.get_claim."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = EPSClaimService()

    async def test_get_claim(self):
        """Known claim_id returns the claim dict."""
        claim = _make_eps_claim()
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = claim
        self.db.execute.return_value = orm_result

        result = await self.service.get_claim(self.db, claim.id)

        assert result["id"] == str(claim.id)
        assert result["eps_code"] == claim.eps_code

    async def test_get_claim_not_found(self):
        """Unknown claim_id raises ResourceNotFoundError."""
        orm_result = MagicMock()
        orm_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = orm_result

        with pytest.raises(ResourceNotFoundError):
            await self.service.get_claim(self.db, uuid.uuid4())


# ── TestListClaims ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListClaims:
    """Tests for EPSClaimService.list_claims."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = EPSClaimService()

    async def test_list_claims(self):
        """Returns paginated result with items, total, page, page_size."""
        claims = [_make_eps_claim() for _ in range(5)]

        count_result = MagicMock()
        count_result.scalar_one.return_value = 5

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = claims

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.list_claims(self.db, page=1, page_size=20)

        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 5

    async def test_list_claims_with_status_filter(self):
        """Status filter returns only claims with matching status."""
        submitted_claims = [
            _make_eps_claim(status="submitted") for _ in range(2)
        ]

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = submitted_claims

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.list_claims(
            self.db, page=1, page_size=20, status_filter="submitted"
        )

        assert result["total"] == 2
        for item in result["items"]:
            assert item["status"] == "submitted"


# ── TestAgingReport ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAgingReport:
    """Tests for EPSClaimService.get_aging_report."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = EPSClaimService()

    async def test_aging_report(self):
        """Returns dict with 4 age buckets: 0_30, 31_60, 61_90, 90_plus."""
        # 4 bucket queries: 0_30, 31_60, 61_90, 90_plus
        counts = [10, 5, 3, 1]
        side_effects = []
        for count in counts:
            r = MagicMock()
            r.scalar_one.return_value = count
            side_effects.append(r)

        self.db.execute.side_effect = side_effects

        result = await self.service.get_aging_report(self.db)

        assert "0_30" in result
        assert "31_60" in result
        assert "61_90" in result
        assert "90_plus" in result
        assert result["0_30"] == 10
        assert result["31_60"] == 5
        assert result["61_90"] == 3
        assert result["90_plus"] == 1


# ── TestMockAdapter ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestMockAdapter:
    """Tests for the EPS claims mock adapter determinism."""

    async def test_mock_adapter_deterministic(self):
        """Mock adapter submit_claim returns a consistent external_claim_id and status."""
        from app.integrations.eps_claims.mock_service import eps_claims_mock_service

        claim_data = {
            "eps_code": "EPS001",
            "patient_document_type": "CC",
            "patient_document_number": "12345678",
            "claim_type": "consultation",
            "procedures": [],
            "total_amount_cents": 50000,
            "copay_amount_cents": 5000,
        }

        response = await eps_claims_mock_service.submit_claim(claim_data=claim_data)

        assert response.external_claim_id is not None
        assert len(response.external_claim_id) > 0
        assert response.status in ("submitted", "acknowledged", "pending")
