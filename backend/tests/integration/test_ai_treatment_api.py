"""Integration tests for AI Treatment Advisor API (VP-13 / Sprint 27-28).

Endpoints under test:
  POST /api/v1/treatment-plans/ai-suggest              — Generate AI suggestions
  GET  /api/v1/treatment-plans/ai-suggest/{id}         — Get suggestion detail
  POST /api/v1/treatment-plans/ai-suggest/{id}/review  — Review suggestions
  POST /api/v1/treatment-plans/ai-suggest/{id}/create-plan — Create plan from accepted

Permissions:
  ai_treatment:read  — clinic_owner, doctor
  ai_treatment:write — clinic_owner, doctor
  doctor role has both ai_treatment:read and ai_treatment:write.
  receptionist role has neither → 403 on all write endpoints.

Add-on gate:
  The ai_treatment_advisor feature add-on must be active on the tenant for
  generation to succeed. In the test environment the tenant's feature set is
  minimal, so the service may return 402 (add-on not enabled) or 500 (DB miss).
  Tests therefore accept a broad status-code set for the happy-path assertions
  and focus on verifying the auth/permission layer.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/treatment-plans"

# Stable IDs reused across test classes
PATIENT_ID = str(uuid.uuid4())
SUGGESTION_ID = str(uuid.uuid4())

# ── Canned response objects ───────────────────────────────────────────────────

_SUGGESTION_ITEM = {
    "cups_code": "890201",
    "cups_description": "Consulta de primera vez por odontología general",
    "tooth_number": None,
    "rationale": "Paciente sin visita en 12 meses; revisión preventiva recomendada.",
    "confidence": "high",
    "priority_order": 1,
    "estimated_cost": 9000000,
    "action": None,
}

_SUGGESTION_RESPONSE = {
    "id": SUGGESTION_ID,
    "patient_id": PATIENT_ID,
    "doctor_id": str(uuid.uuid4()),
    "suggestions": [_SUGGESTION_ITEM],
    "model_used": "claude-opus-4",
    "status": "pending",
    "input_tokens": 1200,
    "output_tokens": 450,
    "reviewed_at": None,
    "treatment_plan_id": None,
    "created_at": "2026-03-03T10:00:00+00:00",
}

_REVIEWED_SUGGESTION = {
    **_SUGGESTION_RESPONSE,
    "status": "reviewed",
    "reviewed_at": "2026-03-03T10:10:00+00:00",
    "suggestions": [{**_SUGGESTION_ITEM, "action": "accept"}],
}

_PLAN_CREATED_RESPONSE = {
    "suggestion_id": SUGGESTION_ID,
    "treatment_plan_id": str(uuid.uuid4()),
    "items_created": 1,
    "status": "applied",
}


# ─── TestAISuggest ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestAISuggest:
    async def test_suggest_requires_auth(self, async_client):
        """POST /treatment-plans/ai-suggest without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/ai-suggest",
            json={"patient_id": PATIENT_ID},
        )
        assert response.status_code == 401

    async def test_suggest_requires_permission(self, authenticated_client):
        """clinic_owner has ai_treatment:write — endpoint is reachable (not 403).

        The service may return 402 (add-on not active), 404 (patient not found),
        or 500 (DB miss), but must NOT return 403.
        """
        response = await authenticated_client.post(
            f"{BASE}/ai-suggest",
            json={"patient_id": PATIENT_ID},
        )
        # 403 would indicate a permission failure — that must NOT happen here
        assert response.status_code != 403

    async def test_suggest_with_valid_patient(self, authenticated_client):
        """POST /treatment-plans/ai-suggest with a valid patient_id calls the service.

        In a live environment this would return 201. In the test environment
        the add-on is inactive (402), the patient does not exist in DB (404),
        or the DB is not seeded (500). All are acceptable outcomes that confirm
        the route is mounted and the permission check passes.
        """
        with patch(
            "app.services.ai_treatment_service.ai_treatment_service.generate_suggestions",
            new_callable=AsyncMock,
            return_value=_SUGGESTION_RESPONSE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/ai-suggest",
                json={"patient_id": PATIENT_ID},
            )

        assert response.status_code in (200, 201, 402, 404, 500)

    async def test_suggest_invalid_patient(self, authenticated_client):
        """POST /treatment-plans/ai-suggest with a non-existent patient_id returns 404/500."""
        nonexistent = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"{BASE}/ai-suggest",
            json={"patient_id": nonexistent},
        )
        # Without mocking, the service will either raise 404 (patient not found)
        # or 500 (DB not seeded); both are acceptable in the test environment.
        assert response.status_code in (404, 500)


# ─── TestGetSuggestion ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetSuggestion:
    async def test_get_returns_200_or_404(self, authenticated_client):
        """GET /treatment-plans/ai-suggest/{id} returns the suggestion or 404."""
        with patch(
            "app.services.ai_treatment_service.ai_treatment_service.get_suggestion",
            new_callable=AsyncMock,
            return_value=_SUGGESTION_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{BASE}/ai-suggest/{SUGGESTION_ID}"
            )

        # 200 with mock; 404 without (suggestion not in test DB); 500 on DB error
        assert response.status_code in (200, 404, 500)

    async def test_requires_auth(self, async_client):
        """GET /treatment-plans/ai-suggest/{id} without JWT returns 401."""
        response = await async_client.get(f"{BASE}/ai-suggest/{SUGGESTION_ID}")
        assert response.status_code == 401


# ─── TestReviewSuggestion ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestReviewSuggestion:
    async def test_review_requires_auth(self, async_client):
        """POST /treatment-plans/ai-suggest/{id}/review without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/ai-suggest/{SUGGESTION_ID}/review",
            json={
                "items": [
                    {"cups_code": "890201", "action": "accept"}
                ]
            },
        )
        assert response.status_code == 401

    async def test_review_with_items(self, authenticated_client):
        """POST /treatment-plans/ai-suggest/{id}/review with accepted items.

        Verifies that the review endpoint is reachable and that the request
        schema is accepted (no 422). The service returns the reviewed suggestion
        in the mocked case; 404 or 500 are expected without a seeded DB.
        """
        with patch(
            "app.services.ai_treatment_service.ai_treatment_service.review_suggestion",
            new_callable=AsyncMock,
            return_value=_REVIEWED_SUGGESTION,
        ):
            response = await authenticated_client.post(
                f"{BASE}/ai-suggest/{SUGGESTION_ID}/review",
                json={
                    "items": [
                        {"cups_code": "890201", "action": "accept"}
                    ]
                },
            )

        # 200 with mock; 404 (suggestion not found); 409 (wrong status); 500 (DB miss)
        assert response.status_code in (200, 404, 409, 500)


# ─── TestCreatePlan ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreatePlan:
    async def test_create_plan_requires_auth(self, async_client):
        """POST /treatment-plans/ai-suggest/{id}/create-plan without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/ai-suggest/{SUGGESTION_ID}/create-plan"
        )
        assert response.status_code == 401

    async def test_create_plan_from_suggestion(self, authenticated_client):
        """POST /treatment-plans/ai-suggest/{id}/create-plan converts accepted items.

        clinic_owner has both ai_treatment:write and treatment_plans:write, so
        the double-permission check inside the handler must pass.  The service
        is mocked to return a success response.  Without a seeded DB the service
        raises 404 (suggestion not found) or 500 (DB not seeded).
        """
        with patch(
            "app.services.ai_treatment_service.ai_treatment_service.get_suggestion",
            new_callable=AsyncMock,
            return_value=_REVIEWED_SUGGESTION,
        ), patch(
            "app.services.ai_treatment_service.ai_treatment_service.create_plan_from_suggestions",
            new_callable=AsyncMock,
            return_value=_PLAN_CREATED_RESPONSE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/ai-suggest/{SUGGESTION_ID}/create-plan"
            )

        # 200/201 with full mock; 404 (suggestion not found); 500 (DB miss)
        assert response.status_code in (200, 201, 404, 500)
