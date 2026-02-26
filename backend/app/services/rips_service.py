"""RIPS service — batch generation and validation.

Manages the lifecycle of RIPS batch exports: creation, querying,
listing with pagination, and publishing validation jobs.  The actual
file generation is done asynchronously by the compliance worker.
"""

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ComplianceError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.rips import RIPSBatch, RIPSBatchError, RIPSBatchFile
from app.schemas.compliance import (
    RIPSBatchErrorResponse,
    RIPSBatchFileResponse,
    RIPSBatchListResponse,
    RIPSBatchResponse,
    RIPSValidateResponse,
)
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.compliance.rips")

VALID_RIPS_FILE_TYPES = frozenset({"AF", "AC", "AP", "AT", "AM", "AN", "AU"})


async def create_rips_batch(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    period_start: date,
    period_end: date,
    file_types: list[str],
) -> RIPSBatchResponse:
    """Create a new RIPS batch and publish a generation job to the worker queue.

    Validates the period, checks for conflicting in-progress batches,
    creates the database row, publishes a ``rips.generate`` job on the
    ``clinical`` queue, and returns a 202-style response with the batch ID.

    Raises:
        ComplianceError: If period is invalid, file types are invalid,
            or a conflicting batch already exists.
    """
    if period_end <= period_start:
        raise ComplianceError(
            error="COMPLIANCE_invalid_period",
            message="Period end must be after period start.",
            status_code=422,
        )

    invalid = set(file_types) - VALID_RIPS_FILE_TYPES
    if invalid:
        raise ComplianceError(
            error="COMPLIANCE_invalid_file_types",
            message=f"Invalid RIPS file types: {', '.join(sorted(invalid))}",
            status_code=422,
        )

    # Check for conflicting in-progress batch for the same period
    start_dt = datetime(
        period_start.year, period_start.month, period_start.day, tzinfo=UTC
    )
    end_dt = datetime(
        period_end.year, period_end.month, period_end.day, tzinfo=UTC
    )

    conflict = await db.execute(
        select(RIPSBatch).where(
            RIPSBatch.period_start == start_dt,
            RIPSBatch.period_end == end_dt,
            RIPSBatch.status.in_(["queued", "generating"]),
        )
    )
    if conflict.scalar_one_or_none():
        raise ComplianceError(
            error="COMPLIANCE_batch_conflict",
            message="A RIPS batch is already being generated for this period.",
            status_code=409,
        )

    # Create the batch record
    batch = RIPSBatch(
        period_start=start_dt,
        period_end=end_dt,
        status="queued",
        file_types=file_types,
        created_by=uuid.UUID(user_id),
    )
    db.add(batch)
    await db.flush()

    # Publish async generation job
    message = QueueMessage(
        tenant_id=tenant_id,
        job_type="rips.generate",
        payload={
            "batch_id": str(batch.id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "file_types": file_types,
        },
    )
    await publish_message("clinical", message)

    await db.commit()
    await db.refresh(batch)

    return _batch_to_response(batch)


async def get_rips_batch(
    db: AsyncSession,
    batch_id: str,
) -> RIPSBatchResponse:
    """Get a single RIPS batch with its files and errors.

    Raises:
        ResourceNotFoundError: If the batch does not exist.
    """
    result = await db.execute(
        select(RIPSBatch).where(RIPSBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise ResourceNotFoundError(
            error="COMPLIANCE_batch_not_found",
            resource_name="RIPS batch",
        )
    return _batch_to_response(batch)


async def list_rips_batches(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> RIPSBatchListResponse:
    """List RIPS batches with standard pagination."""
    offset = (page - 1) * page_size

    count_result = await db.execute(select(func.count(RIPSBatch.id)))
    total = count_result.scalar_one()

    result = await db.execute(
        select(RIPSBatch)
        .order_by(RIPSBatch.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    batches = result.scalars().all()

    return RIPSBatchListResponse(
        items=[_batch_to_response(b) for b in batches],
        total=total,
        page=page,
        page_size=page_size,
    )


async def validate_rips_batch(
    db: AsyncSession,
    batch_id: str,
    tenant_id: str,
) -> RIPSValidateResponse:
    """Publish a validation job for a RIPS batch.

    Returns the current validation state.  The actual validation is
    performed asynchronously by the compliance worker.

    Raises:
        ResourceNotFoundError: If the batch does not exist.
        ComplianceError: If the batch is not in a validatable state.
    """
    result = await db.execute(
        select(RIPSBatch).where(RIPSBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise ResourceNotFoundError(
            error="COMPLIANCE_batch_not_found",
            resource_name="RIPS batch",
        )

    if batch.status not in ("generated", "validated"):
        raise ComplianceError(
            error="COMPLIANCE_batch_not_ready",
            message="Batch must be in 'generated' status to validate.",
            status_code=422,
        )

    # Publish async validation job
    message = QueueMessage(
        tenant_id=tenant_id,
        job_type="rips.validate",
        payload={"batch_id": str(batch.id)},
    )
    await publish_message("clinical", message)

    return RIPSValidateResponse(
        batch_id=str(batch.id),
        is_valid=batch.error_count == 0,
        error_count=batch.error_count,
        warning_count=batch.warning_count,
        errors=[
            RIPSBatchErrorResponse(
                severity=e.severity,
                rule_code=e.rule_code,
                message=e.message,
                record_ref=e.record_ref,
                field_name=e.field_name,
            )
            for e in (batch.errors or [])
        ],
    )


def _batch_to_response(batch: RIPSBatch) -> RIPSBatchResponse:
    """Convert a RIPSBatch ORM instance to its Pydantic response schema."""
    return RIPSBatchResponse(
        id=str(batch.id),
        period_start=batch.period_start.date() if batch.period_start else None,
        period_end=batch.period_end.date() if batch.period_end else None,
        status=batch.status,
        file_types=batch.file_types or [],
        files=[
            RIPSBatchFileResponse(
                file_type=f.file_type,
                storage_path=f.storage_path,
                size_bytes=f.size_bytes,
                record_count=f.record_count,
            )
            for f in (batch.files or [])
        ],
        errors=[
            RIPSBatchErrorResponse(
                severity=e.severity,
                rule_code=e.rule_code,
                message=e.message,
                record_ref=e.record_ref,
                field_name=e.field_name,
            )
            for e in (batch.errors or [])
        ],
        error_count=batch.error_count,
        warning_count=batch.warning_count,
        created_at=batch.created_at,
        generated_at=batch.generated_at,
        validated_at=batch.validated_at,
        failure_reason=batch.failure_reason,
    )
