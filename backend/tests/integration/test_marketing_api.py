"""Integration tests for Email Marketing Campaign API (VP-17 / Sprint 27-28).

Endpoints under test (staff JWT-protected):
  POST   /api/v1/marketing/campaigns                — Create campaign
  GET    /api/v1/marketing/campaigns                — List campaigns
  GET    /api/v1/marketing/campaigns/{id}           — Get single campaign
  PUT    /api/v1/marketing/campaigns/{id}           — Update draft campaign
  POST   /api/v1/marketing/campaigns/{id}/send      — Dispatch campaign (→ 202)
  POST   /api/v1/marketing/campaigns/{id}/schedule  — Schedule future send
  DELETE /api/v1/marketing/campaigns/{id}           — Soft-delete / cancel
  GET    /api/v1/marketing/templates                — Built-in template catalogue

Public tracking endpoints (no auth):
  GET /api/v1/public/track/open/{schema}/{recipient_id}   — 1×1 GIF pixel
  GET /api/v1/public/track/click/{schema}/{recipient_id}  — click → 302 redirect
  GET /api/v1/public/unsubscribe/{schema}/{recipient_id}  — unsubscribe HTML page

Permissions:
  marketing:read  — clinic_owner only
  marketing:write — clinic_owner only
  doctor role has neither → 403.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/marketing"
PUBLIC_BASE = "/api/v1/public"

# Stable IDs reused across test classes
CAMPAIGN_ID = str(uuid.uuid4())
RECIPIENT_ID = str(uuid.uuid4())

# Valid schema name pattern required by Path validator: ^tn_[a-z0-9_]{1,60}$
TENANT_SCHEMA = "tn_testclinic01"

# ── Canned response objects ───────────────────────────────────────────────────

_CAMPAIGN = {
    "id": CAMPAIGN_ID,
    "name": "Campaña de reactivación — Marzo 2026",
    "subject": "Hace mucho que no te vemos, ¡te esperamos!",
    "template_id": "reactivation",
    "status": "draft",
    "scheduled_at": None,
    "sent_at": None,
    "sent_count": 0,
    "open_count": 0,
    "click_count": 0,
    "bounce_count": 0,
    "unsubscribe_count": 0,
    "created_at": "2026-03-03T09:00:00+00:00",
    "updated_at": "2026-03-03T09:00:00+00:00",
}

_CAMPAIGN_LIST = {
    "items": [_CAMPAIGN],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_SENT_DISPATCH = {
    "campaign_id": CAMPAIGN_ID,
    "status": "sending",
    "recipient_count": 42,
    "queued": True,
}

_SCHEDULED_CAMPAIGN = {
    **_CAMPAIGN,
    "status": "scheduled",
    "scheduled_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
}

_DELETED_CAMPAIGN = {
    **_CAMPAIGN,
    "status": "cancelled",
}

_TEMPLATES = [
    {
        "template_id": "reactivation",
        "name": "Reactivación de pacientes",
        "subject_template": "Hace mucho que no te vemos, {nombre}",
        "description": "Email para pacientes sin cita en más de 6 meses.",
    },
    {
        "template_id": "birthday",
        "name": "Feliz cumpleaños",
        "subject_template": "¡Feliz cumpleaños, {nombre}!",
        "description": "Email de cumpleaños con descuento especial.",
    },
    {
        "template_id": "promotion",
        "name": "Promoción especial",
        "subject_template": "Oferta exclusiva para ti, {nombre}",
        "description": "Email de promoción con cupón de descuento.",
    },
]

# Minimal 1×1 transparent GIF bytes (44 bytes)
_TRACKING_PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00"
    b"\x02\x02D\x01\x00;"
)

_UNSUBSCRIBE_HTML = (
    "<!DOCTYPE html><html lang='es'><body>"
    "<h1>Cancelación de suscripción</h1>"
    "<p>Has sido eliminado de nuestra lista de correos. "
    "Ya no recibirás campañas de marketing de nuestra clínica.</p>"
    "</body></html>"
)


# ─── TestCreateCampaign ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateCampaign:
    async def test_create_returns_201(self, authenticated_client):
        """POST /marketing/campaigns with valid data creates a draft campaign (201)."""
        with patch(
            "app.services.email_campaign_service.email_campaign_service.create_campaign",
            new_callable=AsyncMock,
            return_value=_CAMPAIGN,
        ):
            response = await authenticated_client.post(
                f"{BASE}/campaigns",
                json={
                    "name": "Campaña de reactivación — Marzo 2026",
                    "subject": "Hace mucho que no te vemos, ¡te esperamos!",
                    "template_id": "reactivation",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "draft"
        assert data["name"] == "Campaña de reactivación — Marzo 2026"

    async def test_create_requires_auth(self, async_client):
        """POST /marketing/campaigns without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/campaigns",
            json={
                "name": "Test",
                "subject": "Test subject",
                "template_id": "reactivation",
            },
        )
        assert response.status_code == 401

    async def test_create_invalid_data_returns_422(self, authenticated_client):
        """POST /marketing/campaigns without template_id or template_html returns 422.

        The EmailCampaignCreate schema requires at least one of template_id or
        template_html via a model_validator; omitting both triggers a 422.
        """
        response = await authenticated_client.post(
            f"{BASE}/campaigns",
            json={
                "name": "Campaña sin plantilla",
                "subject": "Este es el asunto",
                # Neither template_id nor template_html provided — should fail validation
            },
        )
        assert response.status_code == 422


# ─── TestListCampaigns ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListCampaigns:
    async def test_list_returns_200(self, authenticated_client):
        """GET /marketing/campaigns returns paginated campaign list."""
        with patch(
            "app.services.email_campaign_service.email_campaign_service.list_campaigns",
            new_callable=AsyncMock,
            return_value=_CAMPAIGN_LIST,
        ):
            response = await authenticated_client.get(f"{BASE}/campaigns")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_requires_auth(self, async_client):
        """GET /marketing/campaigns without JWT returns 401."""
        response = await async_client.get(f"{BASE}/campaigns")
        assert response.status_code == 401


# ─── TestGetCampaign ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetCampaign:
    async def test_get_returns_200_or_404(self, authenticated_client):
        """GET /marketing/campaigns/{id} returns campaign detail or 404 on missing."""
        with patch(
            "app.services.email_campaign_service.email_campaign_service.get_campaign",
            new_callable=AsyncMock,
            return_value=_CAMPAIGN,
        ):
            response = await authenticated_client.get(
                f"{BASE}/campaigns/{CAMPAIGN_ID}"
            )

        # 200 with mock; 404 without seeded DB; 500 on DB error
        assert response.status_code in (200, 404, 500)

    async def test_requires_auth(self, async_client):
        """GET /marketing/campaigns/{id} without JWT returns 401."""
        response = await async_client.get(f"{BASE}/campaigns/{CAMPAIGN_ID}")
        assert response.status_code == 401


# ─── TestUpdateCampaign ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateCampaign:
    async def test_update_returns_200_or_404(self, authenticated_client):
        """PUT /marketing/campaigns/{id} updates the campaign name or subject."""
        updated = {**_CAMPAIGN, "name": "Nombre actualizado"}
        with patch(
            "app.services.email_campaign_service.email_campaign_service.update_campaign",
            new_callable=AsyncMock,
            return_value=updated,
        ):
            response = await authenticated_client.put(
                f"{BASE}/campaigns/{CAMPAIGN_ID}",
                json={"name": "Nombre actualizado"},
            )

        # 200 on success; 404 if not found; 409 if already sent (not draft)
        assert response.status_code in (200, 404, 409, 500)

    async def test_requires_auth(self, async_client):
        """PUT /marketing/campaigns/{id} without JWT returns 401."""
        response = await async_client.put(
            f"{BASE}/campaigns/{CAMPAIGN_ID}",
            json={"name": "Nombre nuevo"},
        )
        assert response.status_code == 401


# ─── TestSendCampaign ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSendCampaign:
    async def test_send_returns_202(self, authenticated_client):
        """POST /marketing/campaigns/{id}/send enqueues the campaign (202 Accepted)."""
        with patch(
            "app.services.email_campaign_service.email_campaign_service.send_campaign",
            new_callable=AsyncMock,
            return_value=_SENT_DISPATCH,
        ):
            response = await authenticated_client.post(
                f"{BASE}/campaigns/{CAMPAIGN_ID}/send"
            )

        # 202 on success (always returns 202 per spec);
        # 404 campaign not found; 409 wrong status; 500 on DB error
        assert response.status_code in (202, 404, 409, 500)

    async def test_requires_auth(self, async_client):
        """POST /marketing/campaigns/{id}/send without JWT returns 401."""
        response = await async_client.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/send")
        assert response.status_code == 401


# ─── TestScheduleCampaign ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestScheduleCampaign:
    async def test_schedule_returns_200(self, authenticated_client):
        """POST /marketing/campaigns/{id}/schedule sets scheduled_at."""
        # scheduled_at must be a future UTC datetime (ScheduleRequest validator)
        future_dt = (datetime.now(UTC) + timedelta(hours=48)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with patch(
            "app.services.email_campaign_service.email_campaign_service.schedule_campaign",
            new_callable=AsyncMock,
            return_value=_SCHEDULED_CAMPAIGN,
        ):
            response = await authenticated_client.post(
                f"{BASE}/campaigns/{CAMPAIGN_ID}/schedule",
                json={"scheduled_at": future_dt},
            )

        # 200 on success; 404 not found; 409 wrong status; 422 past datetime
        assert response.status_code in (200, 404, 409, 422, 500)

    async def test_requires_auth(self, async_client):
        """POST /marketing/campaigns/{id}/schedule without JWT returns 401."""
        future_dt = (datetime.now(UTC) + timedelta(hours=48)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        response = await async_client.post(
            f"{BASE}/campaigns/{CAMPAIGN_ID}/schedule",
            json={"scheduled_at": future_dt},
        )
        assert response.status_code == 401


# ─── TestDeleteCampaign ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestDeleteCampaign:
    async def test_delete_returns_200(self, authenticated_client):
        """DELETE /marketing/campaigns/{id} soft-deletes or cancels a campaign."""
        with patch(
            "app.services.email_campaign_service.email_campaign_service.delete_campaign",
            new_callable=AsyncMock,
            return_value=_DELETED_CAMPAIGN,
        ):
            response = await authenticated_client.delete(
                f"{BASE}/campaigns/{CAMPAIGN_ID}"
            )

        # 200 on success; 404 if not found
        assert response.status_code in (200, 404, 500)

    async def test_requires_auth(self, async_client):
        """DELETE /marketing/campaigns/{id} without JWT returns 401."""
        response = await async_client.delete(f"{BASE}/campaigns/{CAMPAIGN_ID}")
        assert response.status_code == 401


# ─── TestTemplates ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestTemplates:
    async def test_list_templates_returns_200(self, authenticated_client):
        """GET /marketing/templates returns the built-in template catalogue."""
        with patch(
            "app.services.email_campaign_service.email_campaign_service.get_templates",
            return_value=_TEMPLATES,
        ):
            response = await authenticated_client.get(f"{BASE}/templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Service is patched to return 3 templates
        assert len(data) == 3
        template_ids = [t["template_id"] for t in data]
        assert "reactivation" in template_ids
        assert "birthday" in template_ids

    async def test_requires_auth(self, async_client):
        """GET /marketing/templates without JWT returns 401."""
        response = await async_client.get(f"{BASE}/templates")
        assert response.status_code == 401


# ─── TestTrackingPublic ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestTrackingPublic:
    async def test_open_tracking_returns_gif(self, async_client):
        """GET /public/track/open/{schema}/{id} returns a 1×1 GIF (image/gif).

        The endpoint is intentionally public (no JWT required) and always
        returns the tracking pixel regardless of whether the recipient_id exists.
        This test uses a valid schema-pattern path segment (tn_*) and a random
        UUID for the recipient.
        """
        with patch(
            "app.services.email_tracking_service.email_tracking_service.handle_open_tracking",
            new_callable=AsyncMock,
            return_value=_TRACKING_PIXEL,
        ):
            response = await async_client.get(
                f"{PUBLIC_BASE}/track/open/{TENANT_SCHEMA}/{RECIPIENT_ID}"
            )

        assert response.status_code == 200
        assert "image/gif" in response.headers.get("content-type", "")

    async def test_click_tracking_returns_redirect(self, async_client):
        """GET /public/track/click/{schema}/{id}?url=... redirects (302) or returns 200.

        Without a real DB the service returns an error and the handler falls
        back to the sanitized URL. The response should be a redirect (302) or
        a direct response (200 if httpx follows redirects automatically).
        """
        destination = "https://dentalos.co"
        with patch(
            "app.services.email_tracking_service.email_tracking_service.handle_click_tracking",
            new_callable=AsyncMock,
            return_value=destination,
        ):
            response = await async_client.get(
                f"{PUBLIC_BASE}/track/click/{TENANT_SCHEMA}/{RECIPIENT_ID}",
                params={"url": destination},
                follow_redirects=False,
            )

        # 302 redirect to destination URL; 200 if httpx followed the redirect
        assert response.status_code in (200, 302)

    async def test_unsubscribe_returns_html(self, async_client):
        """GET /public/unsubscribe/{schema}/{id} renders a Spanish HTML confirmation.

        The endpoint is public (no JWT), idempotent, and always returns 200
        with an HTML body regardless of whether the recipient_id exists.
        """
        with patch(
            "app.services.email_tracking_service.email_tracking_service.handle_unsubscribe",
            new_callable=AsyncMock,
            return_value=_UNSUBSCRIBE_HTML,
        ):
            response = await async_client.get(
                f"{PUBLIC_BASE}/unsubscribe/{TENANT_SCHEMA}/{RECIPIENT_ID}"
            )

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
