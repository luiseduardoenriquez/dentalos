"""Intake form service — template management and submission processing.

Security invariants:
  - PHI is NEVER logged.
  - Submission data may contain PII — handle with care.
  - Soft-delete only.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import IntakeErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.intake_form import IntakeFormTemplate, IntakeSubmission

logger = logging.getLogger("dentalos.intake")


class IntakeService:
    """Stateless intake form service."""

    # ── Template CRUD ─────────────────────────────────────────────────────────

    async def create_template(
        self, *, db: AsyncSession, created_by: str, **fields: Any,
    ) -> dict[str, Any]:
        """Create a new intake form template."""
        template = IntakeFormTemplate(
            name=fields["name"],
            fields=fields["fields"],
            consent_template_ids=fields.get("consent_template_ids"),
            is_default=fields.get("is_default", False),
            is_active=True,
            created_by=uuid.UUID(created_by),
        )
        db.add(template)
        await db.flush()
        await db.refresh(template)
        logger.info("Intake template created: id=%s", str(template.id)[:8])
        return self._template_to_dict(template)

    async def list_templates(
        self, *, db: AsyncSession, include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """List intake form templates."""
        conditions = []
        if not include_inactive:
            conditions.append(IntakeFormTemplate.is_active.is_(True))
        result = await db.execute(
            select(IntakeFormTemplate)
            .where(*conditions)
            .order_by(IntakeFormTemplate.is_default.desc(), IntakeFormTemplate.name)
        )
        return [self._template_to_dict(t) for t in result.scalars().all()]

    async def update_template(
        self, *, db: AsyncSession, template_id: str, **fields: Any,
    ) -> dict[str, Any]:
        """Update an intake form template."""
        template = await self._get_template(db, template_id)
        for key, value in fields.items():
            if value is not None and hasattr(template, key):
                setattr(template, key, value)
        await db.flush()
        await db.refresh(template)
        logger.info("Intake template updated: id=%s", str(template.id)[:8])
        return self._template_to_dict(template)

    # ── Submission Management ─────────────────────────────────────────────────

    async def create_submission(
        self, *, db: AsyncSession, template_id: str, data: dict,
        patient_id: str | None = None, appointment_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new intake form submission."""
        # Validate template exists
        await self._get_template(db, template_id)

        submission = IntakeSubmission(
            template_id=uuid.UUID(template_id),
            patient_id=uuid.UUID(patient_id) if patient_id else None,
            appointment_id=uuid.UUID(appointment_id) if appointment_id else None,
            data=data,
            status="pending",
            submitted_at=datetime.now(UTC),
            is_active=True,
        )
        db.add(submission)
        await db.flush()
        await db.refresh(submission)
        logger.info("Intake submission created: id=%s", str(submission.id)[:8])
        return self._submission_to_dict(submission)

    async def list_submissions(
        self, *, db: AsyncSession, status: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> dict[str, Any]:
        """List intake submissions with optional status filter.

        Returns enriched data with patient name, template name, phone, and
        structured responses for the staff-facing dashboard.
        """
        from app.models.tenant.intake_form import IntakeFormTemplate
        from app.models.tenant.patient import Patient

        offset = (page - 1) * page_size
        conditions = [IntakeSubmission.is_active.is_(True)]
        if status:
            conditions.append(IntakeSubmission.status == status)

        total = (await db.execute(
            select(func.count(IntakeSubmission.id)).where(*conditions)
        )).scalar_one()

        result = await db.execute(
            select(IntakeSubmission)
            .where(*conditions)
            .order_by(IntakeSubmission.submitted_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        submissions = result.scalars().all()

        # Batch-load related templates and patients
        template_ids = {s.template_id for s in submissions}
        patient_ids = {s.patient_id for s in submissions if s.patient_id}

        templates_map: dict[str, str] = {}
        if template_ids:
            tmpl_result = await db.execute(
                select(IntakeFormTemplate.id, IntakeFormTemplate.name, IntakeFormTemplate.fields)
                .where(IntakeFormTemplate.id.in_(template_ids))
            )
            for row in tmpl_result.all():
                templates_map[str(row[0])] = {"name": row[1], "fields": row[2]}

        patients_map: dict[str, dict] = {}
        if patient_ids:
            pat_result = await db.execute(
                select(Patient.id, Patient.first_name, Patient.last_name, Patient.phone, Patient.email)
                .where(Patient.id.in_(patient_ids))
            )
            for row in pat_result.all():
                patients_map[str(row[0])] = {
                    "name": f"{row[1]} {row[2]}",
                    "phone": row[3],
                    "email": row[4],
                }

        items = []
        for sub in submissions:
            enriched = self._submission_to_enriched_dict(sub, templates_map, patients_map)
            items.append(enriched)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def approve_submission(
        self, *, db: AsyncSession, submission_id: str, reviewed_by: str,
    ) -> dict[str, Any]:
        """Approve a submission and auto-populate patient records."""
        sub = await self._get_submission(db, submission_id)

        if sub.status == "approved":
            raise DentalOSError(
                error=IntakeErrors.ALREADY_APPROVED,
                message="Esta solicitud ya fue aprobada.",
                status_code=409,
            )

        sub.status = "approved"
        sub.reviewed_by = uuid.UUID(reviewed_by)
        sub.reviewed_at = datetime.now(UTC)

        # Auto-populate patient records from submission data
        await self._auto_populate_patient_records(db=db, submission=sub)

        await db.flush()
        await db.refresh(sub)
        logger.info("Intake submission approved: id=%s", str(sub.id)[:8])
        return self._submission_to_dict(sub)

    async def reject_submission(
        self, *, db: AsyncSession, submission_id: str, reviewed_by: str,
    ) -> dict[str, Any]:
        """Reject a submission."""
        sub = await self._get_submission(db, submission_id)

        if sub.status == "rejected":
            raise DentalOSError(
                error=IntakeErrors.ALREADY_APPROVED,
                message="Esta solicitud ya fue rechazada.",
                status_code=409,
            )

        sub.status = "rejected"
        sub.reviewed_by = uuid.UUID(reviewed_by)
        sub.reviewed_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(sub)
        logger.info("Intake submission rejected: id=%s", str(sub.id)[:8])
        return self._submission_to_dict(sub)

    async def _auto_populate_patient_records(
        self, *, db: AsyncSession, submission: IntakeSubmission,
    ) -> None:
        """Create or update patient + anamnesis from approved submission data."""
        data = submission.data or {}

        if submission.patient_id:
            # Update existing patient with submitted data
            from app.models.tenant.patient import Patient

            patient_result = await db.execute(
                select(Patient).where(Patient.id == submission.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient:
                for field in ["phone", "email", "address", "city", "emergency_contact_name", "emergency_contact_phone"]:
                    if field in data and data[field]:
                        setattr(patient, field, data[field])
        else:
            # Create new patient from submission
            from app.models.tenant.patient import Patient

            required_fields = ["first_name", "last_name", "document_type", "document_number"]
            if all(f in data for f in required_fields):
                patient = Patient(
                    first_name=data["first_name"].strip(),
                    last_name=data["last_name"].strip(),
                    document_type=data["document_type"],
                    document_number=data["document_number"],
                    phone=data.get("phone"),
                    email=data.get("email"),
                    address=data.get("address"),
                    city=data.get("city"),
                    birthdate=data.get("birthdate"),
                    gender=data.get("gender"),
                    blood_type=data.get("blood_type"),
                    allergies=data.get("allergies"),
                    chronic_conditions=data.get("chronic_conditions"),
                    emergency_contact_name=data.get("emergency_contact_name"),
                    emergency_contact_phone=data.get("emergency_contact_phone"),
                    insurance_provider=data.get("insurance_provider"),
                    insurance_policy_number=data.get("insurance_policy_number"),
                    is_active=True,
                )
                db.add(patient)
                await db.flush()
                submission.patient_id = patient.id

        # Create anamnesis record if medical history data present
        medical_fields = ["allergies", "chronic_conditions", "current_medications", "medical_history"]
        has_medical = any(data.get(f) for f in medical_fields)
        if has_medical and submission.patient_id:
            from app.models.tenant.clinical_record import Anamnesis

            anamnesis = Anamnesis(
                patient_id=submission.patient_id,
                allergies=data.get("allergies", []),
                chronic_conditions=data.get("chronic_conditions", []),
                current_medications=data.get("current_medications"),
                medical_history=data.get("medical_history"),
                family_history=data.get("family_history"),
                habits=data.get("habits"),
            )
            db.add(anamnesis)

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get_template(self, db: AsyncSession, template_id: str) -> IntakeFormTemplate:
        result = await db.execute(
            select(IntakeFormTemplate).where(
                IntakeFormTemplate.id == uuid.UUID(template_id),
                IntakeFormTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise ResourceNotFoundError(
                error=IntakeErrors.TEMPLATE_NOT_FOUND,
                resource_name="IntakeFormTemplate",
            )
        return template

    async def _get_submission(self, db: AsyncSession, submission_id: str) -> IntakeSubmission:
        result = await db.execute(
            select(IntakeSubmission).where(
                IntakeSubmission.id == uuid.UUID(submission_id),
                IntakeSubmission.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            raise ResourceNotFoundError(
                error=IntakeErrors.SUBMISSION_NOT_FOUND,
                resource_name="IntakeSubmission",
            )
        return sub

    def _template_to_dict(self, template: IntakeFormTemplate) -> dict[str, Any]:
        return {
            "id": str(template.id),
            "name": template.name,
            "fields": template.fields,
            "consent_template_ids": template.consent_template_ids,
            "is_default": template.is_default,
            "is_active": template.is_active,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }

    def _submission_to_dict(self, sub: IntakeSubmission) -> dict[str, Any]:
        return {
            "id": str(sub.id),
            "template_id": str(sub.template_id),
            "patient_id": str(sub.patient_id) if sub.patient_id else None,
            "appointment_id": str(sub.appointment_id) if sub.appointment_id else None,
            "data": sub.data,
            "status": sub.status,
            "submitted_at": sub.submitted_at,
            "reviewed_by": str(sub.reviewed_by) if sub.reviewed_by else None,
            "reviewed_at": sub.reviewed_at,
            "is_active": sub.is_active,
            "created_at": sub.created_at,
            "updated_at": sub.updated_at,
        }

    def _submission_to_enriched_dict(
        self,
        sub: IntakeSubmission,
        templates_map: dict[str, dict],
        patients_map: dict[str, dict],
    ) -> dict[str, Any]:
        """Enriched submission dict for the staff dashboard list view."""
        data = sub.data or {}
        template_info = templates_map.get(str(sub.template_id), {})
        template_name = template_info.get("name", "")
        template_fields = template_info.get("fields", [])

        patient_info = patients_map.get(str(sub.patient_id), {}) if sub.patient_id else {}
        # Patient name from linked patient, or from submission data
        patient_name = patient_info.get("name", "")
        if not patient_name:
            first = data.get("first_name", "")
            last = data.get("last_name", "")
            patient_name = f"{first} {last}".strip()

        patient_phone = patient_info.get("phone") or data.get("phone", "")
        patient_email = patient_info.get("email") or data.get("email")

        # Build responses from template fields + submission data
        responses: list[dict[str, str]] = []
        if isinstance(template_fields, list):
            for field in template_fields:
                if isinstance(field, dict):
                    field_name = field.get("name", "")
                    label = field.get("label", field_name)
                    value = data.get(field_name, "")
                    if isinstance(value, (list, dict)):
                        value = str(value)
                    responses.append({"label": label, "value": str(value) if value else ""})

        return {
            "id": str(sub.id),
            "template_name": template_name,
            "patient_name": patient_name,
            "patient_email": patient_email,
            "patient_phone": patient_phone,
            "submitted_at": sub.submitted_at,
            "status": sub.status,
            "responses": responses,
            "matched_patient_id": str(sub.patient_id) if sub.patient_id else None,
        }


intake_service = IntakeService()
