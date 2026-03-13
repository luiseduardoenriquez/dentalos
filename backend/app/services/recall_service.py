"""Recall campaign service — CRUD + patient identification + step processing.

Security invariants:
  - PHI is NEVER logged.
  - Campaign recipients are identified via queries, not stored patient data.
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import RecallErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.appointment import Appointment
from app.models.tenant.patient import Patient
from app.models.tenant.recall_campaign import RecallCampaign, RecallCampaignRecipient
from app.models.tenant.treatment_plan import TreatmentPlan

logger = logging.getLogger("dentalos.recall")


class RecallService:
    """Stateless recall campaign service."""

    # ── Campaign CRUD ─────────────────────────────────────────────────────────

    async def create_campaign(
        self, *, db: AsyncSession, created_by: str, **fields: Any,
    ) -> dict[str, Any]:
        """Create a new recall campaign in draft status."""
        campaign = RecallCampaign(
            name=fields["name"],
            type=fields["type"],
            filters=fields.get("filters"),
            message_templates=fields.get("message_templates"),
            channel=fields.get("channel", "whatsapp"),
            schedule=fields.get("schedule"),
            status="draft",
            created_by=uuid.UUID(created_by),
            is_active=True,
        )
        db.add(campaign)
        await db.flush()
        await db.refresh(campaign)
        logger.info("Recall campaign created: id=%s type=%s", str(campaign.id)[:8], campaign.type)
        return await self._campaign_to_dict(db, campaign)

    async def list_campaigns(
        self, *, db: AsyncSession, page: int = 1, page_size: int = 20,
    ) -> dict[str, Any]:
        """List campaigns with aggregated stats."""
        offset = (page - 1) * page_size
        conditions = [RecallCampaign.is_active.is_(True)]

        total = (await db.execute(
            select(func.count(RecallCampaign.id)).where(*conditions)
        )).scalar_one()

        result = await db.execute(
            select(RecallCampaign)
            .where(*conditions)
            .order_by(RecallCampaign.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        campaigns = result.scalars().all()

        items = []
        for c in campaigns:
            items.append(await self._campaign_to_dict(db, c))

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_campaign(
        self, *, db: AsyncSession, campaign_id: str,
    ) -> dict[str, Any]:
        """Get a single campaign by ID with aggregated stats."""
        campaign = await self._get_campaign(db, campaign_id)
        return await self._campaign_to_dict(db, campaign)

    async def update_campaign(
        self, *, db: AsyncSession, campaign_id: str, **fields: Any,
    ) -> dict[str, Any]:
        """Update a campaign (only draft campaigns can be edited)."""
        campaign = await self._get_campaign(db, campaign_id)
        for key, value in fields.items():
            if value is not None and hasattr(campaign, key):
                setattr(campaign, key, value)
        await db.flush()
        await db.refresh(campaign)
        logger.info("Recall campaign updated: id=%s", str(campaign.id)[:8])
        return await self._campaign_to_dict(db, campaign)

    async def activate_campaign(
        self, *, db: AsyncSession, campaign_id: str,
    ) -> dict[str, Any]:
        """Activate a draft or paused campaign."""
        campaign = await self._get_campaign(db, campaign_id)
        if campaign.status not in ("draft", "paused"):
            raise DentalOSError(
                error=RecallErrors.CANNOT_ACTIVATE,
                message=f"No se puede activar una campaña con estado '{campaign.status}'.",
                status_code=409,
            )
        campaign.status = "active"
        campaign.activated_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(campaign)
        logger.info("Recall campaign activated: id=%s", str(campaign.id)[:8])
        return await self._campaign_to_dict(db, campaign)

    async def pause_campaign(
        self, *, db: AsyncSession, campaign_id: str,
    ) -> dict[str, Any]:
        """Pause an active campaign."""
        campaign = await self._get_campaign(db, campaign_id)
        if campaign.status != "active":
            raise DentalOSError(
                error=RecallErrors.ALREADY_PAUSED,
                message="Solo se pueden pausar campañas activas.",
                status_code=409,
            )
        campaign.status = "paused"
        campaign.paused_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(campaign)
        logger.info("Recall campaign paused: id=%s", str(campaign.id)[:8])
        return await self._campaign_to_dict(db, campaign)

    # ── Patient Identification Methods ────────────────────────────────────────

    async def identify_inactive_patients(
        self, *, db: AsyncSession, months_threshold: int = 6,
    ) -> list[uuid.UUID]:
        """Identify patients with no visit in X months."""
        cutoff = date.today() - timedelta(days=months_threshold * 30)

        latest_appt = (
            select(
                Appointment.patient_id,
                func.max(Appointment.start_time).label("last_visit"),
            )
            .where(Appointment.status == "completed", Appointment.is_active.is_(True))
            .group_by(Appointment.patient_id)
            .subquery()
        )

        result = await db.execute(
            select(Patient.id)
            .outerjoin(latest_appt, Patient.id == latest_appt.c.patient_id)
            .where(
                Patient.is_active.is_(True),
                (latest_appt.c.last_visit < cutoff) | (latest_appt.c.last_visit.is_(None)),
            )
        )
        return [row[0] for row in result.all()]

    async def identify_incomplete_plans(self, *, db: AsyncSession) -> list[uuid.UUID]:
        """Identify patients with incomplete treatment plans."""
        result = await db.execute(
            select(TreatmentPlan.patient_id)
            .where(
                TreatmentPlan.status.in_(["draft", "active", "approved"]),
                TreatmentPlan.is_active.is_(True),
            )
            .distinct()
        )
        return [row[0] for row in result.all()]

    async def identify_hygiene_due(self, *, db: AsyncSession) -> list[uuid.UUID]:
        """Identify patients overdue for 6-month hygiene recall."""
        return await self.identify_inactive_patients(db=db, months_threshold=6)

    async def identify_birthdays(
        self, *, db: AsyncSession, days_ahead: int = 7,
    ) -> list[uuid.UUID]:
        """Identify patients with upcoming birthdays."""
        today = date.today()
        patient_ids = []
        for offset in range(days_ahead):
            target = today + timedelta(days=offset)
            result = await db.execute(
                select(Patient.id).where(
                    Patient.is_active.is_(True),
                    Patient.birthdate.isnot(None),
                    func.extract("month", Patient.birthdate) == target.month,
                    func.extract("day", Patient.birthdate) == target.day,
                )
            )
            patient_ids.extend(row[0] for row in result.all())
        return patient_ids

    # ── Recipient Management ──────────────────────────────────────────────────

    async def add_recipients(
        self, *, db: AsyncSession, campaign_id: uuid.UUID,
        patient_ids: list[uuid.UUID],
    ) -> int:
        """Add patients as campaign recipients. Returns count added."""
        # Get existing recipients to avoid duplicates
        existing = await db.execute(
            select(RecallCampaignRecipient.patient_id).where(
                RecallCampaignRecipient.campaign_id == campaign_id,
            )
        )
        existing_ids = {row[0] for row in existing.all()}

        added = 0
        for pid in patient_ids:
            if pid not in existing_ids:
                recipient = RecallCampaignRecipient(
                    campaign_id=campaign_id,
                    patient_id=pid,
                    status="pending",
                    current_step=0,
                )
                db.add(recipient)
                added += 1

        if added > 0:
            await db.flush()
        return added

    async def process_step(
        self, *, db: AsyncSession, recipient_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Process the current step for a recipient. Returns notification payload or None."""
        result = await db.execute(
            select(RecallCampaignRecipient)
            .where(RecallCampaignRecipient.id == recipient_id)
        )
        recipient = result.scalar_one_or_none()
        if recipient is None or recipient.opted_out:
            return None

        # Load campaign
        campaign_result = await db.execute(
            select(RecallCampaign).where(RecallCampaign.id == recipient.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign is None or campaign.status != "active":
            return None

        # Get the schedule sequence
        schedule = campaign.schedule or []
        if isinstance(schedule, list) and recipient.current_step < len(schedule):
            step = schedule[recipient.current_step]
        else:
            return None

        # Load patient info for the message
        patient_result = await db.execute(
            select(Patient.first_name, Patient.last_name, Patient.phone, Patient.email)
            .where(Patient.id == recipient.patient_id)
        )
        patient = patient_result.one_or_none()
        if patient is None:
            return None

        # Update recipient state
        recipient.status = "sent"
        recipient.sent_at = datetime.now(UTC)
        recipient.current_step += 1
        await db.flush()

        return {
            "patient_id": str(recipient.patient_id),
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "channel": step.get("channel", campaign.channel),
            "message_template": step.get("message_template", ""),
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "recipient_id": str(recipient.id),
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get_campaign(self, db: AsyncSession, campaign_id: str) -> RecallCampaign:
        result = await db.execute(
            select(RecallCampaign).where(
                RecallCampaign.id == uuid.UUID(campaign_id),
                RecallCampaign.is_active.is_(True),
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise ResourceNotFoundError(
                error=RecallErrors.CAMPAIGN_NOT_FOUND,
                resource_name="RecallCampaign",
            )
        return campaign

    async def _campaign_to_dict(
        self, db: AsyncSession, campaign: RecallCampaign,
    ) -> dict[str, Any]:
        """Serialize campaign with aggregated recipient stats."""
        # Count recipients by status
        stats_result = await db.execute(
            select(
                RecallCampaignRecipient.status,
                func.count(RecallCampaignRecipient.id),
            )
            .where(RecallCampaignRecipient.campaign_id == campaign.id)
            .group_by(RecallCampaignRecipient.status)
        )
        stats = {row[0]: row[1] for row in stats_result.all()}

        return {
            "id": str(campaign.id),
            "name": campaign.name,
            "type": campaign.type,
            "filters": campaign.filters,
            "message_templates": campaign.message_templates,
            "channel": campaign.channel,
            "schedule": campaign.schedule,
            "status": campaign.status,
            "created_by": str(campaign.created_by) if campaign.created_by else None,
            "activated_at": campaign.activated_at,
            "paused_at": campaign.paused_at,
            "completed_at": campaign.completed_at,
            "is_active": campaign.is_active,
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
            "total_recipients": sum(stats.values()),
            "sent_count": stats.get("sent", 0) + stats.get("delivered", 0) + stats.get("opened", 0) + stats.get("clicked", 0) + stats.get("booked", 0),
            "delivered_count": stats.get("delivered", 0) + stats.get("opened", 0) + stats.get("clicked", 0) + stats.get("booked", 0),
            "booked_count": stats.get("booked", 0),
            "failed_count": stats.get("failed", 0),
        }


recall_service = RecallService()
