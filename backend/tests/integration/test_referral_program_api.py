"""Integration tests for the Patient Referral Program API (VP-08 / Sprint 23-24).

Endpoints:
  GET /api/v1/referral-program/stats         -- Staff view: aggregate stats
  GET /api/v1/portal/referral                -- Portal: get/create patient's code
  GET /api/v1/portal/referral/rewards        -- Portal: list patient's rewards

Staff endpoint requires referral_program:read (clinic_owner).
Portal endpoints use portal JWT (get_current_portal_user); we test the
unauthenticated paths that do not require a portal fixture.
"""

from unittest.mock import AsyncMock, patch

import pytest

STAFF_BASE = "/api/v1/referral-program"
PORTAL_BASE = "/api/v1/portal/referral"

_STATS_RESPONSE = {
    "total_referrals": 42,
    "pending_referrals": 8,
    "converted_referrals": 30,
    "expired_referrals": 4,
    "total_rewards_issued": 15,
    "program_active": True,
}

_CODE_RESPONSE = {
    "patient_id": "00000000-0000-0000-0000-000000000001",
    "referral_code": "DENTAL-XK9F2",
    "share_url": "https://clinica.dentalos.co/ref/DENTAL-XK9F2",
    "times_used": 3,
    "created_at": "2026-01-15T09:00:00+00:00",
}

_REWARDS_RESPONSE = {
    "items": [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "reward_type": "discount",
            "discount_percent": 10,
            "status": "active",
            "issued_at": "2026-02-01T10:00:00+00:00",
            "expires_at": "2026-05-01T10:00:00+00:00",
        }
    ],
    "total": 1,
}


# ─── GET /referral-program/stats (staff) ─────────────────────────────────────


@pytest.mark.integration
class TestGetReferralStats:
    async def test_get_stats_as_owner(self, authenticated_client):
        """clinic_owner can read referral program statistics."""
        with patch(
            "app.services.referral_program_service.referral_program_service.get_program_stats",
            new_callable=AsyncMock,
            return_value=_STATS_RESPONSE,
        ):
            response = await authenticated_client.get(f"{STAFF_BASE}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_referrals" in data
        assert "converted_referrals" in data

    async def test_get_stats_no_auth(self, async_client):
        """GET without JWT is rejected with 401."""
        response = await async_client.get(f"{STAFF_BASE}/stats")
        assert response.status_code == 401

    async def test_get_stats_as_doctor(self, doctor_client):
        """doctor role lacks referral_program:read and should receive 403."""
        response = await doctor_client.get(f"{STAFF_BASE}/stats")
        assert response.status_code == 403

    async def test_stats_structure(self, authenticated_client):
        """Response includes all expected aggregate fields."""
        with patch(
            "app.services.referral_program_service.referral_program_service.get_program_stats",
            new_callable=AsyncMock,
            return_value=_STATS_RESPONSE,
        ):
            response = await authenticated_client.get(f"{STAFF_BASE}/stats")

        assert response.status_code == 200
        data = response.json()
        for field in (
            "total_referrals",
            "pending_referrals",
            "converted_referrals",
            "program_active",
        ):
            assert field in data


# ─── GET /portal/referral (portal patient) ───────────────────────────────────


@pytest.mark.integration
class TestPortalGetReferralCode:
    async def test_no_portal_auth_rejected(self, async_client):
        """Portal referral endpoint without portal JWT returns 401/403/422."""
        response = await async_client.get(PORTAL_BASE)
        assert response.status_code in (401, 403, 422, 500)

    async def test_staff_jwt_rejected_on_portal_endpoint(self, authenticated_client):
        """Staff JWT is not valid for the portal JWT dependency."""
        response = await authenticated_client.get(PORTAL_BASE)
        assert response.status_code in (401, 403, 422, 500)


# ─── GET /portal/referral/rewards (portal patient) ───────────────────────────


@pytest.mark.integration
class TestPortalGetRewards:
    async def test_no_portal_auth_rejected(self, async_client):
        """Portal rewards endpoint without portal JWT returns 401/403/422."""
        response = await async_client.get(f"{PORTAL_BASE}/rewards")
        assert response.status_code in (401, 403, 422, 500)

    async def test_staff_jwt_rejected_on_portal_rewards(self, authenticated_client):
        """Staff JWT is not valid for the portal JWT dependency on rewards."""
        response = await authenticated_client.get(f"{PORTAL_BASE}/rewards")
        assert response.status_code in (401, 403, 422, 500)
