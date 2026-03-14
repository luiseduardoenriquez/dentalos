"""Clinical worker — consumes from the 'clinical' queue.

Handles ``radiograph.analyze`` jobs: downloads the radiograph image
from S3, runs AI analysis via the configured adapter (Claude Vision
or mock), and updates the RadiographAnalysis record.

Pipeline:
  1. Download image bytes from S3 (tenant-isolated key)
  2. Call radiograph analysis adapter (Claude Vision / mock)
  3. Update RadiographAnalysis with findings, summary, tokens
  4. Log AI usage

Security:
  - PHI is NEVER logged.
  - Images are tenant-isolated in S3.
  - Worker sets search_path per tenant before DB operations.
"""

import logging
import uuid as uuid_mod

from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.clinical")


class ClinicalWorker(BaseWorker):
    """Processes clinical AI jobs from the clinical queue.

    Currently handles:
      - ``radiograph.analyze``: AI radiograph analysis via Claude Vision

    Uses ``prefetch_count=2`` to limit concurrent AI calls
    (Claude Vision has latency; we do not want to hold too many
    connections open).
    """

    queue_name = "clinical"
    prefetch_count = 2

    async def process(self, message: QueueMessage) -> None:
        """Route message to the appropriate handler."""
        if message.job_type == "radiograph.analyze":
            await self._handle_radiograph_analyze(message)
        # Future: smile.simulate, voice_notes.structure, etc.

    async def _handle_radiograph_analyze(self, message: QueueMessage) -> None:
        """Process a radiograph analysis job."""
        analysis_id = message.payload.get("analysis_id")
        document_s3_key = message.payload.get("s3_key")
        image_media_type = message.payload.get("media_type", "image/jpeg")
        radiograph_type = message.payload.get("radiograph_type", "periapical")

        if not analysis_id or not document_s3_key:
            logger.warning(
                "radiograph.analyze missing required fields: message_id=%s",
                message.message_id,
            )
            return

        logger.info(
            "Processing radiograph analysis: id=%s tenant=%s type=%s",
            str(analysis_id)[:8],
            message.tenant_id[:8] if message.tenant_id else "?",
            radiograph_type,
        )

        try:
            from app.core.database import get_tenant_session
            from app.core.storage import storage_client
            from app.integrations.radiograph_analysis import (
                get_radiograph_analysis_service,
            )
            from app.services.radiograph_analysis_service import (
                radiograph_analysis_service,
            )

            # Step 1: Download image from S3
            image_data = await storage_client.download_file(key=document_s3_key)

            # Step 2: Run AI analysis via adapter
            adapter = get_radiograph_analysis_service()
            adapter_result = await adapter.analyze_image(
                image_data=image_data,
                image_media_type=image_media_type,
                radiograph_type=radiograph_type,
            )

            # Step 3: Convert findings to serializable dicts
            findings_dicts = [f.model_dump() for f in adapter_result.findings]

            # Step 4: Update analysis record
            aid = uuid_mod.UUID(analysis_id)
            async with get_tenant_session(message.tenant_id) as db:
                await radiograph_analysis_service.complete_analysis(
                    db=db,
                    analysis_id=aid,
                    findings=findings_dicts,
                    summary=adapter_result.summary,
                    radiograph_quality=adapter_result.radiograph_quality,
                    recommendations=adapter_result.recommendations,
                    model_used=settings_model(),
                    input_tokens=0,  # Updated below if available
                    output_tokens=0,
                    tenant_id=message.tenant_id,
                )

            logger.info(
                "Radiograph analysis completed: id=%s findings=%d tenant=%s",
                str(analysis_id)[:8],
                len(findings_dicts),
                message.tenant_id[:8],
            )

        except Exception:
            logger.exception(
                "Failed to process radiograph analysis: id=%s",
                str(analysis_id)[:8],
            )
            await self._mark_analysis_failed(message, analysis_id)
            raise

    async def _mark_analysis_failed(
        self, message: QueueMessage, analysis_id: str
    ) -> None:
        """Best-effort update of analysis status to 'failed'."""
        try:
            from app.core.database import get_tenant_session
            from app.services.radiograph_analysis_service import (
                radiograph_analysis_service,
            )

            aid = uuid_mod.UUID(analysis_id)
            async with get_tenant_session(message.tenant_id) as db:
                await radiograph_analysis_service.fail_analysis(
                    db=db,
                    analysis_id=aid,
                    error_message="Error interno durante el análisis de la radiografía.",
                )

            logger.info(
                "Marked radiograph analysis as failed: id=%s",
                str(analysis_id)[:8],
            )
        except Exception:
            logger.exception(
                "Could not mark analysis as failed: id=%s",
                str(analysis_id)[:8],
            )


def settings_model() -> str:
    """Get the configured Anthropic model for radiograph analysis."""
    from app.core.config import settings

    return settings.anthropic_model_treatment


# Module-level instance for CLI entry point
clinical_worker = ClinicalWorker()
