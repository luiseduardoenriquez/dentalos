"""Integration tests for RETHUS professional verification API (VP-07 / Sprint 23-24).

Endpoints:
  GET  /api/v1/users/{user_id}/rethus-verification -- Read current status
  POST /api/v1/users/{user_id}/rethus-verification -- Trigger verification

GET requires users:read; POST requires users:write (clinic_owner in practice).
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

USER_ID = str(uuid.uuid4())
BASE = f"/api/v1/users/{USER_ID}/rethus-verification"

_VERIFIED_RESPONSE = {
    "user_id": USER_ID,
    "rethus_number": "CO123456",
    "verification_status": "verified",
    "verified_at": "2026-03-02T08:00:00+00:00",
    "professional_name": None,  # PHI not returned on GET
    "profession": None,
    "specialty": None,
}

_PENDING_RESPONSE = {
    "user_id": USER_ID,
    "rethus_number": None,
    "verification_status": "pending",
    "verified_at": None,
    "professional_name": None,
    "profession": None,
    "specialty": None,
}

_TRIGGER_SUCCESS_RESPONSE = {
    "user_id": USER_ID,
    "rethus_number": "CO123456",
    "verification_status": "verified",
    "verified_at": "2026-03-02T12:00:00+00:00",
    "professional_name": "Dr. Juan Perez",
    "profession": "Odontólogo",
    "specialty": "Odontología General",
}


# ─── GET: Current RETHUS verification status ─────────────────────────────────


@pytest.mark.integration
class TestGetRethusVerification:
    async def test_get_verified_user(self, authenticated_client):
        """GET returns current status for a user whose RETHUS check has passed."""
        with patch(
            "app.services.rethus_verification_service.rethus_verification_service.check_status",
            new_callable=AsyncMock,
            return_value=_VERIFIED_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert data["verification_status"] == "verified"
        assert data["rethus_number"] == "CO123456"
        # PHI fields must not be surfaced on GET per spec
        assert data.get("professional_name") is None

    async def test_get_pending_user(self, authenticated_client):
        """GET returns pending when no verification has been run for this user."""
        with patch(
            "app.services.rethus_verification_service.rethus_verification_service.check_status",
            new_callable=AsyncMock,
            return_value=_PENDING_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert data["verification_status"] == "pending"

    async def test_get_unknown_user_id(self, authenticated_client):
        """GET for a non-existent user_id returns 404 or 500."""
        other_id = str(uuid.uuid4())
        url = f"/api/v1/users/{other_id}/rethus-verification"

        with patch(
            "app.services.rethus_verification_service.rethus_verification_service.check_status",
            new_callable=AsyncMock,
            side_effect=Exception("User not found"),
        ):
            response = await authenticated_client.get(url)

        assert response.status_code in (404, 500)

    async def test_get_invalid_user_id_format(self, authenticated_client):
        """A non-UUID user_id in the path causes FastAPI 422."""
        response = await authenticated_client.get(
            "/api/v1/users/not-a-uuid/rethus-verification"
        )
        assert response.status_code == 422


# ─── POST: Trigger RETHUS verification ────────────────────────────────────────


@pytest.mark.integration
class TestTriggerRethusVerification:
    async def test_trigger_valid_rethus_number(self, authenticated_client):
        """POST with a valid RETHUS number triggers lookup and returns result."""
        with patch(
            "app.services.rethus_verification_service.rethus_verification_service.verify_user",
            new_callable=AsyncMock,
            return_value=_TRIGGER_SUCCESS_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE,
                json={"rethus_number": "CO123456"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["verification_status"] == "verified"
        # professional_name is surfaced only on the trigger response
        assert data["professional_name"] is not None

    async def test_trigger_missing_rethus_number_returns_422(self, authenticated_client):
        """POST without rethus_number in body returns 422."""
        response = await authenticated_client.post(BASE, json={})
        assert response.status_code == 422

    async def test_trigger_empty_rethus_number_returns_422(self, authenticated_client):
        """POST with rethus_number='' fails min_length=1 validation."""
        response = await authenticated_client.post(
            BASE, json={"rethus_number": ""}
        )
        assert response.status_code == 422

    async def test_trigger_invalid_rethus_pattern_returns_422(self, authenticated_client):
        """POST with special characters fails the alphanumeric pattern validation."""
        response = await authenticated_client.post(
            BASE, json={"rethus_number": "CO-123 456"}
        )
        assert response.status_code == 422

    async def test_trigger_too_long_rethus_number_returns_422(self, authenticated_client):
        """POST with rethus_number longer than 50 chars returns 422."""
        response = await authenticated_client.post(
            BASE, json={"rethus_number": "A" * 51}
        )
        assert response.status_code == 422

    async def test_trigger_invalid_user_id_format(self, authenticated_client):
        """POST with a non-UUID user_id in the path returns 422."""
        response = await authenticated_client.post(
            "/api/v1/users/not-a-uuid/rethus-verification",
            json={"rethus_number": "CO123456"},
        )
        assert response.status_code == 422


# ─── Authorization ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestRethusVerificationUnauthorized:
    async def test_get_no_auth_returns_401(self, async_client):
        """GET without JWT is rejected with 401."""
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_post_no_auth_returns_401(self, async_client):
        """POST without JWT is rejected with 401."""
        response = await async_client.post(
            BASE, json={"rethus_number": "CO123456"}
        )
        assert response.status_code == 401
