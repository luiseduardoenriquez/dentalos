"""Clinical record service — create, read, update, and manage anamnesis.

Security invariants:
  - PHI (patient names, document numbers, clinical notes) is NEVER logged.
  - All clinical data is NEVER hard-deleted (Res. 1888 regulatory requirement).
  - Edit window is enforced here, not in the route layer, so it applies
    uniformly regardless of how the service is called (API, worker, CLI).
  - doctor_name is fetched via a LEFT JOIN on the users table inside a raw
    SQL query only for list/get paths; ORM is used for all write paths.
"""

import contextlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.clinical_record import Anamnesis, ClinicalRecord
from app.models.tenant.patient import Patient

logger = logging.getLogger("dentalos.clinical")

# ─── Constants ────────────────────────────────────────────────────────────────

_VALID_RECORD_TYPES = frozenset({"examination", "evolution_note", "procedure"})
_EDIT_WINDOW_HOURS = 24


# ─── Serialization helpers ────────────────────────────────────────────────────


def _record_to_dict(
    record: ClinicalRecord,
    *,
    doctor_name: str | None = None,
) -> dict[str, Any]:
    """Serialize a ClinicalRecord ORM instance to a plain dict.

    is_editable is re-evaluated at read time against the current clock so
    callers always get the live edit-window status, even if the row was
    fetched seconds after edit_locked_at passed.
    """
    now = datetime.now(UTC)
    still_editable: bool = record.is_editable and (
        record.edit_locked_at is None or now < record.edit_locked_at
    )

    return {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "doctor_id": str(record.doctor_id),
        "doctor_name": doctor_name,
        "type": record.type,
        "content": record.content,
        "tooth_numbers": record.tooth_numbers,
        "template_id": str(record.template_id) if record.template_id else None,
        "is_editable": still_editable,
        "edit_locked_at": record.edit_locked_at,
        "is_active": record.is_active,
        "deleted_at": record.deleted_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _anamnesis_to_dict(anamnesis: Anamnesis) -> dict[str, Any]:
    """Serialize an Anamnesis ORM instance to a plain dict."""
    return {
        "id": str(anamnesis.id),
        "patient_id": str(anamnesis.patient_id),
        "allergies": anamnesis.allergies,
        "medications": anamnesis.medications,
        "medical_history": anamnesis.medical_history,
        "dental_history": anamnesis.dental_history,
        "family_history": anamnesis.family_history,
        "habits": anamnesis.habits,
        "last_updated_by": (
            str(anamnesis.last_updated_by) if anamnesis.last_updated_by else None
        ),
        "is_active": anamnesis.is_active,
        "deleted_at": anamnesis.deleted_at,
        "created_at": anamnesis.created_at,
        "updated_at": anamnesis.updated_at,
    }


# ─── Clinical Record Service ───────────────────────────────────────────────────


class ClinicalRecordService:
    """Stateless clinical record service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path for each method is already set by get_tenant_db().
    Methods do NOT call SET search_path themselves — the session is already
    scoped to the correct tenant schema by the time it arrives here.
    """

    # ─── Clinical Records ────────────────────────────────────────────────

    async def create_record(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        type: str,
        content: dict[str, Any],
        tooth_numbers: list[int] | None = None,
        template_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new clinical record for an active patient.

        Raises:
            DentalOSError (404) — patient not found or inactive.
            DentalOSError (422) — invalid record type.
        """
        # 1. Validate record type
        if type not in _VALID_RECORD_TYPES:
            raise DentalOSError(
                error="CLINICAL_invalid_type",
                message=(
                    f"Tipo de registro inválido. Los tipos permitidos son: "
                    f"{', '.join(sorted(_VALID_RECORD_TYPES))}."
                ),
                status_code=422,
                details={"provided": type, "allowed": sorted(_VALID_RECORD_TYPES)},
            )

        # 2. Validate patient exists and is active
        patient_result = await db.execute(
            select(Patient.id).where(
                Patient.id == uuid.UUID(patient_id),
                Patient.is_active.is_(True),
            )
        )
        if patient_result.scalar_one_or_none() is None:
            raise DentalOSError(
                error="CLINICAL_patient_not_found",
                message="El paciente no existe o está inactivo.",
                status_code=404,
            )

        # 3. Compute edit lock deadline
        now = datetime.now(UTC)
        edit_locked_at = now + timedelta(hours=_EDIT_WINDOW_HOURS)

        # 4. Persist
        record = ClinicalRecord(
            patient_id=uuid.UUID(patient_id),
            doctor_id=uuid.UUID(doctor_id),
            type=type,
            content=content,
            tooth_numbers=tooth_numbers,
            template_id=uuid.UUID(template_id) if template_id else None,
            is_editable=True,
            edit_locked_at=edit_locked_at,
            is_active=True,
        )
        db.add(record)
        await db.flush()

        logger.info(
            "ClinicalRecord created: patient=%s record=%s type=%s",
            str(record.patient_id)[:8],
            str(record.id)[:8],
            record.type,
        )

        return _record_to_dict(record)

    async def get_record(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single clinical record with the doctor's display name.

        Uses a raw SQL LEFT JOIN to pull doctor_name in a single round-trip.
        Returns None when the record does not exist or is inactive.
        """
        stmt = text("""
            SELECT
                cr.id,
                cr.patient_id,
                cr.doctor_id,
                cr.type,
                cr.content,
                cr.tooth_numbers,
                cr.template_id,
                cr.is_editable,
                cr.edit_locked_at,
                cr.is_active,
                cr.deleted_at,
                cr.created_at,
                cr.updated_at,
                u.name AS doctor_name
            FROM clinical_records cr
            LEFT JOIN users u ON u.id = cr.doctor_id
            WHERE cr.id = :record_id
              AND cr.patient_id = :patient_id
              AND cr.is_active = true
        """)
        result = await db.execute(
            stmt,
            {"record_id": uuid.UUID(record_id), "patient_id": uuid.UUID(patient_id)},
        )
        row = result.mappings().one_or_none()

        if row is None:
            return None

        now = datetime.now(UTC)
        edit_locked_at = row["edit_locked_at"]
        still_editable: bool = row["is_editable"] and (
            edit_locked_at is None or now < edit_locked_at
        )

        return {
            "id": str(row["id"]),
            "patient_id": str(row["patient_id"]),
            "doctor_id": str(row["doctor_id"]),
            "doctor_name": row["doctor_name"],
            "type": row["type"],
            "content": row["content"],
            "tooth_numbers": row["tooth_numbers"],
            "template_id": str(row["template_id"]) if row["template_id"] else None,
            "is_editable": still_editable,
            "edit_locked_at": edit_locked_at,
            "is_active": row["is_active"],
            "deleted_at": row["deleted_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def list_records(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Return a paginated list of clinical records for a patient.

        Records are ordered newest-first. Each row includes the doctor's
        display name from a LEFT JOIN on the users table (raw SQL required
        because SQLAlchemy ORM join on a cross-schema tenant table adds
        unnecessary complexity vs. a well-parameterised text() query).

        Args:
            type_filter: When provided, restrict results to one record type.
        """
        offset = (page - 1) * page_size
        params: dict[str, Any] = {
            "patient_id": uuid.UUID(patient_id),
            "limit": page_size,
            "offset": offset,
        }

        type_clause = ""
        if type_filter is not None:
            type_clause = "AND cr.type = :type_filter"
            params["type_filter"] = type_filter

        count_sql = text(f"""
            SELECT COUNT(*)
            FROM clinical_records cr
            WHERE cr.patient_id = :patient_id
              AND cr.is_active = true
              {type_clause}
        """)
        count_result = await db.execute(count_sql, params)
        total: int = count_result.scalar_one()

        list_sql = text(f"""
            SELECT
                cr.id,
                cr.patient_id,
                cr.doctor_id,
                cr.type,
                cr.content,
                cr.tooth_numbers,
                cr.template_id,
                cr.is_editable,
                cr.edit_locked_at,
                cr.is_active,
                cr.deleted_at,
                cr.created_at,
                cr.updated_at,
                u.name AS doctor_name
            FROM clinical_records cr
            LEFT JOIN users u ON u.id = cr.doctor_id
            WHERE cr.patient_id = :patient_id
              AND cr.is_active = true
              {type_clause}
            ORDER BY cr.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows_result = await db.execute(list_sql, params)
        rows = rows_result.mappings().all()

        now = datetime.now(UTC)
        items = []
        for row in rows:
            edit_locked_at = row["edit_locked_at"]
            still_editable: bool = row["is_editable"] and (
                edit_locked_at is None or now < edit_locked_at
            )
            items.append({
                "id": str(row["id"]),
                "patient_id": str(row["patient_id"]),
                "doctor_id": str(row["doctor_id"]),
                "doctor_name": row["doctor_name"],
                "type": row["type"],
                "content": row["content"],
                "tooth_numbers": row["tooth_numbers"],
                "template_id": str(row["template_id"]) if row["template_id"] else None,
                "is_editable": still_editable,
                "edit_locked_at": edit_locked_at,
                "is_active": row["is_active"],
                "deleted_at": row["deleted_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_record(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        record_id: str,
        user_id: str,
        content: dict[str, Any] | None = None,
        tooth_numbers: list[int] | None = None,
    ) -> dict[str, Any]:
        """Apply partial updates to an existing active clinical record.

        Only non-None arguments are applied. The 24-hour edit window is
        checked before applying any changes.

        Raises:
            ResourceNotFoundError (404) — record not found or inactive.
            DentalOSError (403) — edit window has expired.
        """
        result = await db.execute(
            select(ClinicalRecord).where(
                ClinicalRecord.id == uuid.UUID(record_id),
                ClinicalRecord.patient_id == uuid.UUID(patient_id),
                ClinicalRecord.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()

        if record is None:
            raise ResourceNotFoundError(
                error="CLINICAL_record_not_found",
                resource_name="ClinicalRecord",
            )

        # Enforce edit window
        now = datetime.now(UTC)
        if record.edit_locked_at is not None and now > record.edit_locked_at:
            raise DentalOSError(
                error="CLINICAL_record_locked",
                message="El periodo de edición de 24 horas ha expirado.",
                status_code=403,
                details={
                    "record_id": record_id,
                    "edit_locked_at": record.edit_locked_at.isoformat(),
                },
            )

        # Apply non-None updates
        if content is not None:
            record.content = content
        if tooth_numbers is not None:
            record.tooth_numbers = tooth_numbers

        await db.flush()

        logger.info(
            "ClinicalRecord updated: patient=%s record=%s by_user=%s",
            str(record.patient_id)[:8],
            str(record.id)[:8],
            user_id[:8],
        )

        return _record_to_dict(record)

    # ─── Anamnesis ───────────────────────────────────────────────────────

    async def create_anamnesis(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        user_id: str,
        allergies: dict[str, Any] | None = None,
        medications: dict[str, Any] | None = None,
        medical_history: dict[str, Any] | None = None,
        dental_history: dict[str, Any] | None = None,
        family_history: dict[str, Any] | None = None,
        habits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update the anamnesis for a patient.

        Because the anamnesis table has a UNIQUE constraint on patient_id,
        there can only be one row per patient. This method enforces that
        invariant in the service layer by upsert semantics: if a row already
        exists it is updated in place; otherwise a new row is created.
        """
        # Check if anamnesis already exists for this patient
        existing_result = await db.execute(
            select(Anamnesis).where(
                Anamnesis.patient_id == uuid.UUID(patient_id),
                Anamnesis.is_active.is_(True),
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            # UPDATE existing anamnesis
            if allergies is not None:
                existing.allergies = allergies
            if medications is not None:
                existing.medications = medications
            if medical_history is not None:
                existing.medical_history = medical_history
            if dental_history is not None:
                existing.dental_history = dental_history
            if family_history is not None:
                existing.family_history = family_history
            if habits is not None:
                existing.habits = habits
            existing.last_updated_by = uuid.UUID(user_id)

            await db.flush()

            logger.info(
                "Anamnesis updated: patient=%s by_user=%s",
                patient_id[:8],
                user_id[:8],
            )

            return _anamnesis_to_dict(existing)

        # CREATE new anamnesis
        anamnesis = Anamnesis(
            patient_id=uuid.UUID(patient_id),
            allergies=allergies,
            medications=medications,
            medical_history=medical_history,
            dental_history=dental_history,
            family_history=family_history,
            habits=habits,
            last_updated_by=uuid.UUID(user_id),
            is_active=True,
        )
        db.add(anamnesis)
        await db.flush()

        logger.info(
            "Anamnesis created: patient=%s by_user=%s",
            patient_id[:8],
            user_id[:8],
        )

        return _anamnesis_to_dict(anamnesis)

    async def get_anamnesis(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any] | None:
        """Fetch the anamnesis for a patient.

        Returns None when no anamnesis record exists for the patient.
        The caller is responsible for converting None to a 404 response.
        """
        result = await db.execute(
            select(Anamnesis).where(
                Anamnesis.patient_id == uuid.UUID(patient_id),
                Anamnesis.is_active.is_(True),
            )
        )
        anamnesis = result.scalar_one_or_none()

        if anamnesis is None:
            return None

        return _anamnesis_to_dict(anamnesis)


# Module-level singleton for dependency injection
clinical_record_service = ClinicalRecordService()
