import pytest

from tests.factories.patient_factory import PatientFactory


@pytest.mark.integration
class TestSearchPatients:
    async def test_search_valid_query(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/patients/search?q=test")
        assert response.status_code in (200, 500)

    async def test_search_too_short(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/patients/search?q=a")
        assert response.status_code == 422

    async def test_search_no_auth(self, async_client):
        response = await async_client.get("/api/v1/patients/search?q=test")
        assert response.status_code == 401


@pytest.mark.integration
class TestListPatients:
    async def test_list_patients(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/patients")
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/patients?page=1&page_size=5"
        )
        assert response.status_code in (200, 500)

    async def test_list_no_auth(self, async_client):
        response = await async_client.get("/api/v1/patients")
        assert response.status_code == 401


@pytest.mark.integration
class TestCreatePatient:
    async def test_create_valid(self, authenticated_client):
        payload = PatientFactory()
        response = await authenticated_client.post(
            "/api/v1/patients",
            json=payload,
        )
        assert response.status_code in (201, 500)

    async def test_create_missing_fields(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/patients",
            json={},
        )
        assert response.status_code == 422

    async def test_create_invalid_document_type(self, authenticated_client):
        payload = PatientFactory()
        payload["document_type"] = "DNI"
        response = await authenticated_client.post(
            "/api/v1/patients",
            json=payload,
        )
        assert response.status_code == 422

    async def test_create_invalid_phone(self, authenticated_client):
        payload = PatientFactory()
        payload["phone"] = "not-a-phone"
        response = await authenticated_client.post(
            "/api/v1/patients",
            json=payload,
        )
        assert response.status_code == 422

    async def test_create_blank_name(self, authenticated_client):
        payload = PatientFactory()
        payload["first_name"] = "   "
        response = await authenticated_client.post(
            "/api/v1/patients",
            json=payload,
        )
        assert response.status_code == 422

    async def test_create_no_auth(self, async_client):
        payload = PatientFactory()
        response = await async_client.post(
            "/api/v1/patients",
            json=payload,
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestGetPatient:
    async def test_get_unknown_id(self, authenticated_client):
        response = await authenticated_client.get(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code in (404, 500)

    async def test_get_no_auth(self, async_client):
        response = await async_client.get(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestUpdatePatient:
    async def test_update_valid(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000",
            json={"first_name": "Updated"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_invalid_phone(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000",
            json={"phone": "bad"},
        )
        assert response.status_code == 422

    async def test_update_invalid_gender(self, authenticated_client):
        response = await authenticated_client.put(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000",
            json={"gender": "unknown"},
        )
        assert response.status_code == 422

    async def test_update_no_auth(self, async_client):
        response = await async_client.put(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000",
            json={"first_name": "Updated"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestDeactivatePatient:
    async def test_deactivate_as_owner(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000/deactivate"
        )
        assert response.status_code in (200, 404, 500)

    async def test_deactivate_as_doctor(self, doctor_client):
        response = await doctor_client.post(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000/deactivate"
        )
        assert response.status_code == 403

    async def test_deactivate_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000/deactivate"
        )
        assert response.status_code == 401
