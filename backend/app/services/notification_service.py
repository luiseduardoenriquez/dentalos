"""Notification service — list, mark-read, preferences.

Security invariants:
  - PHI is NEVER logged.
  - Notifications are NEVER hard-deleted (soft delete only).
  - Users can only access their own notifications.
"""

import base64
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, get_cached, set_cached
from app.core.exceptions import DentalOSError
from app.models.tenant.notification import Notification, NotificationPreference
from app.schemas.notifications import NotificationChannel, NotificationType

logger = logging.getLogger("dentalos.notifications")

# ─── Default Preferences ─────────────────────────────────────────────────────

# Event types that should have whatsapp enabled by default
_WHATSAPP_DEFAULT_TYPES = {
    NotificationType.appointment_reminder,
    NotificationType.appointment_confirmed,
    NotificationType.appointment_cancelled,
}

_ALL_PREFERENCE_TYPES = [
    NotificationType.appointment_reminder,
    NotificationType.appointment_confirmed,
    NotificationType.appointment_cancelled,
    NotificationType.payment_received,
    NotificationType.payment_overdue,
    NotificationType.treatment_plan_approved,
    NotificationType.consent_signed,
]

_MUTABLE_CHANNELS = {
    NotificationChannel.email,
    NotificationChannel.sms,
    NotificationChannel.whatsapp,
}


def _default_preferences() -> dict[str, dict[str, bool]]:
    """Build the default preferences matrix."""
    prefs: dict[str, dict[str, bool]] = {}
    for evt in _ALL_PREFERENCE_TYPES:
        prefs[evt.value] = {
            "email": True,
            "sms": False,
            "whatsapp": evt in _WHATSAPP_DEFAULT_TYPES,
            "in_app": True,
        }
    return prefs


# ─── Cursor Helpers ──────────────────────────────────────────────────────────


def _encode_cursor(created_at: datetime, notification_id: uuid.UUID) -> str:
    """Encode a keyset cursor as base64 JSON."""
    payload = {
        "c": created_at.isoformat(),
        "i": str(notification_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a keyset cursor. Raises DentalOSError on invalid cursor."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(raw)
        return datetime.fromisoformat(data["c"]), uuid.UUID(data["i"])
    except Exception:
        raise DentalOSError(
            error="VALIDATION_invalid_cursor",
            message="El cursor de paginación no es válido.",
            status_code=400,
        )


# ─── ORM → dict helpers ─────────────────────────────────────────────────────


def _notification_to_dict(n: Notification) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "read_at": n.read_at,
        "created_at": n.created_at,
        "metadata": n.metadata or {},
    }


# ─── Cache Key Helpers ───────────────────────────────────────────────────────


def _unread_count_key(tenant_id: str, user_id: str) -> str:
    tid_short = tenant_id.replace("tn_", "")[:12]
    return f"dentalos:{tid_short}:notification:unread:{user_id[:8]}"


async def _get_unread_count_cached(
    tenant_id: str, user_id: str, db: AsyncSession
) -> int:
    """Get unread count, using cache when available (TTL 300s)."""
    cache_key = _unread_count_key(tenant_id, user_id)
    cached = await get_cached(cache_key)
    if cached is not None:
        return int(cached)

    uid = uuid.UUID(user_id)
    count = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == uid,
                Notification.is_active.is_(True),
                Notification.deleted_at.is_(None),
                Notification.read_at.is_(None),
            )
        )
    ).scalar_one()

    await set_cached(cache_key, count, ttl_seconds=300)
    return count


async def _invalidate_notification_caches(tenant_id: str, user_id: str) -> None:
    """Invalidate notification-related caches for a user."""
    tid_short = tenant_id.replace("tn_", "")[:12]
    await cache_delete_pattern(f"dentalos:{tid_short}:notification:*:{user_id[:8]}")


# ─── Service ─────────────────────────────────────────────────────────────────


class NotificationService:
    """Stateless notification service."""

    async def list_notifications(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        tenant_id: str,
        status: str | None = None,
        notification_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Cursor-paginated notification list (N-01).

        Uses keyset pagination on (created_at DESC, id DESC) for stable ordering.
        """
        uid = uuid.UUID(user_id)

        # Base conditions
        conditions = [
            Notification.user_id == uid,
            Notification.is_active.is_(True),
            Notification.deleted_at.is_(None),
        ]

        # Status filter
        if status == "unread":
            conditions.append(Notification.read_at.is_(None))
        elif status == "read":
            conditions.append(Notification.read_at.is_not(None))

        # Type filter
        if notification_type:
            conditions.append(Notification.type == notification_type)

        # Cursor-based pagination (seek method)
        if cursor:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    Notification.created_at < cursor_created_at,
                    and_(
                        Notification.created_at == cursor_created_at,
                        Notification.id < cursor_id,
                    ),
                )
            )

        # Fetch limit+1 to detect has_more
        rows = (
            await db.execute(
                select(Notification)
                .where(*conditions)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .limit(limit + 1)
            )
        ).scalars().all()

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        # Unread count (cached)
        total_unread = await _get_unread_count_cached(tenant_id, user_id, db)

        return {
            "data": [_notification_to_dict(n) for n in items],
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
                "total_unread": total_unread,
            },
        }

    async def mark_read(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        tenant_id: str,
        notification_id: str,
    ) -> dict[str, Any]:
        """Mark a single notification as read (N-02). Idempotent.

        Returns 404 if notification not found or belongs to another user
        (no 403 disclosure).
        """
        uid = uuid.UUID(user_id)
        nid = uuid.UUID(notification_id)

        result = await db.execute(
            select(Notification).where(
                Notification.id == nid,
                Notification.user_id == uid,
                Notification.is_active.is_(True),
                Notification.deleted_at.is_(None),
            )
        )
        notification = result.scalar_one_or_none()

        if notification is None:
            raise DentalOSError(
                error="NOTIFICATION_not_found",
                message="La notificación no existe.",
                status_code=404,
            )

        # Idempotent: only set read_at if currently unread
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await db.flush()
            await _invalidate_notification_caches(tenant_id, user_id)

        return _notification_to_dict(notification)

    async def mark_all_read(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        tenant_id: str,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Mark all unread notifications as read (N-03). Atomic UPDATE.

        Optionally filter by notification type.
        """
        uid = uuid.UUID(user_id)

        conditions = [
            Notification.user_id == uid,
            Notification.is_active.is_(True),
            Notification.deleted_at.is_(None),
            Notification.read_at.is_(None),
        ]

        if type_filter:
            conditions.append(Notification.type == type_filter)

        result = await db.execute(
            update(Notification)
            .where(*conditions)
            .values(read_at=datetime.now(UTC))
        )
        marked_count = result.rowcount

        if marked_count > 0:
            await db.flush()
            await _invalidate_notification_caches(tenant_id, user_id)

        logger.info(
            "Marked all read: user=%s count=%d type_filter=%s",
            user_id[:8],
            marked_count,
            type_filter,
        )

        return {
            "marked_count": marked_count,
            "type_filter": type_filter,
        }

    async def get_preferences(
        self,
        *,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        """Get notification preferences for a user (N-04).

        Returns defaults if no row exists (lazy init).
        """
        uid = uuid.UUID(user_id)

        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == uid,
            )
        )
        pref = result.scalar_one_or_none()

        if pref is None or not pref.preferences:
            return {"preferences": _default_preferences()}

        # Merge with defaults to ensure new event types are included
        defaults = _default_preferences()
        stored = pref.preferences
        merged: dict[str, dict[str, bool]] = {}
        for evt_type, default_channels in defaults.items():
            if evt_type in stored:
                merged[evt_type] = {
                    "email": stored[evt_type].get("email", default_channels["email"]),
                    "sms": stored[evt_type].get("sms", default_channels["sms"]),
                    "whatsapp": stored[evt_type].get("whatsapp", default_channels["whatsapp"]),
                    "in_app": True,  # Always true
                }
            else:
                merged[evt_type] = default_channels

        return {"preferences": merged}

    async def update_preferences(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Update notification preferences (U-09).

        Upsert pattern: creates row if not exists, merges updates into JSONB.
        in_app cannot be set to false.
        """
        uid = uuid.UUID(user_id)

        # Validate updates
        valid_event_types = {t.value for t in _ALL_PREFERENCE_TYPES}
        for upd in updates:
            if upd["event_type"] not in valid_event_types:
                raise DentalOSError(
                    error="VALIDATION_invalid_event_type",
                    message=f"Tipo de evento no válido: {upd['event_type']}.",
                    status_code=400,
                )
            if upd["channel"] not in _MUTABLE_CHANNELS:
                raise DentalOSError(
                    error="VALIDATION_invalid_channel",
                    message=f"Canal no modificable: {upd['channel']}. Solo email, sms y whatsapp son editables.",
                    status_code=400,
                )

        # Fetch or create
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == uid,
            )
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = NotificationPreference(
                user_id=uid,
                preferences=_default_preferences(),
            )
            db.add(pref)
            await db.flush()

        # Apply updates
        current = dict(pref.preferences) if pref.preferences else _default_preferences()
        for upd in updates:
            evt = upd["event_type"]
            channel = upd["channel"]
            enabled = upd["enabled"]
            if evt not in current:
                current[evt] = {"email": True, "sms": False, "whatsapp": False, "in_app": True}
            current[evt][channel] = enabled
            current[evt]["in_app"] = True  # Enforce always-on

        pref.preferences = current
        await db.flush()

        logger.info("Preferences updated: user=%s changes=%d", user_id[:8], len(updates))

        return {"preferences": current}


# Module-level singleton
notification_service = NotificationService()
