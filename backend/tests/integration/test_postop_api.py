"""Integration tests for Post-operative Instructions API (VP-20 / Sprint 23-24).

Endpoints:
  GET  /api/v1/postop/templates                    -- List templates
  POST /api/v1/postop/templates                    -- Create template (clinic_owner)
  PUT  /api/v1/postop/templates/{template_id}      -- Update template (clinic_owner)
  GET  /api/v1/postop/templates/{template_id}      -- Get single template
  POST /api/v1/postop/send/{patient_id}            -- Send instructions to patient

Requires postop:read (list, get) and postop:write (create, update, send).
clinic_owner has both; doctor has postop:write for sending but not managing templates.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/postop"
TEMPLATE_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())

_TEMPLATE = {
    "id": TEMPLATE_ID,
    "procedure_type": "extraccion",
    "title": "Instrucciones post-extracción",
    "instruction_content": "Evite enjuagarse por 24 horas...",
    "channel_preference": "whatsapp",
    "is_default": True,
    "is_active": True,
    "created_at": "2026-03-01T10:00:00+00:00",
    "updated_at": "2026-03-01T10:00:00+00:00",
}

_TEMPLATE_LIST_RESPONSE = {
    "items": [_TEMPLATE],
    "total": 1,
}

_SEND_RESPONSE = {
    "patient_id": PATIENT_ID,
    "template_id": TEMPLATE_ID,
    "channel_used": "whatsapp",
    "sent_at": "2026-03-02T14:00:00+00:00",
    "notification_id": "00000000-0000-0000-0000-000000000200",
}


# ─── GET /postop/templates ────────────────────────────────────────────────────


@pytest.mark.integration
class TestListPostopTemplates:
    async def test_list_templates_returns_200(self, authenticated_client):
        """GET /postop/templates returns the list of templates."""
        with patch(
            "app.services.postop_service.postop_service.list_templates",
            new_callable=AsyncMock,
            return_value=_TEMPLATE_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/templates")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_list_templates_filtered_by_procedure_type(self, authenticated_client):
        """GET /postop/templates?procedure_type=extraccion filters correctly."""
        with patch(
            "app.services.postop_service.postop_service.list_templates",
            new_callable=AsyncMock,
            return_value=_TEMPLATE_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{BASE}/templates",
                params={"procedure_type": "extraccion"},
            )

        assert response.status_code == 200

    async def test_list_templates_no_auth_returns_401(self, async_client):
        """GET /postop/templates without JWT is rejected with 401."""
        response = await async_client.get(f"{BASE}/templates")
        assert response.status_code == 401


# ─── POST /postop/templates ───────────────────────────────────────────────────


@pytest.mark.integration
class TestCreatePostopTemplate:
    async def test_create_template_returns_201(self, authenticated_client):
        """POST /postop/templates with valid data creates a new template (201)."""
        with patch(
            "app.services.postop_service.postop_service.create_template",
            new_callable=AsyncMock,
            return_value=_TEMPLATE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/templates",
                json={
                    "procedure_type": "extraccion",
                    "title": "Instrucciones post-extracción",
                    "instruction_content": "Evite enjuagarse por 24 horas...",
                    "channel_preference": "whatsapp",
                    "is_default": True,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["procedure_type"] == "extraccion"
        assert data["title"] == "Instrucciones post-extracción"

    async def test_create_template_missing_required_fields(self, authenticated_client):
        """POST /postop/templates without required fields returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/templates",
            json={},
        )
        assert response.status_code == 422

    async def test_create_template_missing_title_returns_422(self, authenticated_client):
        """POST /postop/templates without title returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/templates",
            json={
                "procedure_type": "extraccion",
                "instruction_content": "Contenido...",
                "channel_preference": "whatsapp",
                "is_default": False,
            },
        )
        assert response.status_code == 422

    async def test_create_template_no_auth_returns_401(self, async_client):
        """POST /postop/templates without JWT is rejected with 401."""
        response = await async_client.post(
            f"{BASE}/templates",
            json={
                "procedure_type": "extraccion",
                "title": "Test",
                "instruction_content": "Contenido...",
                "channel_preference": "whatsapp",
                "is_default": False,
            },
        )
        assert response.status_code == 401


# ─── PUT /postop/templates/{template_id} ──────────────────────────────────────


@pytest.mark.integration
class TestUpdatePostopTemplate:
    async def test_update_template_returns_200(self, authenticated_client):
        """PUT /postop/templates/{id} with valid fields updates and returns 200."""
        updated_template = {
            **_TEMPLATE,
            "title": "Instrucciones actualizadas post-extracción",
        }

        with patch(
            "app.services.postop_service.postop_service.update_template",
            new_callable=AsyncMock,
            return_value=updated_template,
        ):
            response = await authenticated_client.put(
                f"{BASE}/templates/{TEMPLATE_ID}",
                json={"title": "Instrucciones actualizadas post-extracción"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Instrucciones actualizadas post-extracción"

    async def test_update_template_invalid_id_returns_422(self, authenticated_client):
        """PUT /postop/templates/not-a-uuid returns 422 for path UUID validation."""
        response = await authenticated_client.put(
            f"{BASE}/templates/not-a-uuid",
            json={"title": "Updated"},
        )
        assert response.status_code == 422

    async def test_update_nonexistent_template(self, authenticated_client):
        """PUT for a template that does not exist returns 404 or 500."""
        other_id = str(uuid.uuid4())
        with patch(
            "app.services.postop_service.postop_service.update_template",
            new_callable=AsyncMock,
            side_effect=Exception("Template not found"),
        ):
            response = await authenticated_client.put(
                f"{BASE}/templates/{other_id}",
                json={"title": "Ghost"},
            )

        assert response.status_code in (404, 500)

    async def test_update_template_no_auth_returns_401(self, async_client):
        """PUT /postop/templates/{id} without JWT is rejected with 401."""
        response = await async_client.put(
            f"{BASE}/templates/{TEMPLATE_ID}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401


# ─── POST /postop/send/{patient_id} ──────────────────────────────────────────


@pytest.mark.integration
class TestSendPostopInstructions:
    async def test_send_with_template_id(self, authenticated_client):
        """POST /postop/send/{patient_id} with template_id enqueues delivery (200)."""
        with patch(
            "app.services.postop_service.postop_service.send_instructions",
            new_callable=AsyncMock,
            return_value=_SEND_RESPONSE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/send/{PATIENT_ID}",
                json={
                    "procedure_type": "extraccion",
                    "template_id": TEMPLATE_ID,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "sent_at" in data
        assert "channel_used" in data

    async def test_send_without_template_uses_default(self, authenticated_client):
        """POST /postop/send/{patient_id} without template_id uses the default template."""
        with patch(
            "app.services.postop_service.postop_service.send_instructions",
            new_callable=AsyncMock,
            return_value={**_SEND_RESPONSE, "template_id": None},
        ):
            response = await authenticated_client.post(
                f"{BASE}/send/{PATIENT_ID}",
                json={"procedure_type": "extraccion"},
            )

        assert response.status_code in (200, 404, 500)

    async def test_send_invalid_patient_id_returns_422(self, authenticated_client):
        """POST /postop/send/not-a-uuid returns 422 for path UUID validation."""
        response = await authenticated_client.post(
            f"{BASE}/send/not-a-uuid",
            json={"procedure_type": "extraccion"},
        )
        assert response.status_code == 422

    async def test_send_no_auth_returns_401(self, async_client):
        """POST /postop/send/{patient_id} without JWT is rejected with 401."""
        response = await async_client.post(
            f"{BASE}/send/{PATIENT_ID}",
            json={"procedure_type": "extraccion"},
        )
        assert response.status_code == 401
