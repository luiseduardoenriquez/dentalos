"""Prescription service — create, read, list, and generate PDFs for prescriptions.

Security invariants:
  - PHI (patient names, clinical notes) is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import PrescriptionErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.pdf import render_pdf
from app.models.tenant.patient import Patient
from app.models.tenant.prescription import Prescription
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.prescription")


def _prescription_to_dict(rx: Prescription) -> dict[str, Any]:
    """Serialize a Prescription ORM instance to a plain dict."""
    return {
        "id": str(rx.id),
        "patient_id": str(rx.patient_id),
        "doctor_id": str(rx.doctor_id),
        "medications": rx.medications,
        "diagnosis_id": str(rx.diagnosis_id) if rx.diagnosis_id else None,
        "notes": rx.notes,
        "is_active": rx.is_active,
        "created_at": rx.created_at,
        "updated_at": rx.updated_at,
    }


class PrescriptionService:
    """Stateless prescription service."""

    async def create_prescription(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        medications: list[dict],
        diagnosis_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new prescription for a patient.

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

        prescription = Prescription(
            patient_id=pid,
            doctor_id=uuid.UUID(doctor_id),
            medications=medications,
            diagnosis_id=uuid.UUID(diagnosis_id) if diagnosis_id else None,
            notes=notes,
            is_active=True,
        )
        db.add(prescription)
        await db.flush()

        logger.info(
            "Prescription created: patient=%s medications_count=%d",
            patient_id[:8],
            len(medications),
        )

        return _prescription_to_dict(prescription)

    async def get_prescription(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        prescription_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single prescription by ID."""
        result = await db.execute(
            select(Prescription).where(
                Prescription.id == uuid.UUID(prescription_id),
                Prescription.patient_id == uuid.UUID(patient_id),
                Prescription.is_active.is_(True),
            )
        )
        rx = result.scalar_one_or_none()
        if rx is None:
            return None
        return _prescription_to_dict(rx)

    async def list_prescriptions(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of prescriptions for a patient."""
        pid = uuid.UUID(patient_id)
        offset = (page - 1) * page_size

        total = (
            await db.execute(
                select(func.count(Prescription.id)).where(
                    Prescription.patient_id == pid,
                    Prescription.is_active.is_(True),
                )
            )
        ).scalar_one()

        prescriptions = (
            await db.execute(
                select(Prescription)
                .where(
                    Prescription.patient_id == pid,
                    Prescription.is_active.is_(True),
                )
                .order_by(Prescription.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()

        return {
            "items": [_prescription_to_dict(rx) for rx in prescriptions],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def generate_pdf(
        self,
        *,
        db: AsyncSession,
        prescription_id: str,
        patient_id: str,
    ) -> bytes:
        """Fetch prescription, patient, and doctor data, then render PDF.

        Raises:
            ResourceNotFoundError (404) — prescription not found.
        """
        # Fetch prescription
        rx_result = await db.execute(
            select(Prescription).where(
                Prescription.id == uuid.UUID(prescription_id),
                Prescription.patient_id == uuid.UUID(patient_id),
                Prescription.is_active.is_(True),
            )
        )
        rx = rx_result.scalar_one_or_none()
        if rx is None:
            raise ResourceNotFoundError(
                error=PrescriptionErrors.NOT_FOUND,
                resource_name="Prescription",
            )

        # Fetch patient
        patient_result = await db.execute(
            select(Patient).where(Patient.id == uuid.UUID(patient_id))
        )
        patient = patient_result.scalar_one_or_none()

        # Fetch doctor
        doctor_result = await db.execute(
            select(User).where(User.id == rx.doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()

        patient_name = (
            f"{patient.first_name} {patient.last_name}" if patient else "—"
        )
        patient_document = patient.document_number if patient else "—"
        doctor_name = doctor.name if doctor else "—"
        doctor_license = doctor.professional_license if doctor else "—"

        logger.info(
            "Prescription PDF generated: prescription=%s",
            prescription_id[:8],
        )

        return render_pdf(
            template_name="prescription_es.html",
            context={
                "patient": {
                    "name": patient_name,
                    "document_number": patient_document,
                },
                "doctor": {
                    "name": doctor_name,
                    "professional_license": doctor_license,
                },
                "medications": rx.medications,
                "notes": rx.notes,
                "prescription_date": rx.created_at,
                # clinic info is available via tenant context but injected
                # from the route handler to keep this service stateless
                "clinic": {},
            },
        )


# Module-level singleton
prescription_service = PrescriptionService()
