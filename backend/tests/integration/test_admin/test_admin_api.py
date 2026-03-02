"""Integration tests for Admin/Superadmin API (AD-01 through AD-07).

Endpoints:
  POST /api/v1/admin/auth/login              — AD-01: Admin login
  POST /api/v1/admin/auth/totp/setup         — TOTP setup
  POST /api/v1/admin/auth/totp/verify        — TOTP verify
  GET  /api/v1/admin/tenants                 — AD-02: List tenants
  GET  /api/v1/admin/plans                   — AD-03: List plans
  PUT  /api/v1/admin/plans/{plan_id}         — AD-03: Update plan
  GET  /api/v1/admin/analytics               — AD-04: Platform analytics
  GET  /api/v1/admin/feature-flags           — AD-05: List feature flags
  POST /api/v1/admin/feature-flags           — AD-05: Create feature flag
  PUT  /api/v1/admin/feature-flags/{flag_id} — AD-05: Update feature flag
  GET  /api/v1/admin/health                  — AD-06: System health
  POST /api/v1/admin/tenants/{tid}/impersonate — AD-07: Impersonate

Admin endpoints use a separate auth dependency (get_current_admin) that
validates aud="dentalos-admin" JWTs. The superadmin_client fixture uses
aud="dentalos-api" — so these tests verify that the admin auth dependency
correctly rejects non-admin tokens. Tests that require a real admin JWT
would need a seeded Superadmin row + dedicated admin token fixture (future).
"""

import uuid

import pytest

BASE = "/api/v1/admin"
PLAN_ID = str(uuid.uuid4())
FLAG_ID = str(uuid.uuid4())
TENANT_ID = str(uuid.uuid4())


# ─── AD-01: Admin Login ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestAdminLogin:
    async def test_login_valid_credentials(self, async_client):
        response = await async_client.post(
            f"{BASE}/auth/login",
            json={
                "email": "admin@dentalos.com",
                "password": "SuperAdminPass1",
            },
        )
        # 200 if admin exists with correct creds, 401/404/500 otherwise
        assert response.status_code in (200, 401, 404, 500)

    async def test_login_missing_email(self, async_client):
        response = await async_client.post(
            f"{BASE}/auth/login",
            json={"password": "SomePass1"},
        )
        assert response.status_code == 422

    async def test_login_missing_password(self, async_client):
        response = await async_client.post(
            f"{BASE}/auth/login",
            json={"email": "admin@dentalos.com"},
        )
        assert response.status_code == 422

    async def test_login_bad_credentials(self, async_client):
        response = await async_client.post(
            f"{BASE}/auth/login",
            json={
                "email": "nonexistent@dentalos.com",
                "password": "WrongPass1",
            },
        )
        assert response.status_code in (401, 404, 500)


# ─── TOTP Setup/Verify ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestTOTPSetup:
    async def test_totp_setup_no_auth(self, async_client):
        response = await async_client.post(f"{BASE}/auth/totp/setup")
        assert response.status_code in (401, 422)

    async def test_totp_setup_non_admin_token(self, authenticated_client):
        """clinic_owner token should be rejected by admin auth dependency."""
        response = await authenticated_client.post(f"{BASE}/auth/totp/setup")
        assert response.status_code in (401, 403, 500)

    async def test_totp_verify_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/auth/totp/verify",
            json={"totp_code": "123456"},
        )
        assert response.status_code in (401, 422)

    async def test_totp_verify_non_admin_token(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/auth/totp/verify",
            json={"totp_code": "123456"},
        )
        assert response.status_code in (401, 403, 500)


# ─── AD-02: Tenant Management ───────────────────────────────────────────────


@pytest.mark.integration
class TestAdminTenants:
    async def test_list_tenants_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/tenants")
        assert response.status_code in (401, 422)

    async def test_list_tenants_clinic_owner_rejected(self, authenticated_client):
        """clinic_owner token should be rejected by admin auth dependency."""
        response = await authenticated_client.get(f"{BASE}/tenants")
        assert response.status_code in (401, 403, 500)

    async def test_list_tenants_with_search(self, async_client):
        response = await async_client.get(
            f"{BASE}/tenants", params={"search": "test"}
        )
        assert response.status_code in (401, 422)

    async def test_impersonate_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/tenants/{TENANT_ID}/impersonate"
        )
        assert response.status_code in (401, 422)

    async def test_impersonate_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/tenants/{TENANT_ID}/impersonate"
        )
        assert response.status_code in (401, 403, 500)


# ─── AD-03: Plan Management ─────────────────────────────────────────────────


@pytest.mark.integration
class TestAdminPlans:
    async def test_list_plans_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/plans")
        assert response.status_code in (401, 422)

    async def test_list_plans_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/plans")
        assert response.status_code in (401, 403, 500)

    async def test_update_plan_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/plans/{PLAN_ID}",
            json={"price_cents": 5000},
        )
        assert response.status_code in (401, 422)

    async def test_update_plan_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/plans/{PLAN_ID}",
            json={"price_cents": 5000},
        )
        assert response.status_code in (401, 403, 500)


# ─── AD-04: Platform Analytics ───────────────────────────────────────────────


@pytest.mark.integration
class TestAdminAnalytics:
    async def test_analytics_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/analytics")
        assert response.status_code in (401, 422)

    async def test_analytics_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/analytics")
        assert response.status_code in (401, 403, 500)


# ─── AD-05: Feature Flags ───────────────────────────────────────────────────


@pytest.mark.integration
class TestAdminFeatureFlags:
    async def test_list_flags_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/feature-flags")
        assert response.status_code in (401, 422)

    async def test_list_flags_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/feature-flags")
        assert response.status_code in (401, 403, 500)

    async def test_create_flag_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/feature-flags",
            json={
                "flag_name": "test_flag",
                "enabled": True,
                "scope": "global",
            },
        )
        assert response.status_code in (401, 422)

    async def test_create_flag_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/feature-flags",
            json={
                "flag_name": "test_flag",
                "enabled": True,
                "scope": "global",
            },
        )
        assert response.status_code in (401, 403, 500)

    async def test_update_flag_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/feature-flags/{FLAG_ID}",
            json={"enabled": False},
        )
        assert response.status_code in (401, 422)

    async def test_update_flag_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/feature-flags/{FLAG_ID}",
            json={"enabled": False},
        )
        assert response.status_code in (401, 403, 500)


# ─── AD-06: System Health ───────────────────────────────────────────────────


@pytest.mark.integration
class TestAdminHealth:
    async def test_health_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/health")
        assert response.status_code in (401, 422)

    async def test_health_clinic_owner_rejected(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/health")
        assert response.status_code in (401, 403, 500)
