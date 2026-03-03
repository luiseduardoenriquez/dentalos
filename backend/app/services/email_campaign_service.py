"""Email marketing campaign service — VP-17.

Responsibilities:
  - CRUD for EmailCampaign (draft lifecycle gating).
  - Recipient identification via patient segment filters.
  - Bulk-insert recipients and enqueue the send job.
  - Aggregated stats calculation.
  - Hardcoded template catalogue (Spanish).

Security invariants:
  - PHI is NEVER logged (no patient emails, names, or document numbers).
  - All monetary comparisons use cent values (integer).
  - Segment query always excludes unsubscribed / inactive / no-email patients.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import MarketingErrors
from app.core.exceptions import DentalOSError
from app.core.queue import publish_message
from app.models.tenant.appointment import Appointment
from app.models.tenant.email_campaign import EmailCampaign, EmailCampaignRecipient
from app.models.tenant.invoice import Invoice
from app.models.tenant.patient import Patient
from app.schemas.email_campaign import SegmentFilters
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.marketing")

# ── Built-in Spanish templates ───────────────────────────────────────────────

MARKETING_TEMPLATES: list[dict[str, str]] = [
    {
        "template_id": "recall",
        "name": "Recordatorio de cita",
        "subject_template": "¡Es hora de tu cita en {clinic_name}!",
        "description": "Recordatorio para pacientes que no han visitado recientemente",
    },
    {
        "template_id": "birthday",
        "name": "Feliz cumpleaños",
        "subject_template": "¡Feliz cumpleaños de parte de {clinic_name}! 🎂",
        "description": "Felicitación de cumpleaños con oferta especial",
    },
    {
        "template_id": "new_service",
        "name": "Nuevo servicio",
        "subject_template": "Nuevo servicio disponible en {clinic_name}",
        "description": "Anuncio de nuevo servicio o tratamiento",
    },
    {
        "template_id": "holiday",
        "name": "Saludo festivo",
        "subject_template": "¡Felices fiestas de parte de {clinic_name}!",
        "description": "Saludo para fechas especiales",
    },
    {
        "template_id": "referral_promo",
        "name": "Programa de referidos",
        "subject_template": "Refiere a un amigo y gana descuentos en {clinic_name}",
        "description": "Promoción del programa de referidos",
    },
    {
        "template_id": "membership_promo",
        "name": "Membresía",
        "subject_template": "Conoce nuestro plan de membresía en {clinic_name}",
        "description": "Promoción de planes de membresía",
    },
    {
        "template_id": "treatment_followup",
        "name": "Seguimiento de tratamiento",
        "subject_template": "¿Cómo va tu tratamiento en {clinic_name}?",
        "description": "Seguimiento a pacientes con tratamientos activos",
    },
    {
        "template_id": "post_op_care",
        "name": "Cuidados post-operatorios",
        "subject_template": "Instrucciones de cuidado - {clinic_name}",
        "description": "Recordatorio de cuidados post-operatorios",
    },
    {
        "template_id": "feedback_request",
        "name": "Encuesta de satisfacción",
        "subject_template": "¿Cómo fue tu experiencia en {clinic_name}?",
        "description": "Solicitud de retroalimentación",
    },
    {
        "template_id": "welcome_campaign",
        "name": "Bienvenida",
        "subject_template": "¡Bienvenido(a) a {clinic_name}!",
        "description": "Email de bienvenida para nuevos pacientes",
    },
]

# Index by template_id for O(1) lookup
_TEMPLATE_BY_ID: dict[str, dict[str, str]] = {
    t["template_id"]: t for t in MARKETING_TEMPLATES
}

# Statuses that allow the campaign to be mutated
_MUTABLE_STATUSES = {"draft"}
# Statuses from which a campaign can be dispatched
_SENDABLE_STATUSES = {"draft", "scheduled"}


class EmailCampaignService:
    """Stateless email campaign service.

    All methods receive an AsyncSession from the caller (injected via FastAPI
    Depends or used directly by workers). No state is held between calls.
    """

    # ── Campaign CRUD ─────────────────────────────────────────────────────────

    async def create_campaign(
        self,
        db: AsyncSession,
        data: dict[str, Any],
        created_by: uuid.UUID,
    ) -> dict[str, Any]:
        """Create a new email campaign in draft status.

        Args:
            db: Tenant-scoped async session.
            data: Validated dict from EmailCampaignCreate.
            created_by: UUID of the user creating the campaign.

        Returns:
            Campaign dict matching EmailCampaignResponse fields.
        """
        segment_filters = data.get("segment_filters") or {}
        if hasattr(segment_filters, "model_dump"):
            segment_filters = segment_filters.model_dump(exclude_none=True)

        campaign = EmailCampaign(
            name=data["name"],
            subject=data["subject"],
            template_id=data.get("template_id"),
            template_html=data.get("template_html"),
            segment_filters=segment_filters,
            status="draft",
            created_by=created_by,
            is_active=True,
        )
        db.add(campaign)
        await db.flush()
        await db.refresh(campaign)

        logger.info(
            "Email campaign created: id=%s template=%s",
            str(campaign.id)[:8],
            campaign.template_id or "custom",
        )
        return self._campaign_to_dict(campaign)

    async def update_campaign(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a draft campaign's content or segment filters.

        Raises:
            DentalOSError(CAMPAIGN_NOT_FOUND): if not found or soft-deleted.
            DentalOSError(NOT_DRAFT): if not in draft status.
        """
        campaign = await self._get_active_or_raise(db, campaign_id)

        if campaign.status not in _MUTABLE_STATUSES:
            raise DentalOSError(
                error=MarketingErrors.NOT_DRAFT,
                message=(
                    f"La campaña no puede editarse porque su estado es "
                    f"'{campaign.status}'. Solo se pueden editar campañas en borrador."
                ),
                status_code=409,
                details={"status": campaign.status},
            )

        if data.get("name") is not None:
            campaign.name = data["name"]
        if data.get("subject") is not None:
            campaign.subject = data["subject"]
        if "template_html" in data and data["template_html"] is not None:
            campaign.template_html = data["template_html"]
        if "segment_filters" in data and data["segment_filters"] is not None:
            filters = data["segment_filters"]
            if hasattr(filters, "model_dump"):
                filters = filters.model_dump(exclude_none=True)
            campaign.segment_filters = filters

        await db.flush()
        await db.refresh(campaign)
        return self._campaign_to_dict(campaign)

    async def get_campaign(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Fetch a single campaign by UUID. Returns None if not found or deleted."""
        result = await db.execute(
            select(EmailCampaign).where(
                and_(
                    EmailCampaign.id == campaign_id,
                    EmailCampaign.is_active.is_(True),
                )
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            return None
        return self._campaign_to_dict(campaign)

    async def list_campaigns(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of active campaigns, newest first."""
        offset = (page - 1) * page_size
        where = EmailCampaign.is_active.is_(True)

        total = (
            await db.execute(select(func.count(EmailCampaign.id)).where(where))
        ).scalar_one()

        result = await db.execute(
            select(EmailCampaign)
            .where(where)
            .order_by(EmailCampaign.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        campaigns = result.scalars().all()

        return {
            "items": [self._campaign_to_dict(c) for c in campaigns],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def delete_campaign(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Soft-delete a draft campaign or cancel a scheduled one.

        - draft → soft-delete (is_active=False, deleted_at=now).
        - scheduled → cancel (status='cancelled').
        - sending / sent → error.

        Returns:
            The final campaign dict.
        """
        campaign = await self._get_active_or_raise(db, campaign_id)
        now = datetime.now(UTC)

        if campaign.status == "draft":
            campaign.is_active = False
            campaign.deleted_at = now
            logger.info("Email campaign soft-deleted: id=%s", str(campaign.id)[:8])
        elif campaign.status == "scheduled":
            campaign.status = "cancelled"
            logger.info("Email campaign cancelled: id=%s", str(campaign.id)[:8])
        elif campaign.status in ("sent", "sending"):
            raise DentalOSError(
                error=MarketingErrors.ALREADY_SENT,
                message="No se puede eliminar una campaña que ya fue enviada o está en proceso de envío.",
                status_code=409,
                details={"status": campaign.status},
            )
        else:
            raise DentalOSError(
                error=MarketingErrors.ALREADY_CANCELLED,
                message="La campaña ya fue cancelada.",
                status_code=409,
                details={"status": campaign.status},
            )

        await db.flush()
        await db.refresh(campaign)
        return self._campaign_to_dict(campaign)

    # ── Recipient Identification ──────────────────────────────────────────────

    async def identify_recipients(
        self,
        db: AsyncSession,
        segment_filters: SegmentFilters | dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Build the recipient list for a campaign from segment filters.

        Always excludes:
          - Patients with email IS NULL.
          - Patients with email_unsubscribed = true.
          - Inactive patients (is_active = false).

        Additional filters (all combined with AND when provided):
          - last_visit_before / last_visit_after: joined on appointments.
          - age_min / age_max: derived from birthdate.
          - insurance_type: patients.insurance_provider ilike.
          - has_balance_due: joined on invoices with status != 'paid'.

        Returns:
            List of dicts with 'patient_id' (UUID) and 'email' (str).
        """
        # Normalise to dict for uniform access
        if segment_filters is None:
            filters: dict[str, Any] = {}
        elif hasattr(segment_filters, "model_dump"):
            filters = segment_filters.model_dump(exclude_none=True)
        else:
            filters = dict(segment_filters)

        # Base conditions — always applied
        conditions = [
            Patient.is_active.is_(True),
            Patient.email.isnot(None),
            Patient.email_unsubscribed.is_(False),
        ]

        today = date.today()

        # ── Age filter ────────────────────────────────────────────────────────
        if filters.get("age_min") is not None or filters.get("age_max") is not None:
            age_expr = func.date_part(
                "year", func.age(func.cast(today, type_=None), Patient.birthdate)
            )
            if filters.get("age_min") is not None:
                conditions.append(age_expr >= filters["age_min"])
            if filters.get("age_max") is not None:
                conditions.append(age_expr <= filters["age_max"])

        # ── Insurance type ────────────────────────────────────────────────────
        if filters.get("insurance_type") is not None:
            conditions.append(
                func.lower(Patient.insurance_provider)
                == func.lower(filters["insurance_type"])
            )

        # ── Last visit filters (subquery via appointments) ────────────────────
        need_last_visit = (
            filters.get("last_visit_before") is not None
            or filters.get("last_visit_after") is not None
        )
        if need_last_visit:
            last_visit_subq = (
                select(
                    Appointment.patient_id,
                    func.max(Appointment.scheduled_at).label("last_visit"),
                )
                .where(
                    Appointment.status.in_(["completed", "confirmed", "scheduled"])
                )
                .group_by(Appointment.patient_id)
                .subquery()
            )
            # LEFT JOIN so patients with no appointments still appear when only
            # last_visit_before is specified (no visit = counts as before any date)
            pass  # Handled below with explicit join on the full query

            if filters.get("last_visit_before") is not None:
                before_date = filters["last_visit_before"]
                # Patients whose last visit is before the threshold
                # OR patients who have never had an appointment
                conditions.append(
                    or_(
                        last_visit_subq.c.last_visit < before_date,
                        last_visit_subq.c.last_visit.is_(None),
                    )
                )
            if filters.get("last_visit_after") is not None:
                after_date = filters["last_visit_after"]
                conditions.append(last_visit_subq.c.last_visit >= after_date)

        # ── Balance due filter ────────────────────────────────────────────────
        if filters.get("has_balance_due") is True:
            unpaid_invoice_subq = (
                select(Invoice.patient_id)
                .where(Invoice.status.notin_(["paid", "cancelled", "void"]))
                .distinct()
                .scalar_subquery()
            )
            conditions.append(Patient.id.in_(unpaid_invoice_subq))
        elif filters.get("has_balance_due") is False:
            unpaid_invoice_subq = (
                select(Invoice.patient_id)
                .where(Invoice.status.notin_(["paid", "cancelled", "void"]))
                .distinct()
                .scalar_subquery()
            )
            conditions.append(Patient.id.notin_(unpaid_invoice_subq))

        # ── Build final query ─────────────────────────────────────────────────
        stmt = select(Patient.id, Patient.email).where(and_(*conditions))

        if need_last_visit:
            last_visit_subq = (
                select(
                    Appointment.patient_id,
                    func.max(Appointment.scheduled_at).label("last_visit"),
                )
                .where(
                    Appointment.status.in_(["completed", "confirmed", "scheduled"])
                )
                .group_by(Appointment.patient_id)
                .subquery()
            )
            stmt = stmt.outerjoin(
                last_visit_subq, Patient.id == last_visit_subq.c.patient_id
            )

        result = await db.execute(stmt)
        rows = result.all()

        logger.info(
            "Identified %d email recipients for campaign filters=%s",
            len(rows),
            list(filters.keys()),
        )
        return [{"patient_id": row.id, "email": row.email} for row in rows]

    # ── Send Campaign ─────────────────────────────────────────────────────────

    async def send_campaign(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Dispatch an email campaign.

        Steps:
          1. Load and validate campaign (must be draft or scheduled).
          2. Identify recipients from segment_filters.
          3. Raise NO_RECIPIENTS if list is empty.
          4. Bulk-insert EmailCampaignRecipient rows.
          5. Update campaign.status → 'sending', campaign.sent_count.
          6. Enqueue 'campaign.email.batch' to the notifications queue.

        Returns a 202-style dict with campaign_id and recipient_count.
        """
        campaign = await self._get_active_or_raise(db, campaign_id)

        if campaign.status not in _SENDABLE_STATUSES:
            raise DentalOSError(
                error=MarketingErrors.ALREADY_SENT
                if campaign.status in ("sent", "sending")
                else MarketingErrors.ALREADY_CANCELLED,
                message=(
                    f"La campaña no puede enviarse porque su estado es '{campaign.status}'."
                ),
                status_code=409,
                details={"status": campaign.status},
            )

        # Parse stored segment_filters back into SegmentFilters for the query
        raw_filters = campaign.segment_filters or {}
        segment = SegmentFilters.model_validate(raw_filters)

        recipients = await self.identify_recipients(db, segment)

        if not recipients:
            raise DentalOSError(
                error=MarketingErrors.NO_RECIPIENTS,
                message=(
                    "No se encontraron destinatarios que coincidan con los filtros "
                    "de segmentación de la campaña."
                ),
                status_code=422,
                details={"filters": raw_filters},
            )

        # Bulk-insert recipient rows
        now = datetime.now(UTC)
        recipient_objects = [
            EmailCampaignRecipient(
                campaign_id=campaign.id,
                patient_id=r["patient_id"],
                email=r["email"],
                status="pending",
            )
            for r in recipients
        ]
        db.add_all(recipient_objects)

        # Advance campaign state
        campaign.status = "sending"
        campaign.sent_count = len(recipients)
        campaign.sent_at = now

        await db.flush()
        await db.refresh(campaign)

        # Enqueue async batch send job
        message = QueueMessage(
            tenant_id=tenant_id,
            job_type="campaign.email.batch",
            payload={
                "campaign_id": str(campaign.id),
                "subject": campaign.subject,
                "template_id": campaign.template_id,
                "recipient_count": len(recipients),
            },
            priority=4,
        )
        await publish_message("notifications", message)

        logger.info(
            "Email campaign send enqueued: id=%s recipients=%d",
            str(campaign.id)[:8],
            len(recipients),
        )
        return {
            "campaign_id": campaign.id,
            "status": campaign.status,
            "recipient_count": len(recipients),
            "queued": True,
        }

    # ── Schedule Campaign ─────────────────────────────────────────────────────

    async def schedule_campaign(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        scheduled_at: datetime,
    ) -> dict[str, Any]:
        """Schedule a draft campaign for future delivery.

        Args:
            scheduled_at: UTC datetime; must be in the future (validated by schema).

        Raises:
            DentalOSError(NOT_DRAFT): if not in draft status.
        """
        campaign = await self._get_active_or_raise(db, campaign_id)

        if campaign.status not in _MUTABLE_STATUSES:
            raise DentalOSError(
                error=MarketingErrors.NOT_DRAFT,
                message=(
                    f"Solo las campañas en borrador pueden programarse. "
                    f"Estado actual: '{campaign.status}'."
                ),
                status_code=409,
                details={"status": campaign.status},
            )

        campaign.status = "scheduled"
        campaign.scheduled_at = scheduled_at

        await db.flush()
        await db.refresh(campaign)

        logger.info(
            "Email campaign scheduled: id=%s at=%s",
            str(campaign.id)[:8],
            scheduled_at.isoformat(),
        )
        return self._campaign_to_dict(campaign)

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_campaign_stats(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Aggregate engagement stats for a campaign from the recipients table.

        Falls back to the denormalized counter columns on the campaign row if
        needed. Live aggregation from recipients is used as the authoritative
        source for accuracy after tracking events.
        """
        campaign = await self._get_active_or_raise(db, campaign_id)

        result = await db.execute(
            select(
                func.count(EmailCampaignRecipient.id).label("total"),
                func.sum(
                    case((EmailCampaignRecipient.status != "pending", 1), else_=0)
                ).label("sent_count"),
                func.sum(
                    case(
                        (
                            EmailCampaignRecipient.status.in_(
                                ["opened", "clicked", "unsubscribed"]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("open_count"),
                func.sum(
                    case(
                        (
                            EmailCampaignRecipient.status.in_(
                                ["clicked"]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("click_count"),
                func.sum(
                    case(
                        (EmailCampaignRecipient.status == "bounced", 1), else_=0
                    )
                ).label("bounce_count"),
                func.sum(
                    case(
                        (EmailCampaignRecipient.status == "unsubscribed", 1), else_=0
                    )
                ).label("unsubscribe_count"),
            ).where(
                EmailCampaignRecipient.campaign_id == campaign_id
            )
        )
        row = result.one()

        sent = int(row.sent_count or 0)
        opened = int(row.open_count or 0)
        clicked = int(row.click_count or 0)
        bounced = int(row.bounce_count or 0)
        unsubscribed = int(row.unsubscribe_count or 0)

        open_rate = round((opened / sent * 100) if sent > 0 else 0.0, 2)
        click_rate = round((clicked / sent * 100) if sent > 0 else 0.0, 2)

        return {
            "sent_count": sent,
            "open_count": opened,
            "click_count": clicked,
            "bounce_count": bounced,
            "unsubscribe_count": unsubscribed,
            "open_rate": open_rate,
            "click_rate": click_rate,
        }

    async def get_campaign_recipients(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Return a paginated list of recipients for a campaign."""
        await self._get_active_or_raise(db, campaign_id)

        offset = (page - 1) * page_size
        where = EmailCampaignRecipient.campaign_id == campaign_id

        total = (
            await db.execute(
                select(func.count(EmailCampaignRecipient.id)).where(where)
            )
        ).scalar_one()

        result = await db.execute(
            select(EmailCampaignRecipient)
            .where(where)
            .order_by(EmailCampaignRecipient.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        recipients = result.scalars().all()

        return {
            "items": [self._recipient_to_dict(r) for r in recipients],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Templates ─────────────────────────────────────────────────────────────

    def get_templates(self) -> list[dict[str, str]]:
        """Return the full list of built-in Spanish marketing templates."""
        return MARKETING_TEMPLATES

    def get_template_by_id(self, template_id: str) -> dict[str, str] | None:
        """Fetch a single template by its template_id. Returns None if not found."""
        return _TEMPLATE_BY_ID.get(template_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_active_or_raise(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
    ) -> EmailCampaign:
        """Load an active EmailCampaign or raise CAMPAIGN_NOT_FOUND."""
        result = await db.execute(
            select(EmailCampaign).where(
                and_(
                    EmailCampaign.id == campaign_id,
                    EmailCampaign.is_active.is_(True),
                )
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise DentalOSError(
                error=MarketingErrors.CAMPAIGN_NOT_FOUND,
                message="Campaña de email no encontrada.",
                status_code=404,
                details={"campaign_id": str(campaign_id)},
            )
        return campaign

    def _campaign_to_dict(self, campaign: EmailCampaign) -> dict[str, Any]:
        return {
            "id": campaign.id,
            "name": campaign.name,
            "subject": campaign.subject,
            "template_id": campaign.template_id,
            "status": campaign.status,
            "scheduled_at": campaign.scheduled_at,
            "sent_at": campaign.sent_at,
            "sent_count": campaign.sent_count,
            "open_count": campaign.open_count,
            "click_count": campaign.click_count,
            "bounce_count": campaign.bounce_count,
            "unsubscribe_count": campaign.unsubscribe_count,
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
        }

    def _recipient_to_dict(
        self, recipient: EmailCampaignRecipient
    ) -> dict[str, Any]:
        return {
            "id": recipient.id,
            "patient_id": recipient.patient_id,
            "email": recipient.email,
            "status": recipient.status,
            "sent_at": recipient.sent_at,
            "opened_at": recipient.opened_at,
            "clicked_at": recipient.clicked_at,
            "created_at": recipient.created_at,
        }


# Module-level singleton — matches the pattern used by all other services
email_campaign_service = EmailCampaignService()
