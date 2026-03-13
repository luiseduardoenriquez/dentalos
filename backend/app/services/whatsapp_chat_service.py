"""WhatsApp bidirectional chat service -- VP-12.

Manages conversations, messages, quick replies, and the 24-hour session
window detection for the WhatsApp Business API.

Security invariants:
  - PHI (phone numbers, patient names, message content) is NEVER logged.
  - All operations are tenant-scoped via the AsyncSession's search_path.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.integrations.whatsapp.service import whatsapp_service
from app.models.tenant.patient import Patient
from app.models.tenant.whatsapp import (
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppQuickReply,
)

logger = logging.getLogger("dentalos.whatsapp_chat")

# WhatsApp Business API session window -- free-form messages are only
# allowed within 24 hours of the last inbound message from the patient.
SESSION_WINDOW_HOURS = 24


def _conversation_to_dict(c: WhatsAppConversation) -> dict[str, Any]:
    """Convert a conversation ORM object to a serialisable dict."""
    return {
        "id": str(c.id),
        "patient_id": str(c.patient_id) if c.patient_id else None,
        "phone_number": c.phone_number,
        "status": c.status,
        "assigned_to": str(c.assigned_to) if c.assigned_to else None,
        "last_message_at": c.last_message_at,
        "unread_count": c.unread_count,
        "created_at": c.created_at,
    }


def _message_to_dict(m: WhatsAppMessage) -> dict[str, Any]:
    """Convert a message ORM object to a serialisable dict."""
    return {
        "id": str(m.id),
        "conversation_id": str(m.conversation_id),
        "direction": m.direction,
        "content": m.content,
        "media_url": m.media_url,
        "media_type": m.media_type,
        "whatsapp_message_id": m.whatsapp_message_id,
        "status": m.status,
        "sent_by": str(m.sent_by) if m.sent_by else None,
        "created_at": m.created_at,
    }


def _quick_reply_to_dict(qr: WhatsAppQuickReply) -> dict[str, Any]:
    """Convert a quick reply ORM object to a serialisable dict."""
    return {
        "id": str(qr.id),
        "title": qr.title,
        "body": qr.body,
        "category": qr.category,
        "sort_order": qr.sort_order,
    }


class WhatsAppChatService:
    """Stateless service for WhatsApp bidirectional chat operations."""

    # ─── Phone Matching ──────────────────────────────────────────────────

    async def match_phone_to_patient(
        self,
        db: AsyncSession,
        phone_number: str,
    ) -> uuid.UUID | None:
        """Try to match a phone number to an active patient.

        Performs a simple exact match against the patients.phone column.
        Returns the patient UUID if found, otherwise None.
        """
        result = await db.execute(
            select(Patient.id).where(
                and_(
                    Patient.phone == phone_number,
                    Patient.is_active.is_(True),
                )
            )
        )
        return result.scalar_one_or_none()

    # ─── Conversation Management ─────────────────────────────────────────

    async def find_or_create_conversation(
        self,
        db: AsyncSession,
        phone_number: str,
        patient_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Find an existing active conversation by phone or create a new one.

        Looks for an active or archived conversation with the given phone
        number. If none exists, creates a new active conversation. When a
        patient_id is provided and the existing conversation has no patient
        linked, it updates the link.
        """
        result = await db.execute(
            select(WhatsAppConversation).where(
                and_(
                    WhatsAppConversation.phone_number == phone_number,
                    WhatsAppConversation.status.in_(["active", "archived"]),
                )
            ).order_by(WhatsAppConversation.last_message_at.desc()).limit(1)
        )
        conversation = result.scalar_one_or_none()

        if conversation is not None:
            # Re-activate archived conversations on new inbound message
            if conversation.status == "archived":
                conversation.status = "active"

            # Link patient if not already linked
            if patient_id and conversation.patient_id is None:
                conversation.patient_id = patient_id

            await db.flush()
            logger.info(
                "Conversation found: conversation=%s", str(conversation.id)[:8]
            )
            return _conversation_to_dict(conversation)

        # Create new conversation
        conversation = WhatsAppConversation(
            phone_number=phone_number,
            patient_id=patient_id,
            status="active",
        )
        db.add(conversation)
        await db.flush()

        logger.info("Conversation created: conversation=%s", str(conversation.id)[:8])
        return _conversation_to_dict(conversation)

    # ─── Sending Messages ────────────────────────────────────────────────

    async def send_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        content: str,
        sent_by: str,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Send an outbound message in a conversation.

        Detects the 24-hour session window: if the last inbound message
        was within 24 hours, sends a free-form session message. Otherwise,
        falls back to a template message.

        Creates the message row first (status='pending'), then calls the
        WhatsApp API, and updates status based on the result.
        """
        conv_id = uuid.UUID(conversation_id)
        user_id = uuid.UUID(sent_by)

        # Fetch conversation
        result = await db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.id == conv_id
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ResourceNotFoundError(
                error="WHATSAPP_conversation_not_found",
                resource_name="WhatsAppConversation",
            )

        # Create message row with pending status
        message = WhatsAppMessage(
            conversation_id=conv_id,
            direction="outbound",
            content=content,
            media_url=media_url,
            status="pending",
            sent_by=user_id,
        )
        db.add(message)
        await db.flush()

        # Determine if within 24h session window
        now = datetime.now(UTC)
        within_session = False
        if conversation.last_inbound_at is not None:
            window_end = conversation.last_inbound_at + timedelta(
                hours=SESSION_WINDOW_HOURS
            )
            within_session = now <= window_end

        # Send via WhatsApp API
        wa_result: dict[str, Any] = {}
        try:
            if within_session:
                wa_result = await whatsapp_service.send_session_message(
                    to_phone=conversation.phone_number,
                    text=content,
                )
            else:
                # Outside session window -- must use template
                wa_result = await whatsapp_service.send_template_message(
                    to_phone=conversation.phone_number,
                    template_name="clinic_message",
                    language_code="es",
                    parameters={"message_preview": content[:100]},
                )

            # Extract WhatsApp message ID from response
            wa_msg_id = (
                wa_result.get("messages", [{}])[0].get("id")
                if wa_result.get("messages")
                else None
            )

            message.whatsapp_message_id = wa_msg_id
            message.status = "sent"

        except Exception:
            message.status = "failed"
            logger.exception("WhatsApp send failed: conversation=%s", conversation_id[:8])

        # Update conversation metadata
        conversation.last_message_at = now
        await db.flush()

        logger.info(
            "Message sent: conversation=%s status=%s",
            conversation_id[:8],
            message.status,
        )
        return _message_to_dict(message)

    # ─── Listing ─────────────────────────────────────────────────────────

    async def get_conversations(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """List conversations with offset pagination.

        Ordered by last_message_at descending (most recent first).
        Returns empty list on ProgrammingError (table may not exist yet).
        """
        try:
            return await self._get_conversations_inner(
                db, page, page_size, status_filter, assigned_to,
            )
        except Exception as exc:
            # Table may not exist yet if migration hasn't run
            err_str = str(exc).lower()
            if "relation" in err_str and "does not exist" in err_str:
                logger.warning("whatsapp_conversations table not found — returning empty")
                await db.rollback()
                return {"items": [], "total": 0, "page": page, "page_size": page_size}
            raise

    async def _get_conversations_inner(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """Inner implementation of get_conversations."""
        conditions: list = []

        if status_filter:
            conditions.append(WhatsAppConversation.status == status_filter)

        if assigned_to:
            conditions.append(
                WhatsAppConversation.assigned_to == uuid.UUID(assigned_to)
            )

        # Count total
        count_q = select(func.count(WhatsAppConversation.id))
        if conditions:
            count_q = count_q.where(*conditions)
        total = (await db.execute(count_q)).scalar_one()

        # Fetch page
        offset = (page - 1) * page_size
        query = select(WhatsAppConversation)
        if conditions:
            query = query.where(*conditions)
        query = (
            query
            .order_by(WhatsAppConversation.last_message_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        rows = (await db.execute(query)).scalars().all()

        return {
            "items": [_conversation_to_dict(c) for c in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List messages in a conversation with offset pagination.

        Also resets the unread count to 0 (staff opened the conversation).
        Ordered by created_at ascending (oldest first).
        """
        conv_id = uuid.UUID(conversation_id)

        # Validate conversation exists
        conv_result = await db.execute(
            select(WhatsAppConversation.id).where(
                WhatsAppConversation.id == conv_id
            )
        )
        if conv_result.scalar_one_or_none() is None:
            raise ResourceNotFoundError(
                error="WHATSAPP_conversation_not_found",
                resource_name="WhatsAppConversation",
            )

        # Reset unread count
        await self.reset_unread(db, conversation_id)

        # Count total messages
        count_q = select(func.count(WhatsAppMessage.id)).where(
            WhatsAppMessage.conversation_id == conv_id
        )
        total = (await db.execute(count_q)).scalar_one()

        # Fetch page
        offset = (page - 1) * page_size
        query = (
            select(WhatsAppMessage)
            .where(WhatsAppMessage.conversation_id == conv_id)
            .order_by(WhatsAppMessage.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(query)).scalars().all()

        return {
            "items": [_message_to_dict(m) for m in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ─── Conversation Actions ────────────────────────────────────────────

    async def assign_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Assign a conversation to a staff member."""
        conv_id = uuid.UUID(conversation_id)
        assignee_id = uuid.UUID(user_id)

        result = await db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.id == conv_id
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ResourceNotFoundError(
                error="WHATSAPP_conversation_not_found",
                resource_name="WhatsAppConversation",
            )

        conversation.assigned_to = assignee_id
        await db.flush()

        logger.info(
            "Conversation assigned: conversation=%s",
            conversation_id[:8],
        )
        return _conversation_to_dict(conversation)

    async def archive_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Archive a conversation (sets status='archived')."""
        conv_id = uuid.UUID(conversation_id)

        result = await db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.id == conv_id
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ResourceNotFoundError(
                error="WHATSAPP_conversation_not_found",
                resource_name="WhatsAppConversation",
            )

        conversation.status = "archived"
        await db.flush()

        logger.info(
            "Conversation archived: conversation=%s",
            conversation_id[:8],
        )
        return _conversation_to_dict(conversation)

    # ─── Unread Count ────────────────────────────────────────────────────

    async def increment_unread(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> None:
        """Increment the unread count for a conversation by 1."""
        conv_id = uuid.UUID(conversation_id)
        await db.execute(
            update(WhatsAppConversation)
            .where(WhatsAppConversation.id == conv_id)
            .values(unread_count=WhatsAppConversation.unread_count + 1)
        )
        await db.flush()

    async def reset_unread(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> None:
        """Reset the unread count for a conversation to 0."""
        conv_id = uuid.UUID(conversation_id)
        await db.execute(
            update(WhatsAppConversation)
            .where(WhatsAppConversation.id == conv_id)
            .values(unread_count=0)
        )
        await db.flush()

    # ─── Quick Replies ───────────────────────────────────────────────────

    async def get_quick_replies(
        self,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Get all active quick replies ordered by sort_order."""
        result = await db.execute(
            select(WhatsAppQuickReply)
            .where(WhatsAppQuickReply.is_active.is_(True))
            .order_by(WhatsAppQuickReply.sort_order.asc())
        )
        rows = result.scalars().all()
        return [_quick_reply_to_dict(qr) for qr in rows]

    # ─── Inbound Message Storage ─────────────────────────────────────────

    async def store_inbound_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        content: str,
        whatsapp_message_id: str,
        media_url: str | None = None,
        media_type: str | None = None,
    ) -> dict[str, Any]:
        """Store an inbound message received via the webhook.

        Creates the message row and updates the conversation's
        last_message_at and last_inbound_at timestamps.
        """
        conv_id = uuid.UUID(conversation_id)
        now = datetime.now(UTC)

        message = WhatsAppMessage(
            conversation_id=conv_id,
            direction="inbound",
            content=content,
            media_url=media_url,
            media_type=media_type,
            whatsapp_message_id=whatsapp_message_id,
            status="delivered",
            sent_by=None,
        )
        db.add(message)

        # Update conversation timestamps
        await db.execute(
            update(WhatsAppConversation)
            .where(WhatsAppConversation.id == conv_id)
            .values(
                last_message_at=now,
                last_inbound_at=now,
            )
        )
        await db.flush()

        logger.info(
            "Inbound message stored: conversation=%s",
            conversation_id[:8],
        )
        return _message_to_dict(message)


# Module-level singleton
whatsapp_chat_service = WhatsAppChatService()
