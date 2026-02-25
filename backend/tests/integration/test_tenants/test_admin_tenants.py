"""Integration tests for superadmin tenant management endpoints (T-01 to T-05).

Routes under test:
  GET  /api/v1/admin/tenants          — T-03: list all tenants
  GET  /api/v1/admin/tenants/{id}     — T-02: get tenant detail
  PUT  /api/v1/admin/tenants/{id}     — T-04: update tenant
  POST /api/v1/admin/tenants/{id}/suspend — T-05: suspend tenant

  POST /api/v1/admin/tenants is not tested here because it calls
  provision_tenant_schema (runs Alembic subprocess) which is not
  safe to execute in the integration test environment without mocking.
  A separate test with patch() can be added later.

All routes require role="superadmin". Non-superadmin requests must
return 401 (no token) or 403 (wrong role).
"""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.integration
class TestListTenants:
    """T-03: GET /api/v1/admin/tenants — superadmin pagination."""

    async def test_list_tenants_returns_paginated_response(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Superadmin can list all tenants; the test tenant must appear."""
        # Commit fixture data so the route's DB session can see it.
        await db_session.commit()

        response = await superadmin_client.get("/api/v1/admin/tenants")

        assert response.status_code == 200
        body = response.json()

        # Response matches TenantListResponse shape
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body

        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["total"] >= 1

        # The test tenant must be in the list
        ids = [item["id"] for item in body["items"]]
        assert str(test_tenant.id) in ids

    async def test_list_tenants_item_shape(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Each item in the list contains the required TenantListItem fields."""
        await db_session.commit()

        response = await superadmin_client.get("/api/v1/admin/tenants")

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1

        item = next(i for i in items if i["id"] == str(test_tenant.id))
        assert item["slug"] == test_tenant.slug
        assert item["name"] == "Test Clinic"
        assert item["country_code"] == "CO"
        assert item["status"] == "active"
        assert "plan_name" in item
        assert "owner_email" in item
        assert "member_count" in item
        assert "created_at" in item

    async def test_list_tenants_pagination_params(
        self,
        superadmin_client,
        db_session,
    ):
        """Custom page/page_size query params are reflected in the response."""
        await db_session.commit()

        response = await superadmin_client.get(
            "/api/v1/admin/tenants",
            params={"page": 1, "page_size": 5},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 1
        assert body["page_size"] == 5

    async def test_list_tenants_unauthorized_no_token(self, async_client):
        """Request without Authorization header returns 401."""
        response = await async_client.get("/api/v1/admin/tenants")
        assert response.status_code == 401

    async def test_list_tenants_forbidden_wrong_role(
        self,
        authenticated_client,
        db_session,
    ):
        """clinic_owner role is not allowed; must return 403."""
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/admin/tenants")
        assert response.status_code == 403


@pytest.mark.integration
class TestGetTenantDetail:
    """T-02: GET /api/v1/admin/tenants/{id} — full tenant detail."""

    async def test_get_tenant_returns_full_detail(
        self,
        superadmin_client,
        test_tenant,
        test_plan,
        db_session,
    ):
        """Superadmin gets full tenant detail including plan and member count."""
        await db_session.commit()

        response = await superadmin_client.get(
            f"/api/v1/admin/tenants/{test_tenant.id}"
        )

        assert response.status_code == 200
        body = response.json()

        # Top-level fields
        assert body["id"] == str(test_tenant.id)
        assert body["slug"] == test_tenant.slug
        assert body["name"] == "Test Clinic"
        assert body["country_code"] == "CO"
        assert body["status"] == "active"
        assert body["owner_email"] == "owner@test.co"
        assert body["onboarding_step"] == 0
        assert "schema_name" in body
        assert "timezone" in body
        assert "currency_code" in body
        assert "locale" in body
        assert "settings" in body
        assert "member_count" in body
        assert "created_at" in body
        assert "updated_at" in body

        # Embedded plan
        plan = body["plan"]
        assert plan["id"] == str(test_plan.id)
        assert "name" in plan
        assert "max_patients" in plan
        assert "max_doctors" in plan
        assert "max_users" in plan
        assert "features" in plan
        assert "price_cents" in plan

    async def test_get_tenant_not_found(
        self,
        superadmin_client,
        db_session,
    ):
        """Unknown tenant ID returns 404."""
        await db_session.commit()

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await superadmin_client.get(
            f"/api/v1/admin/tenants/{fake_id}"
        )
        assert response.status_code == 404

    async def test_get_tenant_unauthorized(self, async_client, test_tenant):
        """Request without token returns 401."""
        response = await async_client.get(
            f"/api/v1/admin/tenants/{test_tenant.id}"
        )
        assert response.status_code == 401

    async def test_get_tenant_forbidden_wrong_role(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """clinic_owner cannot access the superadmin tenant detail route."""
        await db_session.commit()

        response = await authenticated_client.get(
            f"/api/v1/admin/tenants/{test_tenant.id}"
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestUpdateTenant:
    """T-04: PUT /api/v1/admin/tenants/{id} — update tenant metadata."""

    async def test_update_tenant_name(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Superadmin can rename the clinic; response reflects the new name."""
        await db_session.commit()

        response = await superadmin_client.put(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            json={"name": "Clinica Actualizada"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Clinica Actualizada"
        assert body["id"] == str(test_tenant.id)

    async def test_update_tenant_phone(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Superadmin can set the tenant phone number."""
        await db_session.commit()

        response = await superadmin_client.put(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            json={"phone": "+573001234567"},
        )

        assert response.status_code == 200
        assert response.json()["phone"] == "+573001234567"

    async def test_update_tenant_preserves_unset_fields(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Unset fields in the PUT body are not overwritten (exclude_unset semantics)."""
        await db_session.commit()

        # Only update address; name should stay as-is
        response = await superadmin_client.put(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            json={"address": "Calle 123, Bogota"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["address"] == "Calle 123, Bogota"
        assert body["name"] == "Test Clinic"  # unchanged

    async def test_update_tenant_invalid_country_code(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Invalid country_code fails Pydantic validation (422)."""
        await db_session.commit()

        response = await superadmin_client.put(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            json={"country_code": "US"},  # US not in the allowed set
        )
        assert response.status_code == 422

    async def test_update_tenant_not_found(
        self,
        superadmin_client,
        db_session,
    ):
        """Updating a non-existent tenant returns 404."""
        await db_session.commit()

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await superadmin_client.put(
            f"/api/v1/admin/tenants/{fake_id}",
            json={"name": "Ghost Clinic"},
        )
        assert response.status_code == 404

    async def test_update_tenant_unauthorized(self, async_client, test_tenant):
        """No token returns 401."""
        response = await async_client.put(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            json={"name": "Hacker Clinic"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestSuspendTenant:
    """T-05: POST /api/v1/admin/tenants/{id}/suspend — suspend tenant."""

    async def test_suspend_active_tenant(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Superadmin can suspend an active tenant; status changes to 'suspended'."""
        await db_session.commit()

        response = await superadmin_client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/suspend"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "suspended"
        assert body["suspended_at"] is not None
        assert body["id"] == str(test_tenant.id)

    async def test_suspend_already_suspended_tenant(
        self,
        superadmin_client,
        test_tenant,
        db_session,
    ):
        """Suspending an already-suspended tenant returns 409 Conflict."""
        await db_session.commit()

        # First suspension
        first = await superadmin_client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/suspend"
        )
        assert first.status_code == 200

        # Second suspension attempt — must be 409
        second = await superadmin_client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/suspend"
        )
        assert second.status_code == 409

    async def test_suspend_tenant_not_found(
        self,
        superadmin_client,
        db_session,
    ):
        """Suspending a non-existent tenant returns 404."""
        await db_session.commit()

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await superadmin_client.post(
            f"/api/v1/admin/tenants/{fake_id}/suspend"
        )
        assert response.status_code == 404

    async def test_suspend_tenant_unauthorized(self, async_client, test_tenant):
        """No token returns 401."""
        response = await async_client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/suspend"
        )
        assert response.status_code == 401

    async def test_suspend_tenant_forbidden_wrong_role(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """clinic_owner cannot suspend tenants."""
        await db_session.commit()

        response = await authenticated_client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/suspend"
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestCreateTenant:
    """T-01: POST /api/v1/admin/tenants — create tenant (mocked provision)."""

    async def test_create_tenant_success(
        self,
        superadmin_client,
        test_plan,
        db_session,
    ):
        """Superadmin creates a new tenant; schema provisioning is mocked."""
        await db_session.commit()

        with patch(
            "app.services.tenant_settings_service.provision_tenant_schema",
            new_callable=AsyncMock,
        ):
            response = await superadmin_client.post(
                "/api/v1/admin/tenants",
                json={
                    "name": "Nueva Clinica",
                    "owner_email": "owner@nuevaclinica.co",
                    "country_code": "CO",
                    "plan_id": str(test_plan.id),
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Nueva Clinica"
        assert body["owner_email"] == "owner@nuevaclinica.co"
        assert body["country_code"] == "CO"
        assert body["status"] == "pending"
        assert "id" in body
        assert "slug" in body
        assert "schema_name" in body

    async def test_create_tenant_invalid_country(
        self,
        superadmin_client,
        test_plan,
        db_session,
    ):
        """Country code not in the allowed list fails validation (422)."""
        await db_session.commit()

        response = await superadmin_client.post(
            "/api/v1/admin/tenants",
            json={
                "name": "Bad Country Clinic",
                "owner_email": "bad@clinic.co",
                "country_code": "US",
                "plan_id": str(test_plan.id),
            },
        )
        assert response.status_code == 422

    async def test_create_tenant_missing_required_fields(
        self,
        superadmin_client,
        db_session,
    ):
        """Missing required fields fail Pydantic validation (422)."""
        await db_session.commit()

        response = await superadmin_client.post(
            "/api/v1/admin/tenants",
            json={"name": "Incomplete"},
        )
        assert response.status_code == 422

    async def test_create_tenant_unauthorized(self, async_client, test_plan):
        """No token returns 401."""
        response = await async_client.post(
            "/api/v1/admin/tenants",
            json={
                "name": "Anon Clinic",
                "owner_email": "anon@clinic.co",
                "country_code": "CO",
                "plan_id": str(test_plan.id),
            },
        )
        assert response.status_code == 401
