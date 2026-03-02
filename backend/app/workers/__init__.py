"""RabbitMQ consumer workers."""

from app.workers.maintenance_worker import MaintenanceWorker
from app.workers.notification_worker import NotificationWorker
from app.workers.voice_worker import VoiceWorker

__all__ = ["MaintenanceWorker", "NotificationWorker", "VoiceWorker"]
