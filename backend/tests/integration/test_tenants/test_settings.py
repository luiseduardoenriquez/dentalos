"""Integration tests for tenant settings endpoints (T-06 to T-09).

Routes under test:
  GET  /api/v1/settings              — T-06: get current tenant settings
  PUT  /api/v1/settings              — T-07: update tenant settings
  GET  /api/v1/settings/usage        — T-08: plan usage stats
  GET  /api/v1/settings/plan-limits  — T-09: plan limits (any authenticated user)

GET /usage and GET /plan-limits run raw SQL against the tenant schema
to count users and patients. The test_tenant_schema fixture creates the
schema and test_user populates the users table, so counts will be >= 1.
"""
import pytest


@pytest.mark.integration
class TestGetSettings:
    """T-06: GET /api/v1/settings — clinic_owner reads own tenant settings."""

    async def test_get_settings_returns_tenant_data(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """clinic_owner receives full TenantSettingsResponse for their tenant."""
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/settings")

        assert response.status_code == 200
        body = response.json()

        assert body["name"] == "Test Clinic"
        assert body["country_code"] == "CO"
        assert body["timezone"] == "America/Bogota"
        assert body["currency_code"] == "COP"
        assert body["locale"] == "es-CO"
        assert isinstance(body["settings"], dict)

        # Nullable fields are present in response (may be None)
        assert "phone" in body
        assert "address" in body
        assert "logo_url" in body

    async def test_get_settings_unauthorized_no_token(self, async_client):
        """Request without token returns 401."""
        response = await async_client.get("/api/v1/settings")
        assert response.status_code == 401

    async def test_get_settings_forbidden_non_owner(
        self,
        doctor_client,
        db_session,
    ):
        """A doctor role cannot access settings; route requires clinic_owner."""
        await db_session.commit()

        response = await doctor_client.get("/api/v1/settings")
        assert response.status_code == 403


@pytest.mark.integration
class TestUpdateSettings:
    """T-07: PUT /api/v1/settings — clinic_owner updates tenant settings."""

    async def test_update_settings_name(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """clinic_owner can rename the clinic; the new name is reflected."""
        await db_session.commit()

        response = await authenticated_client.put(
            "/api/v1/settings",
            json={"name": "Clinica Modificada"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Clinica Modificada"

    async def test_update_settings_phone_and_address(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """clinic_owner can set contact information."""
        await db_session.commit()

        response = await authenticated_client.put(
            "/api/v1/settings",
            json={
                "phone": "+573159876543",
                "address": "Carrera 15 # 80-10, Bogota",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["phone"] == "+573159876543"
        assert body["address"] == "Carrera 15 # 80-10, Bogota"

    async def test_update_settings_merges_settings_jsonb(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """settings JSONB key is merged (shallow), not replaced."""
        await db_session.commit()

        # Set initial custom setting
        await authenticated_client.put(
            "/api/v1/settings",
            json={"settings": {"invoice_prefix": "CLN"}},
        )

        # Add another key — the first must be preserved
        response = await authenticated_client.put(
            "/api/v1/settings",
            json={"settings": {"appointment_reminder_hours": 24}},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["settings"]["invoice_prefix"] == "CLN"
        assert body["settings"]["appointment_reminder_hours"] == 24

    async def test_update_settings_preserves_unset_fields(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Fields not included in the PUT body are not wiped out."""
        await db_session.commit()

        # Set address first
        await authenticated_client.put(
            "/api/v1/settings",
            json={"address": "Avenida El Dorado 90"},
        )

        # Update only timezone
        response = await authenticated_client.put(
            "/api/v1/settings",
            json={"timezone": "America/Bogota"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["timezone"] == "America/Bogota"
        assert body["address"] == "Avenida El Dorado 90"  # preserved

    async def test_update_settings_invalid_currency(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Currency code must be 3 uppercase letters (Pydantic pattern)."""
        await db_session.commit()

        response = await authenticated_client.put(
            "/api/v1/settings",
            json={"currency_code": "usd"},  # lowercase — invalid
        )
        assert response.status_code == 422

    async def test_update_settings_unauthorized(self, async_client):
        """No token returns 401."""
        response = await async_client.put(
            "/api/v1/settings",
            json={"name": "Hacker Clinic"},
        )
        assert response.status_code == 401

    async def test_update_settings_forbidden_non_owner(
        self,
        doctor_client,
        db_session,
    ):
        """doctor role cannot update settings."""
        await db_session.commit()

        response = await doctor_client.put(
            "/api/v1/settings",
            json={"name": "Doctor Override"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestPlanLimits:
    """T-09: GET /api/v1/settings/plan-limits — any authenticated user."""

    async def test_get_plan_limits_returns_limits(
        self,
        authenticated_client,
        test_plan,
        db_session,
    ):
        """clinic_owner receives plan limits matching the assigned test plan."""
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/settings/plan-limits")

        assert response.status_code == 200
        body = response.json()

        assert body["max_patients"] == test_plan.max_patients
        assert body["max_doctors"] == test_plan.max_doctors
        assert body["max_users"] == test_plan.max_users
        assert body["max_storage_mb"] == test_plan.max_storage_mb
        assert isinstance(body["features"], dict)

    async def test_get_plan_limits_accessible_by_doctor(
        self,
        doctor_client,
        test_plan,
        db_session,
    ):
        """plan-limits is accessible by any authenticated user (not just clinic_owner)."""
        await db_session.commit()

        response = await doctor_client.get("/api/v1/settings/plan-limits")
        assert response.status_code == 200

    async def test_get_plan_limits_unauthorized(self, async_client):
        """No token returns 401."""
        response = await async_client.get("/api/v1/settings/plan-limits")
        assert response.status_code == 401


@pytest.mark.integration
class TestPlanUsage:
    """T-08: GET /api/v1/settings/usage — clinic_owner reads live usage."""

    async def test_get_usage_returns_usage_stats(
        self,
        authenticated_client,
        test_user,
        test_tenant,
        test_plan,
        db_session,
    ):
        """Usage response contains counts for patients, doctors, users, and storage."""
        # Ensure all fixture data is visible to the route's DB session.
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/settings/usage")

        assert response.status_code == 200
        body = response.json()

        # All required fields present
        assert "current_patients" in body
        assert "max_patients" in body
        assert "current_doctors" in body
        assert "max_doctors" in body
        assert "current_users" in body
        assert "max_users" in body
        assert "current_storage_mb" in body
        assert "max_storage_mb" in body

        # Plan limits match the fixture plan
        assert body["max_patients"] == test_plan.max_patients
        assert body["max_doctors"] == test_plan.max_doctors
        assert body["max_users"] == test_plan.max_users
        assert body["max_storage_mb"] == test_plan.max_storage_mb

        # At least the test_user exists in the schema (role=clinic_owner, not doctor)
        assert body["current_users"] >= 1
        # Storage is a placeholder in the current implementation
        assert body["current_storage_mb"] == 0

    async def test_get_usage_unauthorized(self, async_client):
        """No token returns 401."""
        response = await async_client.get("/api/v1/settings/usage")
        assert response.status_code == 401

    async def test_get_usage_forbidden_non_owner(
        self,
        doctor_client,
        db_session,
    ):
        """doctor role is not allowed; must return 403."""
        await db_session.commit()

        response = await doctor_client.get("/api/v1/settings/usage")
        assert response.status_code == 403
