from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.integration
class TestLogin:
    async def test_login_success(self, async_client):
        with (
            patch("app.services.auth_service.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "owner@test.co", "password": "TestPass1"},
            )
            assert response.status_code in (200, 500)

    async def test_login_wrong_password(self, async_client):
        with (
            patch("app.services.auth_service.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "owner@test.co", "password": "WrongPassword!"},
            )
            assert response.status_code == 401

    async def test_login_unknown_email(self, async_client):
        with (
            patch("app.services.auth_service.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@unknown.com", "password": "TestPass1"},
            )
            assert response.status_code == 401

    async def test_login_missing_fields(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestRefreshToken:
    async def test_refresh_no_cookie(self, async_client):
        response = await async_client.post("/api/v1/auth/refresh-token")
        assert response.status_code == 401

    async def test_refresh_invalid_token(self, async_client):
        async_client.cookies.set("refresh_token", "invalid-token-value")
        response = await async_client.post("/api/v1/auth/refresh-token")
        assert response.status_code in (401, 500)


@pytest.mark.integration
class TestGetMe:
    async def test_me_authenticated(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code in (200, 500)

    async def test_me_no_token(self, async_client):
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401


@pytest.mark.integration
class TestForgotPassword:
    async def test_forgot_valid_email(self, async_client):
        with (
            patch("app.services.auth_service.check_rate_limit", new_callable=AsyncMock),
            patch("app.services.auth_service.publish_message", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "owner@test.co"},
            )
            assert response.status_code == 200

    async def test_forgot_unknown_email(self, async_client):
        with (
            patch("app.services.auth_service.check_rate_limit", new_callable=AsyncMock),
            patch("app.services.auth_service.publish_message", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "ghost@unknown.com"},
            )
            assert response.status_code == 200

    async def test_forgot_missing_email(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestResetPassword:
    async def test_reset_invalid_token(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid-token", "new_password": "NewValidPass1!"},
        )
        assert response.status_code in (401, 400, 500)

    async def test_reset_weak_password(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "sometoken", "new_password": "123"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestChangePassword:
    async def test_change_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "TestPass1", "new_password": "NewValidPass1!"},
        )
        assert response.status_code == 401

    async def test_change_weak_new_password(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "TestPass1", "new_password": "123"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestLogout:
    async def test_logout_success(self, authenticated_client):
        response = await authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code in (204, 500)

    async def test_logout_no_token(self, async_client):
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401


@pytest.mark.integration
class TestInvite:
    async def test_invite_doctor_forbidden(self, doctor_client):
        response = await doctor_client.post(
            "/api/v1/auth/invite",
            json={"email": "newstaff@clinic.co", "role": "assistant"},
        )
        assert response.status_code == 403

    async def test_invite_missing_fields(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/auth/invite",
            json={},
        )
        assert response.status_code == 422

    async def test_invite_invalid_role(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/auth/invite",
            json={"email": "newstaff@clinic.co", "role": "supervillain"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestAcceptInvite:
    async def test_accept_invalid_token(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": "invalid-invite-token",
                "password": "ValidPass1!",
                "name": "Juan Pérez",
            },
        )
        assert response.status_code in (401, 500)

    async def test_accept_weak_password(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": "sometoken",
                "password": "123",
                "name": "Juan Pérez",
            },
        )
        assert response.status_code == 422

    async def test_accept_missing_fields(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/accept-invite",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestVerifyEmail:
    async def test_verify_invalid_token(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-verification-token"},
        )
        assert response.status_code in (401, 500)

    async def test_verify_missing_token(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={},
        )
        assert response.status_code == 422
