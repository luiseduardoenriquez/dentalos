"""Unit tests for the PaymentQRService class.

Tests cover:
  - generate_payment_qr (nequi): invoice exists → QR generated
  - generate_payment_qr (daviplata): invoice exists → QR generated
  - generate_payment_qr: invoice not found → 404 ResourceNotFoundError
  - reconcile_webhook_payment (success): creates payment record, returns True
  - reconcile_webhook_payment (duplicate): idempotent, returns False without
    calling payment_service again

All DB calls use AsyncMock. Redis helpers (get_cached / set_cached) are
patched via unittest.mock.patch. All amounts are in COP cents (integers).
PHI never appears in assertions.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BillingError, ResourceNotFoundError
from app.services.payment_qr_service import PaymentQRService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_invoice(**overrides) -> MagicMock:
    """Build a minimal Invoice-like mock."""
    inv = MagicMock()
    inv.id = overrides.get("id", uuid.uuid4())
    inv.patient_id = overrides.get("patient_id", uuid.uuid4())
    inv.invoice_number = overrides.get("invoice_number", "INV-0001")
    inv.status = overrides.get("status", "open")
    inv.balance = overrides.get("balance", 150_000)  # 150 000 COP cents
    inv.is_active = True
    return inv


def _make_qr_response(payment_id: str) -> MagicMock:
    """Build a mock QR response from a provider adapter."""
    qr = MagicMock()
    qr.payment_id = payment_id
    qr.qr_code_url = f"https://mock.provider.local/qr/{payment_id}"
    qr.expires_at = datetime.now(UTC) + timedelta(minutes=15)
    return qr


# ── generate_payment_qr — Nequi ───────────────────────────────────────────────


@pytest.mark.unit
class TestGeneratePaymentQrNequi:
    async def test_generate_payment_qr_nequi_returns_qr_dict(self):
        """When invoice exists and provider is 'nequi', return a QR response dict."""
        service = PaymentQRService()
        db = AsyncMock()
        invoice = _make_invoice()
        tenant_id = str(uuid.uuid4())

        # DB returns the invoice
        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice
        db.execute = AsyncMock(return_value=inv_result)

        mock_payment_id = "mock_abc1234567890abc"
        mock_adapter = AsyncMock()
        mock_adapter.generate_qr_payment = AsyncMock(
            return_value=_make_qr_response(mock_payment_id)
        )

        with (
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ) as mock_set_cached,
            patch.object(service, "_get_adapter", return_value=mock_adapter),
            patch(
                "app.services.payment_qr_service.qr_code_service"
            ) as mock_qr_svc,
        ):
            mock_qr_svc.generate_base64.return_value = "iVBORw0KGgoAAAA=="

            result = await service.generate_payment_qr(
                db=db,
                invoice_id=invoice.id,
                provider="nequi",
                tenant_id=tenant_id,
            )

        assert result["provider"] == "nequi"
        assert result["payment_id"] == mock_payment_id
        assert result["amount_cents"] == invoice.balance
        assert result["qr_code_base64"] == "iVBORw0KGgoAAAA=="
        assert "invoice_id" in result

    async def test_generate_payment_qr_nequi_caches_mapping(self):
        """set_cached must be called once to store the payment → invoice mapping."""
        service = PaymentQRService()
        db = AsyncMock()
        invoice = _make_invoice()
        tenant_id = str(uuid.uuid4())

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice
        db.execute = AsyncMock(return_value=inv_result)

        mock_adapter = AsyncMock()
        mock_adapter.generate_qr_payment = AsyncMock(
            return_value=_make_qr_response("mock_xyz999")
        )

        with (
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ) as mock_set_cached,
            patch.object(service, "_get_adapter", return_value=mock_adapter),
            patch("app.services.payment_qr_service.qr_code_service") as mock_qr_svc,
        ):
            mock_qr_svc.generate_base64.return_value = "base64data"

            await service.generate_payment_qr(
                db=db,
                invoice_id=invoice.id,
                provider="nequi",
                tenant_id=tenant_id,
            )

        mock_set_cached.assert_called_once()


@pytest.mark.unit
class TestGeneratePaymentQrDaviplata:
    async def test_generate_payment_qr_daviplata_returns_qr_dict(self):
        """When invoice exists and provider is 'daviplata', return a QR response dict."""
        service = PaymentQRService()
        db = AsyncMock()
        invoice = _make_invoice(balance=80_000)
        tenant_id = str(uuid.uuid4())

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice
        db.execute = AsyncMock(return_value=inv_result)

        mock_payment_id = "mock_daviplata1234"
        mock_adapter = AsyncMock()
        mock_adapter.generate_qr_payment = AsyncMock(
            return_value=_make_qr_response(mock_payment_id)
        )

        with (
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ),
            patch.object(service, "_get_adapter", return_value=mock_adapter),
            patch("app.services.payment_qr_service.qr_code_service") as mock_qr_svc,
        ):
            mock_qr_svc.generate_base64.return_value = "base64daviplata=="

            result = await service.generate_payment_qr(
                db=db,
                invoice_id=invoice.id,
                provider="daviplata",
                tenant_id=tenant_id,
            )

        assert result["provider"] == "daviplata"
        assert result["amount_cents"] == 80_000

    async def test_generate_payment_qr_daviplata_calls_adapter(self):
        """The Daviplata adapter's generate_qr_payment must be invoked once."""
        service = PaymentQRService()
        db = AsyncMock()
        invoice = _make_invoice()
        tenant_id = str(uuid.uuid4())

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice
        db.execute = AsyncMock(return_value=inv_result)

        mock_adapter = AsyncMock()
        mock_adapter.generate_qr_payment = AsyncMock(
            return_value=_make_qr_response("mock_dp_0000")
        )

        with (
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ),
            patch.object(service, "_get_adapter", return_value=mock_adapter),
            patch("app.services.payment_qr_service.qr_code_service") as mock_qr_svc,
        ):
            mock_qr_svc.generate_base64.return_value = "base64=="

            await service.generate_payment_qr(
                db=db,
                invoice_id=invoice.id,
                provider="daviplata",
                tenant_id=tenant_id,
            )

        mock_adapter.generate_qr_payment.assert_called_once()


@pytest.mark.unit
class TestGeneratePaymentQrInvoiceNotFound:
    async def test_invoice_not_found_raises_resource_not_found(self):
        """When the invoice does not exist, a ResourceNotFoundError must be raised."""
        service = PaymentQRService()
        db = AsyncMock()

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=inv_result)

        with pytest.raises(ResourceNotFoundError):
            await service.generate_payment_qr(
                db=db,
                invoice_id=uuid.uuid4(),
                provider="nequi",
                tenant_id=str(uuid.uuid4()),
            )

    async def test_invoice_not_found_has_404_status(self):
        """ResourceNotFoundError must carry HTTP 404."""
        service = PaymentQRService()
        db = AsyncMock()

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=inv_result)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.generate_payment_qr(
                db=db,
                invoice_id=uuid.uuid4(),
                provider="nequi",
                tenant_id=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 404

    async def test_already_paid_invoice_raises_billing_error(self):
        """An already paid invoice must raise BillingError (409)."""
        service = PaymentQRService()
        db = AsyncMock()
        invoice = _make_invoice(status="paid", balance=0)

        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = invoice
        db.execute = AsyncMock(return_value=inv_result)

        with pytest.raises(BillingError) as exc_info:
            await service.generate_payment_qr(
                db=db,
                invoice_id=invoice.id,
                provider="nequi",
                tenant_id=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 409


# ── reconcile_webhook_payment ─────────────────────────────────────────────────


@pytest.mark.unit
class TestReconcileWebhookPaymentSuccess:
    async def test_reconcile_success_returns_true(self):
        """A new (not-yet-seen) webhook should be reconciled and return True."""
        service = PaymentQRService()
        db = AsyncMock()
        tenant_id = str(uuid.uuid4())
        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        payment_id = "mock_new_payment_001"

        # Redis: dedup key not found (None = not processed before)
        # DB: invoice found with patient_id
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        with (
            patch(
                "app.services.payment_qr_service.get_cached",
                new_callable=AsyncMock,
                return_value=None,  # no existing dedup key
            ),
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ),
            patch(
                "app.services.payment_qr_service.payment_service"
            ) as mock_payment_svc,
        ):
            mock_payment_svc.record_payment = AsyncMock()

            result = await service.reconcile_webhook_payment(
                db=db,
                tenant_id=tenant_id,
                provider="nequi",
                payment_id=payment_id,
                amount_cents=150_000,
                reference=f"tenant_short:{invoice_id}",
            )

        assert result is True

    async def test_reconcile_success_calls_record_payment(self):
        """payment_service.record_payment must be called exactly once."""
        service = PaymentQRService()
        db = AsyncMock()
        tenant_id = str(uuid.uuid4())
        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        with (
            patch(
                "app.services.payment_qr_service.get_cached",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ),
            patch(
                "app.services.payment_qr_service.payment_service"
            ) as mock_payment_svc,
        ):
            mock_payment_svc.record_payment = AsyncMock()

            await service.reconcile_webhook_payment(
                db=db,
                tenant_id=tenant_id,
                provider="daviplata",
                payment_id="mock_dp_reconcile",
                amount_cents=80_000,
                reference=f"t1:{invoice_id}",
            )

        mock_payment_svc.record_payment.assert_called_once()

    async def test_reconcile_success_sets_dedup_key(self):
        """After successful reconciliation, set_cached must mark the dedup key."""
        service = PaymentQRService()
        db = AsyncMock()
        tenant_id = str(uuid.uuid4())
        invoice_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=patient_result)

        with (
            patch(
                "app.services.payment_qr_service.get_cached",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.payment_qr_service.set_cached", new_callable=AsyncMock
            ) as mock_set_cached,
            patch(
                "app.services.payment_qr_service.payment_service"
            ) as mock_payment_svc,
        ):
            mock_payment_svc.record_payment = AsyncMock()

            await service.reconcile_webhook_payment(
                db=db,
                tenant_id=tenant_id,
                provider="nequi",
                payment_id="mock_new_001",
                amount_cents=100_000,
                reference=f"t2:{invoice_id}",
            )

        mock_set_cached.assert_called_once()


@pytest.mark.unit
class TestReconcileWebhookPaymentDuplicate:
    async def test_duplicate_webhook_returns_false(self):
        """A webhook with an already-seen dedup key must be skipped (returns False)."""
        service = PaymentQRService()
        db = AsyncMock()

        with (
            patch(
                "app.services.payment_qr_service.get_cached",
                new_callable=AsyncMock,
                return_value="processed",  # dedup key already present
            ),
            patch(
                "app.services.payment_qr_service.payment_service"
            ) as mock_payment_svc,
        ):
            mock_payment_svc.record_payment = AsyncMock()

            result = await service.reconcile_webhook_payment(
                db=db,
                tenant_id=str(uuid.uuid4()),
                provider="nequi",
                payment_id="mock_already_seen",
                amount_cents=100_000,
                reference=f"t1:{uuid.uuid4()}",
            )

        assert result is False

    async def test_duplicate_webhook_does_not_call_record_payment(self):
        """payment_service.record_payment must NOT be called for duplicates."""
        service = PaymentQRService()
        db = AsyncMock()

        with (
            patch(
                "app.services.payment_qr_service.get_cached",
                new_callable=AsyncMock,
                return_value="processed",
            ),
            patch(
                "app.services.payment_qr_service.payment_service"
            ) as mock_payment_svc,
        ):
            mock_payment_svc.record_payment = AsyncMock()

            await service.reconcile_webhook_payment(
                db=db,
                tenant_id=str(uuid.uuid4()),
                provider="daviplata",
                payment_id="mock_seen_twice",
                amount_cents=50_000,
                reference=f"t1:{uuid.uuid4()}",
            )

        mock_payment_svc.record_payment.assert_not_called()

    async def test_duplicate_webhook_does_not_hit_database(self):
        """DB execute must NOT be called when the dedup key is already present."""
        service = PaymentQRService()
        db = AsyncMock()

        with patch(
            "app.services.payment_qr_service.get_cached",
            new_callable=AsyncMock,
            return_value="processed",
        ):
            with patch("app.services.payment_qr_service.payment_service"):
                await service.reconcile_webhook_payment(
                    db=db,
                    tenant_id=str(uuid.uuid4()),
                    provider="nequi",
                    payment_id="mock_dup_db_check",
                    amount_cents=75_000,
                    reference=f"t1:{uuid.uuid4()}",
                )

        db.execute.assert_not_called()
