"""Integration tests for Portal Data API (PP-02, PP-03, PP-04, PP-06, PP-07,
PP-10, PP-13).

All portal data endpoints require portal JWT auth (get_current_portal_user).
Without a valid portal token, requests should fail with 401/403/422/500.

Endpoints:
  GET /api/v1/portal/me               — PP-02
  GET /api/v1/portal/appointments      — PP-03
  GET /api/v1/portal/treatment-plans   — PP-04
  GET /api/v1/portal/invoices          — PP-06
  GET /api/v1/portal/documents         — PP-07
  GET /api/v1/portal/messages          — PP-10
  GET /api/v1/portal/odontogram        — PP-13
"""

import pytest

PORTAL_BASE = "/api/v1/portal"


@pytest.mark.integration
class TestPortalProfile:
    async def test_profile_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/me")
        assert response.status_code in (401, 403, 422, 500)

    async def test_profile_staff_jwt_rejected(self, authenticated_client):
        """Staff JWT should not work on portal endpoints."""
        response = await authenticated_client.get(f"{PORTAL_BASE}/me")
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalAppointments:
    async def test_appointments_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/appointments")
        assert response.status_code in (401, 403, 422, 500)

    async def test_appointments_invalid_view(self, async_client):
        response = await async_client.get(
            f"{PORTAL_BASE}/appointments", params={"view": "invalid"}
        )
        assert response.status_code in (401, 422, 500)

    async def test_appointments_invalid_limit(self, async_client):
        response = await async_client.get(
            f"{PORTAL_BASE}/appointments", params={"limit": 0}
        )
        assert response.status_code in (401, 422, 500)


@pytest.mark.integration
class TestPortalTreatmentPlans:
    async def test_treatment_plans_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/treatment-plans")
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalInvoices:
    async def test_invoices_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/invoices")
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalDocuments:
    async def test_documents_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/documents")
        assert response.status_code in (401, 403, 422, 500)

    async def test_documents_with_type_filter_no_auth(self, async_client):
        response = await async_client.get(
            f"{PORTAL_BASE}/documents", params={"doc_type": "consent"}
        )
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalMessages:
    async def test_messages_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/messages")
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalOdontogram:
    async def test_odontogram_no_auth(self, async_client):
        response = await async_client.get(f"{PORTAL_BASE}/odontogram")
        assert response.status_code in (401, 403, 422, 500)
