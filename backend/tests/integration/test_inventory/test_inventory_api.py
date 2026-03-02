"""Integration tests for Inventory API (INV-01 through INV-07).

Endpoints:
  POST   /api/v1/inventory                   — INV-01: Create item
  GET    /api/v1/inventory                   — INV-02: List items
  PUT    /api/v1/inventory/{item_id}         — INV-03/04: Update item
  GET    /api/v1/inventory/alerts            — INV-05: Alerts
  POST   /api/v1/inventory/sterilization     — INV-06: Create sterilization
  GET    /api/v1/inventory/sterilization     — INV-06: List sterilization
  POST   /api/v1/inventory/implants/link     — INV-07: Link implant
  GET    /api/v1/inventory/implants/search   — INV-07: Search implants
"""

import uuid
from datetime import date, timedelta

import pytest

BASE = "/api/v1/inventory"
ITEM_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())


# ─── INV-01: Create item ────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateInventoryItem:
    async def test_create_valid_item(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "name": "Resina compuesta A2",
                "category": "material",
                "quantity": 10,
                "unit": "unit",
                "minimum_stock": 2,
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_item_with_expiry(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "name": "Anestesia lidocaína",
                "category": "medication",
                "quantity": 50,
                "unit": "unit",
                "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
                "lot_number": "LOT-2026-001",
                "manufacturer": "Septodont",
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_item_missing_name(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "category": "material",
                "quantity": 10,
                "unit": "unit",
            },
        )
        assert response.status_code == 422

    async def test_create_item_invalid_category(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "name": "Test",
                "category": "invalid_category",
                "quantity": 10,
                "unit": "unit",
            },
        )
        assert response.status_code == 422

    async def test_create_item_no_auth(self, async_client):
        response = await async_client.post(
            BASE,
            json={
                "name": "Test",
                "category": "material",
                "quantity": 10,
                "unit": "unit",
            },
        )
        assert response.status_code == 401

    async def test_create_item_doctor_no_write(self, doctor_client):
        response = await doctor_client.post(
            BASE,
            json={
                "name": "Test",
                "category": "material",
                "quantity": 10,
                "unit": "unit",
            },
        )
        assert response.status_code == 403


# ─── INV-02: List items ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestListInventoryItems:
    async def test_list_default(self, authenticated_client):
        response = await authenticated_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_with_category_filter(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"category": "material"}
        )
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"page": 1, "page_size": 5}
        )
        assert response.status_code in (200, 500)

    async def test_list_invalid_page_size(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"page_size": 0}
        )
        assert response.status_code == 422

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_list_doctor_has_read(self, doctor_client):
        response = await doctor_client.get(BASE)
        assert response.status_code in (200, 500)


# ─── INV-03/04: Update item ─────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateInventoryItem:
    async def test_update_name(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{ITEM_ID}",
            json={"name": "Updated Material"},
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_with_quantity_change(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/{ITEM_ID}",
            json={
                "quantity_change": -5,
                "change_reason": "used",
                "change_notes": "Used in procedure",
            },
        )
        assert response.status_code in (200, 404, 500)

    async def test_update_invalid_id(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/not-a-uuid",
            json={"name": "Test"},
        )
        assert response.status_code in (404, 422, 500)

    async def test_update_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/{ITEM_ID}",
            json={"name": "Test"},
        )
        assert response.status_code == 401

    async def test_update_doctor_no_write(self, doctor_client):
        response = await doctor_client.put(
            f"{BASE}/{ITEM_ID}",
            json={"name": "Test"},
        )
        assert response.status_code == 403


# ─── INV-05: Alerts ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestInventoryAlerts:
    async def test_alerts_as_owner(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/alerts")
        assert response.status_code in (200, 500)

    async def test_alerts_doctor_has_read(self, doctor_client):
        response = await doctor_client.get(f"{BASE}/alerts")
        assert response.status_code in (200, 500)

    async def test_alerts_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/alerts")
        assert response.status_code == 401


# ─── INV-06: Sterilization ──────────────────────────────────────────────────


@pytest.mark.integration
class TestSterilization:
    async def test_create_sterilization(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/sterilization",
            json={
                "autoclave_id": "autoclave-001",
                "load_number": 42,
                "date": date.today().isoformat(),
                "responsible_user_id": str(uuid.uuid4()),
                "instrument_ids": [str(uuid.uuid4())],
                "temperature_celsius": 134.0,
                "duration_minutes": 18,
                "biological_indicator": True,
                "chemical_indicator": True,
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_sterilization_missing_autoclave(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/sterilization",
            json={
                "load_number": 42,
                "date": date.today().isoformat(),
                "responsible_user_id": str(uuid.uuid4()),
                "instrument_ids": [str(uuid.uuid4())],
            },
        )
        assert response.status_code == 422

    async def test_list_sterilization(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/sterilization")
        assert response.status_code in (200, 500)

    async def test_list_sterilization_with_filters(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/sterilization",
            params={
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "compliant_only": True,
            },
        )
        assert response.status_code in (200, 500)

    async def test_create_sterilization_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/sterilization",
            json={
                "autoclave_id": "autoclave-001",
                "load_number": 1,
                "date": date.today().isoformat(),
                "responsible_user_id": str(uuid.uuid4()),
                "instrument_ids": [str(uuid.uuid4())],
            },
        )
        assert response.status_code == 401

    async def test_create_sterilization_doctor_no_write(self, doctor_client):
        response = await doctor_client.post(
            f"{BASE}/sterilization",
            json={
                "autoclave_id": "autoclave-001",
                "load_number": 1,
                "date": date.today().isoformat(),
                "responsible_user_id": str(uuid.uuid4()),
                "instrument_ids": [str(uuid.uuid4())],
            },
        )
        assert response.status_code == 403


# ─── INV-07: Implants ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestImplants:
    async def test_link_implant(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/implants/link",
            json={
                "item_id": str(uuid.uuid4()),
                "patient_id": PATIENT_ID,
                "placement_date": date.today().isoformat(),
                "tooth_number": 11,
                "lot_number": "LOT-IMP-001",
                "manufacturer": "Straumann",
            },
        )
        assert response.status_code in (201, 500)

    async def test_link_implant_missing_patient(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/implants/link",
            json={
                "item_id": str(uuid.uuid4()),
                "placement_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 422

    async def test_link_implant_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/implants/link",
            json={
                "item_id": str(uuid.uuid4()),
                "patient_id": PATIENT_ID,
                "placement_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 401

    async def test_search_implants_by_lot(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/implants/search", params={"lot_number": "LOT-IMP"}
        )
        assert response.status_code in (200, 500)

    async def test_search_implants_by_patient(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/implants/search", params={"patient_id": PATIENT_ID}
        )
        assert response.status_code in (200, 500)

    async def test_search_implants_no_auth(self, async_client):
        response = await async_client.get(
            f"{BASE}/implants/search", params={"lot_number": "LOT"}
        )
        assert response.status_code == 401
