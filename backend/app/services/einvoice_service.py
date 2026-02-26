"""E-invoice service -- create and check status of DIAN submissions (CO-06, CO-07)."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ComplianceError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.e_invoice import EInvoice, TenantEInvoiceConfig
from app.models.tenant.invoice import Invoice
from app.schemas.compliance import EInvoiceStatusResponse
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.compliance.einvoice")


async def create_einvoice(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    invoice_id: str,
) -> EInvoiceStatusResponse:
    """Create an e-invoice record and publish to the worker queue.

    Validates that the invoice exists, is not draft, and that DIAN config
    is set up for this tenant.  Returns the initial pending status.
    """
    # Validate invoice exists and is sendable
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.is_active == True,  # noqa: E712
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise ResourceNotFoundError(
            error="COMPLIANCE_invoice_not_found",
            resource_name="Invoice",
        )

    if invoice.status == "draft":
        raise ComplianceError(
            error="COMPLIANCE_invoice_not_ready",
            message="Cannot submit a draft invoice for electronic invoicing.",
            status_code=422,
        )

    # Check if already submitted
    existing = await db.execute(
        select(EInvoice).where(
            EInvoice.invoice_id == uuid.UUID(invoice_id),
            EInvoice.status.in_(["pending", "submitted", "accepted"]),
        )
    )
    if existing.scalar_one_or_none():
        raise ComplianceError(
            error="COMPLIANCE_einvoice_exists",
            message=(
                "This invoice already has an active e-invoice submission."
            ),
            status_code=409,
        )

    # Check tenant DIAN config
    config_result = await db.execute(
        select(TenantEInvoiceConfig).where(
            TenantEInvoiceConfig.is_active == True,  # noqa: E712
        )
    )
    dian_config = config_result.scalar_one_or_none()
    if not dian_config:
        raise ComplianceError(
            error="COMPLIANCE_dian_not_configured",
            message=(
                "DIAN e-invoicing is not configured for this clinic. "
                "Set up NIT and resolution in settings."
            ),
            status_code=422,
        )

    # Create e-invoice record
    einvoice = EInvoice(
        invoice_id=uuid.UUID(invoice_id),
        status="pending",
        dian_environment=dian_config.dian_environment,
        created_by=uuid.UUID(user_id),
    )
    db.add(einvoice)
    await db.flush()

    # Publish to worker queue
    message = QueueMessage(
        tenant_id=tenant_id,
        job_type="einvoice.generate",
        payload={
            "einvoice_id": str(einvoice.id),
            "invoice_id": invoice_id,
        },
    )
    await publish_message("clinical", message)

    await db.commit()
    await db.refresh(einvoice)

    return _einvoice_to_response(einvoice)


async def get_einvoice_status(
    db: AsyncSession,
    einvoice_id: str,
) -> EInvoiceStatusResponse:
    """Get the status of an e-invoice submission.

    If the e-invoice is in ``submitted`` status with a MATIAS submission_id,
    polls the MATIAS API for the latest DIAN response and updates the record.
    """
    result = await db.execute(
        select(EInvoice).where(EInvoice.id == einvoice_id)
    )
    einvoice = result.scalar_one_or_none()
    if not einvoice:
        raise ResourceNotFoundError(
            error="COMPLIANCE_einvoice_not_found",
            resource_name="E-invoice",
        )

    # If submitted and still pending DIAN response, poll MATIAS
    if einvoice.status == "submitted" and einvoice.matias_submission_id:
        try:
            from app.compliance.colombia.dian import MATIASClient

            client = MATIASClient()
            result_data = await client.check_status(
                einvoice.matias_submission_id,
            )
            matias_status = result_data.get("status", "")

            if matias_status == "accepted":
                einvoice.status = "accepted"
                einvoice.cufe = result_data.get("cufe", einvoice.cufe)
                einvoice.xml_url = result_data.get("xml_url")
                einvoice.pdf_url = result_data.get("pdf_url")
                await db.commit()
                await db.refresh(einvoice)
            elif matias_status == "rejected":
                einvoice.status = "rejected"
                einvoice.failure_reason = result_data.get(
                    "message", "Rejected by DIAN.",
                )
                await db.commit()
                await db.refresh(einvoice)
        except Exception:
            logger.debug(
                "Failed to poll MATIAS for e-invoice %s",
                einvoice_id[:8],
            )

    return _einvoice_to_response(einvoice)


def _einvoice_to_response(einvoice: EInvoice) -> EInvoiceStatusResponse:
    """Convert an EInvoice model to a response schema."""
    return EInvoiceStatusResponse(
        id=str(einvoice.id),
        invoice_id=str(einvoice.invoice_id),
        status=einvoice.status,
        cufe=einvoice.cufe,
        matias_submission_id=einvoice.matias_submission_id,
        dian_environment=einvoice.dian_environment,
        xml_url=einvoice.xml_url,
        pdf_url=einvoice.pdf_url,
        retry_count=einvoice.retry_count,
        failure_reason=einvoice.failure_reason,
        created_at=einvoice.created_at,
        updated_at=einvoice.updated_at,
    )
