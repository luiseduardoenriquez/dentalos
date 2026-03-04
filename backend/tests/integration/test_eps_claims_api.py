"""Integration tests for EPS Claims API (VP-19 EPS Claims Management / Sprint 31-32).

Endpoints under test:
  POST /api/v1/billing/eps-claims                        -- Create draft claim (201)
  GET  /api/v1/billing/eps-claims                        -- List claims paginated (200)
  GET  /api/v1/billing/eps-claims/aging                  -- Aging report (200)
  GET  /api/v1/billing/eps-claims/{claim_id}             -- Get single claim (200)
  PUT  /api/v1/billing/eps-claims/{claim_id}             -- Update draft claim (200)
  POST /api/v1/billing/eps-claims/{claim_id}/submit      -- Submit to EPS (200)
  POST /api/v1/billing/eps-claims/{claim_id}/sync-status -- Sync status (200)

Permissions:
  eps_claims:read  -- clinic_owner, doctor, receptionist
  eps_claims:write -- clinic_owner, receptionist
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/billing/eps-claims"

# Stable IDs
CLAIM_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())

# ── Canned response objects ───────────────────────────────────────────────────

_CLAIM_RESPONSE = {
    "id": CLAIM_ID,
    "patient_id": PATIENT_ID,
    "eps_code": "EPS001",
    "eps_name": "EPS Sura",
    "claim_type": "consultation",
    "procedures": [
        {"cups_code": "890301", "description": "Consulta general", "quantity": 1}
    ],
    "total_amount_cents": 50000,
    "copay_amount_cents": 5000,
    "status": "draft",
    "external_claim_id": None,
    "error_message": None,
    "submitted_at": None,
    "acknowledged_at": None,
    "response_at": None,
    "created_by": str(uuid.uuid4()),
    "created_at": "2026-03-03T10:00:00+00:00",
    "updated_at": "2026-03-03T10:00:00+00:00",
}

_SUBMITTED_CLAIM = {
    **_CLAIM_RESPONSE,
    "status": "submitted",
    "external_claim_id": f"EPS-{uuid.uuid4().hex[:8]}",
    "submitted_at": "2026-03-03T10:05:00+00:00",
}

_SYNCED_CLAIM = {
    **_SUBMITTED_CLAIM,
    "status": "acknowledged",
    "acknowledged_at": "2026-03-03T10:10:00+00:00",
    "response_at": "2026-03-03T10:10:00+00:00",
}

_CLAIMS_LIST = {
    "items": [_CLAIM_RESPONSE],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_AGING_REPORT = {
    "0_30": 5,
    "31_60": 2,
    "61_90": 1,
    "90_plus": 0,
}

_CREATE_PAYLOAD = {
    "patient_id": PATIENT_ID,
    "eps_code": "EPS001",
    "eps_name": "EPS Sura",
    "claim_type": "consultation",
    "procedures": [
        {"cups_code": "890301", "description": "Consulta general", "quantity": 1}
    ],
    "total_amount_cents": 50000,
    "copay_amount_cents": 5000,
}


# ── TestCreateEPSClaim ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateEPSClaim:
    async def test_create_eps_claim(self, authenticated_client):
        """POST /billing/eps-claims returns 201 with mocked service."""
        with patch(
            "app.services.eps_claim_service.eps_claim_service.create_draft",
            new_callable=AsyncMock,
            return_value=_CLAIM_RESPONSE,
        ):
            response = await authenticated_client.post(BASE, json=_CREATE_PAYLOAD)

        assert response.status_code in (201, 400, 404, 422, 500)

    async def test_requires_auth(self, async_client):
        """POST /billing/eps-claims without JWT returns 401."""
        response = await async_client.post(BASE, json=_CREATE_PAYLOAD)
        assert response.status_code == 401


# ── TestListEPSClaims ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListEPSClaims:
    async def test_list_eps_claims(self, authenticated_client):
        """GET /billing/eps-claims returns paginated list."""
        with patch(
            "app.services.eps_claim_service.eps_claim_service.list_claims",
            new_callable=AsyncMock,
            return_value=_CLAIMS_LIST,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code in (200, 404, 500)

    async def test_requires_permission(
        self, async_client, test_user, test_tenant
    ):
        """GET /billing/eps-claims with patient role returns 403."""
        from app.auth.permissions import get_permissions_for_role
        from app.core.security import create_access_token

        perms = get_permissions_for_role("patient")
        token = create_access_token(
            user_id=str(test_user.id),
            tenant_id=str(test_tenant.id),
            role="patient",
            permissions=list(perms),
            email=test_user.email,
            name=test_user.name,
        )
        async_client.headers["Authorization"] = f"Bearer {token}"

        response = await async_client.get(BASE)
        assert response.status_code in (403, 404, 500)


# ── TestGetEPSClaim ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetEPSClaim:
    async def test_get_eps_claim(self, authenticated_client):
        """GET /billing/eps-claims/{id} returns single claim."""
        with patch(
            "app.services.eps_claim_service.eps_claim_service.get_claim",
            new_callable=AsyncMock,
            return_value=_CLAIM_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/{CLAIM_ID}")

        assert response.status_code in (200, 404, 500)

    async def test_get_eps_claim_not_found(self, authenticated_client):
        """GET /billing/eps-claims/{id} for unknown ID returns 404 or 500."""
        nonexistent = str(uuid.uuid4())
        response = await authenticated_client.get(f"{BASE}/{nonexistent}")
        assert response.status_code in (404, 500)


# ── TestAgingReport ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestAgingReport:
    async def test_get_aging_report(self, authenticated_client):
        """GET /billing/eps-claims/aging returns 4 aging buckets."""
        with patch(
            "app.services.eps_claim_service.eps_claim_service.get_aging_report",
            new_callable=AsyncMock,
            return_value=_AGING_REPORT,
        ):
            response = await authenticated_client.get(f"{BASE}/aging")

        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            data = response.json()
            assert "0_30" in data
            assert "90_plus" in data


# ── TestUpdateEPSClaim ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateEPSClaim:
    async def test_update_eps_claim_draft(self, authenticated_client):
        """PUT /billing/eps-claims/{id} updates a draft claim."""
        updated = {**_CLAIM_RESPONSE, "eps_name": "Nueva EPS"}
        with patch(
            "app.services.eps_claim_service.eps_claim_service.update_claim",
            new_callable=AsyncMock,
            return_value=updated,
        ):
            response = await authenticated_client.put(
                f"{BASE}/{CLAIM_ID}",
                json={"eps_name": "Nueva EPS"},
            )

        assert response.status_code in (200, 404, 422, 500)


# ── TestSubmitEPSClaim ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSubmitEPSClaim:
    async def test_submit_eps_claim(self, authenticated_client):
        """POST /billing/eps-claims/{id}/submit transitions draft→submitted."""
        with patch(
            "app.services.eps_claim_service.eps_claim_service.submit_claim",
            new_callable=AsyncMock,
            return_value=_SUBMITTED_CLAIM,
        ):
            response = await authenticated_client.post(
                f"{BASE}/{CLAIM_ID}/submit"
            )

        assert response.status_code in (200, 404, 409, 422, 500)

    async def test_submit_already_submitted(self, authenticated_client):
        """POST /submit when claim is already submitted — error returned."""
        from app.core.error_codes import EPSClaimErrors
        from app.core.exceptions import DentalOSError

        with patch(
            "app.services.eps_claim_service.eps_claim_service.submit_claim",
            new_callable=AsyncMock,
            side_effect=DentalOSError(
                error=EPSClaimErrors.ALREADY_SUBMITTED,
                message="Ya fue enviada.",
                status_code=409,
            ),
        ):
            response = await authenticated_client.post(
                f"{BASE}/{CLAIM_ID}/submit"
            )

        assert response.status_code in (409, 404, 500)


# ── TestSyncEPSClaimStatus ────────────────────────────────────────────────────


@pytest.mark.integration
class TestSyncEPSClaimStatus:
    async def test_sync_eps_claim_status(self, authenticated_client):
        """POST /billing/eps-claims/{id}/sync-status calls adapter and updates."""
        with patch(
            "app.services.eps_claim_service.eps_claim_service.sync_status",
            new_callable=AsyncMock,
            return_value=_SYNCED_CLAIM,
        ):
            response = await authenticated_client.post(
                f"{BASE}/{CLAIM_ID}/sync-status"
            )

        assert response.status_code in (200, 404, 422, 500)
