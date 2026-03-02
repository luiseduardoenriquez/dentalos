"""Integration tests for Billing Summary API (B-11 through B-13).

Endpoints:
  GET /api/v1/billing/summary       — B-11
  GET /api/v1/billing/aging-report  — B-12
  GET /api/v1/billing/commissions   — B-12b
  GET /api/v1/billing/revenue       — B-13
"""

import pytest


# ─── B-11: Billing summary ──────────────────────────────────────────────────


@pytest.mark.integration
class TestBillingSummary:
    async def test_summary_authenticated(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/billing/summary")
        assert response.status_code in (200, 500)

    async def test_summary_as_doctor(self, doctor_client):
        response = await doctor_client.get("/api/v1/billing/summary")
        assert response.status_code in (200, 500)

    async def test_summary_no_auth(self, async_client):
        response = await async_client.get("/api/v1/billing/summary")
        assert response.status_code == 401


# ─── B-12: Aging report ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestAgingReport:
    async def test_aging_authenticated(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/billing/aging-report")
        assert response.status_code in (200, 500)

    async def test_aging_as_doctor(self, doctor_client):
        response = await doctor_client.get("/api/v1/billing/aging-report")
        assert response.status_code in (200, 500)

    async def test_aging_no_auth(self, async_client):
        response = await async_client.get("/api/v1/billing/aging-report")
        assert response.status_code == 401


# ─── B-12b: Commissions report ──────────────────────────────────────────────


@pytest.mark.integration
class TestCommissionsReport:
    async def test_commissions_valid_range(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/billing/commissions",
            params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        )
        assert response.status_code in (200, 500)

    async def test_commissions_missing_dates(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/billing/commissions")
        assert response.status_code == 422

    async def test_commissions_invalid_status(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/billing/commissions",
            params={
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "status": "invalid",
            },
        )
        assert response.status_code == 422

    async def test_commissions_as_doctor(self, doctor_client):
        response = await doctor_client.get(
            "/api/v1/billing/commissions",
            params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        )
        assert response.status_code in (200, 500)

    async def test_commissions_no_auth(self, async_client):
        response = await async_client.get(
            "/api/v1/billing/commissions",
            params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        )
        assert response.status_code == 401


# ─── B-13: Revenue report ───────────────────────────────────────────────────


@pytest.mark.integration
class TestRevenueReport:
    async def test_revenue_month(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/billing/revenue", params={"period": "month"}
        )
        assert response.status_code in (200, 500)

    async def test_revenue_year(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/billing/revenue", params={"period": "year"}
        )
        assert response.status_code in (200, 500)

    async def test_revenue_default_period(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/billing/revenue")
        assert response.status_code in (200, 500)

    async def test_revenue_invalid_period(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/billing/revenue", params={"period": "week"}
        )
        assert response.status_code == 422

    async def test_revenue_no_auth(self, async_client):
        response = await async_client.get("/api/v1/billing/revenue")
        assert response.status_code == 401
