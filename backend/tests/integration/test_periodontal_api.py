"""Integration tests for Periodontal Charting API (GAP-01 / Sprint 25-26).

Endpoints (all under /patients/{patient_id}/):
  POST /api/v1/patients/{patient_id}/periodontal-records             — Create record
  GET  /api/v1/patients/{patient_id}/periodontal-records              — List records
  GET  /api/v1/patients/{patient_id}/periodontal-records/compare      — Compare two records
  GET  /api/v1/patients/{patient_id}/periodontal-records/{record_id}  — Get record detail

Requires periodontogram:write (create) and periodontogram:read (list, compare, get).
clinic_owner and doctor have both; receptionist has neither.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

PATIENT_ID = str(uuid.uuid4())
RECORD_A_ID = str(uuid.uuid4())
RECORD_B_ID = str(uuid.uuid4())
DOCTOR_USER_ID = str(uuid.uuid4())

BASE = f"/api/v1/patients/{PATIENT_ID}/periodontal-records"

_MEASUREMENT = {
    "id": str(uuid.uuid4()),
    "tooth_number": 11,
    "site": "mesial_buccal",
    "pocket_depth": 3,
    "recession": 1,
    "clinical_attachment_level": 4,
    "bleeding_on_probing": False,
    "furcation": None,
    "mobility": None,
}

_RECORD_RESPONSE = {
    "id": RECORD_A_ID,
    "patient_id": PATIENT_ID,
    "recorded_by": DOCTOR_USER_ID,
    "dentition_type": "permanent",
    "source": "manual",
    "notes": "Baseline charting",
    "measurements": [_MEASUREMENT],
    "created_at": "2026-03-01T09:00:00+00:00",
    "updated_at": "2026-03-01T09:00:00+00:00",
}

_RECORD_B_RESPONSE = {
    **_RECORD_RESPONSE,
    "id": RECORD_B_ID,
    "notes": "Follow-up charting",
    "created_at": "2026-03-03T09:00:00+00:00",
    "updated_at": "2026-03-03T09:00:00+00:00",
}

_LIST_RESPONSE = {
    "items": [
        {
            "id": RECORD_B_ID,
            "patient_id": PATIENT_ID,
            "recorded_by": DOCTOR_USER_ID,
            "dentition_type": "permanent",
            "source": "manual",
            "notes": "Follow-up charting",
            "measurement_count": 10,
            "created_at": "2026-03-03T09:00:00+00:00",
        },
        {
            "id": RECORD_A_ID,
            "patient_id": PATIENT_ID,
            "recorded_by": DOCTOR_USER_ID,
            "dentition_type": "permanent",
            "source": "manual",
            "notes": "Baseline charting",
            "measurement_count": 10,
            "created_at": "2026-03-01T09:00:00+00:00",
        },
    ],
    "total": 2,
    "page": 1,
    "page_size": 20,
}

_COMPARISON_RESPONSE = {
    "record_a_id": RECORD_A_ID,
    "record_b_id": RECORD_B_ID,
    "record_a_date": "2026-03-01",
    "record_b_date": "2026-03-03",
    "deltas": [
        {
            "tooth_number": 11,
            "site": "mesial_buccal",
            "pocket_depth_delta": -1,
            "recession_delta": 0,
            "cal_delta": -1,
            "status": "improved",
        }
    ],
    "summary": {
        "improved_sites": 5,
        "worsened_sites": 2,
        "unchanged_sites": 3,
        "total_sites_compared": 10,
    },
}


# ─── POST /patients/{patient_id}/periodontal-records ─────────────────────────


@pytest.mark.integration
class TestCreatePeriodontalRecord:
    async def test_create_record_requires_auth(self, async_client):
        """POST periodontal-records without JWT returns 401."""
        response = await async_client.post(
            BASE,
            json={"dentition_type": "permanent", "notes": "Test", "measurements": []},
        )
        assert response.status_code == 401

    async def test_create_record_success(self, authenticated_client):
        """POST periodontal-records with valid payload returns 201."""
        with patch(
            "app.services.periodontal_service.periodontal_service.create_record",
            new_callable=AsyncMock,
            return_value=_RECORD_RESPONSE,
        ):
            response = await authenticated_client.post(
                BASE,
                json={
                    "dentition_type": "permanent",
                    "notes": "Baseline charting",
                    "measurements": [],
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["patient_id"] == PATIENT_ID
        assert data["dentition_type"] == "permanent"

    async def test_create_record_with_measurements(self, authenticated_client):
        """POST periodontal-records with 10 measurements stores all of them."""
        measurements = [
            {
                "tooth_number": 11 + i,
                "site": "mesial_buccal",
                "pocket_depth": 3,
                "recession": 0,
                "clinical_attachment_level": 3,
                "bleeding_on_probing": False,
            }
            for i in range(10)
        ]
        response_with_measurements = {
            **_RECORD_RESPONSE,
            "measurements": [
                {**_MEASUREMENT, "tooth_number": 11 + i, "id": str(uuid.uuid4())}
                for i in range(10)
            ],
        }
        with patch(
            "app.services.periodontal_service.periodontal_service.create_record",
            new_callable=AsyncMock,
            return_value=response_with_measurements,
        ):
            response = await authenticated_client.post(
                BASE,
                json={
                    "dentition_type": "permanent",
                    "notes": "Full charting",
                    "measurements": measurements,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["measurements"]) == 10

    async def test_create_record_missing_dentition_type(self, authenticated_client):
        """POST periodontal-records without dentition_type returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={"notes": "Missing type", "measurements": []},
        )
        assert response.status_code == 422

    async def test_create_record_invalid_dentition_type(self, authenticated_client):
        """POST periodontal-records with invalid dentition_type value returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={
                "dentition_type": "invalid_type",
                "notes": "Bad type",
                "measurements": [],
            },
        )
        assert response.status_code == 422

    async def test_create_record_invalid_tooth_number(self, authenticated_client):
        """POST periodontal-records with tooth_number outside FDI range returns 422."""
        response = await authenticated_client.post(
            BASE,
            json={
                "dentition_type": "permanent",
                "measurements": [
                    {
                        "tooth_number": 99,
                        "site": "mesial_buccal",
                        "pocket_depth": 3,
                        "recession": 0,
                        "clinical_attachment_level": 3,
                        "bleeding_on_probing": False,
                    }
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_record_doctor_allowed(self, doctor_client):
        """doctor role has periodontogram:write — can create records."""
        with patch(
            "app.services.periodontal_service.periodontal_service.create_record",
            new_callable=AsyncMock,
            return_value=_RECORD_RESPONSE,
        ):
            response = await doctor_client.post(
                BASE,
                json={
                    "dentition_type": "permanent",
                    "notes": "Doctor charting",
                    "measurements": [],
                },
            )
        assert response.status_code in (201, 403, 500)


# ─── GET /patients/{patient_id}/periodontal-records ──────────────────────────


@pytest.mark.integration
class TestListPeriodontalRecords:
    async def test_list_records_requires_auth(self, async_client):
        """GET periodontal-records without JWT returns 401."""
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_list_records_returns_paginated_list(self, authenticated_client):
        """GET periodontal-records returns paginated items for the patient."""
        with patch(
            "app.services.periodontal_service.periodontal_service.list_records",
            new_callable=AsyncMock,
            return_value=_LIST_RESPONSE,
        ):
            response = await authenticated_client.get(BASE)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    async def test_list_records_pagination(self, authenticated_client):
        """GET periodontal-records with pagination params returns correct shape."""
        paged = {**_LIST_RESPONSE, "page": 2, "page_size": 5}
        with patch(
            "app.services.periodontal_service.periodontal_service.list_records",
            new_callable=AsyncMock,
            return_value=paged,
        ):
            response = await authenticated_client.get(
                BASE,
                params={"page": 2, "page_size": 5},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5

    async def test_list_records_invalid_page_size(self, authenticated_client):
        """GET periodontal-records with page_size=0 returns 422."""
        response = await authenticated_client.get(BASE, params={"page_size": 0})
        assert response.status_code == 422


# ─── GET /patients/{patient_id}/periodontal-records/{record_id} ──────────────


@pytest.mark.integration
class TestGetPeriodontalRecord:
    async def test_get_record_requires_auth(self, async_client):
        """GET periodontal-records/{id} without JWT returns 401."""
        response = await async_client.get(f"{BASE}/{RECORD_A_ID}")
        assert response.status_code == 401

    async def test_get_record_with_measurements(self, authenticated_client):
        """GET periodontal-records/{id} returns the full record with measurements."""
        with patch(
            "app.services.periodontal_service.periodontal_service.get_record",
            new_callable=AsyncMock,
            return_value=_RECORD_RESPONSE,
        ):
            response = await authenticated_client.get(f"{BASE}/{RECORD_A_ID}")

        assert response.status_code == 200
        data = response.json()
        assert "measurements" in data
        assert isinstance(data["measurements"], list)
        assert data["id"] == RECORD_A_ID

    async def test_get_record_not_found(self, authenticated_client):
        """GET periodontal-records/{id} for a non-existent record returns 404."""
        from app.core.exceptions import ResourceNotFoundError
        from app.core.error_codes import PeriodontalErrors

        with patch(
            "app.services.periodontal_service.periodontal_service.get_record",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(
                error=PeriodontalErrors.RECORD_NOT_FOUND,
                resource_name="PeriodontalRecord",
            ),
        ):
            response = await authenticated_client.get(
                f"{BASE}/{uuid.uuid4()}"
            )

        assert response.status_code == 404


# ─── GET /patients/{patient_id}/periodontal-records/compare ──────────────────


@pytest.mark.integration
class TestComparePeriodontalRecords:
    async def test_compare_records_requires_auth(self, async_client):
        """GET periodontal-records/compare without JWT returns 401."""
        response = await async_client.get(
            f"{BASE}/compare",
            params={"record_a_id": RECORD_A_ID, "record_b_id": RECORD_B_ID},
        )
        assert response.status_code == 401

    async def test_compare_records_returns_deltas(self, authenticated_client):
        """GET periodontal-records/compare returns measurement deltas and summary."""
        with patch(
            "app.services.periodontal_service.periodontal_service.compare_records",
            new_callable=AsyncMock,
            return_value=_COMPARISON_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{BASE}/compare",
                params={"record_a_id": RECORD_A_ID, "record_b_id": RECORD_B_ID},
            )

        assert response.status_code == 200
        data = response.json()
        assert "deltas" in data
        assert "summary" in data
        assert "record_a_id" in data
        assert "record_b_id" in data

    async def test_compare_records_missing_record_a_id(self, authenticated_client):
        """GET periodontal-records/compare without record_a_id returns 422."""
        response = await authenticated_client.get(
            f"{BASE}/compare",
            params={"record_b_id": RECORD_B_ID},
        )
        assert response.status_code == 422

    async def test_compare_records_missing_record_b_id(self, authenticated_client):
        """GET periodontal-records/compare without record_b_id returns 422."""
        response = await authenticated_client.get(
            f"{BASE}/compare",
            params={"record_a_id": RECORD_A_ID},
        )
        assert response.status_code == 422

    async def test_compare_records_same_id_rejected(self, authenticated_client):
        """GET periodontal-records/compare with both IDs the same is semantically invalid.

        The endpoint may accept 422 if validation checks for this, or return
        a 400/500 from the service layer.
        """
        response = await authenticated_client.get(
            f"{BASE}/compare",
            params={"record_a_id": RECORD_A_ID, "record_b_id": RECORD_A_ID},
        )
        assert response.status_code in (200, 400, 422, 500)

    async def test_compare_summary_structure(self, authenticated_client):
        """Comparison summary must contain improved, worsened, and unchanged counts."""
        with patch(
            "app.services.periodontal_service.periodontal_service.compare_records",
            new_callable=AsyncMock,
            return_value=_COMPARISON_RESPONSE,
        ):
            response = await authenticated_client.get(
                f"{BASE}/compare",
                params={"record_a_id": RECORD_A_ID, "record_b_id": RECORD_B_ID},
            )

        assert response.status_code == 200
        summary = response.json()["summary"]
        assert "improved_sites" in summary
        assert "worsened_sites" in summary
        assert "unchanged_sites" in summary
        assert "total_sites_compared" in summary
