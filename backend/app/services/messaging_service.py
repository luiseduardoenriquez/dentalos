"""Messaging service — threads, messages, read tracking.

Security invariants:
  - PHI is NEVER logged.
  - All operations are tenant-scoped via the AsyncSession's search_path.
"""

import base64
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.messaging import Message, MessageThread, ThreadParticipant
from app.models.tenant.patient import Patient
from app.models.tenant.user import User
from app.services.notification_dispatch import dispatch_notification

logger = logging.getLogger("dentalos.messaging")


# ─── Cursor Helpers ──────────────────────────────────────────────────────────


def _encode_cursor(dt: datetime, item_id: uuid.UUID) -> str:
    payload = {"c": dt.isoformat(), "i": str(item_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(raw)
        return datetime.fromisoformat(data["c"]), uuid.UUID(data["i"])
    except Exception:
        raise DentalOSError(
            error="VALIDATION_invalid_cursor",
            message="El cursor de paginacion no es valido.",
            status_code=400,
        )


def _message_to_dict(m: Message, sender_name: str | None = None) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "thread_id": str(m.thread_id),
        "sender_type": m.sender_type,
        "sender_id": str(m.sender_id),
        "sender_name": sender_name,
        "body": m.body,
        "attachments": m.attachments,
        "read_at": m.read_at,
        "created_at": m.created_at,
    }


def _thread_to_dict(t: MessageThread, unread_count: int = 0) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "patient_id": str(t.patient_id),
        "subject": t.subject,
        "status": t.status,
        "created_by": str(t.created_by),
        "last_message_at": t.last_message_at,
        "unread_count": unread_count,
        "created_at": t.created_at,
    }


class MessagingService:
    """Stateless messaging service."""

    async def create_thread(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        created_by_id: str,
        patient_id: str,
        subject: str | None = None,
        initial_message: str,
    ) -> dict[str, Any]:
        """Create a new message thread with an initial message (MS-01)."""
        pid = uuid.UUID(patient_id)
        creator_id = uuid.UUID(created_by_id)

        # Validate patient exists
        patient = (await db.execute(
            select(Patient.id).where(Patient.id == pid, Patient.is_active.is_(True))
        )).scalar_one_or_none()

        if patient is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="El paciente no existe o esta inactivo.",
                status_code=404,
            )

        # Create thread
        thread = MessageThread(
            patient_id=pid,
            subject=subject,
            status="open",
            created_by=creator_id,
        )
        db.add(thread)
        await db.flush()

        # Create initial message
        message = Message(
            thread_id=thread.id,
            sender_type="staff",
            sender_id=creator_id,
            body=initial_message,
        )
        db.add(message)

        # Add creator as participant
        participant = ThreadParticipant(
            thread_id=thread.id,
            user_id=creator_id,
            last_read_at=datetime.now(UTC),
        )
        db.add(participant)
        await db.flush()

        logger.info("Thread created: thread=%s", str(thread.id)[:8])

        # Dispatch notification to patient if they have portal access
        patient_result = await db.execute(
            select(Patient).where(Patient.id == pid)
        )
        patient_obj = patient_result.scalar_one_or_none()
        if patient_obj and patient_obj.portal_access:
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=patient_id,
                event_type="message_received",
                data={
                    "thread_id": str(thread.id),
                    "sender_name": "Clinica",
                    "message_preview": initial_message[:100],
                },
            )

        return _thread_to_dict(thread)

    async def list_threads(
        self,
        *,
        db: AsyncSession,
        patient_id: str | None = None,
        status: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List message threads with cursor pagination (MS-02)."""
        conditions: list = []

        if patient_id:
            conditions.append(MessageThread.patient_id == uuid.UUID(patient_id))

        if status:
            conditions.append(MessageThread.status == status)

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    MessageThread.last_message_at < cursor_dt,
                    and_(
                        MessageThread.last_message_at == cursor_dt,
                        MessageThread.id < cursor_id,
                    ),
                )
            )

        query = select(MessageThread)
        if conditions:
            query = query.where(*conditions)
        query = query.order_by(
            MessageThread.last_message_at.desc(), MessageThread.id.desc()
        ).limit(limit + 1)

        rows = (await db.execute(query)).scalars().all()

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.last_message_at, last.id)

        data = [_thread_to_dict(t) for t in items]

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def send_message(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        thread_id: str,
        sender_type: str,
        sender_id: str,
        body: str,
    ) -> dict[str, Any]:
        """Send a message in an existing thread (MS-03)."""
        tid = uuid.UUID(thread_id)
        sid = uuid.UUID(sender_id)

        # Validate thread exists and is open
        thread_result = await db.execute(
            select(MessageThread).where(MessageThread.id == tid)
        )
        thread = thread_result.scalar_one_or_none()

        if thread is None:
            raise ResourceNotFoundError(
                error="MESSAGING_thread_not_found",
                resource_name="MessageThread",
            )

        if thread.status != "open":
            raise DentalOSError(
                error="MESSAGING_thread_closed",
                message="Este hilo de mensajes esta cerrado.",
                status_code=409,
            )

        # Create message
        message = Message(
            thread_id=tid,
            sender_type=sender_type,
            sender_id=sid,
            body=body,
        )
        db.add(message)

        # Update thread last_message_at
        thread.last_message_at = datetime.now(UTC)
        await db.flush()

        # Resolve sender name
        sender_name = None
        if sender_type == "staff":
            user_result = await db.execute(
                select(User.name).where(User.id == sid)
            )
            sender_name = user_result.scalar_one_or_none()
        elif sender_type == "patient":
            patient_result = await db.execute(
                select(Patient.first_name, Patient.last_name).where(Patient.id == sid)
            )
            row = patient_result.first()
            if row:
                sender_name = f"{row[0]} {row[1]}"

        logger.info("Message sent: thread=%s sender_type=%s", thread_id[:8], sender_type)

        # Dispatch notification
        if sender_type == "patient":
            # Notify staff creator
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=str(thread.created_by),
                event_type="message_received",
                data={
                    "thread_id": thread_id,
                    "sender_name": sender_name or "Paciente",
                    "message_preview": body[:100],
                },
            )
        elif sender_type == "staff":
            # Notify patient
            await dispatch_notification(
                tenant_id=tenant_id,
                user_id=str(thread.patient_id),
                event_type="message_received",
                data={
                    "thread_id": thread_id,
                    "sender_name": sender_name or "Clinica",
                    "message_preview": body[:100],
                },
            )

        return _message_to_dict(message, sender_name=sender_name)

    async def list_messages(
        self,
        *,
        db: AsyncSession,
        thread_id: str,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List messages in a thread with cursor pagination (MS-04)."""
        tid = uuid.UUID(thread_id)

        # Validate thread exists
        thread_exists = (await db.execute(
            select(MessageThread.id).where(MessageThread.id == tid)
        )).scalar_one_or_none()

        if thread_exists is None:
            raise ResourceNotFoundError(
                error="MESSAGING_thread_not_found",
                resource_name="MessageThread",
            )

        conditions = [Message.thread_id == tid]

        if cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    Message.created_at > cursor_dt,
                    and_(
                        Message.created_at == cursor_dt,
                        Message.id > cursor_id,
                    ),
                )
            )

        query = (
            select(Message)
            .where(*conditions)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(limit + 1)
        )

        messages = (await db.execute(query)).scalars().all()

        has_more = len(messages) > limit
        items = messages[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        # Resolve sender names in batch
        staff_ids = {m.sender_id for m in items if m.sender_type == "staff"}
        patient_ids = {m.sender_id for m in items if m.sender_type == "patient"}

        name_map: dict[uuid.UUID, str] = {}

        if staff_ids:
            staff_result = await db.execute(
                select(User.id, User.name).where(User.id.in_(staff_ids))
            )
            for uid, name in staff_result.all():
                name_map[uid] = name

        if patient_ids:
            patient_result = await db.execute(
                select(Patient.id, Patient.first_name, Patient.last_name)
                .where(Patient.id.in_(patient_ids))
            )
            for pid, fn, ln in patient_result.all():
                name_map[pid] = f"{fn} {ln}"

        data = [
            _message_to_dict(m, sender_name=name_map.get(m.sender_id))
            for m in items
        ]

        return {
            "data": data,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }

    async def mark_thread_read(
        self,
        *,
        db: AsyncSession,
        thread_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Mark a thread as read for a user (MS-05)."""
        tid = uuid.UUID(thread_id)
        uid = uuid.UUID(user_id)

        # Upsert participant read timestamp
        result = await db.execute(
            select(ThreadParticipant).where(
                ThreadParticipant.thread_id == tid,
                ThreadParticipant.user_id == uid,
            )
        )
        participant = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if participant:
            participant.last_read_at = now
        else:
            participant = ThreadParticipant(
                thread_id=tid,
                user_id=uid,
                last_read_at=now,
            )
            db.add(participant)

        await db.flush()

        logger.debug("Thread marked read: thread=%s user=%s", thread_id[:8], user_id[:8])

        return {"thread_id": thread_id, "read_at": now}


# Module-level singleton
messaging_service = MessagingService()
