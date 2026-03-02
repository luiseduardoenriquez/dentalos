"""Unit tests for the EPSVerificationService class.

Tests cover:
  - verify_patient: returns dict with affiliation_status, persists a record
  - verify_patient: calls set_cached with the correct 24h TTL
  - get_latest_verification (cache hit): returns from Redis without hitting DB
  - get_latest_verification (cache miss, DB hit): returns from DB, warms cache
  - auto_verify_on_creation: swallows all exceptions, never raises

Mock strategy:
  - DB (AsyncSession) is fully mocked with AsyncMock.
  - ADRES adapter is patched via unittest.mock.patch.
  - Redis (get_cached / set_cached) is patched at the module level.
  - EPSVerification ORM constructor is NOT called — we inject a mock record.

PHI never appears in test assertions (document numbers are never asserted).
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.eps_verification_service import EPSVerificationService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_patient(**overrides) -> MagicMock:
    """Build a minimal Patient-like mock."""
    p = MagicMock()
    p.id = overrides.get("id", uuid.uuid4())
    p.document_type = overrides.get("document_type", "CC")
    p.document_number = overrides.get("document_number", "10000000")  # ends in 0 → activo
    p.is_active = True
    return p


def _make_adres_result(**overrides) -> MagicMock:
    """Build a minimal ADRES verification result mock."""
    r = MagicMock()
    r.eps_name = overrides.get("eps_name", "EPS Sura")
    r.eps_code = overrides.get("eps_code", "EPS010")
    r.affiliation_status = overrides.get("affiliation_status", "activo")
    r.regime = overrides.get("regime", "contributivo")
    r.copay_category = overrides.get("copay_category", "B")
    r.verification_date = overrides.get("verification_date", datetime.now(UTC))
    r.raw_response = overrides.get("raw_response", {"mock": True})
    return r


def _make_eps_record(**overrides) -> MagicMock:
    """Build a minimal EPSVerification ORM record mock."""
    rec = MagicMock()
    rec.id = overrides.get("id", uuid.uuid4())
    rec.patient_id = overrides.get("patient_id", uuid.uuid4())
    rec.verification_date = overrides.get("verification_date", datetime.now(UTC))
    rec.eps_name = overrides.get("eps_name", "EPS Sura")
    rec.eps_code = overrides.get("eps_code", "EPS010")
    rec.affiliation_status = overrides.get("affiliation_status", "activo")
    rec.regime = overrides.get("regime", "contributivo")
    rec.copay_category = overrides.get("copay_category", "B")
    rec.created_at = overrides.get("created_at", datetime.now(UTC))
    return rec


def _build_expected_dict(record: MagicMock) -> dict:
    """Build the expected response dict from a mock record (mirrors _to_dict logic)."""
    return {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "verification_date": record.verification_date,
        "eps_name": record.eps_name,
        "eps_code": record.eps_code,
        "affiliation_status": record.affiliation_status,
        "regime": record.regime,
        "copay_category": record.copay_category,
        "created_at": record.created_at,
    }


# ── verify_patient ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestVerifyPatient:
    async def test_verify_patient_returns_dict_with_affiliation_status(self):
        """verify_patient should return a dict containing 'affiliation_status'."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        adres_result = _make_adres_result(affiliation_status="activo")
        eps_record = _make_eps_record(
            patient_id=patient.id,
            affiliation_status="activo",
        )

        # DB: _get_patient query returns the patient
        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient
        db.execute = AsyncMock(return_value=patient_db_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with (
            patch(
                "app.services.eps_verification_service._get_adapter"
            ) as mock_get_adapter,
            patch(
                "app.services.eps_verification_service.set_cached",
                new_callable=AsyncMock,
            ),
            # Patch the EPSVerification constructor so we control what gets added
            patch(
                "app.services.eps_verification_service.EPSVerification",
                return_value=eps_record,
            ),
        ):
            mock_adapter = AsyncMock()
            mock_adapter.verify_affiliation = AsyncMock(return_value=adres_result)
            mock_get_adapter.return_value = mock_adapter

            result = await service.verify_patient(
                db=db,
                patient_id=patient.id,
                tenant_id=str(uuid.uuid4()),
            )

        assert "affiliation_status" in result
        assert result["affiliation_status"] == "activo"

    async def test_verify_patient_persists_record(self):
        """db.add must be called once to persist the EPSVerification record."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        adres_result = _make_adres_result()
        eps_record = _make_eps_record(patient_id=patient.id)

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient
        db.execute = AsyncMock(return_value=patient_db_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with (
            patch("app.services.eps_verification_service._get_adapter") as mock_get_adapter,
            patch("app.services.eps_verification_service.set_cached", new_callable=AsyncMock),
            patch("app.services.eps_verification_service.EPSVerification", return_value=eps_record),
        ):
            mock_adapter = AsyncMock()
            mock_adapter.verify_affiliation = AsyncMock(return_value=adres_result)
            mock_get_adapter.return_value = mock_adapter

            await service.verify_patient(
                db=db,
                patient_id=patient.id,
                tenant_id=str(uuid.uuid4()),
            )

        db.add.assert_called_once_with(eps_record)

    async def test_verify_patient_raises_404_when_patient_not_found(self):
        """verify_patient must raise ResourceNotFoundError when patient is absent."""
        service = EPSVerificationService()
        db = AsyncMock()

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=patient_db_result)

        with pytest.raises(ResourceNotFoundError):
            await service.verify_patient(
                db=db,
                patient_id=uuid.uuid4(),
                tenant_id=str(uuid.uuid4()),
            )


@pytest.mark.unit
class TestVerifyPatientCachesResult:
    async def test_set_cached_called_with_24h_ttl(self):
        """verify_patient must call set_cached with a 24-hour TTL (86400 seconds)."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        adres_result = _make_adres_result()
        eps_record = _make_eps_record(patient_id=patient.id)

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient
        db.execute = AsyncMock(return_value=patient_db_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with (
            patch("app.services.eps_verification_service._get_adapter") as mock_get_adapter,
            patch(
                "app.services.eps_verification_service.set_cached",
                new_callable=AsyncMock,
            ) as mock_set_cached,
            patch("app.services.eps_verification_service.EPSVerification", return_value=eps_record),
        ):
            mock_adapter = AsyncMock()
            mock_adapter.verify_affiliation = AsyncMock(return_value=adres_result)
            mock_get_adapter.return_value = mock_adapter

            await service.verify_patient(
                db=db,
                patient_id=patient.id,
                tenant_id=str(uuid.uuid4()),
            )

        mock_set_cached.assert_called_once()
        # Third positional arg is ttl_seconds (or kwarg)
        _args, kwargs = mock_set_cached.call_args
        ttl = kwargs.get("ttl_seconds") or (_args[2] if len(_args) > 2 else None)
        assert ttl == 86_400

    async def test_set_cached_not_called_when_no_tenant_id(self):
        """set_cached must NOT be called if tenant_id is None (no cache key can be built)."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        adres_result = _make_adres_result()
        eps_record = _make_eps_record(patient_id=patient.id)

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient
        db.execute = AsyncMock(return_value=patient_db_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        with (
            patch("app.services.eps_verification_service._get_adapter") as mock_get_adapter,
            patch(
                "app.services.eps_verification_service.set_cached",
                new_callable=AsyncMock,
            ) as mock_set_cached,
            patch("app.services.eps_verification_service.EPSVerification", return_value=eps_record),
        ):
            mock_adapter = AsyncMock()
            mock_adapter.verify_affiliation = AsyncMock(return_value=adres_result)
            mock_get_adapter.return_value = mock_adapter

            await service.verify_patient(
                db=db,
                patient_id=patient.id,
                tenant_id=None,  # no tenant_id → cache must be skipped
            )

        mock_set_cached.assert_not_called()


# ── get_latest_verification ───────────────────────────────────────────────────


@pytest.mark.unit
class TestGetLatestVerificationCacheHit:
    async def test_cache_hit_returns_cached_dict(self):
        """When Redis has a cached result, it should be returned without querying DB."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        tenant_id = str(uuid.uuid4())

        cached_value = {
            "id": str(uuid.uuid4()),
            "patient_id": str(patient.id),
            "affiliation_status": "activo",
            "eps_name": "EPS Sura",
            "eps_code": "EPS010",
            "regime": "contributivo",
            "copay_category": "B",
            "verification_date": "2026-03-01T10:00:00+00:00",
            "created_at": "2026-03-01T10:00:00+00:00",
        }

        # DB: _get_patient must still succeed (patient exists check)
        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient
        db.execute = AsyncMock(return_value=patient_db_result)

        with (
            patch(
                "app.services.eps_verification_service.get_cached",
                new_callable=AsyncMock,
                return_value=cached_value,
            ),
            patch(
                "app.services.eps_verification_service.set_cached",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.get_latest_verification(
                db=db,
                patient_id=patient.id,
                tenant_id=tenant_id,
            )

        assert result == cached_value

    async def test_cache_hit_does_not_query_verifications_table(self):
        """On cache hit, db.execute must only be called once (for the patient check)."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        tenant_id = str(uuid.uuid4())

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient
        db.execute = AsyncMock(return_value=patient_db_result)

        with (
            patch(
                "app.services.eps_verification_service.get_cached",
                new_callable=AsyncMock,
                return_value={"affiliation_status": "activo"},
            ),
            patch("app.services.eps_verification_service.set_cached", new_callable=AsyncMock),
        ):
            await service.get_latest_verification(
                db=db,
                patient_id=patient.id,
                tenant_id=tenant_id,
            )

        # db.execute called once (patient lookup), NOT for the verification record
        db.execute.assert_called_once()


@pytest.mark.unit
class TestGetLatestVerificationCacheMissDbHit:
    async def test_cache_miss_falls_through_to_db(self):
        """On cache miss, the most recent EPSVerification record from DB is returned."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        eps_record = _make_eps_record(patient_id=patient.id)
        tenant_id = str(uuid.uuid4())

        # First db.execute: patient lookup
        # Second db.execute: verification record lookup
        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient

        eps_db_result = MagicMock()
        eps_db_result.scalar_one_or_none.return_value = eps_record

        db.execute = AsyncMock(side_effect=[patient_db_result, eps_db_result])

        with (
            patch(
                "app.services.eps_verification_service.get_cached",
                new_callable=AsyncMock,
                return_value=None,  # cache miss
            ),
            patch(
                "app.services.eps_verification_service.set_cached",
                new_callable=AsyncMock,
            ) as mock_set_cached,
        ):
            result = await service.get_latest_verification(
                db=db,
                patient_id=patient.id,
                tenant_id=tenant_id,
            )

        assert result["affiliation_status"] == eps_record.affiliation_status

    async def test_cache_miss_warms_cache_after_db_hit(self):
        """After fetching from DB, set_cached must be called to warm Redis."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        eps_record = _make_eps_record(patient_id=patient.id)
        tenant_id = str(uuid.uuid4())

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient

        eps_db_result = MagicMock()
        eps_db_result.scalar_one_or_none.return_value = eps_record

        db.execute = AsyncMock(side_effect=[patient_db_result, eps_db_result])

        with (
            patch(
                "app.services.eps_verification_service.get_cached",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.eps_verification_service.set_cached",
                new_callable=AsyncMock,
            ) as mock_set_cached,
        ):
            await service.get_latest_verification(
                db=db,
                patient_id=patient.id,
                tenant_id=tenant_id,
            )

        mock_set_cached.assert_called_once()

    async def test_cache_miss_no_record_returns_pending_dict(self):
        """When no verification record exists in DB, return a 'pending' status dict."""
        service = EPSVerificationService()
        db = AsyncMock()
        patient = _make_patient()
        tenant_id = str(uuid.uuid4())

        patient_db_result = MagicMock()
        patient_db_result.scalar_one_or_none.return_value = patient

        eps_db_result = MagicMock()
        eps_db_result.scalar_one_or_none.return_value = None  # no record yet

        db.execute = AsyncMock(side_effect=[patient_db_result, eps_db_result])

        with (
            patch(
                "app.services.eps_verification_service.get_cached",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.services.eps_verification_service.set_cached", new_callable=AsyncMock),
        ):
            result = await service.get_latest_verification(
                db=db,
                patient_id=patient.id,
                tenant_id=tenant_id,
            )

        assert result["verification_status"] == "pending"
        assert str(patient.id) in result["patient_id"]


# ── auto_verify_on_creation ───────────────────────────────────────────────────


@pytest.mark.unit
class TestAutoVerifyOnCreationSwallowsErrors:
    async def test_does_not_raise_when_verify_patient_raises(self):
        """auto_verify_on_creation must never propagate exceptions."""
        service = EPSVerificationService()
        db = AsyncMock()

        with patch.object(
            service,
            "verify_patient",
            new_callable=AsyncMock,
            side_effect=Exception("ADRES is down"),
        ):
            # Must not raise
            await service.auto_verify_on_creation(
                db=db,
                patient_id=uuid.uuid4(),
                tenant_id=str(uuid.uuid4()),
            )

    async def test_does_not_raise_on_resource_not_found(self):
        """Even a ResourceNotFoundError must be swallowed."""
        service = EPSVerificationService()
        db = AsyncMock()

        with patch.object(
            service,
            "verify_patient",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            ),
        ):
            await service.auto_verify_on_creation(
                db=db,
                patient_id=uuid.uuid4(),
                tenant_id=str(uuid.uuid4()),
            )

    async def test_returns_none_on_success(self):
        """auto_verify_on_creation always returns None."""
        service = EPSVerificationService()
        db = AsyncMock()

        with patch.object(
            service,
            "verify_patient",
            new_callable=AsyncMock,
            return_value={"affiliation_status": "activo"},
        ):
            result = await service.auto_verify_on_creation(
                db=db,
                patient_id=uuid.uuid4(),
                tenant_id=str(uuid.uuid4()),
            )

        assert result is None

    async def test_returns_none_on_error(self):
        """auto_verify_on_creation returns None even when swallowing an error."""
        service = EPSVerificationService()
        db = AsyncMock()

        with patch.object(
            service,
            "verify_patient",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network timeout"),
        ):
            result = await service.auto_verify_on_creation(
                db=db,
                patient_id=uuid.uuid4(),
            )

        assert result is None
