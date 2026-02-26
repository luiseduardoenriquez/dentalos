"""RIPS file generators for MinSalud reporting (CO-01 through CO-04).

Generates 7 flat file types per Resolucion 3374:
  AF -- Transacciones (billing summary)
  AC -- Consultas (consultations)
  AP -- Procedimientos (procedures)
  AT -- Otros servicios (other services)
  AM -- Medicamentos (medications)
  AN -- Recien nacidos (newborns) -- stub for dental
  AU -- Urgencias (emergency care)

Each generator queries the tenant DB and writes pipe-delimited text
per the MinSalud specification.  Returns a ``(content, record_count,
errors)`` tuple where ``errors`` is a list of dicts with keys:
``severity``, ``rule_code``, ``message``, ``record_ref``, ``field_name``.
"""

import io
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.colombia.validators import (
    validate_cie10_code,
    validate_cups_code,
    validate_document_number,
)
from app.models.tenant.clinical_record import ClinicalRecord
from app.models.tenant.diagnosis import Diagnosis
from app.models.tenant.invoice import Invoice
from app.models.tenant.patient import Patient
from app.models.tenant.procedure import Procedure

logger = logging.getLogger("dentalos.compliance.rips")

DELIMITER = "|"

# Type alias for generator function signatures
GeneratorResult = tuple[str, int, list[dict[str, Any]]]
GeneratorFunc = Callable[
    [AsyncSession, date, date],
    Coroutine[Any, Any, GeneratorResult],
]


def _to_utc_datetime(d: date) -> datetime:
    """Convert a date to a midnight UTC datetime."""
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _map_document_type(doc_type: str) -> str:
    """Map DentalOS document type to RIPS document type code.

    Falls back to ``CC`` (cedula de ciudadania) for unmapped types.
    """
    mapping = {
        "CC": "CC",
        "TI": "TI",
        "CE": "CE",
        "PA": "PA",
        "PEP": "PE",
        "RC": "RC",
        "MS": "MS",
        "AS": "AS",
        "NIT": "NI",
        "CD": "CD",
        "SC": "SC",
        "PE": "PE",
    }
    return mapping.get(doc_type, "CC")


async def generate_af(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AF file (billing transactions summary).

    One row per non-draft invoice in the period.  Fields (pipe-delimited):
    invoice_number | doc_type | doc_number | subtotal | tax | total
    """
    errors: list[dict[str, Any]] = []
    buffer = io.StringIO()
    count = 0

    start_dt = _to_utc_datetime(period_start)
    end_dt = _to_utc_datetime(period_end)

    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.created_at >= start_dt,
            Invoice.created_at <= end_dt,
            Invoice.is_active == True,  # noqa: E712
            Invoice.status != "draft",
        )
        .order_by(Invoice.created_at)
    )
    invoices = result.scalars().all()

    for inv in invoices:
        pat_result = await db.execute(
            select(Patient).where(Patient.id == inv.patient_id)
        )
        patient = pat_result.scalar_one_or_none()
        if not patient:
            errors.append({
                "severity": "error",
                "rule_code": "AF_MISSING_PATIENT",
                "message": f"Invoice {inv.invoice_number} has no linked patient.",
                "record_ref": str(inv.id),
            })
            continue

        doc_type = _map_document_type(patient.document_type)
        doc_number = patient.document_number or ""

        if doc_number and not validate_document_number(doc_number):
            errors.append({
                "severity": "warning",
                "rule_code": "AF_INVALID_DOCUMENT",
                "message": f"Patient document number format invalid: {doc_number[:4]}...",
                "record_ref": str(inv.id),
                "field_name": "document_number",
            })

        # AF fields: invoice_number, doc_type, doc_number, subtotal, tax, total
        row = DELIMITER.join([
            inv.invoice_number or "",
            doc_type,
            doc_number,
            str(inv.subtotal),
            str(inv.tax),
            str(inv.total),
        ])
        buffer.write(row + "\n")
        count += 1

    return buffer.getvalue(), count, errors


async def generate_ac(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AC file (consultations).

    One row per clinical record in the period.  Fields (pipe-delimited):
    doc_type | doc_number | consultation_date | cie10_code | record_type
    """
    errors: list[dict[str, Any]] = []
    buffer = io.StringIO()
    count = 0

    start_dt = _to_utc_datetime(period_start)
    end_dt = _to_utc_datetime(period_end)

    result = await db.execute(
        select(ClinicalRecord)
        .where(
            ClinicalRecord.created_at >= start_dt,
            ClinicalRecord.created_at <= end_dt,
            ClinicalRecord.is_active == True,  # noqa: E712
        )
        .order_by(ClinicalRecord.created_at)
    )
    records = result.scalars().all()

    for rec in records:
        pat_result = await db.execute(
            select(Patient).where(Patient.id == rec.patient_id)
        )
        patient = pat_result.scalar_one_or_none()
        if not patient:
            errors.append({
                "severity": "error",
                "rule_code": "AC_MISSING_PATIENT",
                "message": f"Clinical record {str(rec.id)[:8]} has no linked patient.",
                "record_ref": str(rec.id),
            })
            continue

        # Fetch most recent active diagnosis for the patient
        diag_result = await db.execute(
            select(Diagnosis)
            .where(
                Diagnosis.patient_id == rec.patient_id,
                Diagnosis.is_active == True,  # noqa: E712
            )
            .order_by(Diagnosis.created_at.desc())
            .limit(1)
        )
        diagnosis = diag_result.scalar_one_or_none()

        cie10_code = diagnosis.cie10_code if diagnosis else ""

        if cie10_code and not validate_cie10_code(cie10_code):
            errors.append({
                "severity": "warning",
                "rule_code": "AC_INVALID_CIE10",
                "message": f"Invalid CIE-10 code: {cie10_code}",
                "record_ref": str(rec.id),
                "field_name": "cie10_code",
            })

        doc_type = _map_document_type(patient.document_type)
        consultation_date = (
            rec.created_at.strftime("%d/%m/%Y") if rec.created_at else ""
        )

        # AC fields: doc_type, doc_number, consultation_date, cie10_code, record_type
        row = DELIMITER.join([
            doc_type,
            patient.document_number or "",
            consultation_date,
            cie10_code,
            rec.type,  # ClinicalRecord.type: examination, evolution_note, procedure
        ])
        buffer.write(row + "\n")
        count += 1

    return buffer.getvalue(), count, errors


async def generate_ap(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AP file (procedures).

    One row per procedure in the period.  Fields (pipe-delimited):
    doc_type | doc_number | procedure_date | cups_code | cups_description
    """
    errors: list[dict[str, Any]] = []
    buffer = io.StringIO()
    count = 0

    start_dt = _to_utc_datetime(period_start)
    end_dt = _to_utc_datetime(period_end)

    result = await db.execute(
        select(Procedure)
        .where(
            Procedure.created_at >= start_dt,
            Procedure.created_at <= end_dt,
            Procedure.is_active == True,  # noqa: E712
        )
        .order_by(Procedure.created_at)
    )
    procedures = result.scalars().all()

    for proc in procedures:
        pat_result = await db.execute(
            select(Patient).where(Patient.id == proc.patient_id)
        )
        patient = pat_result.scalar_one_or_none()
        if not patient:
            errors.append({
                "severity": "error",
                "rule_code": "AP_MISSING_PATIENT",
                "message": f"Procedure {str(proc.id)[:8]} has no linked patient.",
                "record_ref": str(proc.id),
            })
            continue

        cups_code = proc.cups_code or ""

        if cups_code and not validate_cups_code(cups_code):
            errors.append({
                "severity": "warning",
                "rule_code": "AP_INVALID_CUPS",
                "message": f"Invalid CUPS code: {cups_code}",
                "record_ref": str(proc.id),
                "field_name": "cups_code",
            })

        doc_type = _map_document_type(patient.document_type)
        procedure_date = (
            proc.created_at.strftime("%d/%m/%Y") if proc.created_at else ""
        )

        # AP fields: doc_type, doc_number, procedure_date, cups_code, description
        row = DELIMITER.join([
            doc_type,
            patient.document_number or "",
            procedure_date,
            cups_code,
            (proc.cups_description or "")[:100],
        ])
        buffer.write(row + "\n")
        count += 1

    return buffer.getvalue(), count, errors


async def generate_at(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AT file (other services). Stub for dental MVP."""
    return "", 0, []


async def generate_am(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AM file (medications). Stub for dental MVP -- minimal medication use."""
    return "", 0, []


async def generate_an(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AN file (newborns). Not applicable to dental -- always empty."""
    return "", 0, []


async def generate_au(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> GeneratorResult:
    """Generate AU file (emergency care). Stub for dental MVP."""
    return "", 0, []


# Generator dispatch map keyed by RIPS file type code
GENERATORS: dict[str, GeneratorFunc] = {
    "AF": generate_af,
    "AC": generate_ac,
    "AP": generate_ap,
    "AT": generate_at,
    "AM": generate_am,
    "AN": generate_an,
    "AU": generate_au,
}
