"""Notification dispatch helper — publishes notification jobs to RabbitMQ.

Used by other services (appointments, payments, etc.) to trigger notifications
without directly coupling to the notification worker internals.
"""

import logging
from typing import Any

from app.core.queue import publish_message
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.notification_dispatch")


async def dispatch_notification(
    *,
    tenant_id: str,
    user_id: str,
    event_type: str,
    data: dict[str, Any],
    priority: int = 5,
) -> None:
    """Publish a notification.dispatch job to the notifications queue.

    Args:
        tenant_id: Tenant identifier (e.g., "tn_abc123").
        user_id: Target user UUID string.
        event_type: One of the NotificationType values.
        data: Payload data for rendering the notification (title, body, metadata).
        priority: Message priority (1-10, default 5).
    """
    message = QueueMessage(
        tenant_id=tenant_id,
        job_type="notification.dispatch",
        payload={
            "event_type": event_type,
            "user_id": user_id,
            "data": data,
        },
        priority=priority,
    )

    await publish_message("notifications", message)

    logger.debug(
        "Dispatched notification: tenant=%s user=%s event=%s",
        tenant_id,
        user_id[:8],
        event_type,
    )
