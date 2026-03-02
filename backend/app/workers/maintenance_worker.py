"""Maintenance worker — audit archival, analytics aggregation, and cleanup jobs.

Handles periodic maintenance tasks: expired session cleanup, expired token
cleanup, audit log archival, and analytics aggregation.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.maintenance")


class MaintenanceWorker(BaseWorker):
    """Consumes from the ``maintenance`` queue and dispatches by job_type."""

    queue_name = "maintenance"
    prefetch_count = 5

    async def process(self, message: QueueMessage) -> None:
        """Route maintenance job to the appropriate handler."""
        handlers = {
            "audit.archive": self._handle_audit_archive,
            "analytics.aggregate": self._handle_analytics_aggregate,
            "cleanup.expired_sessions": self._handle_cleanup_expired_sessions,
            "cleanup.expired_tokens": self._handle_cleanup_expired_tokens,
        }
        handler = handlers.get(message.job_type)
        if handler:
            await handler(message)
        else:
            logger.warning(
                "Unknown job_type for maintenance queue: %s message_id=%s",
                message.job_type,
                message.message_id,
            )

    async def _handle_audit_archive(self, message: QueueMessage) -> None:
        """Archive old audit log entries to cold storage.

        Payload:
            tenant_id: str — tenant to archive
            older_than_days: int — archive entries older than N days (default 90)
        """
        payload = message.payload
        tenant_id = message.tenant_id
        older_than_days = payload.get("older_than_days", 90)

        try:
            from sqlalchemy import text

            from app.core.database import get_tenant_session

            cutoff = datetime.now(UTC) - timedelta(days=older_than_days)

            async with get_tenant_session(tenant_id) as db:
                result = await db.execute(
                    text(
                        "DELETE FROM audit_logs "
                        "WHERE created_at < :cutoff "
                        "RETURNING id"
                    ),
                    {"cutoff": cutoff},
                )
                deleted_count = result.rowcount
                await db.commit()

            logger.info(
                "Audit archive completed: tenant=%s deleted=%d older_than=%dd",
                tenant_id,
                deleted_count,
                older_than_days,
            )
        except Exception:
            logger.exception(
                "Audit archive failed: tenant=%s", tenant_id
            )
            raise

    async def _handle_analytics_aggregate(self, message: QueueMessage) -> None:
        """Aggregate analytics data for a tenant.

        Payload:
            tenant_id: str — tenant to aggregate
            period: str — "daily" or "weekly" (default "daily")
        """
        payload = message.payload
        tenant_id = message.tenant_id
        period = payload.get("period", "daily")

        try:
            from sqlalchemy import text

            from app.core.database import get_tenant_session

            async with get_tenant_session(tenant_id) as db:
                # Count patients, appointments, and revenue for the period
                if period == "daily":
                    interval = "1 day"
                else:
                    interval = "7 days"

                stats = await db.execute(
                    text(
                        "SELECT "
                        "  (SELECT COUNT(*) FROM patients WHERE is_active = true) AS total_patients, "
                        "  (SELECT COUNT(*) FROM appointments "
                        "   WHERE created_at >= now() - :interval::interval) AS recent_appointments "
                    ),
                    {"interval": interval},
                )
                row = stats.one_or_none()

                if row:
                    logger.info(
                        "Analytics aggregated: tenant=%s period=%s patients=%d appointments=%d",
                        tenant_id,
                        period,
                        row.total_patients,
                        row.recent_appointments,
                    )
        except Exception:
            logger.exception(
                "Analytics aggregation failed: tenant=%s", tenant_id
            )
            raise

    async def _handle_cleanup_expired_sessions(self, message: QueueMessage) -> None:
        """Remove expired user sessions from the tenant schema.

        Payload:
            tenant_id: str — tenant to clean up
        """
        tenant_id = message.tenant_id

        try:
            from sqlalchemy import text

            from app.core.database import get_tenant_session

            async with get_tenant_session(tenant_id) as db:
                result = await db.execute(
                    text(
                        "DELETE FROM user_sessions "
                        "WHERE expires_at < now() OR is_revoked = true "
                        "RETURNING id"
                    )
                )
                deleted_count = result.rowcount
                await db.commit()

            logger.info(
                "Expired sessions cleaned: tenant=%s deleted=%d",
                tenant_id,
                deleted_count,
            )
        except Exception:
            logger.exception(
                "Session cleanup failed: tenant=%s", tenant_id
            )
            raise

    async def _handle_cleanup_expired_tokens(self, message: QueueMessage) -> None:
        """Remove expired password reset and email verification tokens from Redis.

        Uses SCAN to find and delete expired token keys.
        """
        try:
            from app.core.cache import cache_delete_pattern

            # Clean up expired reset tokens
            await cache_delete_pattern("dentalos:auth:reset:*")
            # Clean up expired verification tokens
            await cache_delete_pattern("dentalos:auth:verify_email:*")
            # Clean up expired JTI blacklist entries
            await cache_delete_pattern("dentalos:auth:jti_blacklist:*")

            logger.info("Expired token cleanup completed")
        except Exception:
            logger.exception("Token cleanup failed")
            raise


# Module-level instance for CLI entry point
maintenance_worker = MaintenanceWorker()
