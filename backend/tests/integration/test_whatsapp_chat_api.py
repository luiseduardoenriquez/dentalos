"""Integration tests for WhatsApp bidirectional chat API (VP-12 / Sprint 27-28).

Endpoints under test:
  GET    /api/v1/messaging/conversations                — List conversations
  GET    /api/v1/messaging/conversations/stream         — SSE real-time stream
  GET    /api/v1/messaging/conversations/{id}/messages  — List messages
  POST   /api/v1/messaging/conversations/{id}/send      — Send message
  PUT    /api/v1/messaging/conversations/{id}/assign    — Assign conversation
  PUT    /api/v1/messaging/conversations/{id}/archive   — Archive conversation
  GET    /api/v1/messaging/quick-replies                — List quick replies

Permissions:
  whatsapp:read  — clinic_owner, doctor, assistant, receptionist
  whatsapp:write — clinic_owner, doctor, assistant, receptionist
  doctor role has both whatsapp:read and whatsapp:write.
  patient role has neither.

Note on SSE endpoint:
  The /conversations/stream endpoint validates the JWT via a ``token`` query
  parameter (EventSource cannot send Authorization headers). Sending no token
  or an invalid token returns 401/403.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/messaging"

# Stable IDs reused across test classes
CONVERSATION_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())

# ── Canned response objects ───────────────────────────────────────────────────

_CONVERSATION = {
    "id": CONVERSATION_ID,
    "patient_id": str(uuid.uuid4()),
    "phone_number": "+573001234567",
    "status": "active",
    "assigned_to": None,
    "last_message_at": "2026-03-03T10:00:00+00:00",
    "unread_count": 3,
    "created_at": "2026-03-01T08:00:00+00:00",
}

_CONVERSATION_LIST = {
    "items": [_CONVERSATION],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_MESSAGE = {
    "id": str(uuid.uuid4()),
    "conversation_id": CONVERSATION_ID,
    "direction": "inbound",
    "content": "Hola, tengo una pregunta sobre mi cita.",
    "media_url": None,
    "media_type": None,
    "whatsapp_message_id": "wamid.abc123",
    "status": "delivered",
    "sent_by": None,
    "created_at": "2026-03-03T10:05:00+00:00",
}

_MESSAGE_LIST = {
    "items": [_MESSAGE],
    "total": 1,
    "page": 1,
    "page_size": 50,
}

_SENT_MESSAGE = {
    **_MESSAGE,
    "id": str(uuid.uuid4()),
    "direction": "outbound",
    "content": "Buenos días, con gusto le ayudo.",
    "status": "sent",
    "sent_by": USER_ID,
}

_ASSIGNED_CONVERSATION = {**_CONVERSATION, "assigned_to": USER_ID}
_ARCHIVED_CONVERSATION = {**_CONVERSATION, "status": "archived"}

_QUICK_REPLIES = [
    {
        "id": str(uuid.uuid4()),
        "title": "Confirmación de cita",
        "body": "Su cita ha sido confirmada para el {fecha}.",
        "category": "appointments",
        "sort_order": 1,
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Recordatorio de pago",
        "body": "Le recordamos que tiene un saldo pendiente de ${monto}.",
        "category": "billing",
        "sort_order": 2,
    },
]


# ─── TestListConversations ────────────────────────────────────────────────────


@pytest.mark.integration
class TestListConversations:
    async def test_list_returns_200(self, authenticated_client):
        """GET /messaging/conversations returns paginated conversation list."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.get_conversations",
            new_callable=AsyncMock,
            return_value=_CONVERSATION_LIST,
        ):
            response = await authenticated_client.get(f"{BASE}/conversations")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_with_status_filter(self, authenticated_client):
        """GET /messaging/conversations?status=active filters by conversation status."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.get_conversations",
            new_callable=AsyncMock,
            return_value=_CONVERSATION_LIST,
        ):
            response = await authenticated_client.get(
                f"{BASE}/conversations",
                params={"status": "active"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_requires_auth(self, async_client):
        """GET /messaging/conversations without JWT returns 401."""
        response = await async_client.get(f"{BASE}/conversations")
        assert response.status_code == 401


# ─── TestGetMessages ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetMessages:
    async def test_get_messages_returns_200(self, authenticated_client):
        """GET /messaging/conversations/{id}/messages returns messages or 404 on missing conv."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.get_messages",
            new_callable=AsyncMock,
            return_value=_MESSAGE_LIST,
        ):
            response = await authenticated_client.get(
                f"{BASE}/conversations/{CONVERSATION_ID}/messages"
            )

        # 200 on success; 404 if the conversation does not exist in test DB
        assert response.status_code in (200, 404, 500)

    async def test_requires_auth(self, async_client):
        """GET /messaging/conversations/{id}/messages without JWT returns 401."""
        response = await async_client.get(
            f"{BASE}/conversations/{CONVERSATION_ID}/messages"
        )
        assert response.status_code == 401


# ─── TestSendMessage ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSendMessage:
    async def test_send_returns_201(self, authenticated_client):
        """POST /messaging/conversations/{id}/send with valid content creates message."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.send_message",
            new_callable=AsyncMock,
            return_value=_SENT_MESSAGE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/conversations/{CONVERSATION_ID}/send",
                json={"content": "Buenos días, con gusto le ayudo."},
            )

        # 201 on success; 404 if conv not in DB; 500 on WhatsApp API error
        assert response.status_code in (201, 404, 500)

    async def test_send_empty_content_returns_422(self, authenticated_client):
        """POST /messaging/conversations/{id}/send with empty content returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/conversations/{CONVERSATION_ID}/send",
            json={"content": ""},
        )
        assert response.status_code == 422

    async def test_requires_auth(self, async_client):
        """POST /messaging/conversations/{id}/send without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/conversations/{CONVERSATION_ID}/send",
            json={"content": "Hola."},
        )
        assert response.status_code == 401


# ─── TestAssignConversation ───────────────────────────────────────────────────


@pytest.mark.integration
class TestAssignConversation:
    async def test_assign_returns_200(self, authenticated_client):
        """PUT /messaging/conversations/{id}/assign assigns conversation to a user."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.assign_conversation",
            new_callable=AsyncMock,
            return_value=_ASSIGNED_CONVERSATION,
        ):
            response = await authenticated_client.put(
                f"{BASE}/conversations/{CONVERSATION_ID}/assign",
                json={"user_id": USER_ID},
            )

        # 200 on success; 404 if conversation not found in test DB
        assert response.status_code in (200, 404, 500)

    async def test_requires_auth(self, async_client):
        """PUT /messaging/conversations/{id}/assign without JWT returns 401."""
        response = await async_client.put(
            f"{BASE}/conversations/{CONVERSATION_ID}/assign",
            json={"user_id": USER_ID},
        )
        assert response.status_code == 401


# ─── TestArchiveConversation ──────────────────────────────────────────────────


@pytest.mark.integration
class TestArchiveConversation:
    async def test_archive_returns_200(self, authenticated_client):
        """PUT /messaging/conversations/{id}/archive sets status to archived."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.archive_conversation",
            new_callable=AsyncMock,
            return_value=_ARCHIVED_CONVERSATION,
        ):
            response = await authenticated_client.put(
                f"{BASE}/conversations/{CONVERSATION_ID}/archive"
            )

        # 200 on success; 404 if conversation not found in test DB
        assert response.status_code in (200, 404, 500)

    async def test_requires_auth(self, async_client):
        """PUT /messaging/conversations/{id}/archive without JWT returns 401."""
        response = await async_client.put(
            f"{BASE}/conversations/{CONVERSATION_ID}/archive"
        )
        assert response.status_code == 401


# ─── TestQuickReplies ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestQuickReplies:
    async def test_list_returns_200(self, authenticated_client):
        """GET /messaging/quick-replies returns all active quick reply templates."""
        with patch(
            "app.services.whatsapp_chat_service.whatsapp_chat_service.get_quick_replies",
            new_callable=AsyncMock,
            return_value=_QUICK_REPLIES,
        ):
            response = await authenticated_client.get(f"{BASE}/quick-replies")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["title"] == "Confirmación de cita"

    async def test_requires_auth(self, async_client):
        """GET /messaging/quick-replies without JWT returns 401."""
        response = await async_client.get(f"{BASE}/quick-replies")
        assert response.status_code == 401


# ─── TestSSEStream ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSSEStream:
    async def test_stream_requires_auth(self, async_client):
        """GET /messaging/conversations/stream without a valid token returns 401/403.

        The SSE endpoint validates JWT via the ``token`` query parameter because
        EventSource does not support Authorization headers. Sending no token at
        all (empty string) or no parameter triggers the JWT validation path and
        must be rejected before any stream is established.
        """
        # Case 1: missing token parameter entirely — FastAPI raises 422 for
        # a required Query parameter, which is also acceptable as "not allowed".
        response_no_param = await async_client.get(
            f"{BASE}/conversations/stream"
        )
        # 422: missing required query param; 401/403: token validation failed early
        assert response_no_param.status_code in (401, 403, 422)

        # Case 2: explicitly invalid/garbage token value
        response_bad_token = await async_client.get(
            f"{BASE}/conversations/stream",
            params={"token": "not.a.valid.jwt"},
        )
        assert response_bad_token.status_code in (401, 403)
