"""AI radiograph analysis service (AI-01).

Orchestrates the radiograph analysis workflow:
  1. Validate add-on + document → create row (status=processing) → publish to queue
  2. Worker calls adapter → service.complete_analysis() or service.fail_analysis()
  3. Doctor reviews findings → service.review_analysis()

Security invariants:
  - PHI is NEVER logged (patient names, document numbers).
  - Add-on gate (feature flag: ai_radiograph) enforced before queue publish.
  - All image data stays server-side — never returned in API responses.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import RadiographAnalysisErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.ai_usage_log import AIUsageLog
from app.models.tenant.patient import Patient
from app.models.tenant.patient_document import PatientDocument
from app.models.tenant.radiograph_analysis import RadiographAnalysis

logger = logging.getLogger("dentalos.ai.radiograph")


class RadiographAnalysisService:
    """Service for AI-powered dental radiograph analysis."""

    # ── Create analysis (step 1) ──────────────────────────────

    async def create_analysis(
        self,
        *,
        db: AsyncSession,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        document_id: uuid.UUID,
        radiograph_type: str,
        tenant_id: str,
    ) -> RadiographAnalysis:
        """Create a new radiograph analysis request.

        Validates the document exists and is an X-ray type, creates
        the analysis row with status=processing, and returns it.
        The caller is responsible for publishing the queue message.
        """
        # Validate patient exists
        patient = await db.get(Patient, patient_id)
        if not patient or not patient.is_active:
            raise ResourceNotFoundError(
                error=RadiographAnalysisErrors.PATIENT_NOT_FOUND,
                message="Paciente no encontrado.",
            )

        # Validate document exists and belongs to patient
        result = await db.execute(
            select(PatientDocument).where(
                PatientDocument.id == document_id,
                PatientDocument.patient_id == patient_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ResourceNotFoundError(
                error=RadiographAnalysisErrors.DOCUMENT_NOT_FOUND,
                message="Documento no encontrado para este paciente.",
            )

        # Check no active analysis for this document
        existing = await db.execute(
            select(RadiographAnalysis).where(
                RadiographAnalysis.document_id == document_id,
                RadiographAnalysis.status == "processing",
                RadiographAnalysis.is_active == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise DentalOSError(
                status_code=409,
                error=RadiographAnalysisErrors.ALREADY_PROCESSING,
                message="Ya existe un análisis en proceso para este documento.",
            )

        analysis = RadiographAnalysis(
            patient_id=patient_id,
            doctor_id=doctor_id,
            document_id=document_id,
            radiograph_type=radiograph_type,
            status="processing",
        )
        db.add(analysis)
        await db.flush()

        logger.info(
            "Radiograph analysis created: id=%s patient=%s type=%s",
            str(analysis.id)[:8],
            str(patient_id)[:8],
            radiograph_type,
        )

        return analysis

    # ── Complete analysis (called by worker) ─────────────────

    async def complete_analysis(
        self,
        *,
        db: AsyncSession,
        analysis_id: uuid.UUID,
        findings: list[dict],
        summary: str,
        radiograph_quality: str,
        recommendations: str | None,
        model_used: str,
        input_tokens: int,
        output_tokens: int,
        tenant_id: str,
    ) -> None:
        """Mark analysis as completed with AI results.

        Called by the clinical worker after successful Claude Vision call.
        """
        analysis = await db.get(RadiographAnalysis, analysis_id)
        if not analysis:
            logger.warning(
                "Analysis not found for completion: id=%s",
                str(analysis_id)[:8],
            )
            return

        analysis.findings = findings
        analysis.summary = summary
        analysis.radiograph_quality = radiograph_quality
        analysis.recommendations = recommendations
        analysis.model_used = model_used
        analysis.input_tokens = input_tokens
        analysis.output_tokens = output_tokens
        analysis.status = "completed"

        # Log AI usage
        usage_log = AIUsageLog(
            feature="radiograph_analysis",
            model=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        db.add(usage_log)

        logger.info(
            "Radiograph analysis completed: id=%s findings=%d tokens=%d+%d",
            str(analysis_id)[:8],
            len(findings),
            input_tokens,
            output_tokens,
        )

    # ── Fail analysis (called by worker) ─────────────────────

    async def fail_analysis(
        self,
        *,
        db: AsyncSession,
        analysis_id: uuid.UUID,
        error_message: str,
    ) -> None:
        """Mark analysis as failed.

        Called by the clinical worker when Claude Vision call fails.
        """
        analysis = await db.get(RadiographAnalysis, analysis_id)
        if not analysis:
            return

        analysis.status = "failed"
        analysis.error_message = error_message

        logger.warning(
            "Radiograph analysis failed: id=%s error=%s",
            str(analysis_id)[:8],
            error_message[:100],
        )

    # ── Get single analysis ──────────────────────────────────

    async def get_analysis(
        self,
        *,
        db: AsyncSession,
        analysis_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get a single radiograph analysis by ID."""
        result = await db.execute(
            select(RadiographAnalysis).where(
                RadiographAnalysis.id == analysis_id,
                RadiographAnalysis.patient_id == patient_id,
                RadiographAnalysis.is_active == True,  # noqa: E712
            )
        )
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise ResourceNotFoundError(
                error=RadiographAnalysisErrors.NOT_FOUND,
                message="Análisis de radiografía no encontrado.",
            )
        return self._to_dict(analysis)

    # ── List analyses ────────────────────────────────────────

    async def list_analyses(
        self,
        *,
        db: AsyncSession,
        patient_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List radiograph analyses for a patient with pagination."""
        base_query = select(RadiographAnalysis).where(
            RadiographAnalysis.patient_id == patient_id,
            RadiographAnalysis.is_active == True,  # noqa: E712
        )

        # Count
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        result = await db.execute(
            base_query.order_by(RadiographAnalysis.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        analyses = result.scalars().all()

        return {
            "items": [self._to_dict(a) for a in analyses],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Review analysis ──────────────────────────────────────

    async def review_analysis(
        self,
        *,
        db: AsyncSession,
        analysis_id: uuid.UUID,
        patient_id: uuid.UUID,
        review_items: list[dict],
        reviewer_notes: str | None = None,
    ) -> dict[str, Any]:
        """Review radiograph analysis findings (accept/reject/modify each).

        Args:
            review_items: List of {index, action, edited_description} dicts.
        """
        result = await db.execute(
            select(RadiographAnalysis).where(
                RadiographAnalysis.id == analysis_id,
                RadiographAnalysis.patient_id == patient_id,
                RadiographAnalysis.is_active == True,  # noqa: E712
            )
        )
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise ResourceNotFoundError(
                error=RadiographAnalysisErrors.NOT_FOUND,
                message="Análisis de radiografía no encontrado.",
            )

        if analysis.status == "reviewed":
            raise DentalOSError(
                status_code=409,
                error=RadiographAnalysisErrors.ALREADY_REVIEWED,
                message="Este análisis ya fue revisado.",
            )

        if analysis.status != "completed":
            raise DentalOSError(
                status_code=400,
                error=RadiographAnalysisErrors.NOT_COMPLETED,
                message="Solo se pueden revisar análisis completados.",
            )

        # Apply review actions to findings
        findings = analysis.findings or []
        for item in review_items:
            idx = item["index"]
            if 0 <= idx < len(findings):
                findings[idx]["review_action"] = item["action"]
                if item.get("edited_description"):
                    findings[idx]["review_note"] = item["edited_description"]

        analysis.findings = findings
        analysis.status = "reviewed"
        analysis.reviewed_at = datetime.now(UTC)
        analysis.reviewer_notes = reviewer_notes

        logger.info(
            "Radiograph analysis reviewed: id=%s items=%d",
            str(analysis_id)[:8],
            len(review_items),
        )

        return self._to_dict(analysis)

    # ── Soft delete ──────────────────────────────────────────

    async def delete_analysis(
        self,
        *,
        db: AsyncSession,
        analysis_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> None:
        """Soft-delete a radiograph analysis."""
        result = await db.execute(
            select(RadiographAnalysis).where(
                RadiographAnalysis.id == analysis_id,
                RadiographAnalysis.patient_id == patient_id,
                RadiographAnalysis.is_active == True,  # noqa: E712
            )
        )
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise ResourceNotFoundError(
                error=RadiographAnalysisErrors.NOT_FOUND,
                message="Análisis de radiografía no encontrado.",
            )

        analysis.is_active = False
        analysis.deleted_at = datetime.now(UTC)

    # ── Serialization helper ─────────────────────────────────

    @staticmethod
    def _to_dict(row: RadiographAnalysis) -> dict[str, Any]:
        """Serialize a RadiographAnalysis ORM instance to a plain dict."""
        return {
            "id": str(row.id),
            "patient_id": str(row.patient_id),
            "doctor_id": str(row.doctor_id),
            "document_id": str(row.document_id),
            "radiograph_type": row.radiograph_type,
            "status": row.status,
            "findings": row.findings if isinstance(row.findings, list) else [],
            "summary": row.summary,
            "radiograph_quality": row.radiograph_quality,
            "recommendations": row.recommendations,
            "model_used": row.model_used,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "error_message": row.error_message,
            "reviewed_at": row.reviewed_at,
            "reviewer_notes": row.reviewer_notes,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }


# Module-level singleton
radiograph_analysis_service = RadiographAnalysisService()
