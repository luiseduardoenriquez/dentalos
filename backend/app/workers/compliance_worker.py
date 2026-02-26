"""Compliance worker -- consumes from the 'clinical' queue.

Handles compliance-related jobs:
  - rips.generate: Generate RIPS flat files for a batch
  - rips.validate: Validate a RIPS batch
  - einvoice.generate: Generate and submit electronic invoice (Phase 5)

Production pipeline for rips.generate:
  1. Set tenant search_path
  2. Load RIPSBatch row
  3. Call generator for each requested file_type
  4. Upload files to S3
  5. Persist file records and error records
  6. Update batch status, error/warning counts, generated_at
"""

import logging
from datetime import UTC, date, datetime

from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.compliance")


class ComplianceWorker(BaseWorker):
    """Processes compliance jobs from the clinical queue.

    Handles ``rips.generate``, ``rips.validate``, and ``einvoice.generate``.
    Skips all other job types.  Uses ``prefetch_count=2`` for limited
    concurrency since compliance operations are I/O-heavy (S3 uploads,
    large DB queries).
    """

    queue_name = "clinical"
    prefetch_count = 2

    async def process(self, message: QueueMessage) -> None:
        """Dispatch to the correct handler based on job_type."""
        if message.job_type == "rips.generate":
            await self._handle_rips_generate(message)
        elif message.job_type == "rips.validate":
            await self._handle_rips_validate(message)
        elif message.job_type == "einvoice.generate":
            await self._handle_einvoice_generate(message)
        # Not our job type -- skip silently

    async def _handle_rips_generate(self, message: QueueMessage) -> None:
        """Generate RIPS files for a batch.

        Iterates over each requested file type, runs the corresponding
        generator, uploads the result to S3, and persists file and error
        records.  On unrecoverable failure the batch is marked ``failed``.
        """
        batch_id = message.payload.get("batch_id")
        period_start_str = message.payload.get("period_start")
        period_end_str = message.payload.get("period_end")
        file_types: list[str] = message.payload.get("file_types", [])

        if not batch_id:
            logger.warning(
                "rips.generate missing batch_id: message_id=%s",
                message.message_id,
            )
            return

        logger.info(
            "Processing RIPS generation: batch=%s tenant=%s",
            batch_id[:8],
            message.tenant_id[:8] if message.tenant_id else "?",
        )

        try:
            from sqlalchemy import select, text

            from app.compliance.colombia.rips import GENERATORS
            from app.core.database import AsyncSessionLocal
            from app.core.storage import storage_client
            from app.core.tenant import validate_schema_name
            from app.models.tenant.rips import (
                RIPSBatch,
                RIPSBatchError,
                RIPSBatchFile,
            )

            tenant_id = message.tenant_id
            schema_name = (
                f"tn_{tenant_id}"
                if not tenant_id.startswith("tn_")
                else tenant_id
            )

            period_start = (
                date.fromisoformat(period_start_str)
                if period_start_str
                else None
            )
            period_end = (
                date.fromisoformat(period_end_str)
                if period_end_str
                else None
            )

            if not period_start or not period_end:
                logger.error(
                    "rips.generate invalid period: batch=%s", batch_id[:8]
                )
                return

            async with AsyncSessionLocal() as db:
                # Set tenant search_path
                if validate_schema_name(schema_name):
                    await db.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )

                # Load batch
                result = await db.execute(
                    select(RIPSBatch).where(RIPSBatch.id == batch_id)
                )
                batch = result.scalar_one_or_none()
                if not batch:
                    logger.warning(
                        "RIPS batch not found: id=%s", batch_id[:8]
                    )
                    return

                # Transition to generating
                batch.status = "generating"
                await db.flush()

                total_errors = 0
                total_warnings = 0

                for file_type in file_types:
                    generator = GENERATORS.get(file_type)
                    if not generator:
                        logger.warning(
                            "Unknown RIPS file type: %s", file_type
                        )
                        continue

                    try:
                        content, record_count, errors = await generator(
                            db, period_start, period_end
                        )

                        # Tally errors vs warnings
                        for err in errors:
                            if err.get("severity") == "error":
                                total_errors += 1
                            else:
                                total_warnings += 1

                        # Upload to S3 if content exists
                        s3_key: str | None = None
                        size_bytes = 0
                        if content:
                            s3_key = (
                                f"rips/{tenant_id}/{batch_id}/{file_type}.txt"
                            )
                            content_bytes = content.encode("utf-8")
                            size_bytes = len(content_bytes)
                            await storage_client.upload_file(
                                key=s3_key,
                                data=content_bytes,
                                content_type="text/plain",
                            )

                        # Persist file record
                        batch_file = RIPSBatchFile(
                            batch_id=batch.id,
                            file_type=file_type,
                            storage_path=s3_key,
                            size_bytes=size_bytes,
                            record_count=record_count,
                        )
                        db.add(batch_file)

                        # Persist error records
                        for err in errors:
                            db.add(
                                RIPSBatchError(
                                    batch_id=batch.id,
                                    severity=err.get("severity", "warning"),
                                    rule_code=err.get("rule_code", "UNKNOWN"),
                                    message=err.get("message", ""),
                                    record_ref=err.get("record_ref"),
                                    field_name=err.get("field_name"),
                                )
                            )

                    except Exception:
                        logger.exception(
                            "Failed to generate RIPS file: type=%s batch=%s",
                            file_type,
                            batch_id[:8],
                        )
                        total_errors += 1

                # Finalize batch
                batch.status = "generated"
                batch.error_count = total_errors
                batch.warning_count = total_warnings
                batch.generated_at = datetime.now(UTC)

                await db.commit()

            logger.info(
                "RIPS generation complete: batch=%s errors=%d warnings=%d",
                batch_id[:8],
                total_errors,
                total_warnings,
            )

        except Exception:
            # Attempt to mark batch as failed so the UI reflects the error
            await self._mark_batch_failed(
                batch_id=batch_id,
                tenant_id=message.tenant_id,
                reason="Internal error during generation.",
            )
            raise

    async def _handle_rips_validate(self, message: QueueMessage) -> None:
        """Validate a RIPS batch.  MVP stub -- marks batch as validated."""
        batch_id = message.payload.get("batch_id")
        if not batch_id:
            return

        logger.info("Validating RIPS batch (stub): batch=%s", batch_id[:8])

        try:
            from sqlalchemy import select, text

            from app.core.database import AsyncSessionLocal
            from app.core.tenant import validate_schema_name
            from app.models.tenant.rips import RIPSBatch

            tenant_id = message.tenant_id
            schema_name = (
                f"tn_{tenant_id}"
                if not tenant_id.startswith("tn_")
                else tenant_id
            )

            async with AsyncSessionLocal() as db:
                if validate_schema_name(schema_name):
                    await db.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )

                result = await db.execute(
                    select(RIPSBatch).where(RIPSBatch.id == batch_id)
                )
                batch = result.scalar_one_or_none()
                if batch and batch.status == "generated":
                    batch.status = "validated"
                    batch.validated_at = datetime.now(UTC)
                    await db.commit()

            logger.info(
                "RIPS batch validated (stub): batch=%s", batch_id[:8]
            )
        except Exception:
            logger.exception(
                "Failed to validate RIPS batch: batch=%s", batch_id[:8]
            )
            raise

    async def _handle_einvoice_generate(self, message: QueueMessage) -> None:
        """Generate and submit an electronic invoice to DIAN via MATIAS.

        Pipeline:
          1. Set tenant search_path
          2. Load EInvoice, Invoice (with items), Patient, TenantEInvoiceConfig
          3. Build UBL 2.1 XML with CUFE
          4. Sign XML (stub for MVP)
          5. Submit to MATIAS
          6. Update EInvoice with submission_id, cufe, status
        """
        einvoice_id = message.payload.get("einvoice_id")
        invoice_id = message.payload.get("invoice_id")

        if not einvoice_id or not invoice_id:
            logger.warning(
                "einvoice.generate missing payload fields: message_id=%s",
                message.message_id,
            )
            return

        logger.info(
            "Processing e-invoice generation: einvoice=%s tenant=%s",
            einvoice_id[:8],
            message.tenant_id[:8] if message.tenant_id else "?",
        )

        try:
            from sqlalchemy import select, text
            from sqlalchemy.orm import selectinload

            from app.compliance.colombia.dian import (
                MATIASClient,
                build_ubl_xml,
                compute_cufe,
                sign_xml,
            )
            from app.core.database import AsyncSessionLocal
            from app.core.tenant import validate_schema_name
            from app.models.tenant.e_invoice import EInvoice, TenantEInvoiceConfig
            from app.models.tenant.invoice import Invoice
            from app.models.tenant.patient import Patient

            tenant_id = message.tenant_id
            schema_name = (
                f"tn_{tenant_id}"
                if not tenant_id.startswith("tn_")
                else tenant_id
            )

            async with AsyncSessionLocal() as db:
                # 1. Set tenant search_path
                if validate_schema_name(schema_name):
                    await db.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )

                # 2. Load EInvoice record
                result = await db.execute(
                    select(EInvoice).where(EInvoice.id == einvoice_id)
                )
                einvoice = result.scalar_one_or_none()
                if not einvoice:
                    logger.warning(
                        "E-invoice not found: id=%s", einvoice_id[:8]
                    )
                    return

                if einvoice.status != "pending":
                    logger.info(
                        "E-invoice not in pending status, skipping: id=%s status=%s",
                        einvoice_id[:8],
                        einvoice.status,
                    )
                    return

                # 3. Load Invoice with items (selectinload for eager loading)
                inv_result = await db.execute(
                    select(Invoice)
                    .options(selectinload(Invoice.items))
                    .where(Invoice.id == invoice_id)
                )
                invoice = inv_result.scalar_one_or_none()
                if not invoice:
                    einvoice.status = "error"
                    einvoice.failure_reason = "Linked invoice not found."
                    await db.commit()
                    return

                # 4. Load Patient
                pat_result = await db.execute(
                    select(Patient).where(Patient.id == invoice.patient_id)
                )
                patient = pat_result.scalar_one_or_none()
                if not patient:
                    einvoice.status = "error"
                    einvoice.failure_reason = "Linked patient not found."
                    await db.commit()
                    return

                # 5. Load TenantEInvoiceConfig
                config_result = await db.execute(
                    select(TenantEInvoiceConfig).where(
                        TenantEInvoiceConfig.is_active == True  # noqa: E712
                    )
                )
                dian_config = config_result.scalar_one_or_none()
                if not dian_config:
                    einvoice.status = "error"
                    einvoice.failure_reason = "DIAN config not found for tenant."
                    await db.commit()
                    return

                # 6. Prepare data for UBL XML
                now = datetime.now(UTC)
                issue_date = now.strftime("%Y-%m-%d")
                issue_time = now.strftime("%H:%M:%S-05:00")  # Colombia TZ

                subtotal_str = f"{invoice.subtotal / 100:.2f}"
                tax_str = f"{invoice.tax / 100:.2f}"
                total_str = f"{invoice.total / 100:.2f}"

                # Dental services are IVA-exempt
                tax_code = "01"  # IVA code
                technical_key = dian_config.resolution_number or ""

                receptor_name = f"{patient.first_name} {patient.last_name}"

                # 7. Compute CUFE
                cufe = compute_cufe(
                    invoice_number=invoice.invoice_number,
                    issue_date=issue_date,
                    issue_time=issue_time,
                    subtotal=subtotal_str,
                    tax_code=tax_code,
                    tax_amount=tax_str,
                    total=total_str,
                    nit_emisor=dian_config.nit,
                    nit_receptor=patient.document_number,
                    technical_key=technical_key,
                    environment=dian_config.dian_environment,
                )

                # 8. Build line items from InvoiceItem records
                line_items = [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "line_total": item.line_total,
                        "cups_code": item.cups_code,
                    }
                    for item in invoice.items
                ]

                # 9. Build UBL 2.1 XML
                xml_content = build_ubl_xml(
                    invoice_number=invoice.invoice_number,
                    issue_date=issue_date,
                    issue_time=issue_time,
                    cufe=cufe,
                    nit_emisor=dian_config.nit,
                    nit_dv_emisor=dian_config.nit_dv or "0",
                    emisor_name=f"Clinic {tenant_id}",
                    nit_receptor=patient.document_number,
                    receptor_name=receptor_name,
                    receptor_doc_type=patient.document_type,
                    subtotal_cents=invoice.subtotal,
                    tax_cents=invoice.tax,
                    total_cents=invoice.total,
                    line_items=line_items,
                    currency="COP",
                    environment=dian_config.dian_environment,
                )

                # 10. Sign XML (MVP stub)
                signed_xml = sign_xml(
                    xml_content,
                    certificate_path=dian_config.certificate_s3_path,
                )

                # 11. Submit to MATIAS
                client = MATIASClient()
                matias_response = await client.submit_invoice(
                    xml_content=signed_xml,
                    nit=dian_config.nit,
                    environment=dian_config.dian_environment,
                )

                # 12. Update EInvoice with response
                einvoice.status = "submitted"
                einvoice.cufe = cufe
                einvoice.matias_submission_id = matias_response.get(
                    "submission_id", ""
                )

                # If MATIAS returns an immediate status, handle it
                immediate_status = matias_response.get("status", "")
                if immediate_status == "accepted":
                    einvoice.status = "accepted"
                    einvoice.xml_url = matias_response.get("xml_url")
                    einvoice.pdf_url = matias_response.get("pdf_url")
                elif immediate_status == "rejected":
                    einvoice.status = "rejected"
                    einvoice.failure_reason = matias_response.get(
                        "message", "Rejected by DIAN."
                    )

                await db.commit()

            logger.info(
                "E-invoice submitted: einvoice=%s cufe=%s status=%s",
                einvoice_id[:8],
                cufe[:16],
                einvoice.status,
            )

        except Exception:
            logger.exception(
                "Failed to generate e-invoice: einvoice=%s",
                einvoice_id[:8],
            )
            # Best-effort: mark the e-invoice as error
            await self._mark_einvoice_error(
                einvoice_id=einvoice_id,
                tenant_id=message.tenant_id,
                reason="Internal error during e-invoice generation.",
            )
            raise

    async def _mark_einvoice_error(
        self,
        einvoice_id: str,
        tenant_id: str,
        reason: str,
    ) -> None:
        """Best-effort attempt to mark an e-invoice as error."""
        try:
            from sqlalchemy import select, text

            from app.core.database import AsyncSessionLocal
            from app.core.tenant import validate_schema_name
            from app.models.tenant.e_invoice import EInvoice

            schema_name = (
                f"tn_{tenant_id}"
                if not tenant_id.startswith("tn_")
                else tenant_id
            )
            async with AsyncSessionLocal() as db:
                if validate_schema_name(schema_name):
                    await db.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )
                result = await db.execute(
                    select(EInvoice).where(EInvoice.id == einvoice_id)
                )
                einvoice = result.scalar_one_or_none()
                if einvoice:
                    einvoice.status = "error"
                    einvoice.failure_reason = reason
                    einvoice.retry_count += 1
                    await db.commit()
        except Exception:
            logger.exception(
                "Failed to mark e-invoice as error: einvoice=%s",
                einvoice_id[:8],
            )

    async def _mark_batch_failed(
        self,
        batch_id: str,
        tenant_id: str,
        reason: str,
    ) -> None:
        """Best-effort attempt to mark a RIPS batch as failed."""
        try:
            from sqlalchemy import select, text

            from app.core.database import AsyncSessionLocal
            from app.core.tenant import validate_schema_name
            from app.models.tenant.rips import RIPSBatch

            schema_name = (
                f"tn_{tenant_id}"
                if not tenant_id.startswith("tn_")
                else tenant_id
            )
            async with AsyncSessionLocal() as db:
                if validate_schema_name(schema_name):
                    await db.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )
                result = await db.execute(
                    select(RIPSBatch).where(RIPSBatch.id == batch_id)
                )
                batch = result.scalar_one_or_none()
                if batch:
                    batch.status = "failed"
                    batch.failure_reason = reason
                    await db.commit()
        except Exception:
            logger.exception(
                "Failed to mark batch as failed: batch=%s", batch_id[:8]
            )


# Module-level instance for CLI entry point
compliance_worker = ComplianceWorker()
