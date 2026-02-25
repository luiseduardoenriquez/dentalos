"""Integration tests for the onboarding wizard endpoint (T-10).

Route under test:
  POST /api/v1/onboarding — submit a single onboarding wizard step

Rules enforced by the service:
  - Steps must be submitted in order (0 → 1 → 2 → ... 4).
  - Attempting to skip ahead (e.g., step=2 when current is 0) returns 400.
  - Re-submitting the current or a previous step is allowed.
  - Completing step 4 sets completed=True and, if status was 'pending',
    sets status='active'.
  - Only clinic_owner can submit onboarding steps.

The test_tenant fixture creates a tenant with status='active' and
onboarding_step=0 (defaults). Tests that need a 'pending' tenant
set the status directly via the db_session fixture.
"""
import pytest


@pytest.mark.integration
class TestSubmitOnboardingStep:
    """T-10: POST /api/v1/onboarding — sequential step submission."""

    async def test_submit_step_zero_success(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Step 0 (first step) is always valid from initial state."""
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={
                "step": 0,
                "data": {
                    "clinic_specialty": "general",
                    "num_chairs": 3,
                },
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["current_step"] == 1  # advanced from 0 to 1
        assert body["completed"] is False
        assert "message" in body
        assert "Step 0 saved" in body["message"]

    async def test_submit_step_advances_counter(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Each submitted step advances the onboarding_step counter by one."""
        await db_session.commit()

        for step_num in range(3):
            response = await authenticated_client.post(
                "/api/v1/onboarding",
                json={"step": step_num, "data": {"key": f"value_{step_num}"}},
            )
            assert response.status_code == 200
            assert response.json()["current_step"] == step_num + 1

    async def test_submit_all_steps_completes_onboarding(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Submitting steps 0-4 in order sets completed=True on the final response."""
        await db_session.commit()

        last_response = None
        for step_num in range(5):  # steps 0, 1, 2, 3, 4
            last_response = await authenticated_client.post(
                "/api/v1/onboarding",
                json={
                    "step": step_num,
                    "data": {"completed_step": step_num},
                },
            )
            assert last_response.status_code == 200

        body = last_response.json()  # type: ignore[union-attr]
        assert body["completed"] is True
        assert body["current_step"] == 5  # past the last step (4 + 1)
        assert "Onboarding complete" in body["message"]

    async def test_resubmit_current_step_is_allowed(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Re-sending the current step (same step number) must not raise an error."""
        await db_session.commit()

        # Submit step 0 to advance to step 1
        first = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 0, "data": {"first": True}},
        )
        assert first.status_code == 200

        # Re-submit step 0 (re-visiting previous step) — must be 200
        retry = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 0, "data": {"first": False, "updated": True}},
        )
        assert retry.status_code == 200

    async def test_step_data_is_stored_in_settings(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Step data is persisted into tenant.settings under key 'onboarding_{step}'."""
        await db_session.commit()

        step_payload = {"specialty": "ortodoncia", "chairs": 5}
        await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 0, "data": step_payload},
        )

        # Reload tenant from DB and verify settings were stored
        await db_session.refresh(test_tenant)
        stored = test_tenant.settings or {}
        assert "onboarding_0" in stored
        assert stored["onboarding_0"]["specialty"] == "ortodoncia"
        assert stored["onboarding_0"]["chairs"] == 5


@pytest.mark.integration
class TestOnboardingSkipStep:
    """T-10: Skipping ahead in the onboarding wizard must return 400."""

    async def test_skip_step_from_zero_to_two(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """Attempting step=2 when onboarding_step=0 must return 400."""
        await db_session.commit()
        # onboarding_step starts at 0; skip directly to 2

        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 2, "data": {"skip": True}},
        )

        assert response.status_code == 400
        body = response.json()
        # Error shape: {"error": "...", "message": "...", "details": {}}
        assert "error" in body
        assert "TENANT_onboarding_step_invalid" in body["error"]

    async def test_skip_step_from_one_to_three(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """After submitting step 0 (current=1), attempting step=3 must return 400."""
        await db_session.commit()

        # Advance to step 1
        await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 0, "data": {}},
        )

        # Try to jump to step 3
        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 3, "data": {}},
        )

        assert response.status_code == 400

    async def test_step_out_of_range_high(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """step > 4 fails Pydantic validation (le=4 constraint) — returns 422."""
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 5, "data": {}},
        )
        assert response.status_code == 422

    async def test_step_out_of_range_negative(
        self,
        authenticated_client,
        test_tenant,
        db_session,
    ):
        """step < 0 fails Pydantic validation (ge=0 constraint) — returns 422."""
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": -1, "data": {}},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestOnboardingAuthorization:
    """T-10: Only clinic_owner can submit onboarding steps."""

    async def test_onboarding_unauthorized_no_token(self, async_client):
        """No Authorization header returns 401."""
        response = await async_client.post(
            "/api/v1/onboarding",
            json={"step": 0, "data": {}},
        )
        assert response.status_code == 401

    async def test_onboarding_forbidden_doctor_role(
        self,
        doctor_client,
        db_session,
    ):
        """doctor role is not clinic_owner; must return 403."""
        await db_session.commit()

        response = await doctor_client.post(
            "/api/v1/onboarding",
            json={"step": 0, "data": {}},
        )
        assert response.status_code == 403

    async def test_onboarding_missing_data_field(
        self,
        authenticated_client,
        db_session,
    ):
        """Missing required 'data' field fails Pydantic validation (422)."""
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"step": 0},  # 'data' is required
        )
        assert response.status_code == 422

    async def test_onboarding_missing_step_field(
        self,
        authenticated_client,
        db_session,
    ):
        """Missing required 'step' field fails Pydantic validation (422)."""
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/onboarding",
            json={"data": {"key": "value"}},  # 'step' is required
        )
        assert response.status_code == 422
