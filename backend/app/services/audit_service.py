"""Audit logging service — write-only, async."""
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger("dentalos.audit")


async def write_audit_log(
    *,
    db: AsyncSession,
    tenant_schema: str,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an audit log entry in the tenant schema.

    Never raises — audit logging failures are logged but don't break the request.
    """
    try:
        import uuid as _uuid

        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        log_entry = AuditLog(
            user_id=_uuid.UUID(user_id) if user_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log_entry)
        await db.flush()
    except Exception:
        logger.warning(
            "Failed to write audit log: action=%s resource=%s",
            action,
            resource_type,
        )
    finally:
        try:
            await db.execute(text("SET search_path TO public"))
        except Exception:
            pass
