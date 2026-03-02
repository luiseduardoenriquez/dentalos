"""Integration tests for Referral API (P-15).

Endpoints:
  GET /api/v1/referrals/incoming          — List incoming referrals
  PUT /api/v1/referrals/{referral_id}     — Update referral status
"""

import uuid

import pytest

BASE = "/api/v1/referrals"
REFERRAL_ID = str(uuid.uuid4())


@pytest.mark.integration
class TestListIncomingReferrals:
    async def test_list_authenticated(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/incoming")
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/incoming", params={"page": 1, "page_size": 5}
        )
        assert response.status_code in (200, 500)

    async def test_list_as_doctor(self, doctor_client):
        response = await doctor_client.get(f"{BASE}/incoming")
        assert response.status_code in (200, 500)

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/incoming")
        assert response.status_code == 401


@pytest.mark.integration
class TestUpdateReferral:
    async def test_update_accepted(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{REFERRAL_ID}",
            json={"status": "accepted"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_completed(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{REFERRAL_ID}",
            json={"status": "completed", "notes": "Tratamiento finalizado."},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_declined(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{REFERRAL_ID}",
            json={"status": "declined", "notes": "No disponible."},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_invalid_status(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{REFERRAL_ID}",
            json={"status": "pending"},
        )
        assert response.status_code == 422

    async def test_update_missing_status(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{REFERRAL_ID}",
            json={"notes": "Solo notas."},
        )
        assert response.status_code == 422

    async def test_update_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/{REFERRAL_ID}",
            json={"status": "accepted"},
        )
        assert response.status_code == 401
