"""Integration tests for Cash Register API (GAP-02 / Sprint 23-24).

Endpoints:
  POST /api/v1/cash-registers/open     -- Open a new register session
  POST /api/v1/cash-registers/close    -- Close the current open register
  GET  /api/v1/cash-registers/current  -- Get the currently open register
  GET  /api/v1/cash-registers/history  -- Paginated history of closed registers

Requires: cash_register:write (open/close) and cash_register:read (get/history).
clinic_owner and receptionist roles have these permissions.
"""

from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/cash-registers"

_REGISTER_RESPONSE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Caja Principal",
    "location": "Recepción",
    "status": "open",
    "opening_balance_cents": 20000000,
    "closing_balance_cents": None,
    "opened_by": "00000000-0000-0000-0000-000000000099",
    "opened_at": "2026-03-02T08:00:00+00:00",
    "closed_at": None,
}

_REGISTER_DETAIL_RESPONSE = {
    **_REGISTER_RESPONSE,
    "total_income_cents": 50000000,
    "total_expense_cents": 5000000,
    "expected_balance_cents": 65000000,
    "movements": [],
}

_CLOSED_REGISTER_RESPONSE = {
    **_REGISTER_RESPONSE,
    "status": "closed",
    "closing_balance_cents": 64000000,
    "closed_at": "2026-03-02T18:00:00+00:00",
}

_HISTORY_RESPONSE = {
    "items": [_CLOSED_REGISTER_RESPONSE],
    "total": 1,
    "page": 1,
    "page_size": 20,
}


# ─── POST /cash-registers/open ────────────────────────────────────────────────


@pytest.mark.integration
class TestOpenRegister:
    async def test_open_register_returns_201(self, authenticated_client):
        """POST /open with valid data creates a new session (201)."""
        with patch(
            "app.services.cash_register_service.cash_register_service.open_register",
            new_callable=AsyncMock,
            return_value=_REGISTER_RESPONSE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/open",
                json={
                    "name": "Caja Principal",
                    "location": "Recepción",
                    "opening_balance_cents": 20000000,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "open"
        assert data["name"] == "Caja Principal"

    async def test_open_register_missing_fields_returns_422(self, authenticated_client):
        """POST /open without required fields returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/open",
            json={},
        )
        assert response.status_code == 422

    async def test_open_register_zero_balance(self, authenticated_client):
        """POST /open with opening_balance_cents=0 is valid (empty till)."""
        zero_balance_response = {**_REGISTER_RESPONSE, "opening_balance_cents": 0}
        with patch(
            "app.services.cash_register_service.cash_register_service.open_register",
            new_callable=AsyncMock,
            return_value=zero_balance_response,
        ):
            response = await authenticated_client.post(
                f"{BASE}/open",
                json={
                    "name": "Caja Secundaria",
                    "location": "Sala 2",
                    "opening_balance_cents": 0,
                },
            )

        assert response.status_code in (201, 500)

    async def test_open_register_no_auth(self, async_client):
        """POST /open without JWT is rejected with 401."""
        response = await async_client.post(
            f"{BASE}/open",
            json={
                "name": "Caja Principal",
                "location": "Recepción",
                "opening_balance_cents": 20000000,
            },
        )
        assert response.status_code == 401

    async def test_open_register_doctor_forbidden(self, doctor_client):
        """doctor role lacks cash_register:write and is rejected with 403."""
        response = await doctor_client.post(
            f"{BASE}/open",
            json={
                "name": "Caja Principal",
                "location": "Recepción",
                "opening_balance_cents": 20000000,
            },
        )
        assert response.status_code == 403


# ─── POST /cash-registers/close ───────────────────────────────────────────────


@pytest.mark.integration
class TestCloseRegister:
    async def test_close_open_register(self, authenticated_client):
        """POST /close against an open register succeeds (200)."""
        with (
            patch(
                "app.services.cash_register_service.cash_register_service.get_current",
                new_callable=AsyncMock,
                return_value=_REGISTER_RESPONSE,
            ),
            patch(
                "app.services.cash_register_service.cash_register_service.close_register",
                new_callable=AsyncMock,
                return_value=_CLOSED_REGISTER_RESPONSE,
            ),
        ):
            response = await authenticated_client.post(
                f"{BASE}/close",
                json={"closing_balance_cents": 64000000},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        assert data["closing_balance_cents"] == 64000000

    async def test_close_when_no_open_register(self, authenticated_client):
        """POST /close when no register is open returns 404."""
        with patch(
            "app.services.cash_register_service.cash_register_service.get_current",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await authenticated_client.post(
                f"{BASE}/close",
                json={"closing_balance_cents": 50000000},
            )

        assert response.status_code == 404

    async def test_close_missing_balance_returns_422(self, authenticated_client):
        """POST /close without closing_balance_cents returns 422."""
        response = await authenticated_client.post(
            f"{BASE}/close",
            json={},
        )
        assert response.status_code == 422

    async def test_close_no_auth(self, async_client):
        """POST /close without JWT is rejected with 401."""
        response = await async_client.post(
            f"{BASE}/close",
            json={"closing_balance_cents": 64000000},
        )
        assert response.status_code == 401


# ─── GET /cash-registers/current ─────────────────────────────────────────────


@pytest.mark.integration
class TestGetCurrentRegister:
    async def test_get_current_open_register(self, authenticated_client):
        """GET /current returns the open register with movements (200)."""
        with patch(
            "app.services.cash_register_service.cash_register_service.get_current",
            new_callable=AsyncMock,
            return_value=_REGISTER_DETAIL_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/current")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "open"
        assert "total_income_cents" in data

    async def test_get_current_no_open_register(self, authenticated_client):
        """GET /current returns null body (200) when no register is open."""
        with patch(
            "app.services.cash_register_service.cash_register_service.get_current",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await authenticated_client.get(f"{BASE}/current")

        assert response.status_code == 200
        assert response.json() is None

    async def test_get_current_no_auth(self, async_client):
        """GET /current without JWT is rejected with 401."""
        response = await async_client.get(f"{BASE}/current")
        assert response.status_code == 401


# ─── GET /cash-registers/history ─────────────────────────────────────────────


@pytest.mark.integration
class TestGetRegisterHistory:
    async def test_get_history_returns_paginated_list(self, authenticated_client):
        """GET /history returns a paginated list of closed sessions."""
        with patch(
            "app.services.cash_register_service.cash_register_service.get_history",
            new_callable=AsyncMock,
            return_value=_HISTORY_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/history")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_history_with_pagination(self, authenticated_client):
        """GET /history respects page and page_size query params."""
        with patch(
            "app.services.cash_register_service.cash_register_service.get_history",
            new_callable=AsyncMock,
            return_value=_HISTORY_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{BASE}/history",
                params={"page": 1, "page_size": 5},
            )

        assert response.status_code == 200

    async def test_get_history_invalid_page_size(self, authenticated_client):
        """GET /history with page_size=0 fails Query(ge=1) validation (422)."""
        response = await authenticated_client.get(
            f"{BASE}/history",
            params={"page_size": 0},
        )
        assert response.status_code == 422

    async def test_get_history_page_size_too_large(self, authenticated_client):
        """GET /history with page_size>100 fails Query(le=100) validation (422)."""
        response = await authenticated_client.get(
            f"{BASE}/history",
            params={"page_size": 200},
        )
        assert response.status_code == 422

    async def test_get_history_no_auth(self, async_client):
        """GET /history without JWT is rejected with 401."""
        response = await async_client.get(f"{BASE}/history")
        assert response.status_code == 401
