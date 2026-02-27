"""Import worker -- consumes from the 'import' queue.

Handles import-related jobs:
  - patient.import: Process a CSV file to bulk-create patient records.

Production pipeline for patient.import:
  1. Set tenant search_path
  2. Download CSV from S3
  3. Parse and validate each row via PatientCSVRow
  4. Check for duplicates (document_type + document_number)
  5. Batch insert patients every 50 rows
  6. Update Redis progress periodically
  7. On completion: upload error CSV (if any), update final status

Security invariants:
  - PHI (patient names, document numbers, phone, email) is NEVER logged.
  - All database operations use bound parameters.
"""

import csv
import io
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.core.cache import set_cached
from app.core.database import AsyncSessionLocal
from app.core.storage import storage_client
from app.core.tenant import validate_schema_name
from app.models.tenant.patient import Patient
from app.schemas.patient_import import PatientCSVRow
from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.import")

# ─── Constants ───────────────────────────────────────────────────────────────

_BATCH_SIZE = 50
_IMPORT_JOB_TTL = 86400  # 24 hours — matches the router TTL

# Map from Spanish CSV headers to Patient model field names
_CSV_TO_MODEL_FIELD = {
    "tipo_documento": "document_type",
    "numero_documento": "document_number",
    "nombres": "first_name",
    "apellidos": "last_name",
    "fecha_nacimiento": "birthdate",
    "genero": "gender",
    "email": "email",
    "telefono": "phone",
    "ciudad": "city",
}

# Map from tipo_documento CSV values to internal document_type codes.
# The Patient model CHECK constraint allows CC, CE, PA, PEP, TI.
# CSV import additionally accepts RC and NIT from the spec.
# We map them to the closest internal equivalent.
_DOC_TYPE_MAP = {
    "CC": "CC",
    "TI": "TI",
    "CE": "CE",
    "PA": "PA",
    "RC": "TI",   # Registro Civil → map to TI for storage
    "NIT": "CE",   # NIT → map to CE as closest fit
}


class ImportWorker(BaseWorker):
    """Processes import jobs from the import queue.

    Handles ``patient.import`` job type.  Uses ``prefetch_count=1`` to
    limit concurrency since CSV imports are memory-intensive and
    long-running.
    """

    queue_name = "import"
    prefetch_count = 1

    async def process(self, message: QueueMessage) -> None:
        """Dispatch to the correct handler based on job_type."""
        if message.job_type == "patient.import":
            await self._handle_patient_import(message)
        # Not our job type -- skip silently

    async def _handle_patient_import(self, message: QueueMessage) -> None:
        """Process a patient CSV import file.

        Steps:
          1. Extract job metadata from payload
          2. Set tenant search_path
          3. Download CSV from S3
          4. Parse and validate each row
          5. Batch-insert valid, non-duplicate patients
          6. Track errors and build error CSV
          7. Update Redis with final status
        """
        job_id = message.payload.get("job_id")
        s3_path = message.payload.get("s3_path")
        tenant_id = message.payload.get("tenant_id") or message.tenant_id
        total_rows = message.payload.get("total_rows", 0)

        if not job_id or not s3_path:
            logger.warning(
                "patient.import missing required payload fields: message_id=%s",
                message.message_id,
            )
            return

        redis_key = f"dentalos:{tenant_id[:8]}:import:jobs:{job_id}"

        logger.info(
            "Processing patient import: job=%s tenant=%s",
            job_id[:8],
            tenant_id[:8],
        )

        # Update job status to processing
        await self._update_job_status(
            redis_key,
            status="processing",
            total_rows=total_rows,
            processed_rows=0,
            error_rows=0,
        )

        schema_name = (
            f"tn_{tenant_id}"
            if not tenant_id.startswith("tn_")
            else tenant_id
        )

        try:
            # Download CSV from S3
            csv_bytes = await storage_client.download_file(key=s3_path)
            csv_text = csv_bytes.decode("utf-8-sig")

            async with AsyncSessionLocal() as db:
                # Set tenant search_path
                if validate_schema_name(schema_name):
                    await db.execute(
                        text(f"SET search_path TO {schema_name}, public")
                    )

                reader = csv.DictReader(io.StringIO(csv_text))

                processed_rows = 0
                error_rows = 0
                error_list: list[dict[str, str]] = []
                batch: list[Patient] = []

                for row_num, raw_row in enumerate(reader, start=2):
                    # Normalize header keys to lowercase and strip whitespace
                    row = {
                        k.strip().lower(): v.strip() if v else ""
                        for k, v in raw_row.items()
                        if k is not None
                    }

                    # Replace empty strings with None for optional fields
                    for key in (
                        "fecha_nacimiento", "genero", "email", "telefono", "ciudad"
                    ):
                        if key in row and not row[key]:
                            row[key] = None  # type: ignore[assignment]

                    # Validate row with Pydantic model
                    try:
                        validated = PatientCSVRow(**row)
                    except Exception as e:
                        error_rows += 1
                        error_msg = str(e)
                        # Truncate error message to avoid leaking PHI
                        if len(error_msg) > 200:
                            error_msg = error_msg[:200] + "..."
                        error_list.append({
                            "fila": str(row_num),
                            "error": error_msg,
                        })
                        processed_rows += 1
                        continue

                    # Map CSV document type to internal model type
                    internal_doc_type = _DOC_TYPE_MAP.get(
                        validated.tipo_documento, validated.tipo_documento
                    )

                    # Check for duplicate (document_type + document_number)
                    dup_result = await db.execute(
                        select(Patient.id).where(
                            Patient.document_type == internal_doc_type,
                            Patient.document_number == validated.numero_documento,
                        )
                    )
                    if dup_result.scalar_one_or_none() is not None:
                        error_rows += 1
                        error_list.append({
                            "fila": str(row_num),
                            "error": (
                                "Paciente duplicado: ya existe un registro con "
                                "el mismo tipo y número de documento."
                            ),
                        })
                        processed_rows += 1
                        continue

                    # Build Patient ORM object
                    patient = Patient(
                        document_type=internal_doc_type,
                        document_number=validated.numero_documento,
                        first_name=validated.nombres,
                        last_name=validated.apellidos,
                        birthdate=validated.fecha_nacimiento,
                        gender=validated.genero,
                        email=validated.email,
                        phone=validated.telefono,
                        city=validated.ciudad,
                        is_active=True,
                        no_show_count=0,
                        portal_access=False,
                    )
                    db.add(patient)
                    batch.append(patient)
                    processed_rows += 1

                    # Batch flush every _BATCH_SIZE rows
                    if len(batch) >= _BATCH_SIZE:
                        await db.flush()
                        batch.clear()

                        # Update Redis progress
                        await self._update_job_status(
                            redis_key,
                            status="processing",
                            total_rows=total_rows,
                            processed_rows=processed_rows,
                            error_rows=error_rows,
                        )

                # Flush remaining batch
                if batch:
                    await db.flush()
                    batch.clear()

                # Handle error CSV upload
                error_csv_url: str | None = None
                if error_list:
                    error_csv_url = await self._upload_error_csv(
                        tenant_id=tenant_id,
                        job_id=job_id,
                        errors=error_list,
                    )

                # Commit the transaction
                await db.commit()

            # Update final job status
            await self._update_job_status(
                redis_key,
                status="completed",
                total_rows=total_rows,
                processed_rows=processed_rows,
                error_rows=error_rows,
                error_csv_url=error_csv_url,
            )

            logger.info(
                "Patient import complete: job=%s processed=%d errors=%d",
                job_id[:8],
                processed_rows,
                error_rows,
            )

        except Exception:
            logger.exception(
                "Patient import failed: job=%s", job_id[:8]
            )

            # Best-effort: mark job as failed
            await self._update_job_status(
                redis_key,
                status="failed",
                total_rows=total_rows,
                processed_rows=0,
                error_rows=0,
            )
            raise

    async def _update_job_status(
        self,
        redis_key: str,
        *,
        status: str,
        total_rows: int,
        processed_rows: int,
        error_rows: int,
        error_csv_url: str | None = None,
    ) -> None:
        """Update the import job status in Redis.

        Silently fails on Redis errors to avoid interrupting the import.
        """
        try:
            # Read existing data to preserve created_at
            from app.core.cache import get_cached

            existing = await get_cached(redis_key)
            created_at = (
                existing.get("created_at", datetime.now(UTC).isoformat())
                if existing
                else datetime.now(UTC).isoformat()
            )
            job_id = (
                existing.get("job_id", "")
                if existing
                else redis_key.split(":")[-1]
            )

            job_data = {
                "job_id": job_id,
                "status": status,
                "total_rows": total_rows,
                "processed_rows": processed_rows,
                "error_rows": error_rows,
                "error_csv_url": error_csv_url,
                "created_at": created_at,
            }
            await set_cached(redis_key, job_data, ttl_seconds=_IMPORT_JOB_TTL)
        except Exception:
            logger.warning(
                "Failed to update import job status in Redis: key=%s",
                redis_key[:40],
            )

    async def _upload_error_csv(
        self,
        *,
        tenant_id: str,
        job_id: str,
        errors: list[dict[str, str]],
    ) -> str | None:
        """Build and upload an error CSV to S3.

        Returns a presigned URL for downloading the error report,
        or None if the upload fails.
        """
        try:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=["fila", "error"])
            writer.writeheader()
            writer.writerows(errors)

            csv_bytes = buf.getvalue().encode("utf-8")
            s3_key = f"{tenant_id}/imports/{job_id}_errors.csv"

            await storage_client.upload_file(
                key=s3_key,
                data=csv_bytes,
                content_type="text/plain",
            )

            # Generate presigned URL for the error file
            url = await storage_client.get_presigned_url(key=s3_key)
            return url

        except Exception:
            logger.warning(
                "Failed to upload error CSV: job=%s", job_id[:8]
            )
            return None


# Module-level instance for CLI entry point
import_worker = ImportWorker()
