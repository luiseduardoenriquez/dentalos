"""Integration tests for Schedule Intelligence API (VP-10 / Sprint 25-26).

Endpoints:
  GET /api/v1/analytics/schedule-intelligence  — No-show risks, gaps, utilization
  GET /api/v1/analytics/suggested-fills        — Paginated fill suggestions

Both require schedule_intelligence:read permission.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

ANALYTICS_BASE = "/api/v1/analytics"
DOCTOR_ID = str(uuid.uuid4())

_INTELLIGENCE_RESPONSE = {
    "target_date": "2026-03-03",
    "no_show_risks": [
        {
            "appointment_id": str(uuid.uuid4()),
            "risk_score": 0.78,
            "risk_level": "high",
            "risk_factors": ["last_minute_booking", "previous_no_show"],
        }
    ],
    "gaps": [
        {
            "start_time": "10:30",
            "end_time": "11:00",
            "duration_minutes": 30,
            "doctor_id": DOCTOR_ID,
        }
    ],
    "utilization": {
        "scheduled_minutes": 300,
        "available_minutes": 480,
        "utilization_rate": 62.5,
        "doctor_utilization": [],
    },
}

_SUGGESTED_FILLS_RESPONSE = {
    "items": [
        {
            "patient_id": str(uuid.uuid4()),
            "suggestion_type": "recall",
            "gap_start_time": "10:30",
            "gap_duration_minutes": 30,
            "priority_score": 0.85,
            "reason": "6 months since last cleaning",
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
}


# ─── GET /analytics/schedule-intelligence ────────────────────────────────────


@pytest.mark.integration
class TestGetScheduleIntelligence:
    async def test_get_intelligence_requires_auth(self, async_client):
        """GET /analytics/schedule-intelligence without JWT returns 401."""
        response = await async_client.get(f"{ANALYTICS_BASE}/schedule-intelligence")
        assert response.status_code == 401

    async def test_get_intelligence_default_today(self, authenticated_client):
        """GET /analytics/schedule-intelligence defaults to today's date (200)."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.get_intelligence",
            new_callable=AsyncMock,
            return_value=_INTELLIGENCE_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/schedule-intelligence"
            )

        assert response.status_code == 200
        data = response.json()
        assert "no_show_risks" in data
        assert "gaps" in data
        assert "utilization" in data

    async def test_get_intelligence_with_date(self, authenticated_client):
        """GET /analytics/schedule-intelligence?date=2026-03-15 returns 200."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.get_intelligence",
            new_callable=AsyncMock,
            return_value={**_INTELLIGENCE_RESPONSE, "target_date": "2026-03-15"},
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/schedule-intelligence",
                params={"date": "2026-03-15"},
            )

        assert response.status_code == 200

    async def test_get_intelligence_with_doctor(self, authenticated_client):
        """GET /analytics/schedule-intelligence?doctor_id=uuid returns 200."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.get_intelligence",
            new_callable=AsyncMock,
            return_value=_INTELLIGENCE_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/schedule-intelligence",
                params={"doctor_id": DOCTOR_ID},
            )

        assert response.status_code == 200

    async def test_get_intelligence_invalid_date_format(self, authenticated_client):
        """GET /analytics/schedule-intelligence with invalid date format returns 422."""
        response = await authenticated_client.get(
            f"{ANALYTICS_BASE}/schedule-intelligence",
            params={"date": "15/03/2026"},
        )
        assert response.status_code == 422

    async def test_get_intelligence_invalid_doctor_uuid(self, authenticated_client):
        """GET /analytics/schedule-intelligence with malformed doctor_id returns 422."""
        response = await authenticated_client.get(
            f"{ANALYTICS_BASE}/schedule-intelligence",
            params={"doctor_id": "not-a-uuid"},
        )
        assert response.status_code == 422

    async def test_intelligence_response_shape(self, authenticated_client):
        """Response must contain no_show_risks, gaps, and utilization fields."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.get_intelligence",
            new_callable=AsyncMock,
            return_value=_INTELLIGENCE_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/schedule-intelligence"
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["no_show_risks"], list)
        assert isinstance(data["gaps"], list)
        assert isinstance(data["utilization"], dict)
        assert "utilization_rate" in data["utilization"]

    async def test_intelligence_with_date_and_doctor(self, authenticated_client):
        """GET with both date and doctor_id filters passes both to the service."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.get_intelligence",
            new_callable=AsyncMock,
            return_value=_INTELLIGENCE_RESPONSE,
        ) as mock_svc:
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/schedule-intelligence",
                params={"date": "2026-03-10", "doctor_id": DOCTOR_ID},
            )

        assert response.status_code == 200
        # Verify the service was called with the correct doctor_id
        call_kwargs = mock_svc.call_args.kwargs
        assert str(call_kwargs["doctor_id"]) == DOCTOR_ID


# ─── GET /analytics/suggested-fills ─────────────────────────────────────────


@pytest.mark.integration
class TestGetSuggestedFills:
    async def test_suggested_fills_requires_auth(self, async_client):
        """GET /analytics/suggested-fills without JWT returns 401."""
        response = await async_client.get(f"{ANALYTICS_BASE}/suggested-fills")
        assert response.status_code == 401

    async def test_suggested_fills_paginated(self, authenticated_client):
        """GET /analytics/suggested-fills returns paginated items with total."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.suggest_fills",
            new_callable=AsyncMock,
            return_value=_SUGGESTED_FILLS_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/suggested-fills"
            )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_suggested_fills_with_pagination(self, authenticated_client):
        """GET /analytics/suggested-fills respects page and page_size params."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.suggest_fills",
            new_callable=AsyncMock,
            return_value={**_SUGGESTED_FILLS_RESPONSE, "page": 2, "page_size": 5},
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/suggested-fills",
                params={"page": 2, "page_size": 5},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5

    async def test_suggested_fills_invalid_page_size(self, authenticated_client):
        """GET /analytics/suggested-fills with page_size=0 fails validation."""
        response = await authenticated_client.get(
            f"{ANALYTICS_BASE}/suggested-fills",
            params={"page_size": 0},
        )
        assert response.status_code == 422

    async def test_suggested_fills_page_size_too_large(self, authenticated_client):
        """GET /analytics/suggested-fills with page_size > 100 fails validation."""
        response = await authenticated_client.get(
            f"{ANALYTICS_BASE}/suggested-fills",
            params={"page_size": 200},
        )
        assert response.status_code == 422

    async def test_suggested_fills_with_date_filter(self, authenticated_client):
        """GET /analytics/suggested-fills with date query param returns 200."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.suggest_fills",
            new_callable=AsyncMock,
            return_value=_SUGGESTED_FILLS_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/suggested-fills",
                params={"date": "2026-03-15"},
            )

        assert response.status_code == 200

    async def test_suggested_fills_doctor_filter(self, authenticated_client):
        """GET /analytics/suggested-fills?doctor_id=uuid returns 200."""
        with patch(
            "app.services.schedule_intelligence_service.schedule_intelligence_service.suggest_fills",
            new_callable=AsyncMock,
            return_value=_SUGGESTED_FILLS_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{ANALYTICS_BASE}/suggested-fills",
                params={"doctor_id": DOCTOR_ID},
            )

        assert response.status_code == 200
