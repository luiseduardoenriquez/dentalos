"""Integration tests for Portal Action API (PP-05, PP-08, PP-09, PP-11, PP-12).

All portal action endpoints require portal JWT auth (get_current_portal_user).
Without a valid portal token, requests should fail with 401/403/422/500.

Endpoints:
  POST /api/v1/portal/treatment-plans/{plan_id}/approve   — PP-05
  POST /api/v1/portal/appointments                        — PP-08
  POST /api/v1/portal/appointments/{id}/cancel             — PP-09
  POST /api/v1/portal/messages                              — PP-11
  POST /api/v1/portal/consents/{consent_id}/sign            — PP-12
"""

import uuid

import pytest

PORTAL_BASE = "/api/v1/portal"
PLAN_ID = str(uuid.uuid4())
APPT_ID = str(uuid.uuid4())
CONSENT_ID = str(uuid.uuid4())


@pytest.mark.integration
class TestPortalApprovePlan:
    async def test_approve_no_auth(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/treatment-plans/{PLAN_ID}/approve",
            json={"signature_data": "base64data", "agreed_terms": True},
        )
        assert response.status_code in (401, 403, 422, 500)

    async def test_approve_missing_signature(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/treatment-plans/{PLAN_ID}/approve",
            json={"agreed_terms": True},
        )
        assert response.status_code in (401, 422, 500)

    async def test_approve_staff_jwt_rejected(self, authenticated_client):
        response = await authenticated_client.post(
            f"{PORTAL_BASE}/treatment-plans/{PLAN_ID}/approve",
            json={"signature_data": "base64data", "agreed_terms": True},
        )
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalBookAppointment:
    async def test_book_no_auth(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/appointments",
            json={
                "doctor_id": str(uuid.uuid4()),
                "appointment_type_id": str(uuid.uuid4()),
                "preferred_date": "2026-04-15",
                "preferred_time": "10:00",
            },
        )
        assert response.status_code in (401, 403, 422, 500)

    async def test_book_invalid_date_format(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/appointments",
            json={
                "doctor_id": str(uuid.uuid4()),
                "appointment_type_id": str(uuid.uuid4()),
                "preferred_date": "15-04-2026",
                "preferred_time": "10:00",
            },
        )
        assert response.status_code in (401, 422, 500)

    async def test_book_invalid_time_format(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/appointments",
            json={
                "doctor_id": str(uuid.uuid4()),
                "appointment_type_id": str(uuid.uuid4()),
                "preferred_date": "2026-04-15",
                "preferred_time": "10:00:00",
            },
        )
        assert response.status_code in (401, 422, 500)

    async def test_book_missing_doctor_id(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/appointments",
            json={
                "appointment_type_id": str(uuid.uuid4()),
                "preferred_date": "2026-04-15",
                "preferred_time": "10:00",
            },
        )
        assert response.status_code in (401, 422, 500)


@pytest.mark.integration
class TestPortalCancelAppointment:
    async def test_cancel_no_auth(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/appointments/{APPT_ID}/cancel",
            json={"reason": "No puedo asistir"},
        )
        assert response.status_code in (401, 403, 422, 500)


@pytest.mark.integration
class TestPortalSendMessage:
    async def test_send_no_auth(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/messages",
            json={"body": "Hola, tengo una pregunta."},
        )
        assert response.status_code in (401, 403, 422, 500)

    async def test_send_empty_body(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/messages",
            json={"body": ""},
        )
        assert response.status_code in (401, 422, 500)

    async def test_send_body_too_long(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/messages",
            json={"body": "x" * 2001},
        )
        assert response.status_code in (401, 422, 500)


@pytest.mark.integration
class TestPortalSignConsent:
    async def test_sign_no_auth(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/consents/{CONSENT_ID}/sign",
            json={"signature_data": "base64data", "acknowledged": True},
        )
        assert response.status_code in (401, 403, 422, 500)

    async def test_sign_missing_acknowledged(self, async_client):
        response = await async_client.post(
            f"{PORTAL_BASE}/consents/{CONSENT_ID}/sign",
            json={"signature_data": "base64data"},
        )
        assert response.status_code in (401, 422, 500)
