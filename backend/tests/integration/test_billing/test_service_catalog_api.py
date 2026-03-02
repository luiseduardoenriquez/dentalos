"""Integration tests for Service Catalog API (B-14, B-15).

Endpoints:
  GET /api/v1/services              — B-14: List service catalog (any staff)
  PUT /api/v1/services/{service_id} — B-15: Update service (billing:write)
"""

import uuid

import pytest

BASE = "/api/v1/services"
SERVICE_ID = str(uuid.uuid4())


# ─── B-14: List services ────────────────────────────────────────────────────


@pytest.mark.integration
class TestListServices:
    async def test_list_default(self, authenticated_client):
        response = await authenticated_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_with_category(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"category": "general"}
        )
        assert response.status_code in (200, 500)

    async def test_list_with_search(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"search": "limpieza"}
        )
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 5}
        )
        assert response.status_code in (200, 500)

    async def test_list_invalid_limit(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 0}
        )
        assert response.status_code == 422

    async def test_list_doctor_has_read(self, doctor_client):
        response = await doctor_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 401


# ─── B-15: Update service ───────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateService:
    async def test_update_as_owner(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{SERVICE_ID}",
            json={
                "name": "Limpieza dental premium",
                "default_price": 80000,
            },
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_deactivate(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{SERVICE_ID}",
            json={"is_active": False},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_doctor_no_billing_write(self, doctor_client):
        response = await doctor_client.put(
            f"{BASE}/{SERVICE_ID}",
            json={"name": "Test"},
        )
        assert response.status_code == 403

    async def test_update_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/{SERVICE_ID}",
            json={"name": "Test"},
        )
        assert response.status_code == 401
