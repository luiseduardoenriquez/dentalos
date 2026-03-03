"""Unit tests for the WhatsAppChatService class.

Tests cover:
  - match_phone_to_patient: existing patient returns UUID, no match returns None
  - find_or_create_conversation: returns existing active, creates new, reactivates archived
  - send_message: within 24h window uses session_message, outside window uses template,
    missing conversation raises ResourceNotFoundError
  - get_conversations: paginated list, filter by status
  - assign_conversation: success sets assigned_to, not found raises error
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.services.whatsapp_chat_service import WhatsAppChatService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_conversation(**overrides) -> MagicMock:
    """Build a mock WhatsAppConversation ORM row."""
    conv = MagicMock()
    conv.id = overrides.get("id", uuid.uuid4())
    conv.patient_id = overrides.get("patient_id", None)
    conv.phone_number = overrides.get("phone_number", "+573001234567")
    conv.status = overrides.get("status", "active")
    conv.assigned_to = overrides.get("assigned_to", None)
    conv.last_message_at = overrides.get("last_message_at", datetime.now(UTC))
    conv.last_inbound_at = overrides.get("last_inbound_at", None)
    conv.unread_count = overrides.get("unread_count", 0)
    conv.created_at = overrides.get("created_at", datetime.now(UTC))
    return conv


def _make_message(**overrides) -> MagicMock:
    """Build a mock WhatsAppMessage ORM row."""
    msg = MagicMock()
    msg.id = overrides.get("id", uuid.uuid4())
    msg.conversation_id = overrides.get("conversation_id", uuid.uuid4())
    msg.direction = overrides.get("direction", "outbound")
    msg.content = overrides.get("content", "Hola")
    msg.media_url = overrides.get("media_url", None)
    msg.media_type = overrides.get("media_type", None)
    msg.whatsapp_message_id = overrides.get("whatsapp_message_id", None)
    msg.status = overrides.get("status", "pending")
    msg.sent_by = overrides.get("sent_by", uuid.uuid4())
    msg.created_at = overrides.get("created_at", datetime.now(UTC))
    return msg


# ── TestMatchPhoneToPatient ───────────────────────────────────────────────────


@pytest.mark.unit
class TestMatchPhoneToPatient:
    """Tests for WhatsAppChatService.match_phone_to_patient."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_match_existing_patient(self, db):
        """When a patient row exists for the phone, the UUID is returned."""
        patient_id = uuid.uuid4()
        result = MagicMock()
        result.scalar_one_or_none.return_value = patient_id
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        found = await service.match_phone_to_patient(db, "+573001234567")

        assert found == patient_id

    async def test_match_no_patient(self, db):
        """When no patient row matches the phone number, None is returned."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        found = await service.match_phone_to_patient(db, "+573009999999")

        assert found is None


# ── TestFindOrCreateConversation ─────────────────────────────────────────────


@pytest.mark.unit
class TestFindOrCreateConversation:
    """Tests for WhatsAppChatService.find_or_create_conversation."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_find_existing_active(self, db):
        """An active conversation must be returned without calling db.add."""
        existing = _make_conversation(status="active", phone_number="+573001234567")
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        conv_dict = await service.find_or_create_conversation(db, "+573001234567")

        db.add.assert_not_called()
        assert conv_dict["status"] == "active"
        assert conv_dict["phone_number"] == "+573001234567"

    async def test_create_new_conversation(self, db):
        """When no conversation exists a new one must be created via db.add."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        new_conv = _make_conversation(status="active")

        with patch(
            "app.services.whatsapp_chat_service.WhatsAppConversation",
            return_value=new_conv,
        ):
            service = WhatsAppChatService()
            conv_dict = await service.find_or_create_conversation(
                db, "+573001234567"
            )

        db.add.assert_called_once()
        assert conv_dict["status"] == "active"

    async def test_reactivate_archived(self, db):
        """An archived conversation must have its status changed to 'active'."""
        archived = _make_conversation(status="archived", phone_number="+573001234567")
        result = MagicMock()
        result.scalar_one_or_none.return_value = archived
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        conv_dict = await service.find_or_create_conversation(db, "+573001234567")

        # The ORM object must have been mutated
        assert archived.status == "active"
        assert conv_dict["status"] == "active"
        db.flush.assert_called_once()


# ── TestSendMessage ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSendMessage:
    """Tests for WhatsAppChatService.send_message."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_send_within_24h_window(self, db):
        """When last_inbound_at is within 24 h, send_session_message must be called."""
        conv_id = uuid.uuid4()
        user_id = uuid.uuid4()
        # last inbound 1 hour ago — within session window
        last_inbound = datetime.now(UTC) - timedelta(hours=1)
        conv = _make_conversation(
            id=conv_id, status="active", last_inbound_at=last_inbound
        )
        msg = _make_message(conversation_id=conv_id, status="pending")

        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = conv
        db.execute = AsyncMock(return_value=conv_result)

        with patch(
            "app.services.whatsapp_chat_service.WhatsAppMessage",
            return_value=msg,
        ):
            with patch(
                "app.services.whatsapp_chat_service.whatsapp_service"
            ) as mock_wa:
                mock_wa.send_session_message = AsyncMock(
                    return_value={"messages": [{"id": "wamid.abc"}]}
                )
                mock_wa.send_template_message = AsyncMock()

                service = WhatsAppChatService()
                result = await service.send_message(
                    db=db,
                    conversation_id=str(conv_id),
                    content="Hola doctor",
                    sent_by=str(user_id),
                )

        mock_wa.send_session_message.assert_called_once()
        mock_wa.send_template_message.assert_not_called()
        assert result["direction"] == "outbound"

    async def test_send_outside_24h_window(self, db):
        """When last_inbound_at is older than 24 h, send_template_message is used."""
        conv_id = uuid.uuid4()
        user_id = uuid.uuid4()
        # last inbound 25 hours ago — outside session window
        last_inbound = datetime.now(UTC) - timedelta(hours=25)
        conv = _make_conversation(
            id=conv_id, status="active", last_inbound_at=last_inbound
        )
        msg = _make_message(conversation_id=conv_id, status="pending")

        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = conv
        db.execute = AsyncMock(return_value=conv_result)

        with patch(
            "app.services.whatsapp_chat_service.WhatsAppMessage",
            return_value=msg,
        ):
            with patch(
                "app.services.whatsapp_chat_service.whatsapp_service"
            ) as mock_wa:
                mock_wa.send_session_message = AsyncMock()
                mock_wa.send_template_message = AsyncMock(
                    return_value={"messages": [{"id": "wamid.def"}]}
                )

                service = WhatsAppChatService()
                await service.send_message(
                    db=db,
                    conversation_id=str(conv_id),
                    content="Le recordamos su cita",
                    sent_by=str(user_id),
                )

        mock_wa.send_template_message.assert_called_once()
        mock_wa.send_session_message.assert_not_called()

    async def test_send_conversation_not_found(self, db):
        """Sending a message to a nonexistent conversation raises ResourceNotFoundError."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.send_message(
                db=db,
                conversation_id=str(uuid.uuid4()),
                content="Hola",
                sent_by=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 404


# ── TestGetConversations ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetConversations:
    """Tests for WhatsAppChatService.get_conversations."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_paginated_list(self, db):
        """Paginated list must return items, total, page and page_size."""
        conv1 = _make_conversation(status="active")
        conv2 = _make_conversation(status="active")

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [conv1, conv2]

        db.execute = AsyncMock(side_effect=[count_result, items_result])

        service = WhatsAppChatService()
        result = await service.get_conversations(db, page=1, page_size=20)

        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 2

    async def test_filter_by_status(self, db):
        """Status filter is forwarded — only matching items are returned."""
        conv = _make_conversation(status="archived")

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [conv]

        db.execute = AsyncMock(side_effect=[count_result, items_result])

        service = WhatsAppChatService()
        result = await service.get_conversations(
            db, page=1, page_size=20, status_filter="archived"
        )

        assert result["total"] == 1
        assert result["items"][0]["status"] == "archived"


# ── TestAssignConversation ────────────────────────────────────────────────────


@pytest.mark.unit
class TestAssignConversation:
    """Tests for WhatsAppChatService.assign_conversation."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_assign_success(self, db):
        """Assigning a conversation must set assigned_to on the ORM object."""
        conv_id = uuid.uuid4()
        user_id = uuid.uuid4()
        conv = _make_conversation(id=conv_id, assigned_to=None)

        result = MagicMock()
        result.scalar_one_or_none.return_value = conv
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        conv_dict = await service.assign_conversation(
            db, str(conv_id), str(user_id)
        )

        assert conv.assigned_to == user_id
        assert conv_dict["assigned_to"] == str(user_id)
        db.flush.assert_called_once()

    async def test_assign_not_found(self, db):
        """Assigning a nonexistent conversation raises ResourceNotFoundError (404)."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        service = WhatsAppChatService()
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.assign_conversation(
                db, str(uuid.uuid4()), str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 404
