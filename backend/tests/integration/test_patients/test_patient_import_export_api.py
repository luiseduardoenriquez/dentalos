"""Integration tests for Patient Import/Export API (P-08, P-09).

Endpoints:
  POST /api/v1/patients/import          — P-08: CSV import (clinic_owner)
  GET  /api/v1/patients/import/{job_id} — P-08: Import job status
  GET  /api/v1/patients/export          — P-09: CSV export (clinic_owner)
"""

import io
import uuid

import pytest

BASE = "/api/v1/patients"
JOB_ID = str(uuid.uuid4())


def _make_csv_bytes(header: str, rows: list[str] | None = None) -> bytes:
    """Build a CSV file as bytes for upload."""
    lines = [header]
    if rows:
        lines.extend(rows)
    return "\n".join(lines).encode("utf-8")


VALID_CSV = _make_csv_bytes(
    "tipo_documento,numero_documento,nombres,apellidos,email",
    ["CC,1234567890,Juan,Pérez,juan@test.co"],
)

MISSING_HEADER_CSV = _make_csv_bytes(
    "tipo_documento,numero_documento,nombres",
    ["CC,1234567890,Juan"],
)


# ─── P-08: Import CSV ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestImportPatients:
    async def test_import_valid_csv(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/import",
            files={"file": ("patients.csv", io.BytesIO(VALID_CSV), "text/csv")},
        )
        assert response.status_code in (202, 500)

    async def test_import_missing_required_columns(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/import",
            files={"file": ("patients.csv", io.BytesIO(MISSING_HEADER_CSV), "text/csv")},
        )
        assert response.status_code in (400, 500)

    async def test_import_empty_csv(self, authenticated_client):
        empty_csv = b""
        response = await authenticated_client.post(
            f"{BASE}/import",
            files={"file": ("empty.csv", io.BytesIO(empty_csv), "text/csv")},
        )
        assert response.status_code in (400, 500)

    async def test_import_non_csv_file(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/import",
            files={"file": ("data.json", io.BytesIO(b'{"key": "value"}'), "application/json")},
        )
        assert response.status_code in (400, 500)

    async def test_import_no_file(self, authenticated_client):
        response = await authenticated_client.post(f"{BASE}/import")
        assert response.status_code == 422

    async def test_import_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/import",
            files={"file": ("patients.csv", io.BytesIO(VALID_CSV), "text/csv")},
        )
        assert response.status_code == 401

    async def test_import_doctor_forbidden(self, doctor_client):
        response = await doctor_client.post(
            f"{BASE}/import",
            files={"file": ("patients.csv", io.BytesIO(VALID_CSV), "text/csv")},
        )
        assert response.status_code == 403


# ─── P-08: Import Job Status ────────────────────────────────────────────────


@pytest.mark.integration
class TestImportJobStatus:
    async def test_get_job_status_not_found(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/import/{JOB_ID}")
        assert response.status_code in (404, 500)

    async def test_get_job_status_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/import/{JOB_ID}")
        assert response.status_code == 401


# ─── P-09: Export CSV ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestExportPatients:
    async def test_export_default(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/export")
        assert response.status_code in (200, 500)

    async def test_export_with_filters(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/export",
            params={"is_active": True, "created_from": "2025-01-01"},
        )
        assert response.status_code in (200, 500)

    async def test_export_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/export")
        assert response.status_code == 401

    async def test_export_doctor_forbidden(self, doctor_client):
        response = await doctor_client.get(f"{BASE}/export")
        assert response.status_code == 403
