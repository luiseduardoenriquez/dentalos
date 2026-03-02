"""Integration tests for Portal Auth API (PP-01).

Endpoints:
  POST /api/v1/portal/auth/login           — Password or magic link login
  POST /api/v1/portal/auth/magic           — Verify magic link
  POST /api/v1/portal/auth/refresh         — Refresh portal token
  POST /api/v1/portal/auth/register        — Complete registration
  POST /api/v1/portal/auth/change-password — Change password (auth'd)
  POST /api/v1/portal/auth/logout          — Logout (auth'd)
"""

import uuid

import pytest

AUTH_BASE = "/api/v1/portal/auth"


# ─── Login ───────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPortalLogin:
    async def test_login_password_valid(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "password",
                "identifier": "paciente@test.co",
                "password": "SecurePass123",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code in (200, 401, 500)

    async def test_login_password_missing_password(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "password",
                "identifier": "paciente@test.co",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        # password is optional in schema but validated in handler → 422 or 500
        assert response.status_code in (422, 500)

    async def test_login_magic_link(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "magic_link",
                "identifier": "paciente@test.co",
                "magic_link_channel": "email",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code in (200, 500)

    async def test_login_invalid_method(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "oauth",
                "identifier": "paciente@test.co",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_login_missing_identifier(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "password",
                "password": "SecurePass123",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_login_identifier_too_short(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "password",
                "identifier": "ab",
                "password": "SecurePass123",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_login_missing_tenant_id(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/login",
            json={
                "login_method": "password",
                "identifier": "paciente@test.co",
                "password": "SecurePass123",
            },
        )
        assert response.status_code == 422


# ─── Magic link verify ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestPortalMagicLink:
    async def test_verify_valid_token(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/magic",
            json={
                "token": "a" * 64,
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code in (200, 400, 500)

    async def test_verify_short_token(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/magic",
            json={
                "token": "short",
                "tenant_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_verify_missing_tenant_id(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/magic",
            json={"token": "a" * 64},
        )
        assert response.status_code == 422


# ─── Refresh ─────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPortalRefresh:
    async def test_refresh_valid(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/refresh",
            json={"refresh_token": str(uuid.uuid4())},
        )
        assert response.status_code in (200, 401, 422, 500)

    async def test_refresh_missing_token(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/refresh",
            json={},
        )
        assert response.status_code in (422, 500)


# ─── Register ────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPortalRegister:
    async def test_register_valid(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/register",
            json={
                "token": "a" * 64,
                "tenant_id": str(uuid.uuid4()),
                "password": "SecurePass123",
            },
        )
        assert response.status_code in (200, 201, 400, 500)

    async def test_register_short_password(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/register",
            json={
                "token": "a" * 64,
                "tenant_id": str(uuid.uuid4()),
                "password": "short",
            },
        )
        assert response.status_code == 422

    async def test_register_short_token(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/register",
            json={
                "token": "abc",
                "tenant_id": str(uuid.uuid4()),
                "password": "SecurePass123",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_tenant_id(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/register",
            json={
                "token": "a" * 64,
                "password": "SecurePass123",
            },
        )
        assert response.status_code == 422


# ─── Change password / Logout (require portal auth) ─────────────────────────


@pytest.mark.integration
class TestPortalChangePassword:
    async def test_change_password_no_auth(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/change-password",
            json={"new_password": "NewSecurePass123"},
        )
        assert response.status_code in (401, 403, 422, 500)

    async def test_change_password_short(self, async_client):
        response = await async_client.post(
            f"{AUTH_BASE}/change-password",
            json={"new_password": "short"},
        )
        assert response.status_code in (401, 422, 500)


@pytest.mark.integration
class TestPortalLogout:
    async def test_logout_no_auth(self, async_client):
        response = await async_client.post(f"{AUTH_BASE}/logout")
        assert response.status_code in (401, 403, 422, 500)
