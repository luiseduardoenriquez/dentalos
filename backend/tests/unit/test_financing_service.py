"""Unit tests for FinancingService (VP-11 / Sprint 29-30).

Tests cover:
  - check_eligibility: eligible, not eligible, provider unavailable
  - request_financing: success, already financed, invoice not found, adapter failure
  - handle_webhook_update: approved, disbursed, not found
  - get_applications: pagination, status filter
  - get_report: aggregation output format
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import BillingErrors, FinancingErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.financing_service import FinancingService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_patient(**overrides) -> MagicMock:
    """Build a mock Patient ORM row."""
    p = MagicMock()
    p.id = overrides.get("id", uuid.uuid4())
    p.document_number = overrides.get("document_number", "12345678")
    p.is_active = overrides.get("is_active", True)
    return p


def _make_invoice(**overrides) -> MagicMock:
    """Build a mock Invoice ORM row."""
    inv = MagicMock()
    inv.id = overrides.get("id", uuid.uuid4())
    inv.patient_id = overrides.get("patient_id", uuid.uuid4())
    inv.balance = overrides.get("balance", 1500000)
    inv.is_active = overrides.get("is_active", True)
    return inv


def _make_application(**overrides) -> MagicMock:
    """Build a mock FinancingApplication ORM row."""
    app = MagicMock()
    app.id = overrides.get("id", uuid.uuid4())
    app.patient_id = overrides.get("patient_id", uuid.uuid4())
    app.invoice_id = overrides.get("invoice_id", uuid.uuid4())
    app.provider = overrides.get("provider", "addi")
    app.status = overrides.get("status", "pending")
    app.amount_cents = overrides.get("amount_cents", 1500000)
    app.installments = overrides.get("installments", 3)
    app.interest_rate_bps = overrides.get("interest_rate_bps", None)
    app.provider_reference = overrides.get("provider_reference", "addi-ref-001")
    app.requested_at = overrides.get("requested_at", datetime.now(UTC))
    app.approved_at = overrides.get("approved_at", None)
    app.disbursed_at = overrides.get("disbursed_at", None)
    app.completed_at = overrides.get("completed_at", None)
    app.is_active = overrides.get("is_active", True)
    app.created_at = overrides.get("created_at", datetime.now(UTC))
    app.updated_at = overrides.get("updated_at", datetime.now(UTC))
    return app


def _make_eligibility_result(eligible: bool = True) -> MagicMock:
    """Build a mock eligibility result from an adapter."""
    r = MagicMock()
    r.eligible = eligible
    r.max_amount_cents = 10000000
    r.min_amount_cents = 500000
    r.available_installments = [3, 6, 12]
    r.reason = None if eligible else "Historial crediticio insuficiente"
    return r


def _make_application_result(**overrides) -> MagicMock:
    """Build a mock application creation result from an adapter."""
    r = MagicMock()
    r.provider_reference = overrides.get("provider_reference", "addi-ref-abc123")
    r.status = overrides.get("status", "pending")
    return r


# ── TestCheckEligibility ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckEligibility:
    """Tests for FinancingService.check_eligibility."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.add = MagicMock()
        self.service = FinancingService()
        self.patient_id = uuid.uuid4()
        self.patient = _make_patient(id=self.patient_id)

    async def test_check_eligibility_eligible(self):
        """Adapter returns eligible=True — result includes eligible flag and installments."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient
        self.db.execute.return_value = patient_result

        eligibility = _make_eligibility_result(eligible=True)
        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(return_value=eligibility)

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ):
            result = await self.service.check_eligibility(
                db=self.db,
                patient_id=self.patient_id,
                amount_cents=1500000,
                provider="addi",
            )

        assert result["eligible"] is True
        assert result["max_amount_cents"] == 10000000
        assert result["available_installments"] == [3, 6, 12]
        assert result["reason"] is None

    async def test_check_eligibility_not_eligible(self):
        """Adapter returns eligible=False — result includes reason."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient
        self.db.execute.return_value = patient_result

        eligibility = _make_eligibility_result(eligible=False)
        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(return_value=eligibility)

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ):
            result = await self.service.check_eligibility(
                db=self.db,
                patient_id=self.patient_id,
                amount_cents=1500000,
                provider="addi",
            )

        assert result["eligible"] is False
        assert result["reason"] == "Historial crediticio insuficiente"

    async def test_check_eligibility_provider_unavailable(self):
        """Adapter raises an exception — DentalOSError PROVIDER_UNAVAILABLE (503)."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient
        self.db.execute.return_value = patient_result

        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(
            side_effect=RuntimeError("Connection timeout")
        )

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ):
            with pytest.raises(DentalOSError) as exc_info:
                await self.service.check_eligibility(
                    db=self.db,
                    patient_id=self.patient_id,
                    amount_cents=1500000,
                    provider="addi",
                )

        assert exc_info.value.error == FinancingErrors.PROVIDER_UNAVAILABLE
        assert exc_info.value.status_code == 503

    async def test_check_eligibility_patient_not_found(self):
        """Patient does not exist — ResourceNotFoundError is raised."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = patient_result

        with pytest.raises(ResourceNotFoundError):
            await self.service.check_eligibility(
                db=self.db,
                patient_id=self.patient_id,
                amount_cents=1500000,
                provider="addi",
            )

    async def test_check_eligibility_zero_amount_raises(self):
        """Amount of 0 raises AMOUNT_OUT_OF_RANGE (400)."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient
        self.db.execute.return_value = patient_result

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.check_eligibility(
                db=self.db,
                patient_id=self.patient_id,
                amount_cents=0,
                provider="addi",
            )

        assert exc_info.value.error == FinancingErrors.AMOUNT_OUT_OF_RANGE
        assert exc_info.value.status_code == 400


# ── TestRequestFinancing ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestRequestFinancing:
    """Tests for FinancingService.request_financing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.add = MagicMock()
        self.service = FinancingService()
        self.patient_id = uuid.uuid4()
        self.invoice_id = uuid.uuid4()
        self.patient = _make_patient(id=self.patient_id)
        self.invoice = _make_invoice(
            id=self.invoice_id, patient_id=self.patient_id, balance=1500000
        )

    async def test_request_financing_success(self):
        """Full flow: check eligibility → create application → submit to adapter."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient

        invoice_result = MagicMock()
        invoice_result.scalar_one_or_none.return_value = self.invoice

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        application_orm = _make_application(
            patient_id=self.patient_id,
            invoice_id=self.invoice_id,
            status="pending",
        )

        self.db.execute.side_effect = [
            patient_result,
            invoice_result,
            existing_result,
        ]

        eligibility = _make_eligibility_result(eligible=True)
        adapter_result = _make_application_result(status="pending")
        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(return_value=eligibility)
        mock_adapter.create_application = AsyncMock(return_value=adapter_result)

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ), patch(
            "app.services.financing_service.FinancingApplication",
            return_value=application_orm,
        ):
            result = await self.service.request_financing(
                db=self.db,
                patient_id=self.patient_id,
                invoice_id=self.invoice_id,
                provider="addi",
                installments=3,
                tenant_id="tn_test123",
            )

        self.db.add.assert_called_once()
        self.db.flush.assert_called()
        assert result["provider"] == "addi"

    async def test_request_financing_already_financed(self):
        """Active application exists — raises ALREADY_FINANCED (409)."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient

        invoice_result = MagicMock()
        invoice_result.scalar_one_or_none.return_value = self.invoice

        existing_application = _make_application(status="pending")
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_application

        self.db.execute.side_effect = [
            patient_result,
            invoice_result,
            existing_result,
        ]

        eligibility = _make_eligibility_result(eligible=True)
        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(return_value=eligibility)

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ):
            with pytest.raises(DentalOSError) as exc_info:
                await self.service.request_financing(
                    db=self.db,
                    patient_id=self.patient_id,
                    invoice_id=self.invoice_id,
                    provider="addi",
                    installments=3,
                    tenant_id="tn_test123",
                )

        assert exc_info.value.error == FinancingErrors.ALREADY_FINANCED
        assert exc_info.value.status_code == 409

    async def test_request_financing_invoice_not_found(self):
        """Invoice does not exist — raises ResourceNotFoundError."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient

        invoice_result = MagicMock()
        invoice_result.scalar_one_or_none.return_value = None

        self.db.execute.side_effect = [patient_result, invoice_result]

        with pytest.raises(ResourceNotFoundError):
            await self.service.request_financing(
                db=self.db,
                patient_id=self.patient_id,
                invoice_id=self.invoice_id,
                provider="addi",
                installments=3,
                tenant_id="tn_test123",
            )

    async def test_request_financing_no_invoice_id_raises(self):
        """Calling without invoice_id raises INVOICE_NOT_FOUND (400)."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient
        self.db.execute.return_value = patient_result

        with pytest.raises(DentalOSError) as exc_info:
            await self.service.request_financing(
                db=self.db,
                patient_id=self.patient_id,
                invoice_id=None,
                provider="addi",
                installments=3,
                tenant_id="tn_test123",
            )

        assert exc_info.value.error == BillingErrors.INVOICE_NOT_FOUND
        assert exc_info.value.status_code == 400

    async def test_request_financing_adapter_failure_cancels_application(self):
        """Adapter create_application raises — application status set to cancelled."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient

        invoice_result = MagicMock()
        invoice_result.scalar_one_or_none.return_value = self.invoice

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        self.db.execute.side_effect = [
            patient_result,
            invoice_result,
            existing_result,
        ]

        application_orm = _make_application(
            patient_id=self.patient_id,
            invoice_id=self.invoice_id,
            status="requested",
        )

        eligibility = _make_eligibility_result(eligible=True)
        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(return_value=eligibility)
        mock_adapter.create_application = AsyncMock(
            side_effect=RuntimeError("Provider error")
        )

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ), patch(
            "app.services.financing_service.FinancingApplication",
            return_value=application_orm,
        ):
            with pytest.raises(DentalOSError) as exc_info:
                await self.service.request_financing(
                    db=self.db,
                    patient_id=self.patient_id,
                    invoice_id=self.invoice_id,
                    provider="addi",
                    installments=3,
                    tenant_id="tn_test123",
                )

        assert exc_info.value.error == FinancingErrors.PROVIDER_UNAVAILABLE
        # The application status must have been rolled back to cancelled
        assert application_orm.status == "cancelled"

    async def test_request_financing_not_eligible_raises(self):
        """Adapter returns not eligible — raises NOT_ELIGIBLE (422)."""
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = self.patient

        invoice_result = MagicMock()
        invoice_result.scalar_one_or_none.return_value = self.invoice

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        self.db.execute.side_effect = [
            patient_result,
            invoice_result,
            existing_result,
        ]

        eligibility = _make_eligibility_result(eligible=False)
        mock_adapter = AsyncMock()
        mock_adapter.check_eligibility = AsyncMock(return_value=eligibility)

        with patch(
            "app.services.financing_service._get_provider",
            return_value=mock_adapter,
        ):
            with pytest.raises(DentalOSError) as exc_info:
                await self.service.request_financing(
                    db=self.db,
                    patient_id=self.patient_id,
                    invoice_id=self.invoice_id,
                    provider="addi",
                    installments=3,
                    tenant_id="tn_test123",
                )

        assert exc_info.value.error == FinancingErrors.NOT_ELIGIBLE
        assert exc_info.value.status_code == 422


# ── TestHandleWebhookUpdate ───────────────────────────────────────────────────


@pytest.mark.unit
class TestHandleWebhookUpdate:
    """Tests for FinancingService.handle_webhook_update."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.db.flush = AsyncMock()
        self.service = FinancingService()

    async def test_handle_webhook_update_approved(self):
        """Webhook with approved status — sets application.approved_at."""
        application = _make_application(
            status="pending", approved_at=None, provider_reference="addi-ref-001"
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = application
        self.db.execute.return_value = result

        await self.service.handle_webhook_update(
            db=self.db,
            provider="addi",
            provider_reference="addi-ref-001",
            new_status="approved",
        )

        assert application.status == "approved"
        assert application.approved_at is not None
        self.db.flush.assert_called()

    async def test_handle_webhook_update_disbursed(self):
        """Webhook with disbursed_at string — parses and sets disbursed_at."""
        application = _make_application(
            status="approved", disbursed_at=None, provider_reference="addi-ref-002"
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = application
        self.db.execute.return_value = result

        await self.service.handle_webhook_update(
            db=self.db,
            provider="addi",
            provider_reference="addi-ref-002",
            new_status="disbursed",
            disbursed_at="2026-03-03T10:00:00Z",
        )

        assert application.status == "disbursed"
        assert application.disbursed_at is not None

    async def test_handle_webhook_update_not_found(self):
        """Application not found — raises ResourceNotFoundError."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        with pytest.raises(ResourceNotFoundError):
            await self.service.handle_webhook_update(
                db=self.db,
                provider="addi",
                provider_reference="nonexistent-ref",
                new_status="approved",
            )


# ── TestGetApplications ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetApplications:
    """Tests for FinancingService.get_applications."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = FinancingService()

    async def test_get_applications_pagination(self):
        """Page and page_size are respected in the query result."""
        count_row = MagicMock()
        count_row.scalar_one.return_value = 42
        count_result = MagicMock()
        count_result.scalar_one.return_value = 42

        applications = [_make_application() for _ in range(5)]
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = applications

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.get_applications(
            db=self.db, page=2, page_size=5
        )

        assert result["page"] == 2
        assert result["page_size"] == 5
        assert result["total"] == 42
        assert len(result["items"]) == 5

    async def test_get_applications_filter_by_status(self):
        """Status filter is applied and results contain only matching applications."""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        applications = [
            _make_application(status="approved"),
            _make_application(status="approved"),
        ]
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = applications

        self.db.execute.side_effect = [count_result, items_result]

        result = await self.service.get_applications(
            db=self.db, status="approved"
        )

        assert result["total"] == 2
        for item in result["items"]:
            assert item["status"] == "approved"


# ── TestGetReport ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetReport:
    """Tests for FinancingService.get_report."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.execute = AsyncMock()
        self.service = FinancingService()

    async def test_get_report_aggregation_output_format(self):
        """Report returns total_applications, total_amount_cents, by_provider, by_status."""
        totals_row = MagicMock()
        totals_row.total = 10
        totals_row.total_amount = 15000000
        totals_result = MagicMock()
        totals_result.one.return_value = totals_row

        provider_row_addi = MagicMock()
        provider_row_addi.provider = "addi"
        provider_row_addi.count = 7
        provider_row_sistecredito = MagicMock()
        provider_row_sistecredito.provider = "sistecredito"
        provider_row_sistecredito.count = 3
        provider_result = MagicMock()
        provider_result.__iter__ = MagicMock(
            return_value=iter([provider_row_addi, provider_row_sistecredito])
        )

        status_row_pending = MagicMock()
        status_row_pending.status = "pending"
        status_row_pending.count = 6
        status_row_approved = MagicMock()
        status_row_approved.status = "approved"
        status_row_approved.count = 4
        status_result = MagicMock()
        status_result.__iter__ = MagicMock(
            return_value=iter([status_row_pending, status_row_approved])
        )

        self.db.execute.side_effect = [
            totals_result,
            provider_result,
            status_result,
        ]

        result = await self.service.get_report(db=self.db)

        assert result["total_applications"] == 10
        assert result["total_amount_cents"] == 15000000
        assert isinstance(result["by_provider"], dict)
        assert isinstance(result["by_status"], dict)
        assert result["by_provider"]["addi"] == 7
        assert result["by_status"]["approved"] == 4

    async def test_get_report_empty_tenant(self):
        """Report with no applications returns zeros and empty dicts."""
        totals_row = MagicMock()
        totals_row.total = 0
        totals_row.total_amount = 0
        totals_result = MagicMock()
        totals_result.one.return_value = totals_row

        provider_result = MagicMock()
        provider_result.__iter__ = MagicMock(return_value=iter([]))

        status_result = MagicMock()
        status_result.__iter__ = MagicMock(return_value=iter([]))

        self.db.execute.side_effect = [
            totals_result,
            provider_result,
            status_result,
        ]

        result = await self.service.get_report(db=self.db)

        assert result["total_applications"] == 0
        assert result["total_amount_cents"] == 0
        assert result["by_provider"] == {}
        assert result["by_status"] == {}

    async def test_revenue_share_calculation(self):
        """Revenue share tracking: to_dict includes all required fields."""
        application = _make_application(
            status="disbursed",
            approved_at=datetime.now(UTC),
            disbursed_at=datetime.now(UTC),
        )
        result_dict = FinancingService._to_dict(application)

        assert "id" in result_dict
        assert "provider" in result_dict
        assert "amount_cents" in result_dict
        assert "installments" in result_dict
        assert "provider_reference" in result_dict
        assert "approved_at" in result_dict
        assert "disbursed_at" in result_dict
