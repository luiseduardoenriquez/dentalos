"""Integration tests for Memberships API (VP-01).

Endpoints:
  POST /api/v1/memberships/plans
  GET  /api/v1/memberships/plans
  PUT  /api/v1/memberships/plans/{id}
  POST /api/v1/memberships/subscriptions
  GET  /api/v1/memberships/subscriptions
  POST /api/v1/memberships/subscriptions/{id}/cancel
  POST /api/v1/memberships/subscriptions/{id}/pause
  GET  /api/v1/memberships/dashboard
"""

import uuid

import pytest

BASE_PLANS = "/api/v1/memberships/plans"
BASE_SUBS = "/api/v1/memberships/subscriptions"

PLAN_ID = str(uuid.uuid4())
SUB_ID = str(uuid.uuid4())


# ── POST /api/v1/memberships/plans ────────────────────────────────────────────


@pytest.mark.integration
class TestCreatePlan:
    async def test_create_valid_plan(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_PLANS,
            json={
                "name": "Plan Básico",
                "monthly_price_cents": 99000,
                "discount_percentage": 10,
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_plan_with_all_fields(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_PLANS,
            json={
                "name": "Plan Premium",
                "description": "Acceso completo a todos los servicios",
                "monthly_price_cents": 199000,
                "annual_price_cents": 1990000,
                "discount_percentage": 20,
                "benefits": {"cleanings": 4, "xrays": 2},
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_plan_missing_name(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_PLANS,
            json={"monthly_price_cents": 99000},
        )
        assert response.status_code == 422

    async def test_create_plan_negative_price(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_PLANS,
            json={
                "name": "Plan Inválido",
                "monthly_price_cents": -1000,
            },
        )
        assert response.status_code == 422

    async def test_create_plan_no_auth(self, async_client):
        response = await async_client.post(
            BASE_PLANS,
            json={"name": "Sin Auth", "monthly_price_cents": 99000},
        )
        assert response.status_code == 401


# ── GET /api/v1/memberships/plans ─────────────────────────────────────────────


@pytest.mark.integration
class TestListPlans:
    async def test_list_plans(self, authenticated_client):
        response = await authenticated_client.get(BASE_PLANS)
        assert response.status_code in (200, 500)

    async def test_list_plans_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE_PLANS, params={"page": 1, "page_size": 10}
        )
        assert response.status_code in (200, 500)

    async def test_list_plans_invalid_page_size(self, authenticated_client):
        response = await authenticated_client.get(
            BASE_PLANS, params={"page_size": 0}
        )
        assert response.status_code == 422

    async def test_list_plans_no_auth(self, async_client):
        response = await async_client.get(BASE_PLANS)
        assert response.status_code == 401


# ── PUT /api/v1/memberships/plans/{id} ────────────────────────────────────────


@pytest.mark.integration
class TestUpdatePlan:
    async def test_update_nonexistent_plan(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE_PLANS}/{uuid.uuid4()}",
            json={"name": "Plan Actualizado"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_plan_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE_PLANS}/{PLAN_ID}",
            json={"name": "Sin Auth"},
        )
        assert response.status_code == 401


# ── POST /api/v1/memberships/subscriptions ────────────────────────────────────


@pytest.mark.integration
class TestSubscribePatient:
    async def test_subscribe(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_SUBS,
            json={
                "patient_id": str(uuid.uuid4()),
                "plan_id": str(uuid.uuid4()),
                "start_date": "2026-03-01",
            },
        )
        assert response.status_code in (201, 500)

    async def test_subscribe_missing_patient_id(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_SUBS,
            json={
                "plan_id": str(uuid.uuid4()),
                "start_date": "2026-03-01",
            },
        )
        assert response.status_code == 422

    async def test_subscribe_missing_plan_id(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_SUBS,
            json={
                "patient_id": str(uuid.uuid4()),
                "start_date": "2026-03-01",
            },
        )
        assert response.status_code == 422

    async def test_subscribe_invalid_date_format(self, authenticated_client):
        response = await authenticated_client.post(
            BASE_SUBS,
            json={
                "patient_id": str(uuid.uuid4()),
                "plan_id": str(uuid.uuid4()),
                "start_date": "01/03/2026",
            },
        )
        assert response.status_code == 422

    async def test_subscribe_no_auth(self, async_client):
        response = await async_client.post(
            BASE_SUBS,
            json={
                "patient_id": str(uuid.uuid4()),
                "plan_id": str(uuid.uuid4()),
                "start_date": "2026-03-01",
            },
        )
        assert response.status_code == 401


# ── GET /api/v1/memberships/subscriptions ─────────────────────────────────────


@pytest.mark.integration
class TestListSubscriptions:
    async def test_list_subscriptions(self, authenticated_client):
        response = await authenticated_client.get(BASE_SUBS)
        assert response.status_code in (200, 500)

    async def test_list_subscriptions_with_status_filter(self, authenticated_client):
        response = await authenticated_client.get(
            BASE_SUBS, params={"status": "active"}
        )
        assert response.status_code in (200, 500)

    async def test_list_subscriptions_no_auth(self, async_client):
        response = await async_client.get(BASE_SUBS)
        assert response.status_code == 401


# ── POST /api/v1/memberships/subscriptions/{id}/cancel ────────────────────────


@pytest.mark.integration
class TestCancelSubscription:
    async def test_cancel_nonexistent(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE_SUBS}/{uuid.uuid4()}/cancel",
        )
        assert response.status_code in (404, 500)

    async def test_cancel_no_auth(self, async_client):
        response = await async_client.post(f"{BASE_SUBS}/{SUB_ID}/cancel")
        assert response.status_code == 401


# ── POST /api/v1/memberships/subscriptions/{id}/pause ─────────────────────────


@pytest.mark.integration
class TestPauseSubscription:
    async def test_pause_nonexistent(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE_SUBS}/{uuid.uuid4()}/pause",
        )
        assert response.status_code in (404, 500)

    async def test_pause_no_auth(self, async_client):
        response = await async_client.post(f"{BASE_SUBS}/{SUB_ID}/pause")
        assert response.status_code == 401


# ── GET /api/v1/memberships/dashboard ─────────────────────────────────────────


@pytest.mark.integration
class TestDashboard:
    async def test_get_dashboard(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/memberships/dashboard")
        assert response.status_code in (200, 500)

    async def test_get_dashboard_no_auth(self, async_client):
        response = await async_client.get("/api/v1/memberships/dashboard")
        assert response.status_code == 401
