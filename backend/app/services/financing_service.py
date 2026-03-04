"""Patient financing service -- VP-11 / Sprint 29-30.

Orchestrates eligibility checks, application submissions, status updates,
and reporting for BNPL patient financing through Addi and Sistecrédito.

Security invariants:
  - PHI is NEVER logged (patient names, document numbers in full).
  - All monetary values in COP cents.
  - Duplicate financing is prevented (one active application per invoice).
  - Provider adapters are selected by name at runtime (no hardcoded imports).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.error_codes import BillingErrors, FinancingErrors, PatientErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.integrations.financing.base import FinancingProviderBase
from app.models.tenant.financing import FinancingApplication
from app.models.tenant.invoice import Invoice
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.financing")


# -- Provider factory ---------------------------------------------------------


def _get_provider(provider_name: str) -> FinancingProviderBase:
    """Return the appropriate financing provider adapter.

    Selects the mock service when the provider is not configured (no API key),
    otherwise returns the production service.

    Args:
        provider_name: One of: addi, sistecredito, mercadopago.

    Returns:
        A FinancingProviderBase implementation.

    Raises:
        DentalOSError: If the provider name is not recognized.
    """
    if provider_name == "addi":
        from app.integrations.financing.addi_service import addi_service
        from app.integrations.financing.addi_mock_service import addi_mock_service

        return addi_service if addi_service.is_configured() else addi_mock_service

    if provider_name == "sistecredito":
        from app.integrations.financing.sistecredito_service import sistecredito_service
        from app.integrations.financing.sistecredito_mock_service import sistecredito_mock_service

        return (
            sistecredito_service
            if sistecredito_service.is_configured()
            else sistecredito_mock_service
        )

    raise DentalOSError(
        error=FinancingErrors.PROVIDER_UNAVAILABLE,
        message=f"Proveedor de financiamiento no soportado: {provider_name}",
        status_code=400,
    )


# -- Service class ------------------------------------------------------------


class FinancingService:
    """Stateless patient financing service.

    All methods receive the AsyncSession from the caller (injected via
    FastAPI Depends). No internal state is held between calls.
    """

    # -- Eligibility check ----------------------------------------------------

    async def check_eligibility(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        amount_cents: int,
        provider: str,
    ) -> dict[str, Any]:
        """Check if a patient is eligible for financing a given amount.

        Looks up the patient's document number, then calls the provider adapter
        to perform the eligibility check.

        Args:
            db: Tenant-scoped AsyncSession.
            patient_id: UUID of the patient to check.
            amount_cents: Amount to finance in COP cents.
            provider: Provider name (addi, sistecredito, mercadopago).

        Returns:
            dict with eligibility result fields.

        Raises:
            ResourceNotFoundError: If the patient does not exist.
            DentalOSError: If the provider is unavailable or amount out of range.
        """
        # Resolve patient
        patient = await self._get_patient_or_raise(db, patient_id)

        if amount_cents <= 0:
            raise DentalOSError(
                error=FinancingErrors.AMOUNT_OUT_OF_RANGE,
                message="El monto debe ser mayor a cero.",
                status_code=400,
            )

        adapter = _get_provider(provider)

        try:
            result = await adapter.check_eligibility(
                patient_document=patient.document_number,
                amount_cents=amount_cents,
            )
        except Exception as exc:
            logger.error(
                "Financing eligibility check failed: provider=%s patient=%s... error=%s",
                provider,
                str(patient_id)[:8],
                str(exc),
            )
            raise DentalOSError(
                error=FinancingErrors.PROVIDER_UNAVAILABLE,
                message="El proveedor de financiamiento no está disponible.",
                status_code=503,
            ) from exc

        return {
            "eligible": result.eligible,
            "max_amount_cents": result.max_amount_cents,
            "min_amount_cents": result.min_amount_cents,
            "available_installments": result.available_installments,
            "reason": result.reason,
        }

    # -- Request financing ----------------------------------------------------

    async def request_financing(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        invoice_id: uuid.UUID | None,
        provider: str,
        installments: int,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Create and submit a financing application for a patient/invoice.

        Validates that the invoice is not already financed, checks eligibility,
        creates the local application record, then submits to the provider.

        Args:
            db: Tenant-scoped AsyncSession.
            patient_id: UUID of the patient requesting financing.
            invoice_id: UUID of the invoice to finance (optional).
            provider: Provider name (addi, sistecredito, mercadopago).
            installments: Number of monthly installments.
            tenant_id: Current tenant identifier (for webhook callbacks).

        Returns:
            dict representing the created FinancingApplication.

        Raises:
            ResourceNotFoundError: If patient or invoice is not found.
            DentalOSError: If already financed, not eligible, or provider fails.
        """
        # Resolve patient and document number
        patient = await self._get_patient_or_raise(db, patient_id)

        # Resolve and validate the invoice
        invoice: Invoice | None = None
        amount_cents: int

        if invoice_id is not None:
            invoice = await self._get_invoice_or_raise(db, invoice_id, patient_id)
            amount_cents = invoice.balance  # Finance the outstanding balance

            # Guard against double financing on the same invoice
            existing = await db.execute(
                select(FinancingApplication).where(
                    FinancingApplication.invoice_id == invoice_id,
                    FinancingApplication.status.not_in(["rejected", "cancelled"]),
                    FinancingApplication.is_active.is_(True),
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DentalOSError(
                    error=FinancingErrors.ALREADY_FINANCED,
                    message="Esta factura ya tiene una solicitud de financiamiento activa.",
                    status_code=409,
                )
        else:
            raise DentalOSError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                message="Se requiere una factura para solicitar financiamiento.",
                status_code=400,
            )

        if amount_cents <= 0:
            raise DentalOSError(
                error=FinancingErrors.AMOUNT_OUT_OF_RANGE,
                message="La factura no tiene saldo pendiente para financiar.",
                status_code=400,
            )

        adapter = _get_provider(provider)

        # Check eligibility before creating the application record
        try:
            eligibility = await adapter.check_eligibility(
                patient_document=patient.document_number,
                amount_cents=amount_cents,
            )
        except Exception as exc:
            logger.error(
                "Financing eligibility failed during request: provider=%s patient=%s...",
                provider,
                str(patient_id)[:8],
            )
            raise DentalOSError(
                error=FinancingErrors.PROVIDER_UNAVAILABLE,
                message="El proveedor de financiamiento no está disponible.",
                status_code=503,
            ) from exc

        if not eligibility.eligible:
            raise DentalOSError(
                error=FinancingErrors.NOT_ELIGIBLE,
                message=eligibility.reason or "El paciente no es elegible para financiamiento.",
                status_code=422,
            )

        # Create the local application record (status=requested)
        application = FinancingApplication(
            patient_id=patient_id,
            invoice_id=invoice_id,
            provider=provider,
            status="requested",
            amount_cents=amount_cents,
            installments=installments,
        )
        db.add(application)
        await db.flush()
        await db.refresh(application)

        # Build the callback URL for provider webhook notifications
        callback_url = (
            f"{settings.frontend_url}/api/v1/webhooks/financing/{provider}"
        )

        # Submit to the provider
        try:
            result = await adapter.create_application(
                patient_document=patient.document_number,
                amount_cents=amount_cents,
                installments=installments,
                reference=str(application.id),
                callback_url=callback_url,
            )
        except Exception as exc:
            # Roll back the application to avoid orphaned records
            application.status = "cancelled"
            await db.flush()
            logger.error(
                "Financing application submission failed: provider=%s app=%s... error=%s",
                provider,
                str(application.id)[:8],
                str(exc),
            )
            raise DentalOSError(
                error=FinancingErrors.PROVIDER_UNAVAILABLE,
                message="Error al enviar la solicitud al proveedor.",
                status_code=503,
            ) from exc

        # Update with provider reference and status
        application.provider_reference = result.provider_reference
        application.status = result.status if result.status else "pending"
        await db.flush()
        await db.refresh(application)

        logger.info(
            "Financing application created: provider=%s app=%s... status=%s",
            provider,
            str(application.id)[:8],
            application.status,
        )

        return self._to_dict(application)

    # -- Webhook status update -------------------------------------------------

    async def handle_webhook_update(
        self,
        db: AsyncSession,
        provider: str,
        provider_reference: str,
        new_status: str,
        approved_amount_cents: int | None = None,
        disbursed_at: str | None = None,
    ) -> None:
        """Update a financing application's status from a provider webhook.

        Updates the application status and timestamps. If the application is
        marked as disbursed, records the disbursement timestamp.

        Args:
            db: Tenant-scoped AsyncSession.
            provider: Provider name (addi, sistecredito, mercadopago).
            provider_reference: Provider-assigned application identifier.
            new_status: New status received from the webhook.
            approved_amount_cents: Approved amount in COP cents (if applicable).
            disbursed_at: ISO datetime string of disbursement (if applicable).
        """
        from datetime import UTC, datetime

        result = await db.execute(
            select(FinancingApplication).where(
                FinancingApplication.provider == provider,
                FinancingApplication.provider_reference == provider_reference,
                FinancingApplication.is_active.is_(True),
            )
        )
        application = result.scalar_one_or_none()

        if application is None:
            logger.warning(
                "Webhook update: application not found: provider=%s ref=%s...",
                provider,
                provider_reference[:8],
            )
            raise ResourceNotFoundError(
                error=FinancingErrors.APPLICATION_NOT_FOUND,
                resource_name="FinancingApplication",
            )

        application.status = new_status

        if new_status == "approved" and application.approved_at is None:
            application.approved_at = datetime.now(UTC)

        if disbursed_at and application.disbursed_at is None:
            try:
                application.disbursed_at = datetime.fromisoformat(
                    disbursed_at.replace("Z", "+00:00")
                )
            except ValueError:
                application.disbursed_at = datetime.now(UTC)

        if new_status in ("completed", "paid_off"):
            application.completed_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Financing webhook status updated: provider=%s ref=%s... status=%s",
            provider,
            provider_reference[:8],
            new_status,
        )

    # -- List applications -----------------------------------------------------

    async def get_applications(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of financing applications.

        Optionally filtered by patient and/or status.

        Args:
            db: Tenant-scoped AsyncSession.
            patient_id: Filter by patient UUID (optional).
            status: Filter by application status (optional).
            page: 1-based page number.
            page_size: Items per page (max 100).

        Returns:
            dict with items, total, page, page_size.
        """
        query = select(FinancingApplication).where(
            FinancingApplication.is_active.is_(True)
        )

        if patient_id is not None:
            query = query.where(FinancingApplication.patient_id == patient_id)

        if status is not None:
            query = query.where(FinancingApplication.status == status)

        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Paginated results
        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(FinancingApplication.requested_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        applications = result.scalars().all()

        return {
            "items": [self._to_dict(a) for a in applications],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # -- Aggregate report -----------------------------------------------------

    async def get_report(self, db: AsyncSession) -> dict[str, Any]:
        """Return aggregate financing metrics for the tenant.

        Counts applications and sums amounts grouped by provider and status.

        Args:
            db: Tenant-scoped AsyncSession.

        Returns:
            dict with total_applications, total_amount_cents, by_provider, by_status.
        """
        # Total count and sum
        totals_result = await db.execute(
            select(
                func.count(FinancingApplication.id).label("total"),
                func.coalesce(func.sum(FinancingApplication.amount_cents), 0).label("total_amount"),
            ).where(FinancingApplication.is_active.is_(True))
        )
        totals_row = totals_result.one()
        total_applications: int = totals_row.total
        total_amount_cents: int = totals_row.total_amount

        # By provider
        provider_result = await db.execute(
            select(
                FinancingApplication.provider,
                func.count(FinancingApplication.id).label("count"),
            )
            .where(FinancingApplication.is_active.is_(True))
            .group_by(FinancingApplication.provider)
        )
        by_provider: dict[str, int] = {
            row.provider: row.count for row in provider_result
        }

        # By status
        status_result = await db.execute(
            select(
                FinancingApplication.status,
                func.count(FinancingApplication.id).label("count"),
            )
            .where(FinancingApplication.is_active.is_(True))
            .group_by(FinancingApplication.status)
        )
        by_status: dict[str, int] = {
            row.status: row.count for row in status_result
        }

        return {
            "total_applications": total_applications,
            "total_amount_cents": total_amount_cents,
            "by_provider": by_provider,
            "by_status": by_status,
        }

    # -- Private helpers -------------------------------------------------------

    async def _get_patient_or_raise(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
    ) -> Patient:
        """Fetch a patient or raise ResourceNotFoundError."""
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            raise ResourceNotFoundError(
                error=PatientErrors.NOT_FOUND,
                resource_name="Patient",
            )
        return patient

    async def _get_invoice_or_raise(
        self,
        db: AsyncSession,
        invoice_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> Invoice:
        """Fetch an invoice belonging to the patient or raise ResourceNotFoundError."""
        result = await db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.patient_id == patient_id,
                Invoice.is_active.is_(True),
            )
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="Invoice",
            )
        return invoice

    @staticmethod
    def _to_dict(application: FinancingApplication) -> dict[str, Any]:
        """Serialize a FinancingApplication to a response dict."""
        return {
            "id": str(application.id),
            "patient_id": str(application.patient_id),
            "invoice_id": str(application.invoice_id) if application.invoice_id else None,
            "provider": application.provider,
            "status": application.status,
            "amount_cents": application.amount_cents,
            "installments": application.installments,
            "interest_rate_bps": application.interest_rate_bps,
            "provider_reference": application.provider_reference,
            "requested_at": application.requested_at,
            "approved_at": application.approved_at,
            "disbursed_at": application.disbursed_at,
            "completed_at": application.completed_at,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
        }


# Module-level singleton
financing_service = FinancingService()
