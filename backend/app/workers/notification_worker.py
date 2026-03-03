"""Notification worker — processes email, SMS, WhatsApp, in-app notifications.

Handles individual channel dispatches and the unified notification.dispatch
job type that fans out to enabled channels based on user preferences.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.cache import cache_delete_pattern, get_cached, set_cached
from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.notifications")

# Redis idempotency key TTL (24 hours)
_IDEMPOTENCY_TTL = 86400


class NotificationWorker(BaseWorker):
    """Consumes from the ``notifications`` queue and dispatches by job_type."""

    queue_name = "notifications"
    prefetch_count = 10

    async def process(self, message: QueueMessage) -> None:
        """Route notification to the appropriate handler."""
        handlers = {
            "email.send": self._handle_email,
            "sms.send": self._handle_sms,
            "whatsapp.send": self._handle_whatsapp,
            "notification.in_app": self._handle_in_app,
            "notification.dispatch": self._handle_dispatch,
            "notification.intake_reminder": self._handle_intake_reminder,
            "campaign.email.batch": self._handle_campaign_batch,
        }
        handler = handlers.get(message.job_type)
        if handler:
            await handler(message)
        else:
            logger.warning(
                "Unknown job_type for notifications queue: %s message_id=%s",
                message.job_type,
                message.message_id,
            )

    # ── Unified dispatch handler ─────────────────────────────────────────────

    async def _handle_dispatch(self, message: QueueMessage) -> None:
        """Process notification.dispatch — fan out to enabled channels.

        Payload:
            event_type: str — the notification event type
            user_id: str — target user UUID
            data: dict — {title, body, metadata, ...}
        """
        payload = message.payload
        event_type = payload.get("event_type", "")
        user_id = payload.get("user_id", "")
        data = payload.get("data", {})
        tenant_id = message.tenant_id

        if not event_type or not user_id:
            logger.warning(
                "Dispatch skipped (missing event_type or user_id): message_id=%s",
                message.message_id,
            )
            return

        # Idempotency check
        idempotency_key = f"notif:dispatch:{message.message_id}"
        from app.core.redis import redis_client

        already_processed = await get_cached(idempotency_key)
        if already_processed:
            logger.info(
                "Dispatch already processed (idempotent skip): message_id=%s",
                message.message_id,
            )
            return

        # Look up user preferences
        preferences = await self._get_user_preferences(tenant_id, user_id)
        event_prefs = preferences.get(event_type, {})

        # Fan out to enabled channels concurrently
        tasks: list[asyncio.Task] = []

        # In-app is always enabled
        tasks.append(
            asyncio.create_task(
                self._dispatch_in_app(tenant_id, user_id, event_type, data, message)
            )
        )

        if event_prefs.get("email", False):
            tasks.append(
                asyncio.create_task(
                    self._dispatch_email(tenant_id, user_id, event_type, data, message)
                )
            )

        if event_prefs.get("sms", False):
            tasks.append(
                asyncio.create_task(
                    self._dispatch_sms(tenant_id, user_id, event_type, data, message)
                )
            )

        if event_prefs.get("whatsapp", False):
            tasks.append(
                asyncio.create_task(
                    self._dispatch_whatsapp(tenant_id, user_id, event_type, data, message)
                )
            )

        await asyncio.gather(*tasks, return_exceptions=True)

        # Mark as processed
        await set_cached(idempotency_key, "1", ttl_seconds=_IDEMPOTENCY_TTL)

        logger.info(
            "Dispatch completed: tenant=%s user=%s event=%s channels=%d",
            tenant_id,
            user_id[:8],
            event_type,
            len(tasks),
        )

    async def _get_user_preferences(
        self, tenant_id: str, user_id: str
    ) -> dict[str, dict[str, bool]]:
        """Fetch user notification preferences via service layer."""
        try:
            from app.core.database import get_tenant_session
            from app.services.notification_service import notification_service

            async with get_tenant_session(tenant_id) as db:
                result = await notification_service.get_preferences(
                    db=db, user_id=user_id
                )
                return result.get("preferences", {})
        except Exception:
            logger.warning(
                "Failed to fetch preferences, using defaults: tenant=%s user=%s",
                tenant_id,
                user_id[:8],
            )
            from app.services.notification_service import _default_preferences

            return _default_preferences()

    # ── Channel dispatch helpers ─────────────────────────────────────────────

    async def _dispatch_in_app(
        self,
        tenant_id: str,
        user_id: str,
        event_type: str,
        data: dict[str, Any],
        message: QueueMessage,
    ) -> None:
        """Insert in-app notification into tenant DB."""
        try:
            from app.core.database import get_tenant_session
            from app.models.tenant.notification import (
                Notification,
                NotificationDeliveryLog,
            )

            title = data.get("title", "")
            body = data.get("body", "")
            metadata = data.get("metadata", {})

            async with get_tenant_session(tenant_id) as db:
                notification = Notification(
                    user_id=uuid.UUID(user_id),
                    type=event_type,
                    title=title,
                    body=body,
                    metadata=metadata,
                )
                db.add(notification)
                await db.flush()

                # Log delivery
                delivery_log = NotificationDeliveryLog(
                    notification_id=notification.id,
                    idempotency_key=message.message_id,
                    event_type=event_type,
                    user_id=uuid.UUID(user_id),
                    channel="in_app",
                    status="delivered",
                    delivered_at=datetime.now(UTC),
                )
                db.add(delivery_log)
                await db.commit()

            # Invalidate caches
            tid_short = tenant_id.replace("tn_", "")[:12]
            await cache_delete_pattern(
                f"dentalos:{tid_short}:notification:*:{user_id[:8]}"
            )

            logger.info(
                "In-app notification created: tenant=%s user=%s event=%s",
                tenant_id,
                user_id[:8],
                event_type,
            )
        except Exception:
            logger.exception(
                "Failed to create in-app notification: tenant=%s user=%s",
                tenant_id,
                user_id[:8],
            )

    async def _dispatch_email(
        self,
        tenant_id: str,
        user_id: str,
        event_type: str,
        data: dict[str, Any],
        message: QueueMessage,
    ) -> None:
        """Dispatch email notification and log delivery."""
        try:
            from app.core.database import get_tenant_session
            from app.core.email import email_service
            from app.models.tenant.notification import NotificationDeliveryLog

            to_email = data.get("to_email", "")
            to_name = data.get("to_name", "")
            subject = data.get("title", "Notificación DentalOS")
            template_name = data.get("email_template", "notification_generic")
            context = data.get("email_context", data)

            status = "skipped"
            error_msg = None

            if to_email and template_name:
                success = await email_service.send_email(
                    to_email=to_email,
                    to_name=to_name,
                    subject=subject,
                    template_name=template_name,
                    context=context,
                )
                status = "delivered" if success else "failed"
                if not success:
                    error_msg = "Email service returned failure"
            else:
                error_msg = "Missing to_email or template_name"

            # Log delivery
            async with get_tenant_session(tenant_id) as db:
                delivery_log = NotificationDeliveryLog(
                    idempotency_key=f"{message.message_id}:email",
                    event_type=event_type,
                    user_id=uuid.UUID(user_id),
                    channel="email",
                    status=status,
                    error_message=error_msg,
                    delivered_at=datetime.now(UTC) if status == "delivered" else None,
                )
                db.add(delivery_log)
                await db.commit()

            logger.info(
                "Email dispatch: tenant=%s status=%s event=%s",
                tenant_id,
                status,
                event_type,
            )
        except Exception:
            logger.exception(
                "Email dispatch failed: tenant=%s user=%s",
                tenant_id,
                user_id[:8],
            )

    async def _dispatch_sms(
        self,
        tenant_id: str,
        user_id: str,
        event_type: str,
        data: dict[str, Any],
        message: QueueMessage,
    ) -> None:
        """Dispatch SMS notification via Twilio (INT-02)."""
        try:
            from app.core.database import get_tenant_session
            from app.integrations.sms.service import twilio_sms_service
            from app.models.tenant.notification import NotificationDeliveryLog

            to_phone = data.get("to_phone", "")
            body = data.get("sms_body", data.get("body", ""))

            status = "skipped"
            error_msg = None

            if not twilio_sms_service.is_configured():
                error_msg = "Twilio SMS integration not configured"
            elif not to_phone:
                error_msg = "Missing to_phone in notification data"
            elif not body:
                error_msg = "Missing SMS body in notification data"
            else:
                try:
                    result = await twilio_sms_service.send_sms(
                        to_phone=to_phone,
                        body=body,
                    )
                    if result.get("status") == "skipped":
                        error_msg = result.get("reason", "skipped")
                    else:
                        status = "delivered"
                except Exception as exc:
                    status = "failed"
                    error_msg = str(exc)[:500]

            # Log delivery
            async with get_tenant_session(tenant_id) as db:
                delivery_log = NotificationDeliveryLog(
                    idempotency_key=f"{message.message_id}:sms",
                    event_type=event_type,
                    user_id=uuid.UUID(user_id),
                    channel="sms",
                    status=status,
                    error_message=error_msg,
                    delivered_at=datetime.now(UTC) if status == "delivered" else None,
                )
                db.add(delivery_log)
                await db.commit()

            logger.info(
                "SMS dispatch: tenant=%s status=%s event=%s",
                tenant_id,
                status,
                event_type,
            )
        except Exception:
            logger.exception(
                "SMS dispatch failed: tenant=%s user=%s",
                tenant_id,
                user_id[:8],
            )

    async def _dispatch_whatsapp(
        self,
        tenant_id: str,
        user_id: str,
        event_type: str,
        data: dict[str, Any],
        message: QueueMessage,
    ) -> None:
        """Dispatch WhatsApp notification via Meta Cloud API (INT-01)."""
        try:
            from app.core.database import get_tenant_session
            from app.integrations.whatsapp.service import whatsapp_service
            from app.models.tenant.notification import NotificationDeliveryLog

            to_phone = data.get("to_phone", "")
            template_name = data.get("whatsapp_template", "appointment_reminder")
            template_params = data.get("whatsapp_params", {})

            status = "skipped"
            error_msg = None

            if not whatsapp_service.is_configured():
                error_msg = "WhatsApp integration not configured"
            elif not to_phone:
                error_msg = "Missing to_phone in notification data"
            else:
                try:
                    result = await whatsapp_service.send_template_message(
                        to_phone=to_phone,
                        template_name=template_name,
                        parameters=template_params,
                    )
                    if result.get("status") == "skipped":
                        error_msg = result.get("reason", "skipped")
                    else:
                        status = "delivered"
                except Exception as exc:
                    status = "failed"
                    error_msg = str(exc)[:500]

            # Log delivery
            async with get_tenant_session(tenant_id) as db:
                delivery_log = NotificationDeliveryLog(
                    idempotency_key=f"{message.message_id}:whatsapp",
                    event_type=event_type,
                    user_id=uuid.UUID(user_id),
                    channel="whatsapp",
                    status=status,
                    error_message=error_msg,
                    delivered_at=datetime.now(UTC) if status == "delivered" else None,
                )
                db.add(delivery_log)
                await db.commit()

            logger.info(
                "WhatsApp dispatch: tenant=%s status=%s event=%s",
                tenant_id,
                status,
                event_type,
            )
        except Exception:
            logger.exception(
                "WhatsApp dispatch failed: tenant=%s user=%s",
                tenant_id,
                user_id[:8],
            )

    # ── Direct channel handlers (legacy job types) ───────────────────────────

    async def _handle_email(self, message: QueueMessage) -> None:
        """Dispatch email via EmailService using message payload."""
        from app.core.email import email_service

        payload = message.payload
        to_email = payload.get("to_email", "")
        to_name = payload.get("to_name", "")
        subject = payload.get("subject", "")
        template_name = payload.get("template_name", "")
        context = payload.get("context", {})

        if not to_email or not template_name:
            logger.warning(
                "Email skipped (missing to_email or template_name): message_id=%s",
                message.message_id,
            )
            return

        success = await email_service.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            template_name=template_name,
            context=context,
        )

        if success:
            logger.info(
                "Email dispatched: tenant=%s template=%s",
                message.tenant_id,
                template_name,
            )
        else:
            logger.error(
                "Email dispatch failed: tenant=%s template=%s",
                message.tenant_id,
                template_name,
            )

    async def _handle_sms(self, message: QueueMessage) -> None:
        """Direct SMS send via Twilio service (INT-02)."""
        payload = message.payload
        await self._dispatch_sms(
            tenant_id=message.tenant_id,
            user_id=payload.get("user_id", ""),
            event_type=payload.get("event_type", "sms_direct"),
            data=payload,
            message=message,
        )

    async def _handle_whatsapp(self, message: QueueMessage) -> None:
        """Direct WhatsApp send via service (INT-01)."""
        payload = message.payload
        await self._dispatch_whatsapp(
            tenant_id=message.tenant_id,
            user_id=payload.get("user_id", ""),
            event_type=payload.get("event_type", "whatsapp_direct"),
            data=payload,
            message=message,
        )

    async def _handle_in_app(self, message: QueueMessage) -> None:
        """Direct in-app notification insertion (legacy job type)."""
        await self._dispatch_in_app(
            tenant_id=message.tenant_id,
            user_id=message.payload.get("user_id", ""),
            event_type=message.payload.get("event_type", "system_update"),
            data=message.payload,
            message=message,
        )

    # ── Intake reminder handler (PP-13) ──────────────────────────────────

    async def _handle_intake_reminder(self, message: QueueMessage) -> None:
        """Send pre-appointment intake link 24h before appointment.

        Payload:
            appointment_id: str
            patient_id: str
            patient_name: str
            patient_email: str
            patient_phone: str
            appointment_date: str
            appointment_time: str
        """
        try:
            payload = message.payload
            tenant_id = message.tenant_id
            patient_email = payload.get("patient_email", "")
            patient_name = payload.get("patient_name", "Paciente")
            appointment_date = payload.get("appointment_date", "")
            appointment_time = payload.get("appointment_time", "")
            appointment_id = payload.get("appointment_id", "")

            from app.core.config import settings as app_settings

            base_url = app_settings.frontend_url
            intake_link = f"{base_url}/portal/intake?appointment={appointment_id}"

            # Send via email
            if patient_email:
                from app.core.email import email_service

                await email_service.send_email(
                    to_email=patient_email,
                    to_name=patient_name,
                    subject="Completa tu formulario antes de tu cita",
                    template_name="intake_reminder",
                    context={
                        "patient_name": patient_name,
                        "appointment_date": appointment_date,
                        "appointment_time": appointment_time,
                        "intake_link": intake_link,
                    },
                )

            # Also send WhatsApp if configured
            patient_phone = payload.get("patient_phone", "")
            if patient_phone:
                from app.integrations.whatsapp.service import whatsapp_service

                if whatsapp_service.is_configured():
                    await whatsapp_service.send_template_message(
                        to_phone=patient_phone,
                        template_name="intake_reminder",
                        parameters={
                            "patient_name": patient_name,
                            "appointment_date": appointment_date,
                            "intake_link": intake_link,
                        },
                    )

            logger.info(
                "Intake reminder sent: tenant=%s appointment=%s",
                tenant_id,
                appointment_id[:8] if appointment_id else "?",
            )
        except Exception:
            logger.exception(
                "Intake reminder failed: message_id=%s tenant=%s",
                message.message_id,
                message.tenant_id,
            )

    # ── Campaign email batch handler (VP-17) ─────────────────────────────

    async def _handle_campaign_batch(self, message: QueueMessage) -> None:
        """Process campaign.email.batch — send emails to campaign recipients.

        Payload:
            campaign_id: str — the campaign UUID
            campaign_name: str — campaign name for logging
            subject: str — email subject
            template_html: str — HTML template with variable placeholders
        """
        try:
            from app.core.database import get_tenant_session
            from app.core.email import email_service
            from app.models.tenant.email_campaign import (
                EmailCampaign,
                EmailCampaignRecipient,
            )
            from app.models.tenant.patient import Patient

            from sqlalchemy import select, update
            from sqlalchemy.orm import joinedload

            payload = message.payload
            campaign_id = payload.get("campaign_id", "")
            subject = payload.get("subject", "")
            template_html = payload.get("template_html", "")
            tenant_id = message.tenant_id

            if not campaign_id:
                logger.warning(
                    "Campaign batch skipped (missing campaign_id): message_id=%s",
                    message.message_id,
                )
                return

            async with get_tenant_session(tenant_id) as db:
                # Fetch pending recipients with patient info
                stmt = (
                    select(EmailCampaignRecipient)
                    .where(
                        EmailCampaignRecipient.campaign_id == uuid.UUID(campaign_id),
                        EmailCampaignRecipient.status == "pending",
                    )
                    .limit(500)
                )
                result = await db.execute(stmt)
                recipients = result.scalars().all()

                if not recipients:
                    # All sent — update campaign to 'sent'
                    await db.execute(
                        update(EmailCampaign)
                        .where(EmailCampaign.id == uuid.UUID(campaign_id))
                        .values(status="sent", sent_at=datetime.now(UTC))
                    )
                    await db.commit()
                    logger.info(
                        "Campaign batch complete (all sent): campaign=%s tenant=%s",
                        campaign_id[:8],
                        tenant_id,
                    )
                    return

                sent_count = 0
                for recipient in recipients:
                    # Fetch patient name for template rendering
                    patient_stmt = select(Patient).where(
                        Patient.id == recipient.patient_id
                    )
                    patient_result = await db.execute(patient_stmt)
                    patient = patient_result.scalar_one_or_none()

                    patient_name = "Paciente"
                    if patient:
                        patient_name = f"{patient.first_name} {patient.last_name}"

                    # Render template with variables
                    rendered_html = template_html
                    rendered_html = rendered_html.replace("{patient_name}", patient_name)
                    rendered_html = rendered_html.replace("{email}", recipient.email)

                    # Add tracking pixel and unsubscribe link
                    tid_short = tenant_id.replace("tn_", "")[:12]
                    from app.core.config import settings as app_settings

                    base_url = app_settings.frontend_url
                    tracking_pixel = (
                        f'<img src="{base_url}/api/v1/public/track/open/'
                        f'{tenant_id}/{recipient.id}" width="1" height="1" />'
                    )
                    unsubscribe_link = (
                        f'{base_url}/api/v1/public/unsubscribe/'
                        f'{tenant_id}/{recipient.id}'
                    )
                    rendered_html = rendered_html.replace(
                        "{tracking_pixel}", tracking_pixel
                    )
                    rendered_html = rendered_html.replace(
                        "{unsubscribe_link}", unsubscribe_link
                    )

                    # Render subject with variables
                    rendered_subject = subject.replace(
                        "{patient_name}", patient_name
                    )

                    try:
                        success = await email_service.send_email(
                            to_email=recipient.email,
                            to_name=patient_name,
                            subject=rendered_subject,
                            template_name="campaign_raw_html",
                            context={"html_content": rendered_html},
                        )
                        if success:
                            recipient.status = "sent"
                            recipient.sent_at = datetime.now(UTC)
                            sent_count += 1
                        else:
                            recipient.status = "bounced"
                    except Exception:
                        recipient.status = "bounced"
                        logger.warning(
                            "Campaign email failed for recipient=%s",
                            str(recipient.id)[:8],
                        )

                # Update campaign counters
                await db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == uuid.UUID(campaign_id))
                    .values(
                        sent_count=EmailCampaign.sent_count + sent_count,
                        bounce_count=EmailCampaign.bounce_count
                        + (len(recipients) - sent_count),
                    )
                )
                await db.commit()

            logger.info(
                "Campaign batch processed: campaign=%s sent=%d/%d tenant=%s",
                campaign_id[:8],
                sent_count,
                len(recipients),
                tenant_id,
            )

        except Exception:
            logger.exception(
                "Campaign batch failed: message_id=%s tenant=%s",
                message.message_id,
                message.tenant_id,
            )


# Module-level instance for CLI entry point
notification_worker = NotificationWorker()
