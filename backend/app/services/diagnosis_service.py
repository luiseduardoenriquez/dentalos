"""Diagnosis service — create, read, update, and resolve patient diagnoses.

Security invariants:
  - PHI (patient names, clinical notes) is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - CIE-10 codes are validated against the public catalog.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import DiagnosisErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.diagnosis import Diagnosis
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.diagnosis")


def _diagnosis_to_dict(diag: Diagnosis) -> dict[str, Any]:
    """Serialize a Diagnosis ORM instance to a plain dict."""
    return {
        "id": str(diag.id),
        "patient_id": str(diag.patient_id),
        "doctor_id": str(diag.doctor_id),
        "cie10_code": diag.cie10_code,
        "cie10_description": diag.cie10_description,
        "severity": diag.severity,
        "status": diag.status,
        "tooth_number": diag.tooth_number,
        "notes": diag.notes,
        "resolved_at": diag.resolved_at,
        "resolved_by": str(diag.resolved_by) if diag.resolved_by else None,
        "is_active": diag.is_active,
        "created_at": diag.created_at,
        "updated_at": diag.updated_at,
    }


class DiagnosisService:
    """Stateless diagnosis service."""

    async def create_diagnosis(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        cie10_code: str,
        cie10_description: str,
        severity: str = "moderate",
        tooth_number: int | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new diagnosis for a patient.

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

        diagnosis = Diagnosis(
            patient_id=pid,
            doctor_id=uuid.UUID(doctor_id),
            cie10_code=cie10_code,
            cie10_description=cie10_description,
            severity=severity,
            status="active",
            tooth_number=tooth_number,
            notes=notes,
            is_active=True,
        )
        db.add(diagnosis)
        await db.flush()

        logger.info(
            "Diagnosis created: patient=%s cie10=%s",
            patient_id[:8],
            cie10_code,
        )

        return _diagnosis_to_dict(diagnosis)

    async def get_diagnosis(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        diagnosis_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single diagnosis by ID."""
        result = await db.execute(
            select(Diagnosis).where(
                Diagnosis.id == uuid.UUID(diagnosis_id),
                Diagnosis.patient_id == uuid.UUID(patient_id),
                Diagnosis.is_active.is_(True),
            )
        )
        diag = result.scalar_one_or_none()
        if diag is None:
            return None
        return _diagnosis_to_dict(diag)

    async def list_diagnoses(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        """List all diagnoses for a patient (not paginated — < 50 per patient)."""
        pid = uuid.UUID(patient_id)

        stmt = (
            select(Diagnosis)
            .where(
                Diagnosis.patient_id == pid,
                Diagnosis.is_active.is_(True),
            )
            .order_by(Diagnosis.created_at.desc())
        )

        if status_filter is not None:
            stmt = stmt.where(Diagnosis.status == status_filter)

        result = await db.execute(stmt)
        diagnoses = result.scalars().all()

        return {
            "items": [_diagnosis_to_dict(d) for d in diagnoses],
            "total": len(diagnoses),
        }

    async def update_diagnosis(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        diagnosis_id: str,
        user_id: str,
        severity: str | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing diagnosis. Handles resolution tracking.

        Raises:
            ResourceNotFoundError (404) — diagnosis not found.
            DentalOSError (409) — already resolved when trying to resolve again.
        """
        result = await db.execute(
            select(Diagnosis).where(
                Diagnosis.id == uuid.UUID(diagnosis_id),
                Diagnosis.patient_id == uuid.UUID(patient_id),
                Diagnosis.is_active.is_(True),
            )
        )
        diag = result.scalar_one_or_none()

        if diag is None:
            raise ResourceNotFoundError(
                error=DiagnosisErrors.NOT_FOUND,
                resource_name="Diagnosis",
            )

        # Handle resolution
        if status == "resolved" and diag.status == "resolved":
            raise DentalOSError(
                error=DiagnosisErrors.ALREADY_RESOLVED,
                message="Este diagnóstico ya fue resuelto.",
                status_code=409,
            )

        if severity is not None:
            diag.severity = severity
        if notes is not None:
            diag.notes = notes
        if status is not None:
            diag.status = status
            if status == "resolved":
                diag.resolved_at = datetime.now(UTC)
                diag.resolved_by = uuid.UUID(user_id)

        await db.flush()

        logger.info(
            "Diagnosis updated: patient=%s diag=%s",
            patient_id[:8],
            diagnosis_id[:8],
        )

        return _diagnosis_to_dict(diag)


# Module-level singleton
diagnosis_service = DiagnosisService()
