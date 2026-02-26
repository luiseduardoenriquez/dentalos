"""Notification worker — processes email, SMS, WhatsApp, in-app notifications."""
import logging

from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.notifications")


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

    # ── Handlers (stubs — replace with real integrations) ─────────────────────

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
                "Email dispatched: tenant=%s to=%s template=%s",
                message.tenant_id,
                to_email,
                template_name,
            )
        else:
            logger.error(
                "Email dispatch failed: tenant=%s to=%s template=%s",
                message.tenant_id,
                to_email,
                template_name,
            )

    async def _handle_sms(self, message: QueueMessage) -> None:
        # TODO: Integrate Twilio SMS
        logger.info(
            "SMS send stub: tenant=%s message_id=%s",
            message.tenant_id,
            message.message_id,
        )

    async def _handle_whatsapp(self, message: QueueMessage) -> None:
        # TODO: Integrate WhatsApp Business API
        logger.info(
            "WhatsApp send stub: tenant=%s message_id=%s",
            message.tenant_id,
            message.message_id,
        )

    async def _handle_in_app(self, message: QueueMessage) -> None:
        # TODO: Store in-app notification in tenant DB and push via WebSocket
        logger.info(
            "In-app notification stub: tenant=%s message_id=%s",
            message.tenant_id,
            message.message_id,
        )
