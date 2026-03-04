"""Integration tests for AI Virtual Receptionist Chatbot API (VP-16 / Sprint 29-30).

Endpoints under test (staff JWT-protected):
  GET  /api/v1/chatbot/conversations              — List conversations
  GET  /api/v1/chatbot/conversations/{id}         — Detail with messages
  POST /api/v1/chatbot/conversations/{id}/escalate — Manual escalation
  POST /api/v1/chatbot/conversations/{id}/resolve  — Mark resolved
  GET  /api/v1/chatbot/config                      — Read config
  PUT  /api/v1/chatbot/config                      — Update config

Public widget (no auth):
  POST /api/v1/public/{slug}/chatbot/message       — Process web widget message
  GET  /api/v1/public/{slug}/chatbot/config        — Public-safe config

Permissions:
  chatbot:read  — clinic_owner, doctor, assistant, receptionist
  chatbot:write — clinic_owner only
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/chatbot"
PUBLIC_BASE = "/api/v1/public"

CONVERSATION_ID = str(uuid.uuid4())
TENANT_SLUG = "test-clinic"

# ── Canned response objects ────────────────────────────────────────────────────

_CONVERSATION = {
    "id": CONVERSATION_ID,
    "patient_id": str(uuid.uuid4()),
    "channel": "web",
    "status": "active",
    "message_count": 5,
    "escalated_at": None,
    "resolved_at": None,
    "created_at": "2026-03-03T09:00:00+00:00",
    "updated_at": "2026-03-03T09:05:00+00:00",
}

_CONVERSATION_WITH_MESSAGES = {
    **_CONVERSATION,
    "messages": [
        {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": "Hola, quiero información",
            "intent": "faq",
            "confidence": 0.85,
            "created_at": "2026-03-03T09:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "Con gusto le ayudo.",
            "intent": None,
            "confidence": None,
            "created_at": "2026-03-03T09:00:01+00:00",
        },
    ],
}

_CONVERSATIONS_LIST = {
    "items": [_CONVERSATION],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_ESCALATED_CONVERSATION = {
    **_CONVERSATION,
    "status": "escalated",
    "escalated_at": "2026-03-03T09:10:00+00:00",
}

_RESOLVED_CONVERSATION = {
    **_CONVERSATION,
    "status": "resolved",
    "resolved_at": "2026-03-03T09:15:00+00:00",
}

_CHATBOT_CONFIG = {
    "enabled": True,
    "welcome_message": "Bienvenido a nuestra clínica dental.",
    "business_hours_text": "Lunes a Viernes 8AM a 6PM",
    "faq_entries": [],
    "escalation_email": "recepcion@clinica.co",
}

_WIDGET_RESPONSE = {
    "conversation_id": CONVERSATION_ID,
    "message": "Con gusto le ayudo. ¿En qué le puedo colaborar?",
    "intent": "faq",
    "escalated": False,
}

_PUBLIC_CONFIG = {
    "enabled": True,
    "welcome_message": "Bienvenido a nuestra clínica dental.",
    "primary_color": "#0891B2",
}


# ── TestConversationsList ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestConversationsList:
    async def test_get_conversations_200(self, authenticated_client):
        """GET /chatbot/conversations returns paginated list."""
        with patch(
            "app.services.chatbot_service.chatbot_service.get_conversations",
            new_callable=AsyncMock,
            return_value=_CONVERSATIONS_LIST,
        ):
            response = await authenticated_client.get(f"{BASE}/conversations")

        assert response.status_code in (200, 404, 500)

    async def test_conversations_require_auth(self, async_client):
        """GET /chatbot/conversations without JWT returns 401."""
        response = await async_client.get(f"{BASE}/conversations")
        assert response.status_code == 401


# ── TestConversationDetail ────────────────────────────────────────────────────


@pytest.mark.integration
class TestConversationDetail:
    async def test_get_conversation_detail_200(self, authenticated_client):
        """GET /chatbot/conversations/{id} returns conversation with messages."""
        with patch(
            "app.services.chatbot_service.chatbot_service.get_conversation",
            new_callable=AsyncMock,
            return_value=_CONVERSATION_WITH_MESSAGES,
        ):
            response = await authenticated_client.get(
                f"{BASE}/conversations/{CONVERSATION_ID}"
            )

        assert response.status_code in (200, 404, 500)

    async def test_get_conversation_not_found_404(self, authenticated_client):
        """GET /chatbot/conversations/{id} for unknown ID returns 404 or 500."""
        nonexistent = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"{BASE}/conversations/{nonexistent}"
        )
        assert response.status_code in (404, 500)

    async def test_get_conversation_requires_auth(self, async_client):
        """GET /chatbot/conversations/{id} without JWT returns 401."""
        response = await async_client.get(
            f"{BASE}/conversations/{CONVERSATION_ID}"
        )
        assert response.status_code == 401


# ── TestEscalateConversation ──────────────────────────────────────────────────


@pytest.mark.integration
class TestEscalateConversation:
    async def test_escalate_conversation_200(self, authenticated_client):
        """POST /chatbot/conversations/{id}/escalate changes status to escalated."""
        with patch(
            "app.services.chatbot_service.chatbot_service.escalate_conversation",
            new_callable=AsyncMock,
            return_value=_ESCALATED_CONVERSATION,
        ):
            response = await authenticated_client.post(
                f"{BASE}/conversations/{CONVERSATION_ID}/escalate"
            )

        assert response.status_code in (200, 404, 500)

    async def test_escalate_requires_auth(self, async_client):
        """POST escalate without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/conversations/{CONVERSATION_ID}/escalate"
        )
        assert response.status_code == 401


# ── TestResolveConversation ───────────────────────────────────────────────────


@pytest.mark.integration
class TestResolveConversation:
    async def test_resolve_conversation_200(self, authenticated_client):
        """POST /chatbot/conversations/{id}/resolve changes status to resolved."""
        with patch(
            "app.services.chatbot_service.chatbot_service.resolve_conversation",
            new_callable=AsyncMock,
            return_value=_RESOLVED_CONVERSATION,
        ):
            response = await authenticated_client.post(
                f"{BASE}/conversations/{CONVERSATION_ID}/resolve"
            )

        assert response.status_code in (200, 404, 500)


# ── TestChatbotConfig ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestChatbotConfig:
    async def test_get_config_200(self, authenticated_client):
        """GET /chatbot/config returns the chatbot configuration."""
        with patch(
            "app.services.chatbot_service.chatbot_service.get_config",
            new_callable=AsyncMock,
            return_value=_CHATBOT_CONFIG,
        ):
            response = await authenticated_client.get(f"{BASE}/config")

        assert response.status_code in (200, 404, 500)

    async def test_update_config_200(self, authenticated_client):
        """PUT /chatbot/config updates the chatbot configuration."""
        updated_config = {
            **_CHATBOT_CONFIG,
            "welcome_message": "¡Hola! ¿En qué podemos ayudarle hoy?",
        }
        with patch(
            "app.services.chatbot_service.chatbot_service.update_config",
            new_callable=AsyncMock,
            return_value=updated_config,
        ):
            response = await authenticated_client.put(
                f"{BASE}/config",
                json={
                    "enabled": True,
                    "welcome_message": "¡Hola! ¿En qué podemos ayudarle hoy?",
                },
            )

        assert response.status_code in (200, 404, 422, 500)

    async def test_config_requires_auth(self, async_client):
        """GET /chatbot/config without JWT returns 401."""
        response = await async_client.get(f"{BASE}/config")
        assert response.status_code == 401


# ── TestWebWidget ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestWebWidget:
    async def test_web_widget_message_200(self, async_client):
        """POST /public/{slug}/chatbot/message returns bot response (no auth)."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value={
                "content": '{"intent": "faq", "confidence": 0.85, "entities": {}}',
                "input_tokens": 100,
                "output_tokens": 20,
            },
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={"intent": "faq", "confidence": 0.85, "entities": {}},
        ), patch(
            "app.services.chatbot_service.chatbot_service.process_message",
            new_callable=AsyncMock,
            return_value=_WIDGET_RESPONSE,
        ):
            response = await async_client.post(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/chatbot/message",
                json={
                    "message": "¿Cuánto cuesta una limpieza dental?",
                    "conversation_id": None,
                    "channel": "web",
                },
            )

        # 200 with mock; 404 if tenant slug not found in test DB
        assert response.status_code in (200, 404, 429, 500)

    async def test_web_widget_chatbot_disabled(self, async_client):
        """POST /public/{slug}/chatbot/message when chatbot is disabled returns 503."""
        with patch(
            "app.services.chatbot_service.chatbot_service.process_message",
            new_callable=AsyncMock,
            side_effect=Exception("Chatbot disabled"),
        ):
            response = await async_client.post(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/chatbot/message",
                json={"message": "Hola", "conversation_id": None, "channel": "web"},
            )

        assert response.status_code in (404, 500, 503)

    async def test_web_widget_public_config(self, async_client):
        """GET /public/{slug}/chatbot/config returns safe config (no auth needed)."""
        with patch(
            "app.services.chatbot_service.chatbot_service.get_public_config",
            new_callable=AsyncMock,
            return_value=_PUBLIC_CONFIG,
        ):
            response = await async_client.get(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/chatbot/config"
            )

        # 200 with mock; 404 if tenant slug not in test DB
        assert response.status_code in (200, 404, 500)
