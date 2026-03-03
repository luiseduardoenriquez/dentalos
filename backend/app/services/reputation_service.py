"""Reputation management service — VP-09.

Handles satisfaction survey lifecycle: send, record response, dashboard
aggregation, and private feedback listing.

Security invariants:
  - PHI is NEVER logged (no patient names, emails, phone numbers).
  - Survey tokens are cryptographically random and single-use.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import AppointmentErrors, ReputationErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.appointment import Appointment
from app.models.tenant.satisfaction_survey import SatisfactionSurvey
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.reputation")


class ReputationService:
    """Stateless reputation management service."""

    # ── Send Survey ──────────────────────────────────────────────────────────

    async def send_survey(
        self,
        *,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        channel: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Create a survey record and enqueue a notification to send it.

        Resolves the patient from the appointment, generates a
        cryptographically secure token for the public response endpoint,
        and publishes a message to the notifications queue.
        """
        # Resolve patient_id from the appointment
        appt_result = await db.execute(
            select(Appointment.patient_id).where(Appointment.id == appointment_id)
        )
        patient_id = appt_result.scalar_one_or_none()
        if patient_id is None:
            raise ResourceNotFoundError(
                error=AppointmentErrors.NOT_FOUND,
                resource_name="Appointment",
            )

        token = secrets.token_urlsafe(48)[:64]

        survey = SatisfactionSurvey(
            patient_id=patient_id,
            appointment_id=appointment_id,
            channel_sent=channel,
            survey_token=token,
            sent_at=datetime.now(UTC),
        )
        db.add(survey)
        await db.flush()
        await db.refresh(survey)

        # Enqueue notification for async delivery
        await publish_message(
            "notifications",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="survey.send",
                payload={
                    "survey_id": str(survey.id),
                    "patient_id": str(patient_id),
                    "appointment_id": str(appointment_id),
                    "channel": channel,
                    "survey_token": token,
                },
            ),
        )

        logger.info(
            "Satisfaction survey created and queued: id=%s channel=%s",
            str(survey.id)[:8],
            channel,
        )

        return {
            "id": str(survey.id),
            "patient_id": str(survey.patient_id),
            "appointment_id": str(survey.appointment_id),
            "score": survey.score,
            "feedback_text": survey.feedback_text,
            "channel_sent": survey.channel_sent,
            "survey_token": survey.survey_token,
            "routed_to": survey.routed_to,
            "sent_at": survey.sent_at,
            "responded_at": survey.responded_at,
            "created_at": survey.created_at,
        }

    # ── Record Response ──────────────────────────────────────────────────────

    async def record_response(
        self,
        *,
        db: AsyncSession,
        token: str,
        score: int,
        feedback_text: str | None,
        tenant_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a patient's survey response and route accordingly.

        Routing logic:
          - score >= threshold (default 4) -> routed_to='google_review'
          - score < threshold             -> routed_to='private_feedback'

        The threshold and google_review_url are read from tenant settings.

        Returns a dict with routed_to and google_review_url (if applicable).
        """
        result = await db.execute(
            select(SatisfactionSurvey).where(
                SatisfactionSurvey.survey_token == token,
            )
        )
        survey = result.scalar_one_or_none()

        if survey is None:
            raise ResourceNotFoundError(
                error=ReputationErrors.SURVEY_NOT_FOUND,
                resource_name="SatisfactionSurvey",
            )

        if survey.responded_at is not None:
            raise DentalOSError(
                error=ReputationErrors.SURVEY_ALREADY_RESPONDED,
                message="Esta encuesta ya fue respondida.",
                status_code=409,
            )

        # Read routing threshold and Google Review URL from tenant settings
        settings = tenant_settings or {}
        review_threshold = settings.get("review_score_threshold", 4)
        google_review_url = settings.get("google_review_url")

        # Determine routing
        if score >= review_threshold:
            routed_to = "google_review"
        else:
            routed_to = "private_feedback"

        survey.score = score
        survey.feedback_text = feedback_text
        survey.responded_at = datetime.now(UTC)
        survey.routed_to = routed_to

        await db.flush()

        logger.info(
            "Survey response recorded: id=%s score=%d routed_to=%s",
            str(survey.id)[:8],
            score,
            routed_to,
        )

        return {
            "routed_to": routed_to,
            "google_review_url": google_review_url if routed_to == "google_review" else None,
        }

    # ── Dashboard ────────────────────────────────────────────────────────────

    async def get_dashboard(self, *, db: AsyncSession) -> dict[str, Any]:
        """Aggregate reputation metrics for the dashboard.

        Metrics:
          - average_score: mean of all non-null scores
          - total_surveys: total surveys sent
          - response_rate: responded / total * 100
          - nps_score: (promoters[5] - detractors[1-3]) / responded * 100
          - review_count: surveys routed to google_review
          - private_feedback_count: surveys routed to private_feedback
        """
        # Total surveys
        total_result = await db.execute(
            select(func.count(SatisfactionSurvey.id))
        )
        total_surveys = total_result.scalar_one()

        if total_surveys == 0:
            return {
                "average_score": 0.0,
                "total_surveys": 0,
                "response_rate": 0.0,
                "nps_score": 0.0,
                "review_count": 0,
                "private_feedback_count": 0,
            }

        # Aggregate scores and routing
        stats_result = await db.execute(
            select(
                func.avg(SatisfactionSurvey.score).label("avg_score"),
                func.count(SatisfactionSurvey.responded_at).label("responded_count"),
                func.sum(
                    case(
                        (SatisfactionSurvey.score == 5, 1),
                        else_=0,
                    )
                ).label("promoters"),
                func.sum(
                    case(
                        (SatisfactionSurvey.score.in_([1, 2, 3]), 1),
                        else_=0,
                    )
                ).label("detractors"),
                func.sum(
                    case(
                        (SatisfactionSurvey.routed_to == "google_review", 1),
                        else_=0,
                    )
                ).label("review_count"),
                func.sum(
                    case(
                        (SatisfactionSurvey.routed_to == "private_feedback", 1),
                        else_=0,
                    )
                ).label("private_feedback_count"),
            )
        )
        row = stats_result.one()

        avg_score = float(row.avg_score) if row.avg_score is not None else 0.0
        responded_count = row.responded_count or 0
        promoters = row.promoters or 0
        detractors = row.detractors or 0
        review_count = row.review_count or 0
        private_feedback_count = row.private_feedback_count or 0

        response_rate = (responded_count / total_surveys * 100) if total_surveys > 0 else 0.0
        nps_score = (
            ((promoters - detractors) / responded_count * 100)
            if responded_count > 0
            else 0.0
        )

        return {
            "average_score": round(avg_score, 2),
            "total_surveys": total_surveys,
            "response_rate": round(response_rate, 2),
            "nps_score": round(nps_score, 2),
            "review_count": review_count,
            "private_feedback_count": private_feedback_count,
        }

    # ── Feedback Listing ─────────────────────────────────────────────────────

    async def get_feedback(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List surveys routed to private_feedback, paginated.

        Only returns surveys that have been responded to and routed
        to private_feedback (i.e. detractor/neutral responses).
        """
        offset = (page - 1) * page_size
        conditions = [
            SatisfactionSurvey.routed_to == "private_feedback",
            SatisfactionSurvey.responded_at.isnot(None),
        ]

        # Total count
        total_result = await db.execute(
            select(func.count(SatisfactionSurvey.id)).where(*conditions)
        )
        total = total_result.scalar_one()

        # Fetch page
        result = await db.execute(
            select(SatisfactionSurvey)
            .where(*conditions)
            .order_by(SatisfactionSurvey.responded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        surveys = result.scalars().all()

        items = [self._survey_to_dict(s) for s in surveys]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Private Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _survey_to_dict(survey: SatisfactionSurvey) -> dict[str, Any]:
        """Serialize a SatisfactionSurvey to a dict."""
        return {
            "id": str(survey.id),
            "patient_id": str(survey.patient_id),
            "appointment_id": str(survey.appointment_id) if survey.appointment_id else None,
            "score": survey.score,
            "feedback_text": survey.feedback_text,
            "channel_sent": survey.channel_sent,
            "survey_token": survey.survey_token,
            "routed_to": survey.routed_to,
            "sent_at": survey.sent_at,
            "responded_at": survey.responded_at,
            "created_at": survey.created_at,
        }


reputation_service = ReputationService()
