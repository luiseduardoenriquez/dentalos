"""Periodontal charting service -- create, read, compare periodontal records.

Security invariants:
  - PHI (patient names, document numbers, clinical notes) is NEVER logged.
  - All clinical data is NEVER hard-deleted (Res. 1888 regulatory requirement).
  - Measurements are immutable once written; re-charting creates a new record.
  - Bulk insert is used for measurements to minimize DB round-trips
    (up to 192 rows = 32 teeth x 6 sites per record).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.error_codes import PeriodontalErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.odontogram_constants import VALID_FDI_ALL
from app.models.tenant.patient import Patient
from app.models.tenant.periodontal import PeriodontalMeasurement, PeriodontalRecord
from app.schemas.periodontal import VALID_PERIO_SITES

logger = logging.getLogger("dentalos.periodontal")


# ─── Serialization helpers ───────────────────────────────────────────────────


def _measurement_to_dict(m: PeriodontalMeasurement) -> dict[str, Any]:
    """Serialize a PeriodontalMeasurement ORM instance to a plain dict."""
    return {
        "id": str(m.id),
        "tooth_number": m.tooth_number,
        "site": m.site,
        "pocket_depth": m.pocket_depth,
        "recession": m.recession,
        "clinical_attachment_level": m.clinical_attachment_level,
        "bleeding_on_probing": m.bleeding_on_probing,
        "plaque_index": m.plaque_index,
        "mobility": m.mobility,
        "furcation": m.furcation,
    }


def _record_to_dict(
    record: PeriodontalRecord,
    *,
    include_measurements: bool = True,
) -> dict[str, Any]:
    """Serialize a PeriodontalRecord ORM instance to a plain dict."""
    result: dict[str, Any] = {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "recorded_by": str(record.recorded_by),
        "dentition_type": record.dentition_type,
        "source": record.source,
        "notes": record.notes,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    if include_measurements:
        result["measurements"] = [
            _measurement_to_dict(m) for m in (record.measurements or [])
        ]
    return result


def _record_to_list_item(
    record: PeriodontalRecord,
    measurement_count: int,
) -> dict[str, Any]:
    """Serialize a PeriodontalRecord to a condensed list-view dict."""
    return {
        "id": str(record.id),
        "recorded_by": str(record.recorded_by),
        "dentition_type": record.dentition_type,
        "source": record.source,
        "measurement_count": measurement_count,
        "created_at": record.created_at,
    }


# ─── Validation helpers ─────────────────────────────────────────────────────


def _validate_tooth_numbers(tooth_numbers: list[int]) -> None:
    """Raise DentalOSError if any tooth number is not a valid FDI code."""
    invalid = [t for t in tooth_numbers if t not in VALID_FDI_ALL]
    if invalid:
        raise DentalOSError(
            error=PeriodontalErrors.INVALID_TOOTH_NUMBER,
            message=(
                f"Numeros de diente invalidos: {invalid}. "
                "Use la numeracion FDI."
            ),
            status_code=422,
            details={"invalid_teeth": invalid},
        )


def _validate_sites(sites: list[str]) -> None:
    """Raise DentalOSError if any site is not a valid periodontal site."""
    invalid = [s for s in sites if s not in VALID_PERIO_SITES]
    if invalid:
        raise DentalOSError(
            error=PeriodontalErrors.INVALID_SITE,
            message=(
                f"Sitios periodontales invalidos: {invalid}. "
                f"Valores permitidos: {', '.join(sorted(VALID_PERIO_SITES))}."
            ),
            status_code=422,
            details={"invalid_sites": invalid},
        )


async def _ensure_patient_active(db: AsyncSession, patient_id: uuid.UUID) -> None:
    """Validate that the patient exists and is active. Raises 404 if not."""
    result = await db.execute(
        select(Patient.id).where(
            Patient.id == patient_id,
            Patient.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise ResourceNotFoundError(
            error="PATIENT_not_found",
            resource_name="Patient",
        )


# ─── Periodontal Service ────────────────────────────────────────────────────


class PeriodontalService:
    """Stateless periodontal charting service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path for each method is already set by get_tenant_db().
    """

    async def create_record(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        recorded_by: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a periodontal record with measurements in a single flush.

        Uses bulk insert for measurements to minimize DB round-trips.

        Args:
            db: Tenant-scoped async session.
            patient_id: UUID string of the patient.
            recorded_by: UUID string of the recording clinician.
            data: Dict with dentition_type, source, notes, measurements.

        Raises:
            ResourceNotFoundError (404) -- patient not found or inactive.
            DentalOSError (422) -- invalid tooth number or site.
        """
        pid = uuid.UUID(patient_id)
        uid = uuid.UUID(recorded_by)

        # 1. Validate patient exists and is active
        await _ensure_patient_active(db, pid)

        # 2. Extract and validate measurements
        measurements_data: list[dict[str, Any]] = data.get("measurements", [])
        tooth_numbers = [m["tooth_number"] for m in measurements_data]
        sites = [m["site"] for m in measurements_data]
        _validate_tooth_numbers(tooth_numbers)
        _validate_sites(sites)

        # 3. Create the record
        record = PeriodontalRecord(
            patient_id=pid,
            recorded_by=uid,
            dentition_type=data.get("dentition_type", "adult"),
            source=data.get("source", "manual"),
            notes=data.get("notes"),
            is_active=True,
        )
        db.add(record)
        await db.flush()  # assigns record.id

        # 4. Bulk insert measurements (single round-trip)
        if measurements_data:
            measurement_rows = [
                {
                    "id": uuid.uuid4(),
                    "record_id": record.id,
                    "tooth_number": m["tooth_number"],
                    "site": m["site"],
                    "pocket_depth": m.get("pocket_depth"),
                    "recession": m.get("recession"),
                    "clinical_attachment_level": m.get("clinical_attachment_level"),
                    "bleeding_on_probing": m.get("bleeding_on_probing"),
                    "plaque_index": m.get("plaque_index"),
                    "mobility": m.get("mobility"),
                    "furcation": m.get("furcation"),
                }
                for m in measurements_data
            ]
            await db.execute(insert(PeriodontalMeasurement), measurement_rows)

        # 5. Reload to get measurements via selectin relationship
        await db.refresh(record, attribute_names=["measurements"])

        logger.info(
            "PeriodontalRecord created: patient=%s record=%s measurements=%d",
            str(pid)[:8],
            str(record.id)[:8],
            len(measurements_data),
        )

        return _record_to_dict(record)

    async def get_record(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        record_id: str,
    ) -> dict[str, Any]:
        """Fetch a single periodontal record with its measurements.

        Raises:
            ResourceNotFoundError (404) -- record not found, inactive, or
                                           belongs to a different patient.
        """
        pid = uuid.UUID(patient_id)
        rid = uuid.UUID(record_id)

        result = await db.execute(
            select(PeriodontalRecord)
            .options(selectinload(PeriodontalRecord.measurements))
            .where(
                PeriodontalRecord.id == rid,
                PeriodontalRecord.patient_id == pid,
                PeriodontalRecord.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()

        if record is None:
            raise ResourceNotFoundError(
                error=PeriodontalErrors.RECORD_NOT_FOUND,
                resource_name="PeriodontalRecord",
            )

        return _record_to_dict(record)

    async def list_records(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of periodontal records for a patient.

        List view includes metadata only (no measurements) for performance.
        Records are ordered newest-first.
        """
        pid = uuid.UUID(patient_id)

        # Count total
        count_stmt = (
            select(func.count())
            .select_from(PeriodontalRecord)
            .where(
                PeriodontalRecord.patient_id == pid,
                PeriodontalRecord.is_active.is_(True),
            )
        )
        total = (await db.execute(count_stmt)).scalar_one()

        # Fetch page with measurement counts via subquery
        measurement_count_subq = (
            select(
                PeriodontalMeasurement.record_id,
                func.count().label("measurement_count"),
            )
            .group_by(PeriodontalMeasurement.record_id)
            .subquery()
        )

        offset = (page - 1) * page_size
        records_stmt = (
            select(
                PeriodontalRecord,
                func.coalesce(measurement_count_subq.c.measurement_count, 0).label(
                    "measurement_count"
                ),
            )
            .outerjoin(
                measurement_count_subq,
                PeriodontalRecord.id == measurement_count_subq.c.record_id,
            )
            .where(
                PeriodontalRecord.patient_id == pid,
                PeriodontalRecord.is_active.is_(True),
            )
            .order_by(PeriodontalRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(records_stmt)).all()

        items = [
            _record_to_list_item(row[0], row[1])
            for row in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def compare_records(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        record_a_id: str,
        record_b_id: str,
    ) -> dict[str, Any]:
        """Compare two periodontal records and compute deltas.

        For each common (tooth_number, site) pair, computes the difference
        in pocket_depth, recession, and clinical_attachment_level.

        Status is determined by pocket_depth change:
          - decreased -> improved
          - increased -> worsened
          - unchanged or both null -> unchanged

        Raises:
            ResourceNotFoundError (404) -- either record not found or inactive.
        """
        pid = uuid.UUID(patient_id)
        ra_id = uuid.UUID(record_a_id)
        rb_id = uuid.UUID(record_b_id)

        # Fetch both records with measurements
        result = await db.execute(
            select(PeriodontalRecord)
            .options(selectinload(PeriodontalRecord.measurements))
            .where(
                PeriodontalRecord.id.in_([ra_id, rb_id]),
                PeriodontalRecord.patient_id == pid,
                PeriodontalRecord.is_active.is_(True),
            )
        )
        records_by_id = {r.id: r for r in result.scalars().all()}

        if ra_id not in records_by_id:
            raise ResourceNotFoundError(
                error=PeriodontalErrors.RECORD_NOT_FOUND,
                resource_name="PeriodontalRecord (record_a)",
            )
        if rb_id not in records_by_id:
            raise ResourceNotFoundError(
                error=PeriodontalErrors.RECORD_NOT_FOUND,
                resource_name="PeriodontalRecord (record_b)",
            )

        record_a = records_by_id[ra_id]
        record_b = records_by_id[rb_id]

        # Index measurements by (tooth_number, site) for fast lookup
        measurements_a: dict[tuple[int, str], PeriodontalMeasurement] = {
            (m.tooth_number, m.site): m for m in record_a.measurements
        }
        measurements_b: dict[tuple[int, str], PeriodontalMeasurement] = {
            (m.tooth_number, m.site): m for m in record_b.measurements
        }

        # Compute deltas for common keys
        common_keys = set(measurements_a.keys()) & set(measurements_b.keys())
        deltas: list[dict[str, Any]] = []

        for key in sorted(common_keys):
            ma = measurements_a[key]
            mb = measurements_b[key]

            pd_delta = _safe_delta(mb.pocket_depth, ma.pocket_depth)
            rec_delta = _safe_delta(mb.recession, ma.recession)
            cal_delta = _safe_delta(
                mb.clinical_attachment_level, ma.clinical_attachment_level
            )

            # Status based on pocket_depth trend
            if pd_delta is not None:
                if pd_delta < 0:
                    status = "improved"
                elif pd_delta > 0:
                    status = "worsened"
                else:
                    status = "unchanged"
            else:
                status = "unchanged"

            deltas.append({
                "tooth_number": key[0],
                "site": key[1],
                "pocket_depth_delta": pd_delta,
                "recession_delta": rec_delta,
                "cal_delta": cal_delta,
                "status": status,
            })

        return {
            "record_a_id": str(ra_id),
            "record_b_id": str(rb_id),
            "record_a_date": record_a.created_at,
            "record_b_date": record_b.created_at,
            "deltas": deltas,
        }

    async def bulk_update_measurements(
        self,
        *,
        db: AsyncSession,
        record_id: str,
        measurements: list[dict[str, Any]],
        source: str = "manual",
    ) -> dict[str, Any]:
        """Update or insert measurements on an existing record.

        Used by the voice pipeline when target_type='periodontogram'.
        Existing measurements at the same (tooth, site) are replaced;
        new (tooth, site) pairs are inserted.

        Args:
            db: Tenant-scoped async session.
            record_id: UUID string of the periodontal record.
            measurements: List of measurement dicts.
            source: Provenance tag ('manual' or 'voice').

        Raises:
            ResourceNotFoundError (404) -- record not found or inactive.
            DentalOSError (422) -- invalid tooth number or site.
        """
        rid = uuid.UUID(record_id)

        # 1. Validate record exists and is active
        result = await db.execute(
            select(PeriodontalRecord).where(
                PeriodontalRecord.id == rid,
                PeriodontalRecord.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise ResourceNotFoundError(
                error=PeriodontalErrors.RECORD_NOT_FOUND,
                resource_name="PeriodontalRecord",
            )

        # 2. Validate inputs
        tooth_numbers = [m["tooth_number"] for m in measurements]
        sites = [m["site"] for m in measurements]
        _validate_tooth_numbers(tooth_numbers)
        _validate_sites(sites)

        # 3. Delete existing measurements at the same (tooth, site) pairs
        keys_to_replace = [(m["tooth_number"], m["site"]) for m in measurements]
        for tooth_num, site in keys_to_replace:
            await db.execute(
                delete(PeriodontalMeasurement).where(
                    PeriodontalMeasurement.record_id == rid,
                    PeriodontalMeasurement.tooth_number == tooth_num,
                    PeriodontalMeasurement.site == site,
                )
            )

        # 4. Bulk insert new measurements
        measurement_rows = [
            {
                "id": uuid.uuid4(),
                "record_id": rid,
                "tooth_number": m["tooth_number"],
                "site": m["site"],
                "pocket_depth": m.get("pocket_depth"),
                "recession": m.get("recession"),
                "clinical_attachment_level": m.get("clinical_attachment_level"),
                "bleeding_on_probing": m.get("bleeding_on_probing"),
                "plaque_index": m.get("plaque_index"),
                "mobility": m.get("mobility"),
                "furcation": m.get("furcation"),
            }
            for m in measurements
        ]
        await db.execute(insert(PeriodontalMeasurement), measurement_rows)

        # 5. Update record source if voice
        if source == "voice" and record.source != "voice":
            record.source = "voice"

        await db.flush()

        # 6. Reload and return
        await db.refresh(record, attribute_names=["measurements"])

        logger.info(
            "PeriodontalRecord updated (bulk): record=%s measurements=%d source=%s",
            str(rid)[:8],
            len(measurements),
            source,
        )

        return _record_to_dict(record)


# ─── Helper ──────────────────────────────────────────────────────────────────


def _safe_delta(new_val: int | None, old_val: int | None) -> int | None:
    """Compute new - old, returning None if either value is None."""
    if new_val is not None and old_val is not None:
        return new_val - old_val
    return None


# ─── Singleton ───────────────────────────────────────────────────────────────

periodontal_service = PeriodontalService()
