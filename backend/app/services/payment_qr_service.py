"""QR payment service -- generate payment QRs and reconcile webhook payments.

Security invariants:
  - PHI is NEVER logged.
  - Webhook reconciliation is IDEMPOTENT (Redis dedup key per payment_id).
  - All monetary values in COP cents.
  - Payment recording delegates to existing payment_service.

Sprint 23-24 / VP-05: Nequi/Daviplata QR Payments.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, set_cached
from app.core.error_codes import BillingErrors
from app.core.exceptions import BillingError, ResourceNotFoundError
from app.models.tenant.invoice import Invoice
from app.services.qr_code_service import qr_code_service

logger = logging.getLogger("dentalos.payment_qr")

# Idempotency dedup TTL -- 24 hours covers any reasonable webhook retry window
_DEDUP_TTL_SECONDS = 86_400

# QR code + cached mapping TTL -- 15 minutes matches provider expiry
_QR_CACHE_TTL_SECONDS = 900


class PaymentQRService:
    """Generate QR codes for mobile wallet payments and reconcile webhooks.

    This service orchestrates two flows:

    1. **QR generation** (called from the billing router):
       Validates the invoice, calls the appropriate provider adapter
       (Nequi or Daviplata), generates a scannable QR image, and caches
       the payment_id -> invoice_id mapping for later reconciliation.

    2. **Webhook reconciliation** (called from webhook routers):
       Uses Redis dedup keys to guarantee idempotency, extracts the invoice
       reference from the payment, and delegates to payment_service to
       record the payment and update invoice balance.
    """

    # -- QR Generation ---------------------------------------------------------

    async def generate_payment_qr(
        self,
        *,
        db: AsyncSession,
        invoice_id: uuid.UUID,
        provider: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Generate a QR code for paying an invoice via Nequi or Daviplata.

        Args:
            db: Tenant-scoped database session.
            invoice_id: The invoice to generate payment for.
            provider: ``"nequi"`` or ``"daviplata"``.
            tenant_id: Current tenant ID for cache keys.

        Returns:
            Dict matching PaymentQRResponse schema fields.

        Raises:
            ResourceNotFoundError: If invoice not found.
            BillingError: If invoice is not payable (already paid/cancelled).
        """
        # Fetch invoice
        result = await db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.is_active.is_(True),
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="Invoice",
            )

        if invoice.status in ("paid", "cancelled"):
            raise BillingError(
                error=BillingErrors.INVOICE_NOT_PAYABLE,
                message="Invoice is not payable.",
                status_code=409,
            )

        amount_cents = invoice.balance
        if amount_cents <= 0:
            raise BillingError(
                error=BillingErrors.INVOICE_ALREADY_PAID,
                message="Invoice has no outstanding balance.",
                status_code=409,
            )

        # Build reference: "{tenant_short}:{invoice_id}"
        tenant_short = tenant_id[:12] if len(tenant_id) > 12 else tenant_id
        reference = f"{tenant_short}:{invoice_id}"
        description = f"DentalOS Invoice {invoice.invoice_number}"

        # Call the appropriate provider adapter
        adapter = self._get_adapter(provider)
        qr_response = await adapter.generate_qr_payment(
            amount_cents=amount_cents,
            reference=reference,
            description=description,
        )

        # Generate QR code image from the provider URL
        qr_base64 = qr_code_service.generate_base64(data=qr_response.qr_code_url)

        # Determine expiry -- adapters always return expires_at
        expires_at = qr_response.expires_at

        # Cache payment_id -> invoice_id mapping for webhook reconciliation
        cache_key = (
            f"dentalos:{tenant_id}:payment_qr:{provider}:{qr_response.payment_id}"
        )
        mapping_value = {
            "invoice_id": str(invoice_id),
            "patient_id": str(invoice.patient_id),
            "amount_cents": amount_cents,
        }
        await set_cached(cache_key, mapping_value, ttl_seconds=_QR_CACHE_TTL_SECONDS)

        logger.info(
            "QR payment generated: provider=%s payment_id=%s invoice=%s",
            provider,
            qr_response.payment_id[:8],
            str(invoice_id)[:8],
        )

        return {
            "qr_code_base64": qr_base64,
            "payment_id": qr_response.payment_id,
            "provider": provider,
            "amount_cents": amount_cents,
            "expires_at": expires_at,
            "invoice_id": str(invoice_id),
        }

    # -- Webhook Reconciliation ------------------------------------------------

    async def reconcile_webhook_payment(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        provider: str,
        payment_id: str,
        amount_cents: int,
        reference: str,
    ) -> bool:
        """Reconcile a webhook payment notification with an invoice.

        Idempotent: uses a Redis dedup key (24h TTL) to prevent duplicate
        payment recording. Returns True if the payment was newly recorded,
        False if it was a duplicate.

        Args:
            db: Tenant-scoped database session.
            tenant_id: Current tenant ID.
            provider: ``"nequi"`` or ``"daviplata"``.
            payment_id: External payment ID from provider.
            amount_cents: Payment amount in COP cents.
            reference: Payment reference (format: ``{tenant_short}:{invoice_id}``).

        Returns:
            True if payment recorded, False if duplicate.

        Raises:
            Exception: Re-raises any payment_service errors after logging.
        """
        # Idempotency check -- if key exists, this webhook was already processed
        dedup_key = f"dentalos:{tenant_id}:webhook_dedup:{provider}:{payment_id}"
        existing = await get_cached(dedup_key)
        if existing:
            logger.info(
                "Duplicate webhook ignored: provider=%s payment_id=%s",
                provider,
                payment_id[:8],
            )
            return False

        # Extract invoice_id from reference
        invoice_id_str = self._extract_invoice_id(reference)
        if not invoice_id_str:
            logger.warning(
                "Cannot extract invoice_id from reference: provider=%s payment_id=%s",
                provider,
                payment_id[:8],
            )
            return False

        try:
            invoice_uuid = uuid.UUID(invoice_id_str)
        except ValueError:
            logger.warning(
                "Invalid invoice_id in reference: provider=%s payment_id=%s",
                provider,
                payment_id[:8],
            )
            return False

        # Look up patient_id from the invoice (needed by payment_service)
        inv_result = await db.execute(
            select(Invoice.patient_id).where(
                Invoice.id == invoice_uuid,
                Invoice.is_active.is_(True),
            )
        )
        patient_id = inv_result.scalar_one_or_none()
        if patient_id is None:
            logger.warning(
                "Invoice not found for webhook: provider=%s payment_id=%s",
                provider,
                payment_id[:8],
            )
            return False

        # Record payment via existing payment service
        from app.services.payment_service import payment_service

        try:
            await payment_service.record_payment(
                db=db,
                patient_id=str(patient_id),
                invoice_id=str(invoice_uuid),
                amount=amount_cents,
                payment_method=provider,
                received_by="00000000-0000-0000-0000-000000000000",  # System user
                reference_number=payment_id,
                notes=f"Auto-reconciled from {provider} webhook",
                tenant_id=tenant_id,
            )
        except Exception:
            logger.exception(
                "Failed to record webhook payment: provider=%s payment_id=%s",
                provider,
                payment_id[:8],
            )
            raise

        # Mark as processed AFTER successful recording (dedup)
        await set_cached(dedup_key, "processed", ttl_seconds=_DEDUP_TTL_SECONDS)

        logger.info(
            "Webhook payment reconciled: provider=%s payment_id=%s",
            provider,
            payment_id[:8],
        )
        return True

    # -- Helpers ---------------------------------------------------------------

    def _extract_invoice_id(self, reference: str) -> str | None:
        """Extract invoice_id from payment reference string.

        Reference format: ``"{tenant_short}:{invoice_id}"``

        Returns:
            The invoice_id portion, or None if the format is invalid.
        """
        if ":" not in reference:
            return None
        parts = reference.split(":", 1)
        return parts[1] if len(parts) == 2 and parts[1] else None

    def _get_adapter(self, provider: str):
        """Get the appropriate payment adapter for the provider.

        Selects the production adapter if configured (API keys present),
        otherwise falls back to the mock adapter for development.

        Args:
            provider: ``"nequi"`` or ``"daviplata"``.

        Returns:
            An adapter instance implementing ``generate_qr_payment``.

        Raises:
            BillingError: If the provider is not supported.
        """
        if provider == "nequi":
            from app.integrations.nequi.mock_service import nequi_service_mock
            from app.integrations.nequi.service import nequi_service

            return nequi_service if nequi_service.is_configured() else nequi_service_mock
        elif provider == "daviplata":
            from app.integrations.daviplata.mock_service import daviplata_service_mock
            from app.integrations.daviplata.service import daviplata_service

            return (
                daviplata_service
                if daviplata_service.is_configured()
                else daviplata_service_mock
            )
        else:
            raise BillingError(
                error=BillingErrors.PAYMENT_METHOD_NOT_SUPPORTED,
                message=f"Unsupported provider: {provider}",
                status_code=400,
            )


# Module-level singleton
payment_qr_service = PaymentQRService()
