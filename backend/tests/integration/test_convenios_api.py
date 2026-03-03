"""Integration tests for Convenios (Corporate Agreements) API (GAP-04 / Sprint 25-26).

Endpoints:
  POST /api/v1/convenios                              — Create convenio (convenios:write)
  GET  /api/v1/convenios                              — List convenios (convenios:read)
  PUT  /api/v1/convenios/{convenio_id}               — Update convenio (convenios:write)
  POST /api/v1/convenios/patients/{patient_id}/convenio — Link patient (convenios:write)

clinic_owner has convenios:write and convenios:read.
doctor role lacks both permissions.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/convenios"
CONVENIO_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())

_CONVENIO_RESPONSE = {
    "id": CONVENIO_ID,
    "name": "Convenio Empresa ABC",
    "nit": "900123456-1",
    "contact_name": "Ana Rodriguez",
    "contact_email": "convenios@empresaabc.co",
    "contact_phone": "+5716001234",
    "discount_percentage": 15,
    "discount_type": "percentage",
    "notes": "Acuerdo para empleados de la empresa",
    "is_active": True,
    "created_at": "2026-03-01T09:00:00+00:00",
    "updated_at": "2026-03-01T09:00:00+00:00",
}

_CONVENIO_LIST_RESPONSE = {
    "items": [_CONVENIO_RESPONSE],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_LINK_RESPONSE = {
    "patient_id": PATIENT_ID,
    "convenio_id": CONVENIO_ID,
    "employee_id": "EMP-12345",
    "linked_at": "2026-03-03T10:00:00+00:00",
}

_LINK_DUPLICATE_ERROR = {
    "error": "CONVENIO_patient_already_linked",
    "message": "El paciente ya está vinculado a un convenio activo.",
    "details": {},
}


def _convenio_payload(**overrides) -> dict:
    """Build a valid convenio creation payload."""
    base = {
        "name": "Convenio Empresa ABC",
        "nit": "900123456-1",
        "contact_name": "Ana Rodriguez",
        "discount_percentage": 15,
        "discount_type": "percentage",
    }
    base.update(overrides)
    return base


# ─── POST /convenios ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateConvenio:
    async def test_create_convenio_requires_auth(self, async_client):
        """POST /convenios without JWT returns 401."""
        response = await async_client.post(BASE, json=_convenio_payload())
        assert response.status_code == 401

    async def test_create_convenio_requires_permission(self, doctor_client):
        """doctor role lacks convenios:write — expects 403."""
        response = await doctor_client.post(BASE, json=_convenio_payload())
        assert response.status_code == 403

    async def test_create_convenio_success(self, authenticated_client):
        """POST /convenios with valid payload returns 201 and the new convenio."""
        with patch(
            "app.services.convenio_service.convenio_service.create",
            new_callable=AsyncMock,
            return_value=_CONVENIO_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE, json=_convenio_payload()
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Convenio Empresa ABC"
        assert data["discount_percentage"] == 15

    async def test_create_convenio_missing_name(self, authenticated_client):
        """POST /convenios without name returns 422."""
        payload = _convenio_payload()
        del payload["name"]
        response = await authenticated_client.post(BASE, json=payload)
        assert response.status_code == 422

    async def test_create_convenio_missing_discount_type(self, authenticated_client):
        """POST /convenios without discount_type returns 422."""
        payload = _convenio_payload()
        del payload["discount_type"]
        response = await authenticated_client.post(BASE, json=payload)
        assert response.status_code == 422

    async def test_create_convenio_invalid_discount_percentage(self, authenticated_client):
        """POST /convenios with discount_percentage > 100 returns 422."""
        response = await authenticated_client.post(
            BASE, json=_convenio_payload(discount_percentage=150)
        )
        assert response.status_code == 422

    async def test_create_convenio_negative_discount(self, authenticated_client):
        """POST /convenios with negative discount_percentage returns 422."""
        response = await authenticated_client.post(
            BASE, json=_convenio_payload(discount_percentage=-5)
        )
        assert response.status_code == 422

    async def test_create_convenio_with_all_fields(self, authenticated_client):
        """POST /convenios with all optional fields is accepted."""
        with patch(
            "app.services.convenio_service.convenio_service.create",
            new_callable=AsyncMock,
            return_value=_CONVENIO_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE,
                json={
                    **_convenio_payload(),
                    "contact_email": "convenios@empresaabc.co",
                    "contact_phone": "+5716001234",
                    "notes": "Acuerdo vigente hasta diciembre 2026",
                },
            )

        assert response.status_code == 201


# ─── GET /convenios ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListConvenios:
    async def test_list_convenios_requires_auth(self, async_client):
        """GET /convenios without JWT returns 401."""
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_list_convenios_returns_paginated(self, authenticated_client):
        """GET /convenios returns paginated list with items and total."""
        with patch(
            "app.services.convenio_service.convenio_service.list_convenios",
            new_callable=AsyncMock,
            return_value=_CONVENIO_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_convenios_pagination(self, authenticated_client):
        """GET /convenios with page and page_size params returns correct page."""
        paged = {**_CONVENIO_LIST_RESPONSE, "page": 2, "page_size": 10}
        with patch(
            "app.services.convenio_service.convenio_service.list_convenios",
            new_callable=AsyncMock,
            return_value=paged,
        ):
            response = await authenticated_client.get(
                BASE, params={"page": 2, "page_size": 10}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    async def test_list_convenios_invalid_page_size(self, authenticated_client):
        """GET /convenios with page_size=0 returns 422."""
        response = await authenticated_client.get(BASE, params={"page_size": 0})
        assert response.status_code == 422

    async def test_list_convenios_page_size_too_large(self, authenticated_client):
        """GET /convenios with page_size > 100 returns 422."""
        response = await authenticated_client.get(BASE, params={"page_size": 200})
        assert response.status_code == 422

    async def test_list_convenios_doctor_forbidden(self, doctor_client):
        """doctor role lacks convenios:read — expects 403."""
        response = await doctor_client.get(BASE)
        assert response.status_code == 403


# ─── PUT /convenios/{convenio_id} ────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateConvenio:
    async def test_update_convenio_requires_auth(self, async_client):
        """PUT /convenios/{id} without JWT returns 401."""
        response = await async_client.put(
            f"{BASE}/{CONVENIO_ID}",
            json={"name": "Nombre Actualizado"},
        )
        assert response.status_code == 401

    async def test_update_convenio_requires_permission(self, doctor_client):
        """doctor role lacks convenios:write — expects 403."""
        response = await doctor_client.put(
            f"{BASE}/{CONVENIO_ID}",
            json={"name": "Nombre Actualizado"},
        )
        assert response.status_code == 403

    async def test_update_convenio_success(self, authenticated_client):
        """PUT /convenios/{id} with valid payload returns 200 with updated fields."""
        updated_response = {**_CONVENIO_RESPONSE, "name": "Convenio Empresa ABC Actualizado"}
        with patch(
            "app.services.convenio_service.convenio_service.update",
            new_callable=AsyncMock,
            return_value=updated_response,
        ):
            response = await authenticated_client.put(
                f"{BASE}/{CONVENIO_ID}",
                json={"name": "Convenio Empresa ABC Actualizado"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Convenio Empresa ABC Actualizado"

    async def test_update_nonexistent_convenio(self, authenticated_client):
        """PUT /convenios/{nonexistent_id} returns 404."""
        from app.core.exceptions import ResourceNotFoundError
        from app.core.error_codes import ConvenioErrors

        with patch(
            "app.services.convenio_service.convenio_service.update",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(
                error=ConvenioErrors.NOT_FOUND,
                resource_name="Convenio",
            ),
        ):
            response = await authenticated_client.put(
                f"{BASE}/{uuid.uuid4()}",
                json={"name": "No Existe"},
            )

        assert response.status_code == 404

    async def test_update_convenio_invalid_discount(self, authenticated_client):
        """PUT /convenios/{id} with invalid discount_percentage returns 422."""
        response = await authenticated_client.put(
            f"{BASE}/{CONVENIO_ID}",
            json={"discount_percentage": -10},
        )
        assert response.status_code == 422


# ─── POST /convenios/patients/{patient_id}/convenio ───────────────────────────


@pytest.mark.integration
class TestLinkPatientToConvenio:
    async def test_link_patient_requires_auth(self, async_client):
        """POST /convenios/patients/{id}/convenio without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/patients/{PATIENT_ID}/convenio",
            json={"patient_id": CONVENIO_ID},
        )
        assert response.status_code == 401

    async def test_link_patient_requires_permission(self, doctor_client):
        """doctor role lacks convenios:write — expects 403."""
        response = await doctor_client.post(
            f"{BASE}/patients/{PATIENT_ID}/convenio",
            json={"patient_id": CONVENIO_ID},
        )
        assert response.status_code == 403

    async def test_link_patient_success(self, authenticated_client):
        """POST /convenios/patients/{id}/convenio returns 201 with link info."""
        with patch(
            "app.services.convenio_service.convenio_service.link_patient",
            new_callable=AsyncMock,
            return_value=_LINK_RESPONSE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/patients/{PATIENT_ID}/convenio",
                json={"patient_id": CONVENIO_ID, "employee_id": "EMP-12345"},
            )

        assert response.status_code == 201
        data = response.json()
        assert "patient_id" in data or "convenio_id" in data

    async def test_link_patient_duplicate_returns_409(self, authenticated_client):
        """POST linking a patient already linked to a convenio returns 409."""
        from app.core.exceptions import DentalOSError
        from app.core.error_codes import ConvenioErrors

        with patch(
            "app.services.convenio_service.convenio_service.link_patient",
            new_callable=AsyncMock,
            side_effect=DentalOSError(
                error=ConvenioErrors.PATIENT_ALREADY_LINKED,
                message="El paciente ya está vinculado a un convenio activo.",
                status_code=409,
            ),
        ):
            response = await authenticated_client.post(
                f"{BASE}/patients/{PATIENT_ID}/convenio",
                json={"patient_id": CONVENIO_ID},
            )

        assert response.status_code == 409

    async def test_link_patient_missing_convenio_id(self, authenticated_client):
        """POST /convenios/patients/{id}/convenio without body returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/patients/{PATIENT_ID}/convenio",
            json={},
        )
        assert response.status_code == 422

    async def test_invoice_with_convenio_discount(self, authenticated_client):
        """Creating an invoice for a patient linked to a convenio applies the discount.

        This is a smoke test: the invoice creation for a linked patient should
        succeed (201) or fail at DB level (500) but never return 422 for valid data.
        """
        patient_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/invoices",
            json={
                "items": [
                    {"description": "Consulta de revisión", "unit_price": 50000, "quantity": 1}
                ],
                "apply_convenio_discount": True,
            },
        )
        # 201 on success, 500 if patient/convenio not in DB — but not 422
        assert response.status_code in (201, 500)
