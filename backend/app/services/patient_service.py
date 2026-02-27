"""Patient service — create, read, update, deactivate, search, export, and merge.

Security invariants:
  - PHI (patient names, document numbers, phone, email) is NEVER logged.
  - Raw SQL is used only for PostgreSQL FTS (websearch_to_tsquery / tsvector)
    and the ILIKE fallback — these cannot be expressed in pure SQLAlchemy ORM.
    All other queries use the ORM exclusively.
  - Soft delete only — clinical data is never hard-deleted (Res. 1888).
  - Plan limits are enforced before every patient creation.
  - Merge operations run in a single transaction and use bound parameters.
"""

import contextlib
import csv
import hashlib
import io
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, get_cached, set_cached
from app.core.exceptions import (
    BusinessValidationError,
    DentalOSError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.tenant.patient import Patient
from app.services.tenant_service import get_tenant_with_plan

logger = logging.getLogger("dentalos.patients")

# ─── Constants ───────────────────────────────────────────────────────────────

_SEARCH_CACHE_TTL = 120  # 2 minutes


# ─── Dentition helper ────────────────────────────────────────────────────────


def compute_dentition_type(birthdate: date | None) -> str | None:
    """Classify dentition stage from age.

    adult     — age >= 12 (permanent dentition)
    mixed     — age 6-11 (transitional dentition)
    pediatric — age < 6  (primary dentition)
    None      — no birthdate available
    """
    if birthdate is None:
        return None
    today = date.today()
    age = today.year - birthdate.year - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )
    if age >= 12:
        return "adult"
    elif age >= 6:
        return "mixed"
    else:
        return "pediatric"


# ─── Serialization helper ────────────────────────────────────────────────────


def _patient_to_dict(patient: Patient, *, include_clinical_summary: bool = False) -> dict[str, Any]:
    """Serialize a Patient ORM instance to a plain dict.

    dentition_type is computed here rather than stored in the DB.
    clinical_summary is a stub until Sprint 5-6 (odontogram, treatment plans).
    """
    data: dict[str, Any] = {
        "id": str(patient.id),
        "document_type": patient.document_type,
        "document_number": patient.document_number,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "birthdate": patient.birthdate,
        "gender": patient.gender,
        "phone": patient.phone,
        "phone_secondary": patient.phone_secondary,
        "email": patient.email,
        "address": patient.address,
        "city": patient.city,
        "state_province": patient.state_province,
        "emergency_contact_name": patient.emergency_contact_name,
        "emergency_contact_phone": patient.emergency_contact_phone,
        "insurance_provider": patient.insurance_provider,
        "insurance_policy_number": patient.insurance_policy_number,
        "blood_type": patient.blood_type,
        "allergies": patient.allergies,
        "chronic_conditions": patient.chronic_conditions,
        "referral_source": patient.referral_source,
        "notes": patient.notes,
        "is_active": patient.is_active,
        "deleted_at": patient.deleted_at,
        "no_show_count": patient.no_show_count,
        "portal_access": patient.portal_access,
        "created_by": str(patient.created_by) if patient.created_by else None,
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
        "dentition_type": compute_dentition_type(patient.birthdate),
    }

    if include_clinical_summary:
        # TODO: Replace with real counts from clinical tables (Sprint 5-6)
        data["clinical_summary"] = {
            "active_diagnoses": 0,
            "treatment_plans": 0,
            "pending_treatments": 0,
            "next_appointment": None,
        }

    return data


# ─── Cache helpers ───────────────────────────────────────────────────────────


def _search_cache_key(tenant_id: str, q_normalized: str) -> str:
    """Build Redis cache key for a patient search query.

    Uses an MD5 prefix of the normalized query to avoid storing PHI in
    the key name while still producing a stable, collision-resistant key.
    """
    q_hash = hashlib.md5(q_normalized.encode()).hexdigest()[:12]  # noqa: S324
    return f"dentalos:{tenant_id[:8]}:patients:search:{q_hash}"


def _patient_cache_key(tenant_id: str, patient_id: str) -> str:
    return f"dentalos:{tenant_id[:8]}:patients:detail:{patient_id}"


def _invalidate_search_cache(tenant_id: str) -> str:
    """Return the glob pattern to wipe all search cache entries for a tenant."""
    return f"dentalos:{tenant_id[:8]}:patients:search:*"


# ─── Patient Service ─────────────────────────────────────────────────────────


class PatientService:
    """Stateless patient service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path for each method is already set by get_tenant_db().
    Methods do NOT call SET search_path themselves — the session is already
    scoped to the correct tenant schema by the time it arrives here.
    """

    # ─── Create ─────────────────────────────────────────────────────────

    async def create_patient(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        created_by_id: str,
        document_type: str,
        document_number: str,
        first_name: str,
        last_name: str,
        birthdate: date | None = None,
        gender: str | None = None,
        phone: str | None = None,
        phone_secondary: str | None = None,
        email: str | None = None,
        address: str | None = None,
        city: str | None = None,
        state_province: str | None = None,
        emergency_contact_name: str | None = None,
        emergency_contact_phone: str | None = None,
        insurance_provider: str | None = None,
        insurance_policy_number: str | None = None,
        blood_type: str | None = None,
        allergies: list[str] | None = None,
        chronic_conditions: list[str] | None = None,
        referral_source: str | None = None,
        notes: str | None = None,
        grant_portal_access: bool = True,
    ) -> dict[str, Any]:
        """Register a new patient in the current tenant schema.

        Enforces plan limits and document uniqueness before persisting.

        Raises:
            DentalOSError (402) — plan patient limit reached.
            ResourceConflictError (409) — document_type + document_number already exists.
        """
        # 1. Resolve tenant context to check plan limits
        tenant_ctx = await get_tenant_with_plan(tenant_id, db)
        max_patients: int = tenant_ctx.limits.get("max_patients", 0)
        plan_name: str = tenant_ctx.plan_name

        # 2. Count active patients
        count_result = await db.execute(
            select(func.count(Patient.id)).where(Patient.is_active.is_(True))
        )
        current_count: int = count_result.scalar_one()

        if max_patients > 0 and current_count >= max_patients:
            raise DentalOSError(
                error="PATIENT_plan_limit_reached",
                message="Ha alcanzado el límite de pacientes de su plan.",
                status_code=402,
                details={
                    "current_count": current_count,
                    "max_allowed": max_patients,
                    "plan_name": plan_name,
                },
            )

        # 3. Uniqueness check — document_type + document_number within this tenant
        existing = await db.execute(
            select(Patient.id).where(
                Patient.document_type == document_type,
                Patient.document_number == document_number,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ResourceConflictError(
                error="PATIENT_document_already_exists",
                message=(
                    "Ya existe un paciente registrado con ese tipo y número de documento."
                ),
            )

        # 4. Determine portal access
        should_grant_portal = grant_portal_access and email is not None

        # 5. Persist (portal_access starts False — grant_access() sets it to True)
        patient = Patient(
            document_type=document_type,
            document_number=document_number,
            first_name=first_name,
            last_name=last_name,
            birthdate=birthdate,
            gender=gender,
            phone=phone,
            phone_secondary=phone_secondary,
            email=email,
            address=address,
            city=city,
            state_province=state_province,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            insurance_provider=insurance_provider,
            insurance_policy_number=insurance_policy_number,
            blood_type=blood_type,
            allergies=allergies,
            chronic_conditions=chronic_conditions,
            referral_source=referral_source,
            notes=notes,
            is_active=True,
            no_show_count=0,
            portal_access=False,
            created_by=uuid.UUID(created_by_id),
        )
        db.add(patient)
        await db.flush()  # Assign patient.id without committing

        # 6. Auto-grant portal access (generates temp password + sends email)
        if should_grant_portal:
            try:
                from app.services.portal_access_service import portal_access_service

                await portal_access_service.grant_access(
                    db=db,
                    patient_id=str(patient.id),
                    invitation_channel="email",
                    created_by=created_by_id,
                    tenant_id=tenant_id,
                )
            except Exception:
                # Don't fail patient creation if portal access fails
                logger.warning(
                    "Auto-grant portal access failed for patient=%s",
                    str(patient.id)[:8],
                    exc_info=True,
                )

        # TODO: Auto-create odontogram_states for this patient — deferred to Sprint 5-6.

        logger.info(
            "Patient created in tenant=%s (id=%s)",
            tenant_id[:8],
            str(patient.id)[:8],
        )

        # Invalidate search cache for this tenant so the new patient appears
        await cache_delete_pattern(_invalidate_search_cache(tenant_id))

        return _patient_to_dict(patient, include_clinical_summary=True)

    # ─── Read ────────────────────────────────────────────────────────────

    async def get_patient(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        include_deleted: bool = False,
    ) -> dict[str, Any] | None:
        """Load a single patient by ID.

        Returns None when the patient does not exist. The caller is responsible
        for converting None to a 404 response.

        Args:
            include_deleted: When True, also returns soft-deleted patients
                             (clinic_owner / superadmin only — enforced in
                             the route layer, not here).
        """
        stmt = select(Patient).where(Patient.id == uuid.UUID(patient_id))
        if not include_deleted:
            stmt = stmt.where(Patient.is_active.is_(True))

        result = await db.execute(stmt)
        patient = result.scalar_one_or_none()

        if patient is None:
            return None

        return _patient_to_dict(patient, include_clinical_summary=True)

    # ─── List ────────────────────────────────────────────────────────────

    async def list_patients(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
        sort_by: str = "last_name",
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        """Return a paginated list of patients with optional filters.

        Full-text search over first_name, last_name, and document_number is
        performed via PostgreSQL's websearch_to_tsquery('spanish', ...) when
        the `search` parameter is provided. This requires a text() call because
        SQLAlchemy ORM has no first-class support for PostgreSQL FTS ranking.

        Supported sort_by values: last_name, created_at.
        Unsupported values default to last_name (defensive).
        """
        # Determine sort column and direction safely
        _allowed_sort = {"last_name", "created_at"}
        _sort_col = sort_by if sort_by in _allowed_sort else "last_name"
        _sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        offset = (page - 1) * page_size

        if search:
            # Full-text search path — uses raw SQL for FTS functions.
            # Bound parameters prevent injection.
            fts_base = """
                SELECT id
                FROM patients
                WHERE to_tsvector('spanish',
                    coalesce(first_name, '') || ' ' ||
                    coalesce(last_name, '') || ' ' ||
                    coalesce(document_number, '')
                ) @@ websearch_to_tsquery('spanish', :q)
            """
            params: dict[str, Any] = {"q": search.strip()}

            # Apply is_active filter inside FTS query
            if is_active is not None:
                fts_base += " AND is_active = :is_active"
                params["is_active"] = is_active

            # Count query
            count_sql = text(f"SELECT COUNT(*) FROM ({fts_base}) AS sub")
            count_result = await db.execute(count_sql, params)
            total: int = count_result.scalar_one()

            # Paginated query with sort
            list_sql = text(
                f"""
                SELECT id, first_name, last_name, document_type, document_number,
                       phone, email, is_active, created_at
                FROM patients
                WHERE to_tsvector('spanish',
                    coalesce(first_name, '') || ' ' ||
                    coalesce(last_name, '') || ' ' ||
                    coalesce(document_number, '')
                ) @@ websearch_to_tsquery('spanish', :q)
                {"AND is_active = :is_active" if is_active is not None else ""}
                ORDER BY {_sort_col} {_sort_dir}
                LIMIT :limit OFFSET :offset
                """
            )
            params["limit"] = page_size
            params["offset"] = offset

            rows_result = await db.execute(list_sql, params)
            rows = rows_result.mappings().all()

            items = [
                {
                    "id": str(row["id"]),
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "document_type": row["document_type"],
                    "document_number": row["document_number"],
                    "phone": row["phone"],
                    "email": row["email"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

            return {"items": items, "total": total, "page": page, "page_size": page_size}

        # Standard ORM path (no full-text search)
        stmt = select(Patient)

        if is_active is not None:
            stmt = stmt.where(Patient.is_active.is_(is_active))
        else:
            # Default: only active patients
            stmt = stmt.where(Patient.is_active.is_(True))

        if created_from is not None:
            stmt = stmt.where(Patient.created_at >= datetime(
                created_from.year, created_from.month, created_from.day,
                tzinfo=UTC,
            ))
        if created_to is not None:
            # Include the entire end day
            created_to_end = datetime(
                created_to.year, created_to.month, created_to.day,
                23, 59, 59, tzinfo=UTC,
            )
            stmt = stmt.where(Patient.created_at <= created_to_end)

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Apply sort
        sort_column = Patient.last_name if _sort_col == "last_name" else Patient.created_at
        if _sort_dir == "DESC":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.offset(offset).limit(page_size)

        patients_result = await db.execute(stmt)
        patients = patients_result.scalars().all()

        return {
            "items": [_patient_to_dict(p) for p in patients],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ─── Update ──────────────────────────────────────────────────────────

    async def update_patient(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        document_type: str | None = None,
        document_number: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        birthdate: date | None = None,
        gender: str | None = None,
        phone: str | None = None,
        phone_secondary: str | None = None,
        email: str | None = None,
        address: str | None = None,
        city: str | None = None,
        state_province: str | None = None,
        emergency_contact_name: str | None = None,
        emergency_contact_phone: str | None = None,
        insurance_provider: str | None = None,
        insurance_policy_number: str | None = None,
        blood_type: str | None = None,
        allergies: list[str] | None = None,
        chronic_conditions: list[str] | None = None,
        referral_source: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Apply partial updates to an existing active patient.

        Only non-None arguments are applied. If document_type or
        document_number is changing, uniqueness is re-checked.

        Raises:
            ResourceNotFoundError (404) — patient not found or inactive.
            ResourceConflictError (409) — new document already exists.
        """
        result = await db.execute(
            select(Patient).where(
                Patient.id == uuid.UUID(patient_id),
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            )

        # Re-check document uniqueness if either document field is changing
        new_doc_type = document_type if document_type is not None else patient.document_type
        new_doc_num = document_number if document_number is not None else patient.document_number
        doc_changed = (
            new_doc_type != patient.document_type
            or new_doc_num != patient.document_number
        )

        if doc_changed:
            conflict = await db.execute(
                select(Patient.id).where(
                    Patient.document_type == new_doc_type,
                    Patient.document_number == new_doc_num,
                    Patient.id != uuid.UUID(patient_id),
                )
            )
            if conflict.scalar_one_or_none() is not None:
                raise ResourceConflictError(
                    error="PATIENT_document_already_exists",
                    message=(
                        "Ya existe un paciente registrado con ese tipo y número de documento."
                    ),
                )

        # Apply only non-None updates
        if document_type is not None:
            patient.document_type = document_type
        if document_number is not None:
            patient.document_number = document_number
        if first_name is not None:
            patient.first_name = first_name
        if last_name is not None:
            patient.last_name = last_name
        if birthdate is not None:
            patient.birthdate = birthdate
        if gender is not None:
            patient.gender = gender
        if phone is not None:
            patient.phone = phone
        if phone_secondary is not None:
            patient.phone_secondary = phone_secondary
        if email is not None:
            patient.email = email
        if address is not None:
            patient.address = address
        if city is not None:
            patient.city = city
        if state_province is not None:
            patient.state_province = state_province
        if emergency_contact_name is not None:
            patient.emergency_contact_name = emergency_contact_name
        if emergency_contact_phone is not None:
            patient.emergency_contact_phone = emergency_contact_phone
        if insurance_provider is not None:
            patient.insurance_provider = insurance_provider
        if insurance_policy_number is not None:
            patient.insurance_policy_number = insurance_policy_number
        if blood_type is not None:
            patient.blood_type = blood_type
        if allergies is not None:
            patient.allergies = allergies
        if chronic_conditions is not None:
            patient.chronic_conditions = chronic_conditions
        if referral_source is not None:
            patient.referral_source = referral_source
        if notes is not None:
            patient.notes = notes

        await db.flush()
        await db.refresh(patient, attribute_names=["updated_at"])

        logger.info(
            "Patient updated in tenant=%s (id=%s)",
            tenant_id[:8],
            patient_id[:8],
        )

        # Invalidate cached detail and all search results for this tenant
        await cache_delete_pattern(_invalidate_search_cache(tenant_id))

        return _patient_to_dict(patient, include_clinical_summary=True)

    # ─── Deactivate ──────────────────────────────────────────────────────

    async def deactivate_patient(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
    ) -> dict[str, Any]:
        """Soft-deactivate a patient (is_active=False, deleted_at=now).

        Clinical data is NEVER hard-deleted per Resolución 1888 requirements.

        Raises:
            ResourceNotFoundError (404) — patient not found or already inactive.
        """
        result = await db.execute(
            select(Patient).where(
                Patient.id == uuid.UUID(patient_id),
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            )

        patient.is_active = False
        patient.deleted_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Patient deactivated in tenant=%s (id=%s)",
            tenant_id[:8],
            patient_id[:8],
        )

        # Invalidate search cache so deactivated patient disappears from results
        await cache_delete_pattern(_invalidate_search_cache(tenant_id))

        return _patient_to_dict(patient)

    # ─── Search ──────────────────────────────────────────────────────────

    async def search_patients(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        q: str,
    ) -> dict[str, Any]:
        """Fast patient type-ahead search backed by PostgreSQL FTS.

        Flow:
          1. Normalize query (strip + lower).
          2. Check Redis cache — return immediately on hit.
          3. Primary: FTS via websearch_to_tsquery('spanish', ...) with ts_rank.
          4. Fallback (0 FTS results): ILIKE on document_number and phone.
          5. Cache result for 120 seconds.
          6. Return up to 10 matches.

        Only searches active patients. PHI is never logged.
        """
        q_normalized = q.strip().lower()
        cache_key = _search_cache_key(tenant_id, q_normalized)

        # 1. Cache hit
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached

        # 2. Primary FTS search (raw SQL — FTS functions require text())
        fts_query = text("""
            SELECT id,
                   first_name || ' ' || last_name AS full_name,
                   document_number,
                   phone,
                   is_active
            FROM patients
            WHERE is_active = true
              AND to_tsvector('spanish',
                    coalesce(first_name, '') || ' ' ||
                    coalesce(last_name, '') || ' ' ||
                    coalesce(document_number, '') || ' ' ||
                    coalesce(phone, '')
                  ) @@ websearch_to_tsquery('spanish', :q)
            ORDER BY ts_rank(
                to_tsvector('spanish',
                    coalesce(first_name, '') || ' ' ||
                    coalesce(last_name, '') || ' ' ||
                    coalesce(document_number, '') || ' ' ||
                    coalesce(phone, '')
                ),
                websearch_to_tsquery('spanish', :q)
            ) DESC
            LIMIT 10
        """)

        fts_result = await db.execute(fts_query, {"q": q_normalized})
        rows = fts_result.mappings().all()

        # 3. Fallback to ILIKE if FTS returned nothing
        if not rows:
            fallback_query = text("""
                SELECT id,
                       first_name || ' ' || last_name AS full_name,
                       document_number,
                       phone,
                       is_active
                FROM patients
                WHERE is_active = true
                  AND (
                        document_number ILIKE :prefix || '%'
                     OR phone ILIKE '%' || :prefix || '%'
                  )
                ORDER BY last_name, first_name
                LIMIT 10
            """)
            fallback_result = await db.execute(fallback_query, {"prefix": q_normalized})
            rows = fallback_result.mappings().all()

        data = [
            {
                "id": str(row["id"]),
                "full_name": row["full_name"],
                "document_number": row["document_number"],
                "phone": row["phone"],
                "is_active": row["is_active"],
            }
            for row in rows
        ]

        response = {"data": data, "count": len(data)}

        # 4. Cache result
        with contextlib.suppress(Exception):
            await set_cached(cache_key, response, ttl_seconds=_SEARCH_CACHE_TTL)

        return response

    # ─── Export CSV ───────────────────────────────────────────────────────

    async def export_patients_csv(
        self,
        *,
        db: AsyncSession,
        is_active: bool | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
    ) -> AsyncGenerator[str, None]:
        """Yield patient data as CSV rows for streaming download.

        Uses chunked query execution to avoid loading all patient
        records into memory at once. The first yielded value is the
        CSV header line.

        Args:
            is_active: Filter by active/inactive status.
            created_from: Include patients created on or after this date.
            created_to: Include patients created on or before this date.
        """
        # Header row
        header_buf = io.StringIO()
        writer = csv.writer(header_buf)
        writer.writerow([
            "tipo_documento",
            "numero_documento",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "genero",
            "email",
            "telefono",
            "ciudad",
            "fecha_creacion",
        ])
        yield header_buf.getvalue()

        # Build query with filters
        stmt = select(Patient)

        if is_active is not None:
            stmt = stmt.where(Patient.is_active.is_(is_active))
        else:
            stmt = stmt.where(Patient.is_active.is_(True))

        if created_from is not None:
            stmt = stmt.where(Patient.created_at >= datetime(
                created_from.year, created_from.month, created_from.day,
                tzinfo=UTC,
            ))
        if created_to is not None:
            created_to_end = datetime(
                created_to.year, created_to.month, created_to.day,
                23, 59, 59, tzinfo=UTC,
            )
            stmt = stmt.where(Patient.created_at <= created_to_end)

        stmt = stmt.order_by(Patient.last_name.asc())

        # Stream results in chunks to keep memory bounded
        result = await db.stream_scalars(stmt)
        async for patient in result:
            row_buf = io.StringIO()
            row_writer = csv.writer(row_buf)
            row_writer.writerow([
                patient.document_type or "",
                patient.document_number or "",
                patient.first_name or "",
                patient.last_name or "",
                patient.birthdate.isoformat() if patient.birthdate else "",
                patient.gender or "",
                patient.email or "",
                patient.phone or "",
                patient.city or "",
                patient.created_at.isoformat() if patient.created_at else "",
            ])
            yield row_buf.getvalue()

    # ─── Merge Patients ──────────────────────────────────────────────────

    # Tables that hold a patient_id FK and need re-pointing during merge.
    _MERGE_TABLES: list[str] = [
        "clinical_records",
        "odontogram_states",
        "appointments",
        "invoices",
        "prescriptions",
        "consents",
        "diagnoses",
        "treatment_plans",
        "patient_documents",
        "implant_placements",
        "procedures",
        "quotations",
    ]

    async def merge_patients(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        primary_patient_id: str,
        secondary_patient_id: str,
        merged_by_id: str,
    ) -> dict[str, Any]:
        """Merge two patient records by transferring all clinical data.

        All FK references in related tables are re-pointed from the
        secondary patient to the primary patient in a single transaction.
        The secondary patient is then soft-deactivated.

        Uses raw SQL UPDATE with bound parameters for each table because
        the merge touches many tables that may not all have ORM models
        loaded, and the FK update is a simple SET operation.

        Args:
            primary_patient_id: The patient that survives the merge.
            secondary_patient_id: The patient to be absorbed and deactivated.
            merged_by_id: User ID performing the merge (for audit trail).

        Returns:
            dict with primary_patient_id, merged_records (counts per table),
            and deactivated_secondary flag.

        Raises:
            BusinessValidationError — if both IDs are the same.
            ResourceNotFoundError — if either patient is not found or inactive.
        """
        if primary_patient_id == secondary_patient_id:
            raise BusinessValidationError(
                message="No se puede fusionar un paciente consigo mismo."
            )

        # Load both patients (must exist and be active)
        primary_result = await db.execute(
            select(Patient).where(
                Patient.id == uuid.UUID(primary_patient_id),
                Patient.is_active.is_(True),
            )
        )
        primary = primary_result.scalar_one_or_none()
        if primary is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Primary Patient",
            )

        secondary_result = await db.execute(
            select(Patient).where(
                Patient.id == uuid.UUID(secondary_patient_id),
                Patient.is_active.is_(True),
            )
        )
        secondary = secondary_result.scalar_one_or_none()
        if secondary is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Secondary Patient",
            )

        # Transfer FK references across all clinical tables
        merged_records: dict[str, int] = {}
        params = {
            "primary_id": uuid.UUID(primary_patient_id),
            "secondary_id": uuid.UUID(secondary_patient_id),
        }

        for table_name in self._MERGE_TABLES:
            update_sql = text(
                f"UPDATE {table_name} "
                f"SET patient_id = :primary_id "
                f"WHERE patient_id = :secondary_id"
            )
            result = await db.execute(update_sql, params)
            merged_records[table_name] = result.rowcount

        # Deactivate the secondary patient
        secondary.is_active = False
        secondary.deleted_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Patients merged in tenant=%s: primary=%s secondary=%s tables=%d",
            tenant_id[:8],
            primary_patient_id[:8],
            secondary_patient_id[:8],
            sum(merged_records.values()),
        )

        # Invalidate all patient caches for this tenant
        await cache_delete_pattern(_invalidate_search_cache(tenant_id))

        return {
            "primary_patient_id": str(primary.id),
            "merged_records": merged_records,
            "deactivated_secondary": True,
        }


# Module-level singleton for dependency injection
patient_service = PatientService()
