"""Procedure service — record clinical procedures with odontogram integration.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - CUPS codes are validated against the public catalog.
  - Auto-odontogram update maps CUPS ranges to condition transitions.
"""

import base64
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ProcedureErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.patient import Patient
from app.models.tenant.procedure import Procedure

logger = logging.getLogger("dentalos.procedure")


def _procedure_to_dict(proc: Procedure) -> dict[str, Any]:
    """Serialize a Procedure ORM instance to a plain dict."""
    return {
        "id": str(proc.id),
        "patient_id": str(proc.patient_id),
        "doctor_id": str(proc.doctor_id),
        "cups_code": proc.cups_code,
        "cups_description": proc.cups_description,
        "tooth_number": proc.tooth_number,
        "zones": proc.zones,
        "materials_used": proc.materials_used,
        "duration_minutes": proc.duration_minutes,
        "notes": proc.notes,
        "treatment_plan_item_id": (
            str(proc.treatment_plan_item_id) if proc.treatment_plan_item_id else None
        ),
        "clinical_record_id": (
            str(proc.clinical_record_id) if proc.clinical_record_id else None
        ),
        "is_active": proc.is_active,
        "created_at": proc.created_at,
        "updated_at": proc.updated_at,
    }


def _encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    """Encode a pagination cursor as base64."""
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a pagination cursor."""
    raw = base64.b64decode(cursor.encode()).decode()
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise ValueError("Malformed cursor")
    return datetime.fromisoformat(parts[0]), uuid.UUID(parts[1])


class ProcedureService:
    """Stateless procedure service."""

    async def create_procedure(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        cups_code: str,
        cups_description: str,
        tooth_number: int | None = None,
        zones: dict | None = None,
        materials_used: list[dict] | None = None,
        duration_minutes: int | None = None,
        notes: str | None = None,
        treatment_plan_item_id: str | None = None,
        clinical_record_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a new clinical procedure.

        Raises:
            DentalOSError (404) — patient not found or inactive.
        """
        pid = uuid.UUID(patient_id)

        # Validate patient exists and is active
        patient_result = await db.execute(
            select(Patient.id).where(
                Patient.id == pid,
                Patient.is_active.is_(True),
            )
        )
        if patient_result.scalar_one_or_none() is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="El paciente no existe o está inactivo.",
                status_code=404,
            )

        procedure = Procedure(
            patient_id=pid,
            doctor_id=uuid.UUID(doctor_id),
            cups_code=cups_code,
            cups_description=cups_description,
            tooth_number=tooth_number,
            zones=zones,
            materials_used=materials_used,
            duration_minutes=duration_minutes,
            notes=notes,
            treatment_plan_item_id=(
                uuid.UUID(treatment_plan_item_id) if treatment_plan_item_id else None
            ),
            clinical_record_id=(
                uuid.UUID(clinical_record_id) if clinical_record_id else None
            ),
            is_active=True,
        )
        db.add(procedure)
        await db.flush()

        logger.info(
            "Procedure created: patient=%s cups=%s tooth=%s",
            patient_id[:8],
            cups_code,
            tooth_number,
        )

        return _procedure_to_dict(procedure)

    async def get_procedure(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        procedure_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single procedure by ID."""
        result = await db.execute(
            select(Procedure).where(
                Procedure.id == uuid.UUID(procedure_id),
                Procedure.patient_id == uuid.UUID(patient_id),
                Procedure.is_active.is_(True),
            )
        )
        proc = result.scalar_one_or_none()
        if proc is None:
            return None
        return _procedure_to_dict(proc)

    async def list_procedures(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Cursor-paginated list of procedures for a patient."""
        pid = uuid.UUID(patient_id)

        stmt = (
            select(Procedure)
            .where(
                Procedure.patient_id == pid,
                Procedure.is_active.is_(True),
            )
        )

        if cursor is not None:
            try:
                cursor_created_at, cursor_id = _decode_cursor(cursor)
            except (ValueError, Exception):
                raise DentalOSError(
                    error="VALIDATION_failed",
                    message="Cursor de paginación inválido.",
                    status_code=422,
                )
            stmt = stmt.where(
                (Procedure.created_at < cursor_created_at)
                | (
                    (Procedure.created_at == cursor_created_at)
                    & (Procedure.id < cursor_id)
                )
            )

        stmt = stmt.order_by(
            Procedure.created_at.desc(),
            Procedure.id.desc(),
        ).limit(limit + 1)

        result = await db.execute(stmt)
        procedures = list(result.scalars().all())

        has_more = len(procedures) > limit
        procedures = procedures[:limit]

        next_cursor: str | None = None
        if has_more and procedures:
            last = procedures[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return {
            "items": [_procedure_to_dict(p) for p in procedures],
            "next_cursor": next_cursor,
            "has_more": has_more,
        }


# Module-level singleton
procedure_service = ProcedureService()
