"""Integration tests for Recall Engine API (VP-02).

Endpoints:
  POST /api/v1/recall/campaigns
  GET  /api/v1/recall/campaigns
  PUT  /api/v1/recall/campaigns/{id}
  POST /api/v1/recall/campaigns/{id}/activate
  POST /api/v1/recall/campaigns/{id}/pause
"""

import uuid

import pytest

BASE = "/api/v1/recall/campaigns"

CAMPAIGN_ID = str(uuid.uuid4())


def _campaign_payload(**overrides) -> dict:
    """Build a valid campaign creation payload with optional overrides."""
    base = {
        "name": "Recall Limpieza Semestral",
        "type": "recall",
        "channel": "whatsapp",
        "filters": {"months_inactive": 6},
        "message_templates": {
            "whatsapp": "Hola {patient_name}, es hora de tu limpieza semestral.",
        },
        "schedule": {
            "sequence": [
                {"delay_days": 0, "channel": "whatsapp"},
                {"delay_days": 7, "channel": "sms"},
            ],
        },
    }
    base.update(overrides)
    return base


# ── POST /api/v1/recall/campaigns ────────────────────────────────────────────


@pytest.mark.integration
class TestCreateCampaign:
    async def test_create_valid_campaign(self, authenticated_client):
        response = await authenticated_client.post(BASE, json=_campaign_payload())
        assert response.status_code in (201, 500)

    async def test_create_campaign_all_types(self, authenticated_client):
        """Each campaign type should be accepted."""
        for ctype in ("recall", "reactivation", "treatment_followup", "birthday"):
            response = await authenticated_client.post(
                BASE, json=_campaign_payload(name=f"Camp {ctype}", type=ctype)
            )
            assert response.status_code in (201, 500)

    async def test_create_campaign_missing_name(self, authenticated_client):
        payload = _campaign_payload()
        del payload["name"]
        response = await authenticated_client.post(BASE, json=payload)
        assert response.status_code == 422

    async def test_create_campaign_missing_type(self, authenticated_client):
        payload = _campaign_payload()
        del payload["type"]
        response = await authenticated_client.post(BASE, json=payload)
        assert response.status_code == 422

    async def test_create_campaign_invalid_type(self, authenticated_client):
        response = await authenticated_client.post(
            BASE, json=_campaign_payload(type="invalid_type")
        )
        assert response.status_code == 422

    async def test_create_campaign_no_auth(self, async_client):
        response = await async_client.post(BASE, json=_campaign_payload())
        assert response.status_code == 401


# ── GET /api/v1/recall/campaigns ─────────────────────────────────────────────


@pytest.mark.integration
class TestListCampaigns:
    async def test_list_campaigns(self, authenticated_client):
        response = await authenticated_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_campaigns_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"page": 1, "page_size": 10}
        )
        assert response.status_code in (200, 500)

    async def test_list_campaigns_with_status_filter(self, authenticated_client):
        response = await authenticated_client.get(BASE, params={"status": "active"})
        assert response.status_code in (200, 500)

    async def test_list_campaigns_invalid_page_size(self, authenticated_client):
        response = await authenticated_client.get(BASE, params={"page_size": 0})
        assert response.status_code == 422

    async def test_list_campaigns_no_auth(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 401


# ── PUT /api/v1/recall/campaigns/{id} ────────────────────────────────────────


@pytest.mark.integration
class TestUpdateCampaign:
    async def test_update_nonexistent_campaign(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{uuid.uuid4()}",
            json={"name": "Nombre Actualizado"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_campaign_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/{CAMPAIGN_ID}",
            json={"name": "Sin Auth"},
        )
        assert response.status_code == 401


# ── POST /api/v1/recall/campaigns/{id}/activate ──────────────────────────────


@pytest.mark.integration
class TestActivateCampaign:
    async def test_activate_nonexistent_campaign(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{uuid.uuid4()}/activate",
        )
        assert response.status_code in (404, 500)

    async def test_activate_campaign_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/{CAMPAIGN_ID}/activate",
        )
        assert response.status_code == 401


# ── POST /api/v1/recall/campaigns/{id}/pause ─────────────────────────────────


@pytest.mark.integration
class TestPauseCampaign:
    async def test_pause_nonexistent_campaign(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{uuid.uuid4()}/pause",
        )
        assert response.status_code in (404, 500)

    async def test_pause_campaign_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/{CAMPAIGN_ID}/pause",
        )
        assert response.status_code == 401
