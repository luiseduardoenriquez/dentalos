"""Call log service -- VP-18 VoIP Screen Pop.

Handles call log CRUD, phone-to-patient matching, and Redis pub/sub
for real-time screen-pop events.

Security: PHI (phone numbers) is NEVER logged.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.tenant.call_log import CallLog
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.call_log")


class CallLogService:
    """Stateless service for call log operations."""

    async def match_phone_to_patient(
        self, db: AsyncSession, phone_number: str
    ) -> uuid.UUID | None:
        """Match a phone number to an active patient (phone or phone_secondary).

        Returns patient UUID if found, None otherwise.
        """
        result = await db.execute(
            select(Patient.id).where(
                and_(
                    or_(
                        Patient.phone == phone_number,
                        Patient.phone_secondary == phone_number,
                    ),
                    Patient.is_active.is_(True),
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_call_log(
        self,
        db: AsyncSession,
        *,
        phone_number: str,
        direction: str,
        twilio_call_sid: str | None = None,
        patient_id: uuid.UUID | None = None,
        staff_id: uuid.UUID | None = None,
    ) -> CallLog:
        """Create a new call log entry."""
        call = CallLog(
            phone_number=phone_number,
            direction=direction,
            status="ringing",
            twilio_call_sid=twilio_call_sid,
            patient_id=patient_id,
            staff_id=staff_id,
            started_at=datetime.now(UTC),
        )
        db.add(call)
        await db.flush()
        await db.refresh(call)
        return call

    async def update_call_status(
        self,
        db: AsyncSession,
        *,
        twilio_call_sid: str,
        status: str,
        duration_seconds: int | None = None,
    ) -> CallLog | None:
        """Update a call log by Twilio SID."""
        result = await db.execute(
            select(CallLog).where(CallLog.twilio_call_sid == twilio_call_sid)
        )
        call = result.scalar_one_or_none()
        if not call:
            return None

        call.status = status
        if duration_seconds is not None:
            call.duration_seconds = duration_seconds
        if status in ("completed", "missed", "voicemail"):
            call.ended_at = datetime.now(UTC)

        await db.flush()
        await db.refresh(call)
        return call

    async def update_notes(
        self, db: AsyncSession, call_id: uuid.UUID, notes: str
    ) -> CallLog:
        """Update notes on a call log entry."""
        result = await db.execute(
            select(CallLog).where(CallLog.id == call_id)
        )
        call = result.scalar_one_or_none()
        if not call:
            raise ResourceNotFoundError(
                error="CALL_LOG_not_found",
                resource_name="CallLog",
            )

        call.notes = notes
        await db.flush()
        await db.refresh(call)
        return call

    async def get_call_log(
        self, db: AsyncSession, call_id: uuid.UUID
    ) -> CallLog:
        """Get a single call log by ID."""
        result = await db.execute(
            select(CallLog).where(CallLog.id == call_id)
        )
        call = result.scalar_one_or_none()
        if not call:
            raise ResourceNotFoundError(
                error="CALL_LOG_not_found",
                resource_name="CallLog",
            )
        return call

    async def list_call_logs(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        direction: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List call logs with pagination and filters."""
        query = select(CallLog)
        count_query = select(func.count()).select_from(CallLog)

        if direction:
            query = query.where(CallLog.direction == direction)
            count_query = count_query.where(CallLog.direction == direction)
        if status:
            query = query.where(CallLog.status == status)
            count_query = count_query.where(CallLog.status == status)

        total = (await db.execute(count_query)).scalar() or 0

        # Order by started_at desc (most recent calls first); fall back to
        # created_at for rows where started_at is NULL (edge case on creation).
        query = query.order_by(
            CallLog.started_at.desc().nullslast(),
            CallLog.created_at.desc(),
        )
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def publish_screen_pop(
        self,
        tenant_id: str,
        call_log: CallLog,
        patient_name: str | None = None,
    ) -> None:
        """Publish incoming call event to Redis for SSE screen-pop.

        This is a convenience wrapper around publish_incoming_call that builds
        the call_data dict from a CallLog ORM instance.
        """
        call_data = {
            "call_id": str(call_log.id),
            "phone_number": call_log.phone_number,
            "patient_id": str(call_log.patient_id) if call_log.patient_id else None,
            "patient_name": patient_name,
            "direction": call_log.direction,
            "started_at": call_log.started_at.isoformat() if call_log.started_at else None,
        }
        await self.publish_incoming_call(tenant_id, call_data)

    async def publish_incoming_call(
        self,
        tenant_id: str,
        call_data: dict[str, Any],
    ) -> None:
        """Publish incoming call event dict to Redis channel for SSE screen-pop.

        Channel: dentalos:{tenant_id}:calls:incoming
        """
        from app.core.redis import redis_client

        channel = f"dentalos:{tenant_id}:calls:incoming"
        await redis_client.publish(channel, json.dumps(call_data, default=str))


call_log_service = CallLogService()
