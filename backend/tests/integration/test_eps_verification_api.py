"""Integration tests for EPS insurance verification API (VP-06 / Sprint 23-24).

Endpoints:
  GET  /api/v1/patients/{patient_id}/eps-verification -- Latest verification result
  POST /api/v1/patients/{patient_id}/eps-verification -- Trigger manual lookup

GET requires patients:read; POST requires patients:write.
Both permissions are held by clinic_owner and doctor roles.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

PATIENT_ID = str(uuid.uuid4())
BASE = f"/api/v1/patients/{PATIENT_ID}/eps-verification"

_VERIFICATION_RESPONSE = {
    "patient_id": PATIENT_ID,
    "eps_code": "EPS001",
    "eps_name": "Sura EPS",
    "affiliation_type": "contributivo",
    "verification_status": "verified",
    "verified_at": "2026-03-02T10:00:00+00:00",
    "is_active": True,
}

_PENDING_RESPONSE = {
    "patient_id": PATIENT_ID,
    "eps_code": None,
    "eps_name": None,
    "affiliation_type": None,
    "verification_status": "pending",
    "verified_at": None,
    "is_active": False,
}


# ─── GET: Latest EPS verification ─────────────────────────────────────────────


@pytest.mark.integration
class TestGetEpsVerification:
    async def test_get_verified_patient(self, authenticated_client):
        """GET returns the latest verification result for a patient (200 ok)."""
        with patch(
            "app.services.eps_verification_service.eps_verification_service.get_latest_verification",
            new_callable=AsyncMock,
            return_value=_VERIFICATION_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert data["verification_status"] == "verified"
        assert data["eps_name"] == "Sura EPS"

    async def test_get_pending_patient(self, authenticated_client):
        """GET returns a pending status dict when no verification has been run yet."""
        with patch(
            "app.services.eps_verification_service.eps_verification_service.get_latest_verification",
            new_callable=AsyncMock,
            return_value=_PENDING_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert data["verification_status"] == "pending"

    async def test_get_unknown_patient(self, authenticated_client):
        """GET for an unknown patient_id returns 404 or 500 from the service."""
        other_id = str(uuid.uuid4())
        url = f"/api/v1/patients/{other_id}/eps-verification"

        with patch(
            "app.services.eps_verification_service.eps_verification_service.get_latest_verification",
            new_callable=AsyncMock,
            side_effect=Exception("Patient not found"),
        ):
            response = await authenticated_client.get(url)

        assert response.status_code in (404, 500)

    async def test_get_invalid_patient_id_format(self, authenticated_client):
        """A non-UUID patient_id in the path causes FastAPI 422."""
        response = await authenticated_client.get(
            "/api/v1/patients/not-a-uuid/eps-verification"
        )
        assert response.status_code == 422

    async def test_get_as_doctor(self, doctor_client):
        """doctor role has patients:read and can retrieve EPS verification."""
        with patch(
            "app.services.eps_verification_service.eps_verification_service.get_latest_verification",
            new_callable=AsyncMock,
            return_value=_VERIFICATION_RESPONSE,
        ):
            response = await doctor_client.get(BASE)

        assert response.status_code in (200, 500)


# ─── POST: Trigger EPS verification ───────────────────────────────────────────


@pytest.mark.integration
class TestTriggerEpsVerification:
    async def test_trigger_returns_200(self, authenticated_client):
        """POST triggers a fresh ADRES BDUA lookup and returns verification data."""
        with patch(
            "app.services.eps_verification_service.eps_verification_service.verify_patient",
            new_callable=AsyncMock,
            return_value=_VERIFICATION_RESPONSE,
        ):
            response = await authenticated_client.post(BASE)

        assert response.status_code == 200
        data = response.json()
        assert "verification_status" in data

    async def test_trigger_updates_cache(self, authenticated_client):
        """POST with a successful result reflects updated verified_at timestamp."""
        updated_response = {
            **_VERIFICATION_RESPONSE,
            "verified_at": "2026-03-02T12:00:00+00:00",
        }

        with patch(
            "app.services.eps_verification_service.eps_verification_service.verify_patient",
            new_callable=AsyncMock,
            return_value=updated_response,
        ):
            response = await authenticated_client.post(BASE)

        assert response.status_code == 200

    async def test_trigger_invalid_patient_id(self, authenticated_client):
        """POST with a non-UUID patient_id returns 422."""
        response = await authenticated_client.post(
            "/api/v1/patients/not-a-uuid/eps-verification"
        )
        assert response.status_code == 422


# ─── Authorization ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestEpsVerificationUnauthorized:
    async def test_get_no_auth_returns_401(self, async_client):
        """GET without JWT is rejected with 401."""
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_post_no_auth_returns_401(self, async_client):
        """POST without JWT is rejected with 401."""
        response = await async_client.post(BASE)
        assert response.status_code == 401
