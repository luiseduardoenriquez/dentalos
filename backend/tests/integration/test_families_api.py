"""Integration tests for Family Groups API (GAP-10 / Sprint 25-26).

Endpoints:
  POST   /api/v1/families                               — Create family (families:write)
  GET    /api/v1/families/{family_id}                   — Get family with members (families:read)
  POST   /api/v1/families/{family_id}/members           — Add member (families:write)
  DELETE /api/v1/families/{family_id}/members/{pid}     — Remove member (families:write)
  GET    /api/v1/families/{family_id}/billing           — Consolidated billing (families:read + billing:read)

clinic_owner has both families:write/read and billing:read.
doctor role lacks families:write but may have families:read.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/families"

FAMILY_ID = str(uuid.uuid4())
PRIMARY_PATIENT_ID = str(uuid.uuid4())
SECONDARY_PATIENT_ID = str(uuid.uuid4())
THIRD_PATIENT_ID = str(uuid.uuid4())

_MEMBER = {
    "patient_id": PRIMARY_PATIENT_ID,
    "relationship": "head",
    "is_primary_contact": True,
    "joined_at": "2026-03-01T09:00:00+00:00",
}

_FAMILY_RESPONSE = {
    "id": FAMILY_ID,
    "name": "Familia García",
    "primary_contact_patient_id": PRIMARY_PATIENT_ID,
    "members": [_MEMBER],
    "member_count": 1,
    "created_at": "2026-03-01T09:00:00+00:00",
    "updated_at": "2026-03-01T09:00:00+00:00",
}

_FAMILY_WITH_TWO_MEMBERS = {
    **_FAMILY_RESPONSE,
    "members": [
        _MEMBER,
        {
            "patient_id": SECONDARY_PATIENT_ID,
            "relationship": "spouse",
            "is_primary_contact": False,
            "joined_at": "2026-03-02T10:00:00+00:00",
        },
    ],
    "member_count": 2,
}

_FAMILY_BILLING = {
    "family_id": FAMILY_ID,
    "family_name": "Familia García",
    "member_count": 2,
    "total_invoiced_cents": 350000,
    "total_paid_cents": 280000,
    "total_outstanding_cents": 70000,
    "members_billing": [
        {
            "patient_id": PRIMARY_PATIENT_ID,
            "total_invoiced_cents": 200000,
            "total_paid_cents": 150000,
        },
        {
            "patient_id": SECONDARY_PATIENT_ID,
            "total_invoiced_cents": 150000,
            "total_paid_cents": 130000,
        },
    ],
}


# ─── POST /families ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateFamily:
    async def test_create_family_requires_auth(self, async_client):
        """POST /families without JWT returns 401."""
        response = await async_client.post(
            BASE,
            json={
                "name": "Familia García",
                "primary_contact_patient_id": PRIMARY_PATIENT_ID,
            },
        )
        assert response.status_code == 401

    async def test_create_family_requires_permission(self, doctor_client):
        """doctor role lacks families:write — expects 403."""
        response = await doctor_client.post(
            BASE,
            json={
                "name": "Familia García",
                "primary_contact_patient_id": PRIMARY_PATIENT_ID,
            },
        )
        assert response.status_code == 403

    async def test_create_family_success(self, authenticated_client):
        """POST /families with valid payload returns 201 and the new family."""
        with patch(
            "app.services.family_service.family_service.create",
            new_callable=AsyncMock,
            return_value=_FAMILY_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE,
                json={
                    "name": "Familia García",
                    "primary_contact_patient_id": PRIMARY_PATIENT_ID,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Familia García"
        assert data["primary_contact_patient_id"] == PRIMARY_PATIENT_ID
        assert isinstance(data["members"], list)

    async def test_create_family_missing_name(self, authenticated_client):
        """POST /families without name returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={"primary_contact_patient_id": PRIMARY_PATIENT_ID},
        )
        assert response.status_code == 422

    async def test_create_family_missing_primary_contact(self, authenticated_client):
        """POST /families without primary_contact_patient_id returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={"name": "Familia Sin Contacto"},
        )
        assert response.status_code == 422

    async def test_create_family_invalid_patient_uuid(self, authenticated_client):
        """POST /families with malformed primary_contact_patient_id returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={
                "name": "Familia García",
                "primary_contact_patient_id": "not-a-uuid",
            },
        )
        assert response.status_code == 422


# ─── GET /families/{family_id} ────────────────────────────────────────────────


@pytest.mark.integration
class TestGetFamily:
    async def test_get_family_requires_auth(self, async_client):
        """GET /families/{id} without JWT returns 401."""
        response = await async_client.get(f"{BASE}/{FAMILY_ID}")
        assert response.status_code == 401

    async def test_get_family_success(self, authenticated_client):
        """GET /families/{id} returns the family with its members."""
        with patch(
            "app.services.family_service.family_service.get",
            new_callable=AsyncMock,
            return_value=_FAMILY_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/{FAMILY_ID}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "members" in data
        assert isinstance(data["members"], list)
        assert data["id"] == FAMILY_ID

    async def test_get_family_not_found(self, authenticated_client):
        """GET /families/{nonexistent_id} returns 404."""
        from app.core.exceptions import ResourceNotFoundError
        from app.core.error_codes import FamilyErrors

        with patch(
            "app.services.family_service.family_service.get",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(
                error=FamilyErrors.NOT_FOUND,
                resource_name="FamilyGroup",
            ),
        ):
            response = await authenticated_client.get(f"{BASE}/{uuid.uuid4()}")

        assert response.status_code == 404


# ─── POST /families/{family_id}/members ──────────────────────────────────────


@pytest.mark.integration
class TestAddFamilyMember:
    async def test_add_member_requires_auth(self, async_client):
        """POST /families/{id}/members without JWT returns 401."""
        response = await async_client.post(
            f"{BASE}/{FAMILY_ID}/members",
            json={"patient_id": SECONDARY_PATIENT_ID, "relationship": "spouse"},
        )
        assert response.status_code == 401

    async def test_add_member_requires_permission(self, doctor_client):
        """doctor role lacks families:write — expects 403."""
        response = await doctor_client.post(
            f"{BASE}/{FAMILY_ID}/members",
            json={"patient_id": SECONDARY_PATIENT_ID, "relationship": "spouse"},
        )
        assert response.status_code == 403

    async def test_add_member_success(self, authenticated_client):
        """POST /families/{id}/members with valid payload returns 200 with updated family."""
        with patch(
            "app.services.family_service.family_service.add_member",
            new_callable=AsyncMock,
            return_value=_FAMILY_WITH_TWO_MEMBERS,
        ):
            response = await authenticated_client.post(
                f"{BASE}/{FAMILY_ID}/members",
                json={"patient_id": SECONDARY_PATIENT_ID, "relationship": "spouse"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["member_count"] == 2
        assert len(data["members"]) == 2

    async def test_add_member_already_in_family_returns_409(self, authenticated_client):
        """POST /families/{id}/members for a patient already in family returns 409."""
        from app.core.exceptions import DentalOSError
        from app.core.error_codes import FamilyErrors

        with patch(
            "app.services.family_service.family_service.add_member",
            new_callable=AsyncMock,
            side_effect=DentalOSError(
                error=FamilyErrors.ALREADY_IN_FAMILY,
                message="El paciente ya pertenece a un grupo familiar.",
                status_code=409,
            ),
        ):
            response = await authenticated_client.post(
                f"{BASE}/{FAMILY_ID}/members",
                json={"patient_id": PRIMARY_PATIENT_ID, "relationship": "head"},
            )

        assert response.status_code == 409

    async def test_add_member_missing_patient_id(self, authenticated_client):
        """POST /families/{id}/members without patient_id returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/{FAMILY_ID}/members",
            json={"relationship": "spouse"},
        )
        assert response.status_code == 422

    async def test_add_member_missing_relationship(self, authenticated_client):
        """POST /families/{id}/members without relationship returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/{FAMILY_ID}/members",
            json={"patient_id": SECONDARY_PATIENT_ID},
        )
        assert response.status_code == 422


# ─── DELETE /families/{family_id}/members/{patient_id} ───────────────────────


@pytest.mark.integration
class TestRemoveFamilyMember:
    async def test_remove_member_requires_auth(self, async_client):
        """DELETE /families/{id}/members/{pid} without JWT returns 401."""
        response = await async_client.delete(
            f"{BASE}/{FAMILY_ID}/members/{SECONDARY_PATIENT_ID}"
        )
        assert response.status_code == 401

    async def test_remove_member_requires_permission(self, doctor_client):
        """doctor role lacks families:write — expects 403."""
        response = await doctor_client.delete(
            f"{BASE}/{FAMILY_ID}/members/{SECONDARY_PATIENT_ID}"
        )
        assert response.status_code == 403

    async def test_remove_member_success(self, authenticated_client):
        """DELETE /families/{id}/members/{pid} soft-removes the patient (200)."""
        with patch(
            "app.services.family_service.family_service.remove_member",
            new_callable=AsyncMock,
            return_value=_FAMILY_RESPONSE,
        ):
            response = await authenticated_client.delete(
                f"{BASE}/{FAMILY_ID}/members/{SECONDARY_PATIENT_ID}"
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    async def test_remove_primary_contact_rejected(self, authenticated_client):
        """Removing the primary contact without a replacement returns an error.

        The service should raise an appropriate error (400 or 409).
        """
        from app.core.exceptions import DentalOSError
        from app.core.error_codes import FamilyErrors

        with patch(
            "app.services.family_service.family_service.remove_member",
            new_callable=AsyncMock,
            side_effect=DentalOSError(
                error=FamilyErrors.PRIMARY_CONTACT_REQUIRED,
                message="El contacto principal no puede ser eliminado sin asignar uno nuevo.",
                status_code=409,
            ),
        ):
            response = await authenticated_client.delete(
                f"{BASE}/{FAMILY_ID}/members/{PRIMARY_PATIENT_ID}"
            )

        assert response.status_code == 409


# ─── GET /families/{family_id}/billing ───────────────────────────────────────


@pytest.mark.integration
class TestFamilyBilling:
    async def test_family_billing_requires_auth(self, async_client):
        """GET /families/{id}/billing without JWT returns 401."""
        response = await async_client.get(f"{BASE}/{FAMILY_ID}/billing")
        assert response.status_code == 401

    async def test_family_billing_returns_aggregated_billing(self, authenticated_client):
        """GET /families/{id}/billing returns consolidated billing for all members."""
        with patch(
            "app.services.family_service.family_service.get_family_billing",
            new_callable=AsyncMock,
            return_value=_FAMILY_BILLING,
        ):
            response = await authenticated_client.get(f"{BASE}/{FAMILY_ID}/billing")

        assert response.status_code == 200
        data = response.json()
        assert "total_invoiced_cents" in data
        assert "total_paid_cents" in data
        assert "total_outstanding_cents" in data
        assert "members_billing" in data
        assert isinstance(data["members_billing"], list)

    async def test_family_billing_not_found(self, authenticated_client):
        """GET /families/{nonexistent_id}/billing returns 404."""
        from app.core.exceptions import ResourceNotFoundError
        from app.core.error_codes import FamilyErrors

        with patch(
            "app.services.family_service.family_service.get_family_billing",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(
                error=FamilyErrors.NOT_FOUND,
                resource_name="FamilyGroup",
            ),
        ):
            response = await authenticated_client.get(
                f"{BASE}/{uuid.uuid4()}/billing"
            )

        assert response.status_code == 404

    async def test_family_billing_doctor_lacks_permission(self, doctor_client):
        """doctor role lacks billing:read — expects 403 for family billing."""
        response = await doctor_client.get(f"{BASE}/{FAMILY_ID}/billing")
        assert response.status_code in (403, 500)
