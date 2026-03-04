"""NPS/CSAT survey service — VP-21.

Handles NPS survey lifecycle: send, submit response, dashboard aggregation,
per-doctor breakdown, and auto-send after appointment.

Security invariants:
  - PHI is NEVER logged (no patient names, emails, phone numbers).
  - Survey tokens are cryptographically random (secrets.token_urlsafe) and single-use.
  - Detractor handling only logs a structured event — notification integration
    is scoped to a future sprint.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, date
from typing import Any

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import SurveyErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.nps_survey import NPSSurveyResponse
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.nps_survey")


def _classify_nps(nps_score: int) -> str:
    """Classify an NPS score into promoter / passive / detractor."""
    if nps_score >= 9:
        return "promoter"
    if nps_score >= 7:
        return "passive"
    return "detractor"


def _calculate_nps(promoters: int, detractors: int, total: int) -> float:
    """Calculate NPS = (promoters% - detractors%) where % is of total responded."""
    if total == 0:
        return 0.0
    return round((promoters - detractors) / total * 100, 2)


class NPSSurveyService:
    """Stateless NPS/CSAT survey service."""

    # ── Send Survey ──────────────────────────────────────────────────────────

    async def send_survey(
        self,
        *,
        db: AsyncSession,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        appointment_id: uuid.UUID | None = None,
        channel: str = "whatsapp",
    ) -> dict[str, Any]:
        """Create an NPS survey record and return it with the token.

        Generates a cryptographically secure token for the public response
        endpoint. Returns the survey dict including the token so the caller
        can enqueue a notification.
        """
        token = secrets.token_urlsafe(48)[:64]

        survey = NPSSurveyResponse(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            channel_sent=channel,
            survey_token=token,
            sent_at=datetime.now(UTC),
            responded_at=None,
        )
        db.add(survey)
        await db.flush()
        await db.refresh(survey)

        logger.info(
            "NPS survey created: id=%s channel=%s appointment=%s",
            str(survey.id)[:8],
            channel,
            str(appointment_id)[:8] if appointment_id else "none",
        )

        return self._survey_to_dict(survey)

    # ── Submit Response ──────────────────────────────────────────────────────

    async def submit_response(
        self,
        *,
        db: AsyncSession,
        token: str,
        nps_score: int,
        csat_score: int | None,
        comments: str | None,
    ) -> dict[str, Any]:
        """Record a patient's NPS/CSAT response.

        Validates:
          - Token exists (404 if not).
          - Survey has not already been responded (409 ALREADY_RESPONDED).
          - nps_score is 0-10, csat_score is 1-5 if provided.

        If nps_score <= 6 (detractor), calls _handle_detractor for follow-up.
        """
        result = await db.execute(
            select(NPSSurveyResponse).where(
                NPSSurveyResponse.survey_token == token,
            )
        )
        survey = result.scalar_one_or_none()

        if survey is None:
            raise ResourceNotFoundError(
                error="SURVEY_not_found",
                resource_name="NPSSurveyResponse",
            )

        if survey.responded_at is not None:
            raise DentalOSError(
                error=SurveyErrors.ALREADY_RESPONDED,
                message="Esta encuesta ya fue respondida.",
                status_code=409,
            )

        # Validate scores (defensive — Pydantic already checked on the router layer)
        if not (0 <= nps_score <= 10):
            raise DentalOSError(
                error=SurveyErrors.INVALID_SCORE,
                message="El puntaje NPS debe estar entre 0 y 10.",
                status_code=422,
            )
        if csat_score is not None and not (1 <= csat_score <= 5):
            raise DentalOSError(
                error=SurveyErrors.INVALID_SCORE,
                message="El puntaje CSAT debe estar entre 1 y 5.",
                status_code=422,
            )

        survey.nps_score = nps_score
        survey.csat_score = csat_score
        survey.comments = comments
        survey.responded_at = datetime.now(UTC)

        await db.flush()

        classification = _classify_nps(nps_score)

        logger.info(
            "NPS survey response recorded: id=%s score=%d classification=%s",
            str(survey.id)[:8],
            nps_score,
            classification,
        )

        # Detractor follow-up
        if classification == "detractor":
            await self._handle_detractor(db=db, survey=survey)

        return self._survey_to_dict(survey)

    # ── Detractor Handling ───────────────────────────────────────────────────

    async def _handle_detractor(
        self, *, db: AsyncSession, survey: NPSSurveyResponse
    ) -> None:
        """Log a detractor event for clinic staff follow-up.

        Full notification integration (creating a staff_task or sending an
        internal notification) is deferred to a future sprint. For now,
        this logs a structured event that can be picked up by log aggregation.

        PHI safety: only IDs are logged, never patient name or comments.
        """
        logger.warning(
            "NPS detractor detected: survey_id=%s doctor_id=%s nps_score=%d — "
            "staff follow-up required",
            str(survey.id)[:8],
            str(survey.doctor_id)[:8] if survey.doctor_id else "unknown",
            survey.nps_score,
        )
        # TODO (Sprint 31+): Create a staff_task record or enqueue a notification
        # for the clinic_owner when full notification integration is scoped.

    # ── NPS Dashboard ────────────────────────────────────────────────────────

    async def get_nps_dashboard(
        self,
        *,
        db: AsyncSession,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Calculate overall NPS/CSAT dashboard metrics with monthly trend.

        NPS classification:
          - Promoters: 9-10
          - Passives:  7-8
          - Detractors: 0-6

        NPS score = (promoters% - detractors%) of total responded.
        Trend: last 12 full calendar months, sorted ascending.
        """
        base_conditions = [NPSSurveyResponse.responded_at.isnot(None)]
        if start_date:
            base_conditions.append(NPSSurveyResponse.responded_at >= start_date)
        if end_date:
            base_conditions.append(NPSSurveyResponse.responded_at <= end_date)

        # Aggregate totals
        agg_result = await db.execute(
            select(
                func.count(NPSSurveyResponse.id).label("total"),
                func.sum(
                    case(
                        (NPSSurveyResponse.nps_score >= 9, 1),
                        else_=0,
                    )
                ).label("promoters"),
                func.sum(
                    case(
                        (
                            and_(
                                NPSSurveyResponse.nps_score >= 7,
                                NPSSurveyResponse.nps_score <= 8,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("passives"),
                func.sum(
                    case(
                        (NPSSurveyResponse.nps_score <= 6, 1),
                        else_=0,
                    )
                ).label("detractors"),
            ).where(and_(*base_conditions))
        )
        row = agg_result.one()

        total = row.total or 0
        promoters = row.promoters or 0
        passives = row.passives or 0
        detractors = row.detractors or 0
        nps_score = _calculate_nps(promoters, detractors, total)

        # Monthly trend — group by year+month
        trend_result = await db.execute(
            select(
                extract("year", NPSSurveyResponse.responded_at).label("year"),
                extract("month", NPSSurveyResponse.responded_at).label("month"),
                func.count(NPSSurveyResponse.id).label("responses"),
                func.sum(
                    case((NPSSurveyResponse.nps_score >= 9, 1), else_=0)
                ).label("p"),
                func.sum(
                    case((NPSSurveyResponse.nps_score <= 6, 1), else_=0)
                ).label("d"),
            )
            .where(and_(*base_conditions))
            .group_by("year", "month")
            .order_by("year", "month")
        )
        trend_rows = trend_result.all()

        trend = []
        for tr in trend_rows:
            yr = int(tr.year)
            mo = int(tr.month)
            tr_total = tr.responses or 0
            tr_p = tr.p or 0
            tr_d = tr.d or 0
            trend.append(
                {
                    "period": f"{yr:04d}-{mo:02d}",
                    "nps_score": _calculate_nps(tr_p, tr_d, tr_total),
                    "responses": tr_total,
                }
            )

        return {
            "nps_score": nps_score,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "total_responses": total,
            "trend": trend,
        }

    # ── NPS by Doctor ────────────────────────────────────────────────────────

    async def get_nps_by_doctor(
        self,
        *,
        db: AsyncSession,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Aggregate NPS breakdown per doctor with names from the users table.

        Only includes doctors who have at least one responded survey.
        Doctors with no responses are excluded from the result.
        """
        base_conditions = [NPSSurveyResponse.responded_at.isnot(None)]
        if start_date:
            base_conditions.append(NPSSurveyResponse.responded_at >= start_date)
        if end_date:
            base_conditions.append(NPSSurveyResponse.responded_at <= end_date)

        result = await db.execute(
            select(
                NPSSurveyResponse.doctor_id,
                User.name.label("doctor_name"),
                func.count(NPSSurveyResponse.id).label("total"),
                func.sum(
                    case((NPSSurveyResponse.nps_score >= 9, 1), else_=0)
                ).label("promoters"),
                func.sum(
                    case(
                        (
                            and_(
                                NPSSurveyResponse.nps_score >= 7,
                                NPSSurveyResponse.nps_score <= 8,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("passives"),
                func.sum(
                    case((NPSSurveyResponse.nps_score <= 6, 1), else_=0)
                ).label("detractors"),
            )
            .join(User, User.id == NPSSurveyResponse.doctor_id, isouter=True)
            .where(and_(*base_conditions))
            .group_by(NPSSurveyResponse.doctor_id, User.name)
            .order_by(func.count(NPSSurveyResponse.id).desc())
        )
        rows = result.all()

        items = []
        for r in rows:
            total = r.total or 0
            promoters = r.promoters or 0
            passives = r.passives or 0
            detractors = r.detractors or 0
            items.append(
                {
                    "doctor_id": str(r.doctor_id) if r.doctor_id else "unknown",
                    "doctor_name": r.doctor_name or "Desconocido",
                    "nps_score": _calculate_nps(promoters, detractors, total),
                    "promoters": promoters,
                    "passives": passives,
                    "detractors": detractors,
                    "total": total,
                }
            )

        return {"items": items}

    # ── Auto-Send After Appointment ──────────────────────────────────────────

    async def auto_send_after_appointment(
        self,
        *,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Auto-send an NPS survey for a just-completed appointment.

        Idempotent: if a survey was already sent for this appointment_id,
        returns None without creating a duplicate.
        """
        existing_result = await db.execute(
            select(NPSSurveyResponse.id).where(
                NPSSurveyResponse.appointment_id == appointment_id,
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            logger.info(
                "NPS survey already sent for appointment=%s — skipping",
                str(appointment_id)[:8],
            )
            return None

        return await self.send_survey(
            db=db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            channel="whatsapp",
        )

    # ── List Surveys ─────────────────────────────────────────────────────────

    async def list_surveys(
        self,
        *,
        db: AsyncSession,
        doctor_id: uuid.UUID | None = None,
        responded: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of NPS survey records with optional filters."""
        offset = (page - 1) * page_size
        conditions: list[Any] = []

        if doctor_id is not None:
            conditions.append(NPSSurveyResponse.doctor_id == doctor_id)
        if responded is True:
            conditions.append(NPSSurveyResponse.responded_at.isnot(None))
        elif responded is False:
            conditions.append(NPSSurveyResponse.responded_at.is_(None))

        where_clause = and_(*conditions) if conditions else True  # type: ignore[arg-type]

        total_result = await db.execute(
            select(func.count(NPSSurveyResponse.id)).where(where_clause)
        )
        total = total_result.scalar_one()

        rows_result = await db.execute(
            select(NPSSurveyResponse)
            .where(where_clause)
            .order_by(NPSSurveyResponse.sent_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        surveys = rows_result.scalars().all()

        return {
            "items": [self._survey_to_dict(s) for s in surveys],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Get by Token ─────────────────────────────────────────────────────────

    async def get_survey_by_token(
        self, *, db: AsyncSession, token: str
    ) -> NPSSurveyResponse | None:
        """Fetch a survey record by its public token. Returns None if not found."""
        result = await db.execute(
            select(NPSSurveyResponse).where(
                NPSSurveyResponse.survey_token == token,
            )
        )
        return result.scalar_one_or_none()

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _survey_to_dict(survey: NPSSurveyResponse) -> dict[str, Any]:
        """Serialize an NPSSurveyResponse ORM object to a plain dict."""
        return {
            "id": survey.id,
            "patient_id": survey.patient_id,
            "appointment_id": survey.appointment_id,
            "doctor_id": survey.doctor_id,
            "nps_score": survey.nps_score,
            "csat_score": survey.csat_score,
            "comments": survey.comments,
            "channel_sent": survey.channel_sent,
            "sent_at": survey.sent_at,
            "responded_at": survey.responded_at,
        }


nps_survey_service = NPSSurveyService()
