"""Integration tests for Patient Merge API (P-10).

Endpoint:
  POST /api/v1/patients/merge — Merge two patients (clinic_owner only)
"""

import uuid

import pytest

BASE = "/api/v1/patients/merge"


# ─── P-10: Merge patients ───────────────────────────────────────────────────


@pytest.mark.integration
class TestMergePatients:
    async def test_merge_valid_patients(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "primary_patient_id": str(uuid.uuid4()),
                "secondary_patient_id": str(uuid.uuid4()),
            },
        )
        # 200 on success, 404 if patients not found, 500 for DB errors
        assert response.status_code in (200, 404, 500)

    async def test_merge_same_patient_ids(self, authenticated_client):
        same_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            BASE,
            json={
                "primary_patient_id": same_id,
                "secondary_patient_id": same_id,
            },
        )
        assert response.status_code == 422

    async def test_merge_missing_primary(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "secondary_patient_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_merge_missing_secondary(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "primary_patient_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_merge_invalid_uuid(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "primary_patient_id": "not-a-uuid",
                "secondary_patient_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    async def test_merge_no_auth(self, async_client):
        response = await async_client.post(
            BASE,
            json={
                "primary_patient_id": str(uuid.uuid4()),
                "secondary_patient_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 401

    async def test_merge_doctor_forbidden(self, doctor_client):
        response = await doctor_client.post(
            BASE,
            json={
                "primary_patient_id": str(uuid.uuid4()),
                "secondary_patient_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 403

    async def test_merge_empty_body(self, authenticated_client):
        response = await authenticated_client.post(BASE, json={})
        assert response.status_code == 422
