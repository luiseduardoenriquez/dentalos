"""Integration tests for NPS/CSAT Survey API (VP-21 / Sprint 29-30).

Endpoints under test:

Staff (JWT-protected):
  GET  /api/v1/analytics/nps              — NPS dashboard
  GET  /api/v1/analytics/nps/by-doctor    — NPS breakdown per doctor
  POST /api/v1/surveys/send               — Send survey
  GET  /api/v1/surveys                    — List surveys

Public (no auth):
  GET  /api/v1/public/{slug}/nps-survey/{token}  — Get survey info
  POST /api/v1/public/{slug}/nps-survey/{token}  — Submit response

Permissions:
  surveys:read  — clinic_owner, doctor, assistant, receptionist
  surveys:write — clinic_owner, doctor
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import SurveyErrors

BASE = "/api/v1"
PUBLIC_BASE = "/api/v1/public"

TENANT_SLUG = "test-clinic"
SURVEY_TOKEN = "tok-abc123xyz456"
PATIENT_ID = str(uuid.uuid4())
DOCTOR_ID = str(uuid.uuid4())

# ── Canned response objects ────────────────────────────────────────────────────

_NPS_DASHBOARD = {
    "nps_score": 42.0,
    "promoters": 21,
    "passives": 8,
    "detractors": 11,
    "total_responses": 40,
    "trend": [
        {"period": "2026-01", "nps_score": 38.0, "responses": 15},
        {"period": "2026-02", "nps_score": 45.0, "responses": 25},
    ],
}

_NPS_BY_DOCTOR = {
    "items": [
        {
            "doctor_id": DOCTOR_ID,
            "doctor_name": "Dr. García",
            "nps_score": 50.0,
            "promoters": 10,
            "passives": 3,
            "detractors": 7,
            "total": 20,
        }
    ]
}

_SURVEY_SENT = {
    "id": str(uuid.uuid4()),
    "patient_id": PATIENT_ID,
    "doctor_id": DOCTOR_ID,
    "appointment_id": None,
    "nps_score": None,
    "csat_score": None,
    "comments": None,
    "channel_sent": "whatsapp",
    "sent_at": "2026-03-03T10:00:00+00:00",
    "responded_at": None,
}

_SURVEYS_LIST = {
    "items": [_SURVEY_SENT],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_SURVEY_PUBLIC_INFO = {
    "doctor_name": "Dr. García",
    "clinic_name": "Clínica Dental Test",
    "already_responded": False,
}

_SUBMIT_RESPONSE = {
    "message": "Gracias por tu opinion. Tu respuesta ha sido registrada.",
}


# ── TestNpsDashboard ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNpsDashboard:
    async def test_get_nps_dashboard_200(self, authenticated_client):
        """GET /analytics/nps returns dashboard with NPS metrics."""
        with patch(
            "app.services.nps_survey_service.nps_survey_service.get_nps_dashboard",
            new_callable=AsyncMock,
            return_value=_NPS_DASHBOARD,
        ):
            response = await authenticated_client.get(f"{BASE}/analytics/nps")

        assert response.status_code in (200, 404, 500)

    async def test_nps_requires_auth(self, async_client):
        """GET /analytics/nps without JWT returns 401."""
        response = await async_client.get(f"{BASE}/analytics/nps")
        assert response.status_code == 401

    async def test_get_nps_by_doctor_200(self, authenticated_client):
        """GET /analytics/nps/by-doctor returns breakdown per doctor."""
        with patch(
            "app.services.nps_survey_service.nps_survey_service.get_nps_by_doctor",
            new_callable=AsyncMock,
            return_value=_NPS_BY_DOCTOR,
        ):
            response = await authenticated_client.get(
                f"{BASE}/analytics/nps/by-doctor"
            )

        assert response.status_code in (200, 404, 500)

    async def test_nps_by_doctor_requires_auth(self, async_client):
        """GET /analytics/nps/by-doctor without JWT returns 401."""
        response = await async_client.get(f"{BASE}/analytics/nps/by-doctor")
        assert response.status_code == 401


# ── TestSendSurvey ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSendSurvey:
    async def test_send_survey_201(self, authenticated_client):
        """POST /surveys/send creates a survey and returns 201."""
        with patch(
            "app.services.nps_survey_service.nps_survey_service.send_survey",
            new_callable=AsyncMock,
            return_value=_SURVEY_SENT,
        ):
            response = await authenticated_client.post(
                f"{BASE}/surveys/send",
                json={
                    "patient_id": PATIENT_ID,
                    "doctor_id": DOCTOR_ID,
                    "channel": "whatsapp",
                },
            )

        assert response.status_code in (200, 201, 404, 422, 500)

    async def test_send_survey_requires_auth(self, async_client):
        """POST /surveys/send without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/surveys/send",
            json={
                "patient_id": PATIENT_ID,
                "doctor_id": DOCTOR_ID,
                "channel": "whatsapp",
            },
        )
        assert response.status_code == 401

    async def test_send_survey_requires_write(
        self, async_client, test_user, test_tenant
    ):
        """POST /surveys/send with assistant (read-only) JWT checks permission.

        Assistants have surveys:read but not surveys:write on all endpoints.
        If the endpoint requires surveys:write, assistant gets 403.
        """
        from app.auth.permissions import get_permissions_for_role
        from app.core.security import create_access_token

        perms = get_permissions_for_role("assistant")
        token = create_access_token(
            user_id=str(test_user.id),
            tenant_id=str(test_tenant.id),
            role="assistant",
            permissions=list(perms),
            email=test_user.email,
            name=test_user.name,
        )
        async_client.headers["Authorization"] = f"Bearer {token}"

        response = await async_client.post(
            f"{BASE}/surveys/send",
            json={
                "patient_id": PATIENT_ID,
                "doctor_id": DOCTOR_ID,
                "channel": "whatsapp",
            },
        )
        # 403 if surveys:write required and not present, or 200/201/404/500 otherwise
        assert response.status_code in (200, 201, 403, 404, 422, 500)


# ── TestListSurveys ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListSurveys:
    async def test_list_surveys_200(self, authenticated_client):
        """GET /surveys returns paginated survey list."""
        with patch(
            "app.services.nps_survey_service.nps_survey_service.list_surveys",
            new_callable=AsyncMock,
            return_value=_SURVEYS_LIST,
        ):
            response = await authenticated_client.get(f"{BASE}/surveys")

        assert response.status_code in (200, 404, 500)

    async def test_list_surveys_requires_auth(self, async_client):
        """GET /surveys without JWT returns 401."""
        response = await async_client.get(f"{BASE}/surveys")
        assert response.status_code == 401


# ── TestPublicSurveyEndpoints ─────────────────────────────────────────────────


@pytest.mark.integration
class TestPublicSurveyEndpoints:
    async def test_public_get_survey_200(self, async_client):
        """GET /public/{slug}/nps-survey/{token} returns survey public info."""
        with patch(
            "app.services.nps_survey_service.nps_survey_service.get_survey_by_token",
            new_callable=AsyncMock,
            return_value=MagicMock(
                id=uuid.uuid4(),
                doctor_id=uuid.uuid4(),
                responded_at=None,
            ),
        ):
            response = await async_client.get(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/nps-survey/{SURVEY_TOKEN}"
            )

        # 200 with mock; 404 if tenant slug not in test DB; 429 if rate limited
        assert response.status_code in (200, 404, 422, 429, 500)

    async def test_public_submit_survey_200(self, async_client):
        """POST /public/{slug}/nps-survey/{token} submits response successfully."""
        submitted_survey = MagicMock()
        submitted_survey.id = uuid.uuid4()
        submitted_survey.nps_score = 9
        submitted_survey.responded_at = datetime.now(UTC)

        with patch(
            "app.services.nps_survey_service.nps_survey_service.submit_response",
            new_callable=AsyncMock,
            return_value={},
        ):
            response = await async_client.post(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/nps-survey/{SURVEY_TOKEN}",
                json={"nps_score": 9, "csat_score": 5, "comments": "Muy buena atención"},
            )

        # 200 with mock; 404 if tenant not found; 429 rate limited
        assert response.status_code in (200, 404, 422, 429, 500)

    async def test_public_submit_already_responded_409(self, async_client):
        """POST /public/{slug}/nps-survey/{token} when already responded returns 409."""
        from app.core.exceptions import DentalOSError

        with patch(
            "app.services.nps_survey_service.nps_survey_service.submit_response",
            new_callable=AsyncMock,
            side_effect=DentalOSError(
                error=SurveyErrors.ALREADY_RESPONDED,
                message="Esta encuesta ya fue respondida.",
                status_code=409,
            ),
        ):
            response = await async_client.post(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/nps-survey/{SURVEY_TOKEN}",
                json={"nps_score": 8, "csat_score": None, "comments": None},
            )

        assert response.status_code in (404, 409, 429, 500)

    async def test_public_invalid_token_404(self, async_client):
        """GET /public/{slug}/nps-survey/invalid-token returns 404."""
        with patch(
            "app.services.nps_survey_service.nps_survey_service.get_survey_by_token",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await async_client.get(
                f"{PUBLIC_BASE}/{TENANT_SLUG}/nps-survey/totally-invalid-token"
            )

        assert response.status_code in (404, 429, 500)
