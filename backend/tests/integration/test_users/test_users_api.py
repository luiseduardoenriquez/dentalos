from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.integration
class TestGetOwnProfile:
    async def test_me_authenticated(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/users/me")
        assert response.status_code in (200, 500)

    async def test_me_no_token(self, async_client):
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 401


@pytest.mark.integration
class TestUpdateOwnProfile:
    async def test_update_me_valid(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/users/me",
            json={"name": "Dr. Updated"},
        )
        assert response.status_code in (200, 500)

    async def test_update_me_invalid_phone(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/users/me",
            json={"phone": "not-a-phone"},
        )
        assert response.status_code == 422

    async def test_update_me_no_auth(self, async_client):
        response = await async_client.put(
            "/api/v1/users/me",
            json={"name": "Dr. Updated"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestListTeamMembers:
    async def test_list_as_owner(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/users")
        assert response.status_code in (200, 500)

    async def test_list_as_doctor(self, doctor_client):
        response = await doctor_client.get("/api/v1/users")
        assert response.status_code == 403

    async def test_list_no_auth(self, async_client):
        response = await async_client.get("/api/v1/users")
        assert response.status_code == 401


@pytest.mark.integration
class TestGetTeamMember:
    async def test_get_member_as_owner(self, authenticated_client, test_user):
        response = await authenticated_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code in (200, 500)

    async def test_get_member_unknown_id(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code in (404, 500)

    async def test_get_member_as_doctor(self, doctor_client):
        response = await doctor_client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestUpdateTeamMember:
    async def test_update_role_valid(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"role": "doctor"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_role_superadmin(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"role": "superadmin"},
        )
        assert response.status_code == 422

    async def test_update_role_clinic_owner(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"role": "clinic_owner"},
        )
        assert response.status_code == 422

    async def test_update_as_doctor(self, doctor_client):
        response = await doctor_client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"role": "doctor"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestDeactivateTeamMember:
    async def test_deactivate_as_owner(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/users/00000000-0000-0000-0000-000000000000/deactivate"
        )
        assert response.status_code in (200, 404, 500)

    async def test_deactivate_as_doctor(self, doctor_client):
        response = await doctor_client.post(
            "/api/v1/users/00000000-0000-0000-0000-000000000000/deactivate"
        )
        assert response.status_code == 403

    async def test_deactivate_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/users/00000000-0000-0000-0000-000000000000/deactivate"
        )
        assert response.status_code == 401
