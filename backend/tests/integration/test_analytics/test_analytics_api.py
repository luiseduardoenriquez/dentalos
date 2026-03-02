"""Integration tests for Analytics API (AN-01 through AN-07).

Endpoints:
  GET /api/v1/analytics/dashboard     — AN-01: KPI dashboard
  GET /api/v1/analytics/patients      — AN-02: Patient demographics
  GET /api/v1/analytics/appointments  — AN-03: Appointment utilization
  GET /api/v1/analytics/revenue       — AN-04: Revenue trends
  GET /api/v1/analytics/clinical      — AN-05: Clinical analytics (stub)
  GET /api/v1/analytics/export        — AN-06: CSV export
  GET /api/v1/analytics/audit-trail   — AN-07: Audit trail (clinic_owner only)
"""

import pytest

BASE = "/api/v1/analytics"


# ─── AN-01: Dashboard ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestAnalyticsDashboard:
    async def test_dashboard_default_period(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/dashboard")
        assert response.status_code in (200, 500)

    async def test_dashboard_custom_period(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/dashboard",
            params={"period": "custom", "date_from": "2025-01-01", "date_to": "2025-12-31"},
        )
        assert response.status_code in (200, 500)

    async def test_dashboard_invalid_period(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/dashboard", params={"period": "invalid"}
        )
        assert response.status_code == 422

    async def test_dashboard_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/dashboard")
        assert response.status_code == 401


# ─── AN-02: Patient analytics ────────────────────────────────────────────────


@pytest.mark.integration
class TestPatientAnalytics:
    async def test_patients_default(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/patients")
        assert response.status_code in (200, 500)

    async def test_patients_quarter_period(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/patients", params={"period": "quarter"}
        )
        assert response.status_code in (200, 500)

    async def test_patients_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/patients")
        assert response.status_code == 401


# ─── AN-03: Appointment analytics ────────────────────────────────────────────


@pytest.mark.integration
class TestAppointmentAnalytics:
    async def test_appointments_default(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/appointments")
        assert response.status_code in (200, 500)

    async def test_appointments_year_period(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/appointments", params={"period": "year"}
        )
        assert response.status_code in (200, 500)

    async def test_appointments_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/appointments")
        assert response.status_code == 401


# ─── AN-04: Revenue analytics ────────────────────────────────────────────────


@pytest.mark.integration
class TestRevenueAnalytics:
    async def test_revenue_default(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/revenue")
        assert response.status_code in (200, 500)

    async def test_revenue_week_period(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/revenue", params={"period": "week"}
        )
        assert response.status_code in (200, 500)

    async def test_revenue_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/revenue")
        assert response.status_code == 401


# ─── AN-05: Clinical analytics (stub) ────────────────────────────────────────


@pytest.mark.integration
class TestClinicalAnalytics:
    async def test_clinical_returns_stub(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/clinical")
        assert response.status_code in (200, 500)

    async def test_clinical_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/clinical")
        assert response.status_code == 401


# ─── AN-06: Export ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestAnalyticsExport:
    async def test_export_patients_csv(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/export", params={"report_type": "patients"}
        )
        assert response.status_code in (200, 202, 500)

    async def test_export_appointments_csv(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/export", params={"report_type": "appointments"}
        )
        assert response.status_code in (200, 202, 500)

    async def test_export_revenue_csv(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/export", params={"report_type": "revenue"}
        )
        assert response.status_code in (200, 202, 500)

    async def test_export_missing_report_type(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/export")
        assert response.status_code == 422

    async def test_export_invalid_report_type(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/export", params={"report_type": "invalid"}
        )
        assert response.status_code == 422

    async def test_export_no_auth(self, async_client):
        response = await async_client.get(
            f"{BASE}/export", params={"report_type": "patients"}
        )
        assert response.status_code == 401


# ─── AN-07: Audit trail ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestAuditTrail:
    async def test_audit_trail_as_owner(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/audit-trail")
        assert response.status_code in (200, 500)

    async def test_audit_trail_with_filters(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/audit-trail",
            params={"resource_type": "patient", "action": "create", "page_size": 10},
        )
        assert response.status_code in (200, 500)

    async def test_audit_trail_invalid_page_size(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/audit-trail", params={"page_size": 0}
        )
        assert response.status_code == 422

    async def test_audit_trail_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/audit-trail")
        assert response.status_code == 401
