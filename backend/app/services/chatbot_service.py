"""AI Virtual Receptionist orchestration service -- VP-16.

Coordinates the chatbot engine, conversation persistence, config
management, and escalation/resolution flows.

Security:
  - PHI (message content, patient names) is NEVER logged.
  - All DB operations are tenant-scoped via the AsyncSession search_path.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.chatbot import ChatbotConversation, ChatbotMessage
from app.models.tenant.patient import Patient
from app.services.chatbot_engine import chatbot_engine

logger = logging.getLogger("dentalos.chatbot")


# ─── ORM-to-dict helpers ────────────────────────────────────────────────────


def _conversation_to_dict(
    c: ChatbotConversation,
    include_messages: bool = False,
    messages: list[ChatbotMessage] | None = None,
    patient_name: str | None = None,
    patient_phone: str | None = None,
    message_count: int = 0,
) -> dict[str, Any]:
    """Convert a ChatbotConversation ORM object to a serialisable dict."""
    intent_history = c.intent_history if c.intent_history else []
    last_intent = intent_history[-1] if intent_history else None
    # Extract last intent string — may be a dict or plain string
    last_intent_str = None
    intent_confidence = None
    if isinstance(last_intent, dict):
        last_intent_str = last_intent.get("intent")
        intent_confidence = last_intent.get("confidence")
    elif isinstance(last_intent, str):
        last_intent_str = last_intent

    result: dict[str, Any] = {
        "id": str(c.id),
        "channel": c.channel,
        "patient_id": str(c.patient_id) if c.patient_id else None,
        "patient_name": patient_name,
        "patient_phone": patient_phone,
        "status": c.status,
        "last_intent": last_intent_str,
        "intent_confidence": intent_confidence,
        "intent_history": intent_history,
        "started_at": c.started_at,
        "updated_at": c.resolved_at or c.started_at,
        "resolved_at": c.resolved_at,
        "message_count": message_count,
    }
    if include_messages and messages is not None:
        result["messages"] = [_message_to_dict(m) for m in messages]
    return result


def _message_to_dict(m: ChatbotMessage) -> dict[str, Any]:
    """Convert a ChatbotMessage ORM object to a serialisable dict."""
    return {
        "id": str(m.id),
        "conversation_id": str(m.conversation_id),
        "role": m.role,
        "content": m.content,
        "intent": m.intent,
        "confidence_score": float(m.confidence_score) if m.confidence_score is not None else None,
        "created_at": m.created_at,
    }


# ─── Config helpers ──────────────────────────────────────────────────────────

_DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "greeting_message": (
        "Hola, soy el asistente virtual de la clinica. "
        "Puedo ayudarle a agendar citas, responder preguntas "
        "frecuentes y mas. En que puedo servirle?"
    ),
    "faq_entries": [],
    "business_hours_text": (
        "Lunes a viernes de 8:00 AM a 6:00 PM, "
        "sabados de 8:00 AM a 1:00 PM."
    ),
    "escalation_message": (
        "Entiendo. Le transfiero con un miembro de nuestro equipo "
        "para que pueda atenderle personalmente. Por favor espere "
        "un momento."
    ),
}


async def _read_chatbot_config(db: AsyncSession) -> dict[str, Any]:
    """Read chatbot_config from clinic_settings JSONB.

    Returns the merged config (defaults + persisted overrides).
    """
    result = await db.execute(
        text(
            "SELECT settings->'chatbot_config' FROM clinic_settings LIMIT 1"
        )
    )
    row = result.scalar_one_or_none()

    config = dict(_DEFAULT_CONFIG)
    if row and isinstance(row, dict):
        config.update(row)
    return config


async def _write_chatbot_config(
    db: AsyncSession,
    config: dict[str, Any],
) -> None:
    """Write chatbot_config into clinic_settings JSONB."""
    config_json = json.dumps(config)
    await db.execute(
        text(
            "UPDATE clinic_settings"
            " SET settings = jsonb_set("
            "   COALESCE(settings, '{}'), '{chatbot_config}', :config::jsonb"
            " )"
            " WHERE id = (SELECT id FROM clinic_settings LIMIT 1)"
        ),
        {"config": config_json},
    )
    await db.flush()


# ─── Service class ───────────────────────────────────────────────────────────


class ChatbotService:
    """Stateless orchestration service for the AI Virtual Receptionist."""

    # ─── Main Message Handler ────────────────────────────────────────────

    async def handle_message(
        self,
        db: AsyncSession,
        message: str,
        channel: str,
        patient_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        whatsapp_conversation_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Process an incoming patient message and return the bot response.

        Orchestration flow:
          1. Find or create the chatbot conversation.
          2. Save the user message.
          3. Classify intent via chatbot_engine.
          4. Check if escalation is needed.
          5. If escalating, hand off; else generate bot response.
          6. Save the assistant/system message.
          7. Return the response dict.

        Args:
            db: Tenant-scoped async database session.
            message: The patient's message text.
            channel: 'whatsapp' or 'web'.
            patient_id: Optional linked patient UUID.
            conversation_id: Existing chatbot conversation to continue.
            whatsapp_conversation_id: Linked WhatsApp conversation UUID.

        Returns:
            dict with conversation_id, response (assistant message dict),
            and escalated flag.
        """
        # 1. Find or create conversation
        conversation_orm: ChatbotConversation
        if conversation_id:
            result = await db.execute(
                select(ChatbotConversation).where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.status == "active",
                )
            )
            conversation_orm = result.scalar_one_or_none()  # type: ignore[assignment]
            if conversation_orm is None:
                raise ResourceNotFoundError(
                    error="CHATBOT_conversation_not_found",
                    resource_name="ChatbotConversation",
                )
        else:
            conversation_orm = ChatbotConversation(
                channel=channel,
                patient_id=patient_id,
                whatsapp_conversation_id=whatsapp_conversation_id,
                status="active",
                intent_history=[],
            )
            db.add(conversation_orm)
            await db.flush()

        # 2. Save user message
        user_msg = ChatbotMessage(
            conversation_id=conversation_orm.id,
            role="user",
            content=message,
        )
        db.add(user_msg)
        await db.flush()

        # Build conversation history for intent classifier
        history_result = await db.execute(
            select(ChatbotMessage)
            .where(ChatbotMessage.conversation_id == conversation_orm.id)
            .order_by(ChatbotMessage.created_at.asc())
        )
        all_messages = history_result.scalars().all()

        conversation_history: list[dict[str, str]] = []
        for msg in all_messages:
            if msg.role in ("user", "assistant"):
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        # 3. Classify intent
        classification = await chatbot_engine.classify_intent(
            message=message,
            conversation_history=conversation_history[:-1],  # exclude current message
        )

        intent = classification["intent"]
        confidence = classification["confidence"]
        entities = classification["entities"]

        # Update user message with classification
        user_msg.intent = intent
        user_msg.confidence_score = confidence
        await db.flush()

        # Update intent history on the conversation
        intent_entry = {
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "message": message[:100],  # truncate for history
        }
        current_history = list(conversation_orm.intent_history or [])
        current_history.append(intent_entry)
        conversation_orm.intent_history = current_history
        await db.flush()

        # 4. Check escalation
        escalated = False
        tenant_config = await _read_chatbot_config(db)

        if chatbot_engine.should_escalate(intent, confidence, message):
            # Escalate to human
            escalation_message = tenant_config.get(
                "escalation_message",
                _DEFAULT_CONFIG["escalation_message"],
            )
            conversation_orm.status = "escalated"

            system_msg = ChatbotMessage(
                conversation_id=conversation_orm.id,
                role="system",
                content="Conversacion escalada a atencion humana.",
                intent="escalation",
            )
            db.add(system_msg)

            assistant_msg = ChatbotMessage(
                conversation_id=conversation_orm.id,
                role="assistant",
                content=escalation_message,
                intent=intent,
                confidence_score=confidence,
            )
            db.add(assistant_msg)
            await db.flush()
            escalated = True

            logger.info(
                "Conversation escalated: conversation=%s intent=%s confidence=%.2f",
                str(conversation_orm.id)[:8],
                intent,
                confidence,
            )

            return {
                "conversation_id": str(conversation_orm.id),
                "response": _message_to_dict(assistant_msg),
                "escalated": True,
            }

        # 5. Generate bot response
        conversation_dict = _conversation_to_dict(conversation_orm)
        response_text = await chatbot_engine.generate_response(
            intent=intent,
            entities=entities,
            conversation=conversation_dict,
            tenant_config=tenant_config,
        )

        # 6. Save assistant message
        assistant_msg = ChatbotMessage(
            conversation_id=conversation_orm.id,
            role="assistant",
            content=response_text,
            intent=intent,
            confidence_score=confidence,
        )
        db.add(assistant_msg)
        await db.flush()

        logger.info(
            "Chatbot response generated: conversation=%s intent=%s",
            str(conversation_orm.id)[:8],
            intent,
        )

        return {
            "conversation_id": str(conversation_orm.id),
            "response": _message_to_dict(assistant_msg),
            "escalated": False,
        }

    # ─── Conversation Listing ────────────────────────────────────────────

    async def get_conversations(
        self,
        db: AsyncSession,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of chatbot conversations.

        Ordered by started_at descending (most recent first).
        """
        conditions: list = []
        if status:
            conditions.append(ChatbotConversation.status == status)

        # Count total
        count_q = select(func.count(ChatbotConversation.id))
        if conditions:
            count_q = count_q.where(*conditions)
        total = (await db.execute(count_q)).scalar_one()

        # Fetch page with patient info via LEFT JOIN
        offset = (page - 1) * page_size
        query = (
            select(
                ChatbotConversation,
                Patient.first_name,
                Patient.last_name,
                Patient.phone,
            )
            .outerjoin(Patient, Patient.id == ChatbotConversation.patient_id)
        )
        if conditions:
            query = query.where(*conditions)
        query = (
            query
            .order_by(ChatbotConversation.started_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(query)).all()

        # Get message counts per conversation
        conv_ids = [row[0].id for row in rows]
        msg_counts: dict[uuid.UUID, int] = {}
        if conv_ids:
            count_result = await db.execute(
                select(
                    ChatbotMessage.conversation_id,
                    func.count(ChatbotMessage.id).label("cnt"),
                )
                .where(ChatbotMessage.conversation_id.in_(conv_ids))
                .group_by(ChatbotMessage.conversation_id)
            )
            msg_counts = {r.conversation_id: r.cnt for r in count_result.all()}

        items = []
        for row in rows:
            conv = row[0]
            first_name = row[1]
            last_name = row[2]
            phone = row[3]
            patient_name = f"{first_name} {last_name}" if first_name else None
            items.append(_conversation_to_dict(
                conv,
                patient_name=patient_name,
                patient_phone=phone,
                message_count=msg_counts.get(conv.id, 0),
            ))

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ─── Conversation Detail ─────────────────────────────────────────────

    async def get_conversation_detail(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Fetch a single chatbot conversation with all its messages.

        Raises ResourceNotFoundError if the conversation does not exist.
        """
        result = await db.execute(
            select(ChatbotConversation).where(
                ChatbotConversation.id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ResourceNotFoundError(
                error="CHATBOT_conversation_not_found",
                resource_name="ChatbotConversation",
            )

        # Fetch messages ordered by creation time
        msg_result = await db.execute(
            select(ChatbotMessage)
            .where(ChatbotMessage.conversation_id == conversation_id)
            .order_by(ChatbotMessage.created_at.asc())
        )
        messages = msg_result.scalars().all()

        return _conversation_to_dict(
            conversation,
            include_messages=True,
            messages=list(messages),
        )

    # ─── Config Management ───────────────────────────────────────────────

    async def get_config(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Read the current chatbot configuration."""
        return await _read_chatbot_config(db)

    async def update_config(
        self,
        db: AsyncSession,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge partial updates into the chatbot configuration.

        Only provided (non-None) fields are merged.

        Args:
            db: Tenant-scoped async database session.
            updates: Dict of field names to new values.

        Returns:
            The full updated config dict.
        """
        current = await _read_chatbot_config(db)

        for key, value in updates.items():
            if value is not None:
                current[key] = value

        await _write_chatbot_config(db, current)

        logger.info("Chatbot config updated")
        return current

    # ─── Escalation ──────────────────────────────────────────────────────

    async def escalate_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Manually escalate a chatbot conversation to human staff.

        Sets status to 'escalated' and appends a system message.

        Raises ResourceNotFoundError if conversation does not exist.
        Raises DentalOSError if conversation is not in 'active' status.
        """
        result = await db.execute(
            select(ChatbotConversation).where(
                ChatbotConversation.id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ResourceNotFoundError(
                error="CHATBOT_conversation_not_found",
                resource_name="ChatbotConversation",
            )

        if conversation.status != "active":
            raise DentalOSError(
                error="CHATBOT_escalation_failed",
                message=(
                    f"No se puede escalar una conversacion en estado "
                    f"'{conversation.status}'."
                ),
                status_code=409,
            )

        conversation.status = "escalated"

        system_msg = ChatbotMessage(
            conversation_id=conversation.id,
            role="system",
            content="Conversacion escalada manualmente por el personal.",
            intent="escalation",
        )
        db.add(system_msg)
        await db.flush()

        logger.info(
            "Conversation manually escalated: conversation=%s",
            str(conversation_id)[:8],
        )
        return _conversation_to_dict(conversation)

    # ─── Resolution ──────────────────────────────────────────────────────

    async def resolve_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Mark a chatbot conversation as resolved.

        Sets status to 'resolved' and records resolved_at timestamp.

        Raises ResourceNotFoundError if conversation does not exist.
        Raises DentalOSError if conversation is already resolved.
        """
        result = await db.execute(
            select(ChatbotConversation).where(
                ChatbotConversation.id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ResourceNotFoundError(
                error="CHATBOT_conversation_not_found",
                resource_name="ChatbotConversation",
            )

        if conversation.status == "resolved":
            raise DentalOSError(
                error="CHATBOT_escalation_failed",
                message="La conversacion ya esta resuelta.",
                status_code=409,
            )

        conversation.status = "resolved"
        conversation.resolved_at = datetime.now(UTC)

        system_msg = ChatbotMessage(
            conversation_id=conversation.id,
            role="system",
            content="Conversacion marcada como resuelta.",
            intent="resolution",
        )
        db.add(system_msg)
        await db.flush()

        logger.info(
            "Conversation resolved: conversation=%s",
            str(conversation_id)[:8],
        )
        return _conversation_to_dict(conversation)


# Module-level singleton
chatbot_service = ChatbotService()
