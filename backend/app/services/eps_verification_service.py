"""EPS insurance verification service — VP-06.

Orchestrates ADRES BDUA lookups by resolving the correct adapter (production
or mock), persisting results as EPSVerification records, and managing a Redis
cache to avoid repeated expensive ADRES API calls within a 24-hour window.

PHI rules:
  - document_number is PHI — NEVER written to logs at any log level.
  - patient_id (UUID) is safe to log as an opaque identifier.
  - raw_response stored for audit but NOT returned in public API responses.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, set_cached
from app.core.error_codes import EPSErrors, PatientErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.integrations.adres.base import ADRESServiceBase
from app.integrations.adres.mock_service import adres_mock_service
from app.integrations.adres.service import adres_service
from app.models.tenant.eps_verification import EPSVerification
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.eps_verification")

# Redis TTL for cached verification results — 24 hours.
_CACHE_TTL_SECONDS = 86_400


def _get_adapter() -> ADRESServiceBase:
    """Return the appropriate ADRES adapter based on configuration.

    Uses the production service when credentials are present; falls back to
    the mock service for development and CI environments.
    """
    if adres_service.is_configured():
        return adres_service
    return adres_mock_service


def _cache_key(tenant_id: str, patient_id: str) -> str:
    """Build the Redis cache key for an EPS verification result.

    Key pattern: dentalos:{tenant_id_short}:eps:verification:{patient_id}
    """
    # Use the first 8 chars of tenant_id as the short ID to match the
    # dentalos:{tid}:{domain}:{resource}:{id} convention.
    tid_short = tenant_id.replace("-", "")[:8]
    return f"dentalos:{tid_short}:eps:verification:{patient_id}"


class EPSVerificationService:
    """Orchestrates EPS insurance verification for patient records.

    All methods are stateless and accept an AsyncSession injected by the
    FastAPI dependency system or the maintenance worker.
    """

    async def verify_patient(
        self,
        *,
        db: AsyncSession,
        patient_id: UUID | str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Verify a patient's EPS insurance affiliation via ADRES.

        Looks up the patient's document type and number, calls the ADRES
        adapter, persists an EPSVerification record, and caches the result
        in Redis for 24 hours.

        Args:
            db: Tenant-scoped async database session.
            patient_id: UUID of the patient to verify.
            tenant_id: Tenant ID string for cache key scoping (optional;
                       pass when available from the request context).

        Returns:
            dict matching EPSVerificationResponse schema.

        Raises:
            ResourceNotFoundError: If the patient does not exist in this tenant.
            DentalOSError: If the ADRES adapter returns an unexpected error.
        """
        patient_id_str = str(patient_id)
        logger.info("EPS verification requested: patient_id=%s", patient_id_str)

        patient = await self._get_patient(db=db, patient_id=patient_id_str)

        adapter = _get_adapter()
        try:
            # NOTE: document_number is PHI — the adapter is responsible for
            # never logging it; we likewise never log it here.
            result = await adapter.verify_affiliation(
                document_type=patient.document_type,
                document_number=patient.document_number,
            )
        except Exception as exc:
            logger.error(
                "ADRES adapter error for patient_id=%s: %s",
                patient_id_str,
                type(exc).__name__,
            )
            raise DentalOSError(
                error=EPSErrors.SERVICE_UNAVAILABLE,
                message="EPS verification service is currently unavailable.",
                status_code=503,
            ) from exc

        # Persist a new verification record regardless of found/not-found.
        record = EPSVerification(
            patient_id=patient.id,
            verification_date=result.verification_date,
            eps_name=result.eps_name,
            eps_code=result.eps_code,
            affiliation_status=result.affiliation_status,
            regime=result.regime,
            copay_category=result.copay_category,
            # raw_response is stored for audit — never returned in public APIs.
            raw_response=result.raw_response,
        )
        db.add(record)
        await db.flush()

        # Check for coverage change and alert if needed
        if tenant_id:
            await self.check_coverage_change(
                db=db,
                patient_id=patient_id,
                tenant_id=tenant_id,
                new_status=result.affiliation_status,
            )

        response_dict = self._to_dict(record)

        # Cache the result keyed by patient_id.  Cache failures are swallowed
        # since Redis is a performance enhancement, not a hard dependency.
        if tenant_id:
            key = _cache_key(tenant_id=tenant_id, patient_id=patient_id_str)
            await set_cached(key, response_dict, _CACHE_TTL_SECONDS)

        logger.info(
            "EPS verification complete: patient_id=%s affiliation_status=%s",
            patient_id_str,
            result.affiliation_status,
        )

        return response_dict

    async def get_latest_verification(
        self,
        *,
        db: AsyncSession,
        patient_id: UUID | str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the most recent EPS verification for a patient.

        Checks Redis cache first; falls back to a DB query if the cache is
        cold or has expired.

        Args:
            db: Tenant-scoped async database session.
            patient_id: UUID of the patient.
            tenant_id: Tenant ID string for cache key scoping (optional).

        Returns:
            dict matching EPSVerificationResponse schema, or an empty dict
            with patient_id if no verification exists yet.

        Raises:
            ResourceNotFoundError: If the patient does not exist in this tenant.
        """
        patient_id_str = str(patient_id)

        # Confirm the patient exists — raises 404 if not.
        await self._get_patient(db=db, patient_id=patient_id_str)

        # 1. Try Redis cache.
        if tenant_id:
            key = _cache_key(tenant_id=tenant_id, patient_id=patient_id_str)
            cached = await get_cached(key)
            if cached is not None:
                logger.debug(
                    "EPS verification cache hit: patient_id=%s", patient_id_str
                )
                return cached

        # 2. Fall back to DB — fetch the most recent record.
        stmt = (
            select(EPSVerification)
            .where(EPSVerification.patient_id == patient_id)
            .order_by(desc(EPSVerification.verification_date))
            .limit(1)
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            logger.info(
                "No EPS verification on record: patient_id=%s", patient_id_str
            )
            return {"patient_id": patient_id_str, "verification_status": "pending"}

        response_dict = self._to_dict(record)

        # Warm the cache for subsequent reads.
        if tenant_id:
            key = _cache_key(tenant_id=tenant_id, patient_id=patient_id_str)
            await set_cached(key, response_dict, _CACHE_TTL_SECONDS)

        return response_dict

    async def auto_verify_on_creation(
        self,
        *,
        db: AsyncSession,
        patient_id: UUID | str,
        tenant_id: str | None = None,
    ) -> None:
        """Trigger EPS verification in the background after patient creation.

        Called from the maintenance worker or an async task.  Errors are
        logged and swallowed so a transient ADRES outage does not fail patient
        creation.

        Args:
            db: Tenant-scoped async database session.
            patient_id: UUID of the newly created patient.
            tenant_id: Tenant ID string for cache key scoping (optional).
        """
        patient_id_str = str(patient_id)
        try:
            await self.verify_patient(
                db=db,
                patient_id=patient_id_str,
                tenant_id=tenant_id,
            )
        except Exception as exc:
            # Swallow the error — auto-verification is best-effort.
            logger.warning(
                "Auto EPS verification failed for patient_id=%s: %s — "
                "will retry on next manual trigger.",
                patient_id_str,
                type(exc).__name__,
            )

    async def check_coverage_change(
        self,
        *,
        db: AsyncSession,
        patient_id: UUID | str,
        tenant_id: str,
        new_status: str,
    ) -> None:
        """Check if EPS coverage changed and dispatch alert if so.

        Compares the new affiliation_status to the previous verification.
        If different, publishes an alert to the notifications queue.
        """
        patient_id_str = str(patient_id)

        # Fetch previous verification (skip the current just-inserted one)
        stmt = (
            select(EPSVerification)
            .where(EPSVerification.patient_id == patient_id)
            .order_by(desc(EPSVerification.verification_date))
            .offset(1)  # Skip the current (just-inserted) one
            .limit(1)
        )
        result = await db.execute(stmt)
        previous = result.scalar_one_or_none()

        if previous is None:
            return  # First verification — no comparison

        if previous.affiliation_status != new_status:
            logger.info(
                "EPS coverage changed: patient_id=%s old=%s new=%s",
                patient_id_str,
                previous.affiliation_status,
                new_status,
            )
            try:
                from app.core.queue import publish_message

                await publish_message(
                    queue="notifications",
                    job_type="notification.dispatch",
                    tenant_id=tenant_id,
                    payload={
                        "event_type": "eps.coverage_change",
                        "user_id": "",  # Will be resolved to clinic_owner
                        "data": {
                            "title": "Cambio en cobertura EPS",
                            "body": (
                                f"El estado de afiliación del paciente cambió de "
                                f"{previous.affiliation_status} a {new_status}."
                            ),
                            "metadata": {
                                "patient_id": patient_id_str,
                                "old_status": previous.affiliation_status,
                                "new_status": new_status,
                            },
                        },
                    },
                )
            except Exception:
                logger.warning(
                    "Failed to dispatch EPS coverage change alert: patient_id=%s",
                    patient_id_str,
                )

    # ─── Private helpers ──────────────────────────────────────────────────────

    async def _get_patient(self, *, db: AsyncSession, patient_id: str) -> Patient:
        """Fetch an active Patient by ID or raise ResourceNotFoundError."""
        stmt = select(Patient).where(
            Patient.id == patient_id,
            Patient.is_active.is_(True),
        )
        result = await db.execute(stmt)
        patient = result.scalar_one_or_none()
        if patient is None:
            raise ResourceNotFoundError(
                error=PatientErrors.NOT_FOUND,
                resource_name="Patient",
            )
        return patient

    @staticmethod
    def _to_dict(record: EPSVerification) -> dict[str, Any]:
        """Map an EPSVerification ORM record to the response dict contract."""
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


# Module-level singleton.
eps_verification_service = EPSVerificationService()
