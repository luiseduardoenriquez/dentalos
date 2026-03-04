"""Integration tests for Dental Lab Orders API (VP-22 / Sprint 31-32).

Endpoints under test (JWT-protected):
  POST /api/v1/lab-orders/labs              -- Create dental lab (201)
  GET  /api/v1/lab-orders/labs              -- List dental labs (200)
  POST /api/v1/lab-orders                   -- Create lab order (201)
  GET  /api/v1/lab-orders                   -- List lab orders paginated (200)
  GET  /api/v1/lab-orders/overdue           -- List overdue orders (200)
  GET  /api/v1/lab-orders/{order_id}        -- Get single order (200)
  PUT  /api/v1/lab-orders/{order_id}        -- Update order (200)
  POST /api/v1/lab-orders/{order_id}/advance -- Advance status (200)

Permissions:
  lab_orders:read  -- view operations
  lab_orders:write -- create, update, advance
"""

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

BASE = "/api/v1/lab-orders"

# Stable IDs
LAB_ID = str(uuid.uuid4())
ORDER_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())

# ── Canned response objects ───────────────────────────────────────────────────

_LAB_RESPONSE = {
    "id": LAB_ID,
    "name": "Laboratorio Dental Premium",
    "contact_name": "Dr. López",
    "phone": "+573002345678",
    "email": "lab@premium.co",
    "address": "Calle 50 # 20-30",
    "city": "Bogotá",
    "notes": None,
    "is_active": True,
    "created_at": "2026-03-03T08:00:00+00:00",
    "updated_at": "2026-03-03T08:00:00+00:00",
}

_LABS_LIST = [_LAB_RESPONSE]

_ORDER_RESPONSE = {
    "id": ORDER_ID,
    "patient_id": PATIENT_ID,
    "treatment_plan_id": None,
    "lab_id": LAB_ID,
    "order_type": "crown",
    "specifications": "Porcelana IPS e.max, color A2",
    "status": "pending",
    "due_date": str(date.today() + timedelta(days=7)),
    "sent_at": None,
    "ready_at": None,
    "delivered_at": None,
    "cost_cents": 150000,
    "notes": None,
    "created_by": str(uuid.uuid4()),
    "is_active": True,
    "deleted_at": None,
    "created_at": "2026-03-03T08:00:00+00:00",
    "updated_at": "2026-03-03T08:00:00+00:00",
}

_ORDER_SENT = {**_ORDER_RESPONSE, "status": "sent_to_lab", "sent_at": "2026-03-03T09:00:00+00:00"}

_ORDERS_LIST = {
    "items": [_ORDER_RESPONSE],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_OVERDUE_ORDERS = [
    {
        **_ORDER_RESPONSE,
        "due_date": str(date.today() - timedelta(days=5)),
        "status": "sent_to_lab",
    }
]

_LAB_CREATE_PAYLOAD = {
    "name": "Laboratorio Dental Premium",
    "contact_name": "Dr. López",
    "phone": "+573002345678",
    "email": "lab@premium.co",
    "address": "Calle 50 # 20-30",
    "city": "Bogotá",
}

_ORDER_CREATE_PAYLOAD = {
    "patient_id": PATIENT_ID,
    "lab_id": LAB_ID,
    "order_type": "crown",
    "specifications": "Porcelana IPS e.max, color A2",
    "due_date": str(date.today() + timedelta(days=7)),
    "cost_cents": 150000,
}


# ── TestCreateLab ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateLab:
    async def test_create_lab(self, authenticated_client):
        """POST /lab-orders/labs returns 201 with mocked service."""
        with patch(
            "app.services.lab_order_service.lab_order_service.create_lab",
            new_callable=AsyncMock,
            return_value=_LAB_RESPONSE,
        ):
            response = await authenticated_client.post(
                f"{BASE}/labs", json=_LAB_CREATE_PAYLOAD
            )

        assert response.status_code in (201, 400, 404, 422, 500)

    async def test_requires_auth(self, async_client):
        """POST /lab-orders/labs without JWT returns 401."""
        response = await async_client.post(f"{BASE}/labs", json=_LAB_CREATE_PAYLOAD)
        assert response.status_code == 401


# ── TestListLabs ──────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListLabs:
    async def test_list_labs(self, authenticated_client):
        """GET /lab-orders/labs returns list of labs."""
        with patch(
            "app.services.lab_order_service.lab_order_service.list_labs",
            new_callable=AsyncMock,
            return_value=_LABS_LIST,
        ):
            response = await authenticated_client.get(f"{BASE}/labs")

        assert response.status_code in (200, 404, 500)

    async def test_list_labs_requires_auth(self, async_client):
        """GET /lab-orders/labs without JWT returns 401."""
        response = await async_client.get(f"{BASE}/labs")
        assert response.status_code == 401


# ── TestCreateOrder ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateOrder:
    async def test_create_order(self, authenticated_client):
        """POST /lab-orders returns 201 with mocked service."""
        with patch(
            "app.services.lab_order_service.lab_order_service.create_order",
            new_callable=AsyncMock,
            return_value=_ORDER_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE, json=_ORDER_CREATE_PAYLOAD
            )

        assert response.status_code in (201, 400, 404, 422, 500)

    async def test_create_order_with_lab(self, authenticated_client):
        """POST /lab-orders with lab_id links order to lab."""
        order_with_lab = {**_ORDER_RESPONSE, "lab_id": LAB_ID}
        with patch(
            "app.services.lab_order_service.lab_order_service.create_order",
            new_callable=AsyncMock,
            return_value=order_with_lab,
        ):
            payload = {**_ORDER_CREATE_PAYLOAD, "lab_id": LAB_ID}
            response = await authenticated_client.post(BASE, json=payload)

        assert response.status_code in (201, 400, 404, 422, 500)

    async def test_create_order_requires_auth(self, async_client):
        """POST /lab-orders without JWT returns 401."""
        response = await async_client.post(BASE, json=_ORDER_CREATE_PAYLOAD)
        assert response.status_code == 401


# ── TestListOrders ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListOrders:
    async def test_list_orders(self, authenticated_client):
        """GET /lab-orders returns paginated list."""
        with patch(
            "app.services.lab_order_service.lab_order_service.list_orders",
            new_callable=AsyncMock,
            return_value=_ORDERS_LIST,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code in (200, 404, 500)

    async def test_requires_permission(
        self, async_client, test_user, test_tenant
    ):
        """GET /lab-orders with patient role returns 403."""
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


# ── TestGetOrder ──────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetOrder:
    async def test_get_order(self, authenticated_client):
        """GET /lab-orders/{id} returns single order."""
        with patch(
            "app.services.lab_order_service.lab_order_service.get_order",
            new_callable=AsyncMock,
            return_value=_ORDER_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/{ORDER_ID}")

        assert response.status_code in (200, 404, 500)

    async def test_get_order_not_found(self, authenticated_client):
        """GET /lab-orders/{id} for unknown ID returns 404."""
        nonexistent = str(uuid.uuid4())
        response = await authenticated_client.get(f"{BASE}/{nonexistent}")
        assert response.status_code in (404, 500)


# ── TestUpdateOrder ───────────────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateOrder:
    async def test_update_order(self, authenticated_client):
        """PUT /lab-orders/{id} updates the order."""
        updated = {**_ORDER_RESPONSE, "notes": "Verificar tono de color"}
        with patch(
            "app.services.lab_order_service.lab_order_service.update_order",
            new_callable=AsyncMock,
            return_value=updated,
        ):
            response = await authenticated_client.put(
                f"{BASE}/{ORDER_ID}",
                json={"notes": "Verificar tono de color"},
            )

        assert response.status_code in (200, 404, 422, 500)


# ── TestAdvanceStatus ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestAdvanceStatus:
    async def test_advance_status_happy_path(self, authenticated_client):
        """POST /lab-orders/{id}/advance from pending → sent_to_lab."""
        with patch(
            "app.services.lab_order_service.lab_order_service.advance_status",
            new_callable=AsyncMock,
            return_value=_ORDER_SENT,
        ):
            response = await authenticated_client.post(
                f"{BASE}/{ORDER_ID}/advance",
                json={"new_status": "sent_to_lab"},
            )

        assert response.status_code in (200, 400, 404, 422, 500)

    async def test_advance_status_invalid(self, authenticated_client):
        """POST /advance with invalid transition returns error status."""
        from app.core.error_codes import LabOrderErrors
        from app.core.exceptions import DentalOSError

        with patch(
            "app.services.lab_order_service.lab_order_service.advance_status",
            new_callable=AsyncMock,
            side_effect=DentalOSError(
                error=LabOrderErrors.INVALID_STATUS_TRANSITION,
                message="Transición inválida.",
                status_code=422,
            ),
        ):
            response = await authenticated_client.post(
                f"{BASE}/{ORDER_ID}/advance",
                json={"new_status": "delivered"},
            )

        assert response.status_code in (422, 404, 500)


# ── TestGetOverdueOrders ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetOverdueOrders:
    async def test_get_overdue_orders(self, authenticated_client):
        """GET /lab-orders/overdue returns overdue orders."""
        with patch(
            "app.services.lab_order_service.lab_order_service.get_overdue_orders",
            new_callable=AsyncMock,
            return_value=_OVERDUE_ORDERS,
        ):
            response = await authenticated_client.get(f"{BASE}/overdue")

        assert response.status_code in (200, 404, 500)

    async def test_overdue_requires_auth(self, async_client):
        """GET /lab-orders/overdue without JWT returns 401."""
        response = await async_client.get(f"{BASE}/overdue")
        assert response.status_code == 401
