"""Integration tests for Expenses API (GAP-03 / Sprint 23-24).

Endpoints:
  POST /api/v1/expenses                 -- Record a new expense
  GET  /api/v1/expenses                 -- List expenses with optional filters
  GET  /api/v1/expenses/categories      -- List active expense categories
  GET  /api/v1/expenses/profit-loss     -- Profit & loss summary for a date range

Requires: expenses:write (POST) and expenses:read (GET).
clinic_owner has both; doctor has neither.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/expenses"
CATEGORY_ID = str(uuid.uuid4())

_EXPENSE_RESPONSE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "category_id": CATEGORY_ID,
    "category_name": "Materiales Dentales",
    "amount_cents": 5000000,
    "description": "Compra de materiales de impresión",
    "expense_date": "2026-03-02",
    "receipt_url": None,
    "recorded_by": "00000000-0000-0000-0000-000000000099",
    "created_at": "2026-03-02T10:00:00+00:00",
}

_EXPENSE_LIST_RESPONSE = {
    "items": [_EXPENSE_RESPONSE],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_CATEGORY_LIST = [
    {
        "id": CATEGORY_ID,
        "name": "Materiales Dentales",
        "is_default": True,
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Arriendo",
        "is_default": True,
        "is_active": True,
    },
]

_PROFIT_LOSS_RESPONSE = {
    "date_from": "2026-03-01",
    "date_to": "2026-03-31",
    "total_revenue_cents": 120000000,
    "total_expenses_cents": 30000000,
    "net_profit_cents": 90000000,
    "revenue_breakdown": [],
    "expense_breakdown": [],
}


# ─── POST /expenses ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateExpense:
    async def test_create_valid_expense_returns_201(self, authenticated_client):
        """POST /expenses with valid data returns 201 and the created expense."""
        with patch(
            "app.services.expense_service.expense_service.create_expense",
            new_callable=AsyncMock,
            return_value=_EXPENSE_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE,
                json={
                    "category_id": CATEGORY_ID,
                    "amount_cents": 5000000,
                    "description": "Compra de materiales de impresión",
                    "expense_date": "2026-03-02",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["amount_cents"] == 5000000
        assert "id" in data

    async def test_create_missing_required_fields_returns_422(self, authenticated_client):
        """POST /expenses without required fields returns 422."""
        response = await authenticated_client.post(BASE, json={})
        assert response.status_code == 422

    async def test_create_missing_amount_returns_422(self, authenticated_client):
        """POST /expenses without amount_cents returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={
                "category_id": CATEGORY_ID,
                "description": "Sin monto",
                "expense_date": "2026-03-02",
            },
        )
        assert response.status_code == 422

    async def test_create_with_receipt_url(self, authenticated_client):
        """POST /expenses with an optional receipt_url is accepted."""
        response_with_receipt = {
            **_EXPENSE_RESPONSE,
            "receipt_url": "https://storage.dentalos.co/receipts/abc.pdf",
        }
        with patch(
            "app.services.expense_service.expense_service.create_expense",
            new_callable=AsyncMock,
            return_value=response_with_receipt,
        ):
            response = await authenticated_client.post(
                BASE,
                json={
                    "category_id": CATEGORY_ID,
                    "amount_cents": 5000000,
                    "description": "Con recibo",
                    "expense_date": "2026-03-02",
                    "receipt_url": "https://storage.dentalos.co/receipts/abc.pdf",
                },
            )

        assert response.status_code == 201

    async def test_create_no_auth_returns_401(self, async_client):
        """POST /expenses without JWT is rejected with 401."""
        response = await async_client.post(
            BASE,
            json={
                "category_id": CATEGORY_ID,
                "amount_cents": 5000000,
                "description": "Test",
                "expense_date": "2026-03-02",
            },
        )
        assert response.status_code == 401

    async def test_create_as_doctor_returns_403(self, doctor_client):
        """doctor role lacks expenses:write and is rejected with 403."""
        response = await doctor_client.post(
            BASE,
            json={
                "category_id": CATEGORY_ID,
                "amount_cents": 5000000,
                "description": "Test",
                "expense_date": "2026-03-02",
            },
        )
        assert response.status_code == 403


# ─── GET /expenses ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListExpenses:
    async def test_list_expenses_returns_200(self, authenticated_client):
        """GET /expenses returns a paginated list."""
        with patch(
            "app.services.expense_service.expense_service.list_expenses",
            new_callable=AsyncMock,
            return_value=_EXPENSE_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_with_pagination(self, authenticated_client):
        """GET /expenses with pagination params returns 200."""
        with patch(
            "app.services.expense_service.expense_service.list_expenses",
            new_callable=AsyncMock,
            return_value=_EXPENSE_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(
                BASE,
                params={"page": 1, "page_size": 10},
            )

        assert response.status_code == 200

    async def test_list_with_date_filter(self, authenticated_client):
        """GET /expenses with date_from/date_to filters returns 200."""
        with patch(
            "app.services.expense_service.expense_service.list_expenses",
            new_callable=AsyncMock,
            return_value=_EXPENSE_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(
                BASE,
                params={"date_from": "2026-03-01", "date_to": "2026-03-31"},
            )

        assert response.status_code == 200

    async def test_list_invalid_page_size_returns_422(self, authenticated_client):
        """GET /expenses with page_size=0 fails Query(ge=1) validation."""
        response = await authenticated_client.get(
            BASE, params={"page_size": 0}
        )
        assert response.status_code == 422

    async def test_list_no_auth_returns_401(self, async_client):
        """GET /expenses without JWT is rejected with 401."""
        response = await async_client.get(BASE)
        assert response.status_code == 401


# ─── GET /expenses/categories ─────────────────────────────────────────────────


@pytest.mark.integration
class TestGetExpenseCategories:
    async def test_get_categories_returns_200(self, authenticated_client):
        """GET /expenses/categories returns a list of active categories."""
        with patch(
            "app.services.expense_service.expense_service.list_categories",
            new_callable=AsyncMock,
            return_value=_CATEGORY_LIST,
        ):
            response = await authenticated_client.get(f"{BASE}/categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "Materiales Dentales"

    async def test_get_categories_no_auth_returns_401(self, async_client):
        """GET /expenses/categories without JWT is rejected with 401."""
        response = await async_client.get(f"{BASE}/categories")
        assert response.status_code == 401

    async def test_get_categories_as_doctor_returns_403(self, doctor_client):
        """doctor role lacks expenses:read and is rejected with 403."""
        response = await doctor_client.get(f"{BASE}/categories")
        assert response.status_code == 403


# ─── GET /expenses/profit-loss ────────────────────────────────────────────────


@pytest.mark.integration
class TestGetProfitLoss:
    async def test_get_profit_loss_returns_200(self, authenticated_client):
        """GET /expenses/profit-loss with required date params returns P&L summary."""
        with patch(
            "app.services.expense_service.expense_service.get_profit_loss",
            new_callable=AsyncMock,
            return_value=_PROFIT_LOSS_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{BASE}/profit-loss",
                params={"date_from": "2026-03-01", "date_to": "2026-03-31"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "net_profit_cents" in data
        assert "total_revenue_cents" in data
        assert "total_expenses_cents" in data

    async def test_get_profit_loss_missing_dates_returns_422(self, authenticated_client):
        """GET /expenses/profit-loss without required date_from/date_to returns 422."""
        response = await authenticated_client.get(f"{BASE}/profit-loss")
        assert response.status_code == 422

    async def test_get_profit_loss_missing_date_to_returns_422(self, authenticated_client):
        """GET /expenses/profit-loss with only date_from returns 422."""
        response = await authenticated_client.get(
            f"{BASE}/profit-loss",
            params={"date_from": "2026-03-01"},
        )
        assert response.status_code == 422

    async def test_get_profit_loss_no_auth_returns_401(self, async_client):
        """GET /expenses/profit-loss without JWT is rejected with 401."""
        response = await async_client.get(
            f"{BASE}/profit-loss",
            params={"date_from": "2026-03-01", "date_to": "2026-03-31"},
        )
        assert response.status_code == 401
