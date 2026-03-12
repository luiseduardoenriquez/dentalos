"""Odontogram service — full dental chart management for a patient.

Handles the lifecycle of odontogram state, individual tooth-zone conditions,
immutable history tracking, point-in-time snapshots, and snapshot comparison.

Security invariants:
  - PHI (patient names, clinical notes) is NEVER logged.
  - Soft delete only — clinical data is never hard-deleted (Res. 1888).
  - All condition mutations produce an immutable history entry.
  - Cache is invalidated after every write operation.
"""

import base64
import contextlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, get_cached, set_cached
from app.core.error_codes import OdontogramErrors
from app.core.exceptions import (
    BusinessValidationError,
    OdontogramError,
    ResourceNotFoundError,
)
from app.core.odontogram_constants import (
    ANTERIOR_TEETH,
    VALID_CONDITION_CODES,
    VALID_DENTITION_TYPES,
    get_condition_by_code,
    get_teeth_for_dentition,
    get_valid_zones_for_tooth,
    is_zone_valid_for_condition,
    validate_tooth_for_dentition,
)
from app.models.tenant.odontogram import (
    OdontogramCondition,
    OdontogramHistory,
    OdontogramSnapshot,
    OdontogramState,
)
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.odontogram")

# ─── Constants ───────────────────────────────────────────────────────────────

_CACHE_TTL = 300  # 5 minutes (per spec)
_HISTORY_DEFAULT_LIMIT = 50
_TOOTH_DETAIL_HISTORY_LIMIT = 20


# ─── Cache helpers ───────────────────────────────────────────────────────────


def _odontogram_cache_key(tenant_id: str, patient_id: str) -> str:
    """Build Redis cache key for a patient's full odontogram state."""
    return f"dentalos:{tenant_id[:8]}:clinical:odontogram:{patient_id}"


# ─── Serialization helpers ───────────────────────────────────────────────────


def _condition_to_dict(cond: OdontogramCondition) -> dict[str, Any]:
    """Serialize an OdontogramCondition ORM instance to a plain dict."""
    condition_def = get_condition_by_code(cond.condition_code)
    return {
        "id": str(cond.id),
        "tooth_number": cond.tooth_number,
        "zone": cond.zone,
        "condition_code": cond.condition_code,
        "condition_name": condition_def["name_es"] if condition_def else None,
        "condition_color": condition_def["color_hex"] if condition_def else None,
        "severity": cond.severity,
        "notes": cond.notes,
        "source": cond.source,
        "created_by": str(cond.created_by) if cond.created_by else None,
        "created_at": cond.created_at,
        "updated_at": cond.updated_at,
    }


def _history_to_dict(
    hist: OdontogramHistory,
    performed_by_name: str | None = None,
) -> dict[str, Any]:
    """Serialize an OdontogramHistory ORM instance to a plain dict."""
    return {
        "id": str(hist.id),
        "tooth_number": hist.tooth_number,
        "zone": hist.zone,
        "action": hist.action,
        "condition_code": hist.condition_code,
        "previous_data": hist.previous_data,
        "new_data": hist.new_data,
        "performed_by": str(hist.performed_by) if hist.performed_by else None,
        "performed_by_name": performed_by_name,
        "created_at": hist.created_at,
    }


def _snapshot_to_dict(
    snap: OdontogramSnapshot,
    *,
    include_data: bool = False,
) -> dict[str, Any]:
    """Serialize an OdontogramSnapshot ORM instance to a plain dict."""
    data: dict[str, Any] = {
        "id": str(snap.id),
        "patient_id": str(snap.patient_id),
        "dentition_type": snap.dentition_type,
        "label": snap.label,
        "linked_record_id": str(snap.linked_record_id) if snap.linked_record_id else None,
        "linked_treatment_plan_id": (
            str(snap.linked_treatment_plan_id) if snap.linked_treatment_plan_id else None
        ),
        "created_by": str(snap.created_by) if snap.created_by else None,
        "created_at": snap.created_at,
    }
    if include_data:
        data["snapshot_data"] = snap.snapshot_data
    return data


# ─── Cursor helpers ──────────────────────────────────────────────────────────


def _encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    """Encode a pagination cursor as base64 of 'created_at_iso|uuid'."""
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a pagination cursor. Raises ValueError on malformed input."""
    raw = base64.b64decode(cursor.encode()).decode()
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise ValueError("Malformed cursor")
    created_at = datetime.fromisoformat(parts[0])
    row_id = uuid.UUID(parts[1])
    return created_at, row_id


# ─── Odontogram Service ─────────────────────────────────────────────────────


class OdontogramService:
    """Stateless odontogram service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path is already set by get_tenant_db() — methods do NOT
    call SET search_path themselves.
    """

    # ─── 1. Ensure State ─────────────────────────────────────────────────

    async def ensure_odontogram_exists(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> OdontogramState:
        """Ensure an OdontogramState row exists for the given patient.

        If one does not exist, creates a new one with default dentition_type='adult'.
        Returns the OdontogramState ORM instance.
        """
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(OdontogramState).where(
                OdontogramState.patient_id == pid,
                OdontogramState.is_active.is_(True),
            )
        )
        state = result.scalar_one_or_none()

        if state is not None:
            return state

        # Create default state
        state = OdontogramState(
            patient_id=pid,
            dentition_type="adult",
            is_active=True,
        )
        db.add(state)
        await db.flush()

        logger.info(
            "Odontogram state created for patient=%s",
            patient_id[:8],
        )

        return state

    # ─── 2. Get Odontogram ───────────────────────────────────────────────

    async def get_odontogram(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Return the full odontogram state for a patient.

        Checks Redis cache first. On miss, builds the complete tooth
        structure in Python from a flat query of all active conditions
        and a history count subquery.

        The dataset is small (max ~312 condition rows for 52 teeth x 6 zones)
        so building in Python is more maintainable than a massive SQL join.
        """
        cache_key = _odontogram_cache_key(tenant_id, patient_id)

        # 1. Cache hit
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached

        # 2. Build from DB
        return await self._build_odontogram(db=db, patient_id=patient_id, tenant_id=tenant_id)

    async def _build_odontogram(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        skip_cache: bool = False,
    ) -> dict[str, Any]:
        """Build the full odontogram structure from DB and optionally cache it.

        Shared by get_odontogram (with cache) and create_snapshot (without cache).
        """
        pid = uuid.UUID(patient_id)

        # Ensure state exists
        state = await self.ensure_odontogram_exists(db=db, patient_id=patient_id)
        dentition_type = state.dentition_type

        # Fetch all active conditions for this patient in one query
        conditions_result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.patient_id == pid,
                OdontogramCondition.is_active.is_(True),
            )
        )
        conditions = conditions_result.scalars().all()

        # Index conditions by (tooth_number, zone) for O(1) lookup
        cond_by_tooth_zone: dict[tuple[int, str], OdontogramCondition] = {}
        for cond in conditions:
            cond_by_tooth_zone[(cond.tooth_number, cond.zone)] = cond

        # Fetch history counts per tooth in one query
        history_counts_result = await db.execute(
            select(
                OdontogramHistory.tooth_number,
                func.count(OdontogramHistory.id).label("cnt"),
            )
            .where(OdontogramHistory.patient_id == pid)
            .group_by(OdontogramHistory.tooth_number)
        )
        history_counts: dict[int, int] = {
            row.tooth_number: row.cnt for row in history_counts_result
        }

        # Build tooth structure
        teeth_list = get_teeth_for_dentition(dentition_type)
        teeth: list[dict[str, Any]] = []

        for tooth_num in teeth_list:
            valid_zones = get_valid_zones_for_tooth(tooth_num)
            zones: list[dict[str, Any]] = []

            for zone_name in valid_zones:
                cond = cond_by_tooth_zone.get((tooth_num, zone_name))
                zone_data: dict[str, Any] = {"zone": zone_name}
                if cond is not None:
                    zone_data["condition"] = _condition_to_dict(cond)
                else:
                    zone_data["condition"] = None
                zones.append(zone_data)

            teeth.append({
                "tooth_number": tooth_num,
                "zones": zones,
                "history_count": history_counts.get(tooth_num, 0),
            })

        # Compute aggregates
        total_conditions = len(conditions)

        # Last updated = MAX of all conditions' updated_at
        last_updated: datetime | None = None
        if conditions:
            last_updated = max(c.updated_at for c in conditions)

        result = {
            "patient_id": patient_id,
            "dentition_type": dentition_type,
            "teeth": teeth,
            "total_conditions": total_conditions,
            "last_updated": last_updated,
        }

        # Cache the result (unless caller explicitly skipped)
        if not skip_cache:
            cache_key = _odontogram_cache_key(tenant_id, patient_id)
            with contextlib.suppress(Exception):
                await set_cached(cache_key, result, ttl_seconds=_CACHE_TTL)

        return result

    # ─── 3. Update Condition ─────────────────────────────────────────────

    async def update_condition(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        user_id: str,
        tooth_number: int,
        zone: str,
        condition_code: str,
        severity: str | None = None,
        notes: str | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Add or update a condition on a specific tooth zone.

        Validates tooth number against the patient's dentition type, zone
        against the tooth morphology, and condition code against the catalog.
        Creates an immutable history entry for every mutation.

        Returns a dict matching ConditionUpdateResult shape.
        """
        state = await self.ensure_odontogram_exists(db=db, patient_id=patient_id)
        pid = uuid.UUID(patient_id)
        uid = uuid.UUID(user_id)

        # Validate tooth number for dentition
        if not validate_tooth_for_dentition(tooth_number, state.dentition_type):
            raise OdontogramError(
                error=OdontogramErrors.INVALID_TOOTH_NUMBER,
                message=(
                    f"Diente {tooth_number} no es valido para denticion "
                    f"'{state.dentition_type}'."
                ),
                status_code=422,
            )

        # Validate zone for tooth
        valid_zones = get_valid_zones_for_tooth(tooth_number)
        if zone not in valid_zones and zone != "full":
            raise OdontogramError(
                error=OdontogramErrors.INVALID_TOOTH_NUMBER,
                message=(
                    f"Zona '{zone}' no es valida para el diente {tooth_number}. "
                    f"Zonas validas: {', '.join(valid_zones)}, full."
                ),
                status_code=422,
            )

        # Validate condition code exists
        if condition_code not in VALID_CONDITION_CODES:
            raise OdontogramError(
                error=OdontogramErrors.INVALID_FDI_CODE,
                message=f"Codigo de condicion '{condition_code}' no existe en el catalogo.",
                status_code=422,
            )

        # Validate zone is valid for this condition
        if not is_zone_valid_for_condition(zone, condition_code):
            condition_def = get_condition_by_code(condition_code)
            valid_cond_zones = condition_def["zones"] if condition_def else []
            raise OdontogramError(
                error=OdontogramErrors.INVALID_TOOTH_NUMBER,
                message=(
                    f"Zona '{zone}' no es valida para la condicion '{condition_code}'. "
                    f"Zonas validas: {', '.join(valid_cond_zones)}."
                ),
                status_code=422,
            )

        # Check for existing condition at this (patient_id, tooth_number, zone)
        existing_result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.patient_id == pid,
                OdontogramCondition.tooth_number == tooth_number,
                OdontogramCondition.zone == zone,
                OdontogramCondition.is_active.is_(True),
            )
        )
        existing = existing_result.scalar_one_or_none()

        previous_condition: dict[str, Any] | None = None
        action: str

        if existing is not None:
            # Update existing condition
            previous_condition = _condition_to_dict(existing)
            previous_data = {
                "condition_code": existing.condition_code,
                "severity": existing.severity,
                "notes": existing.notes,
                "source": existing.source,
            }

            existing.condition_code = condition_code
            existing.severity = severity
            existing.notes = notes
            existing.source = source
            existing.created_by = uid
            action = "update"
            condition_obj = existing
        else:
            # Create new condition
            previous_data = None
            condition_obj = OdontogramCondition(
                patient_id=pid,
                tooth_number=tooth_number,
                zone=zone,
                condition_code=condition_code,
                severity=severity,
                notes=notes,
                source=source,
                created_by=uid,
                is_active=True,
            )
            db.add(condition_obj)
            action = "add"

        await db.flush()

        # Build new_data for history
        new_data = {
            "condition_code": condition_code,
            "severity": severity,
            "notes": notes,
            "source": source,
        }

        # Create immutable history entry
        history = OdontogramHistory(
            patient_id=pid,
            tooth_number=tooth_number,
            zone=zone,
            action=action,
            condition_code=condition_code,
            previous_data=previous_data,
            new_data=new_data,
            performed_by=uid,
        )
        db.add(history)
        await db.flush()

        # Invalidate cache
        await cache_delete(_odontogram_cache_key(tenant_id, patient_id))

        logger.info(
            "Condition %s on tooth=%d zone=%s for patient=%s",
            action,
            tooth_number,
            zone,
            patient_id[:8],
        )

        return {
            "condition_id": str(condition_obj.id),
            "action": action,
            "previous_condition": previous_condition,
            "history_entry_id": str(history.id),
        }

    # ─── 4. Remove Condition ─────────────────────────────────────────────

    async def remove_condition(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        user_id: str,
        condition_id: str,
    ) -> dict[str, Any]:
        """Soft-delete a condition and record the removal in history.

        Returns the removed condition data.

        Raises:
            ResourceNotFoundError — condition not found for this patient.
        """
        pid = uuid.UUID(patient_id)
        cid = uuid.UUID(condition_id)
        uid = uuid.UUID(user_id)

        result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.id == cid,
                OdontogramCondition.patient_id == pid,
                OdontogramCondition.is_active.is_(True),
            )
        )
        condition = result.scalar_one_or_none()

        if condition is None:
            raise ResourceNotFoundError(
                error=OdontogramErrors.CONDITION_NOT_FOUND,
                resource_name="OdontogramCondition",
            )

        # Capture current state before soft-delete
        previous_data = {
            "condition_code": condition.condition_code,
            "severity": condition.severity,
            "notes": condition.notes,
            "source": condition.source,
        }
        removed_data = _condition_to_dict(condition)

        # Soft-delete
        condition.is_active = False
        condition.deleted_at = datetime.now(UTC)

        # Create history entry
        history = OdontogramHistory(
            patient_id=pid,
            tooth_number=condition.tooth_number,
            zone=condition.zone,
            action="remove",
            condition_code=condition.condition_code,
            previous_data=previous_data,
            new_data=None,
            performed_by=uid,
        )
        db.add(history)
        await db.flush()

        # Invalidate cache
        await cache_delete(_odontogram_cache_key(tenant_id, patient_id))

        logger.info(
            "Condition removed on tooth=%d zone=%s for patient=%s",
            condition.tooth_number,
            condition.zone,
            patient_id[:8],
        )

        return removed_data

    # ─── 5. Get History ──────────────────────────────────────────────────

    async def get_history(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tooth_number: int | None = None,
        zone: str | None = None,
        cursor: str | None = None,
        limit: int = _HISTORY_DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Return cursor-paginated history entries for a patient's odontogram.

        Cursor pagination uses (created_at DESC, id DESC). The cursor is a
        base64-encoded string of 'created_at_iso|uuid'.

        Optional filters: tooth_number, zone.
        LEFT JOINs the users table to resolve performed_by_name.
        """
        pid = uuid.UUID(patient_id)

        # Build base query with LEFT JOIN to users for performed_by_name
        stmt = (
            select(OdontogramHistory, User.name.label("performer_name"))
            .outerjoin(User, OdontogramHistory.performed_by == User.id)
            .where(OdontogramHistory.patient_id == pid)
        )

        # Apply optional filters
        if tooth_number is not None:
            stmt = stmt.where(OdontogramHistory.tooth_number == tooth_number)
        if zone is not None:
            stmt = stmt.where(OdontogramHistory.zone == zone)

        # Apply cursor filter
        if cursor is not None:
            try:
                cursor_created_at, cursor_id = _decode_cursor(cursor)
            except (ValueError, Exception):
                raise BusinessValidationError(
                    message="Cursor de paginacion invalido.",
                )
            # Seek past the cursor position: rows older than cursor, or same time but smaller id
            stmt = stmt.where(
                (OdontogramHistory.created_at < cursor_created_at)
                | (
                    (OdontogramHistory.created_at == cursor_created_at)
                    & (OdontogramHistory.id < cursor_id)
                )
            )

        # Order and limit — fetch one extra to detect has_more
        stmt = stmt.order_by(
            OdontogramHistory.created_at.desc(),
            OdontogramHistory.id.desc(),
        ).limit(limit + 1)

        result = await db.execute(stmt)
        rows = result.all()

        has_more = len(rows) > limit
        rows = rows[:limit]

        items: list[dict[str, Any]] = []
        for row in rows:
            history_obj = row[0]  # OdontogramHistory
            performer_name = row[1]  # User.name or None
            items.append(_history_to_dict(history_obj, performed_by_name=performer_name))

        next_cursor: str | None = None
        if has_more and items:
            last = rows[-1][0]  # last OdontogramHistory object
            next_cursor = _encode_cursor(last.created_at, last.id)

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # ─── 6. Create Snapshot ──────────────────────────────────────────────

    async def create_snapshot(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        user_id: str,
        label: str | None = None,
        linked_record_id: str | None = None,
        linked_treatment_plan_id: str | None = None,
    ) -> dict[str, Any]:
        """Capture a point-in-time snapshot of the patient's odontogram.

        Fetches the current full odontogram (bypassing cache) and stores
        the entire structure as JSONB in the snapshot_data column.
        """
        # Build fresh odontogram data (skip cache to get current state)
        odontogram_data = await self._build_odontogram(
            db=db,
            patient_id=patient_id,
            tenant_id=tenant_id,
            skip_cache=True,
        )

        pid = uuid.UUID(patient_id)
        uid = uuid.UUID(user_id)

        snapshot = OdontogramSnapshot(
            patient_id=pid,
            snapshot_data=odontogram_data,
            dentition_type=odontogram_data["dentition_type"],
            label=label,
            linked_record_id=uuid.UUID(linked_record_id) if linked_record_id else None,
            linked_treatment_plan_id=(
                uuid.UUID(linked_treatment_plan_id) if linked_treatment_plan_id else None
            ),
            created_by=uid,
        )
        db.add(snapshot)
        await db.flush()

        logger.info(
            "Snapshot created for patient=%s (id=%s)",
            patient_id[:8],
            str(snapshot.id)[:8],
        )

        return _snapshot_to_dict(snapshot, include_data=True)

    # ─── 7. Get Snapshot ─────────────────────────────────────────────────

    async def get_snapshot(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        snapshot_id: str,
    ) -> dict[str, Any]:
        """Fetch a single snapshot by ID, including the full snapshot_data.

        Raises:
            ResourceNotFoundError — snapshot not found for this patient.
        """
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(snapshot_id)

        result = await db.execute(
            select(OdontogramSnapshot).where(
                OdontogramSnapshot.id == sid,
                OdontogramSnapshot.patient_id == pid,
            )
        )
        snapshot = result.scalar_one_or_none()

        if snapshot is None:
            raise ResourceNotFoundError(
                error=OdontogramErrors.SNAPSHOT_FAILED,
                resource_name="OdontogramSnapshot",
            )

        return _snapshot_to_dict(snapshot, include_data=True)

    # ─── 8. List Snapshots ───────────────────────────────────────────────

    async def list_snapshots(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any]:
        """List all snapshots for a patient, ordered by created_at DESC.

        Returns metadata only (no snapshot_data) for performance.
        """
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(OdontogramSnapshot)
            .where(OdontogramSnapshot.patient_id == pid)
            .order_by(OdontogramSnapshot.created_at.desc())
        )
        snapshots = result.scalars().all()

        return {
            "items": [_snapshot_to_dict(s, include_data=False) for s in snapshots],
            "total": len(snapshots),
        }

    # ─── 9. Compare Snapshots ────────────────────────────────────────────

    async def compare_snapshots(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        snapshot_a_id: str,
        snapshot_b_id: str,
    ) -> dict[str, Any]:
        """Diff two snapshots by comparing conditions keyed by (tooth_number, zone).

        Returns:
            added   — conditions in B not in A
            removed — conditions in A not in B
            changed — conditions in both but with different data
        """
        snap_a = await self.get_snapshot(
            db=db, patient_id=patient_id, snapshot_id=snapshot_a_id
        )
        snap_b = await self.get_snapshot(
            db=db, patient_id=patient_id, snapshot_id=snapshot_b_id
        )

        # Extract condition maps from each snapshot's tooth structure
        map_a = self._extract_condition_map(snap_a["snapshot_data"])
        map_b = self._extract_condition_map(snap_b["snapshot_data"])

        keys_a = set(map_a.keys())
        keys_b = set(map_b.keys())

        # Added: in B but not A
        added = [map_b[k] for k in sorted(keys_b - keys_a)]

        # Removed: in A but not B
        removed = [map_a[k] for k in sorted(keys_a - keys_b)]

        # Changed: in both but different
        changed: list[dict[str, Any]] = []
        for key in sorted(keys_a & keys_b):
            cond_a = map_a[key]
            cond_b = map_b[key]
            # Compare meaningful fields
            if (
                cond_a.get("condition_code") != cond_b.get("condition_code")
                or cond_a.get("severity") != cond_b.get("severity")
                or cond_a.get("notes") != cond_b.get("notes")
            ):
                changed.append({
                    "tooth_number": key[0],
                    "zone": key[1],
                    "before": cond_a,
                    "after": cond_b,
                })

        return {
            "snapshot_a_id": snapshot_a_id,
            "snapshot_b_id": snapshot_b_id,
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    @staticmethod
    def _extract_condition_map(
        snapshot_data: dict[str, Any],
    ) -> dict[tuple[int, str], dict[str, Any]]:
        """Build a dict keyed by (tooth_number, zone) from a snapshot's teeth structure.

        Only includes zones that have an active condition.
        """
        condition_map: dict[tuple[int, str], dict[str, Any]] = {}
        for tooth in snapshot_data.get("teeth", []):
            tooth_num = tooth["tooth_number"]
            for zone_data in tooth.get("zones", []):
                cond = zone_data.get("condition")
                if cond is not None:
                    key = (tooth_num, zone_data["zone"])
                    condition_map[key] = cond
        return condition_map

    # ─── 10. Get Tooth Detail ────────────────────────────────────────────

    async def get_tooth_detail(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tooth_number: int,
    ) -> dict[str, Any]:
        """Return all active conditions and recent history for a specific tooth.

        Combines condition data and the last 20 history entries for the tooth.
        """
        pid = uuid.UUID(patient_id)

        # Fetch all active conditions for this tooth
        conditions_result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.patient_id == pid,
                OdontogramCondition.tooth_number == tooth_number,
                OdontogramCondition.is_active.is_(True),
            )
        )
        conditions = conditions_result.scalars().all()

        # Fetch recent history for this tooth (with performer names)
        history_result = await db.execute(
            select(OdontogramHistory, User.name.label("performer_name"))
            .outerjoin(User, OdontogramHistory.performed_by == User.id)
            .where(
                OdontogramHistory.patient_id == pid,
                OdontogramHistory.tooth_number == tooth_number,
            )
            .order_by(
                OdontogramHistory.created_at.desc(),
                OdontogramHistory.id.desc(),
            )
            .limit(_TOOTH_DETAIL_HISTORY_LIMIT)
        )
        history_rows = history_result.all()

        return {
            "tooth_number": tooth_number,
            "is_anterior": tooth_number in ANTERIOR_TEETH,
            "conditions": [_condition_to_dict(c) for c in conditions],
            "history": [
                _history_to_dict(row[0], performed_by_name=row[1])
                for row in history_rows
            ],
        }

    # ─── 11. Bulk Update ─────────────────────────────────────────────────

    async def bulk_update(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        user_id: str,
        updates: list[dict[str, Any]],
        session_notes: str | None = None,
    ) -> dict[str, Any]:
        """Apply multiple condition updates in a single atomic operation.

        ATOMIC: validates ALL updates first. If ANY validation fails, the
        entire batch is rejected with details of which items failed.
        Then persists all in a loop, creating history entries for each.
        Single cache invalidation at the end.

        Returns a dict matching BulkUpdateResult shape.

        Raises:
            BusinessValidationError — one or more updates failed validation.
        """
        state = await self.ensure_odontogram_exists(db=db, patient_id=patient_id)
        pid = uuid.UUID(patient_id)
        uid = uuid.UUID(user_id)

        # Phase 1: Validate all updates before persisting any
        errors: dict[str, list[str]] = {}
        for idx, update in enumerate(updates):
            item_errors: list[str] = []
            tn = update["tooth_number"]
            z = update["zone"]
            cc = update["condition_code"]

            if not validate_tooth_for_dentition(tn, state.dentition_type):
                item_errors.append(
                    f"Diente {tn} no es valido para denticion '{state.dentition_type}'."
                )

            if cc not in VALID_CONDITION_CODES:
                item_errors.append(
                    f"Codigo de condicion '{cc}' no existe en el catalogo."
                )
            else:
                # Only validate zone-for-condition if condition code is valid
                valid_zones = get_valid_zones_for_tooth(tn)
                if z not in valid_zones and z != "full":
                    item_errors.append(
                        f"Zona '{z}' no es valida para el diente {tn}."
                    )
                if not is_zone_valid_for_condition(z, cc):
                    item_errors.append(
                        f"Zona '{z}' no es valida para la condicion '{cc}'."
                    )

            if item_errors:
                errors[f"updates[{idx}]"] = item_errors

        if errors:
            raise BusinessValidationError(
                message="Una o mas actualizaciones contienen errores de validacion.",
                field_errors=errors,
            )

        # Phase 2: Persist all updates
        # Pre-load all existing active conditions for this patient to avoid N+1
        existing_result = await db.execute(
            select(OdontogramCondition).where(
                OdontogramCondition.patient_id == pid,
                OdontogramCondition.is_active.is_(True),
            )
        )
        existing_conditions = existing_result.scalars().all()
        existing_map: dict[tuple[int, str], OdontogramCondition] = {
            (c.tooth_number, c.zone): c for c in existing_conditions
        }

        results: list[dict[str, Any]] = []
        added_count = 0
        updated_count = 0

        for update in updates:
            tn = update["tooth_number"]
            z = update["zone"]
            cc = update["condition_code"]
            sev = update.get("severity")
            notes = update.get("notes")
            src = update.get("source", "manual")

            existing = existing_map.get((tn, z))
            previous_condition: dict[str, Any] | None = None
            action: str

            if existing is not None:
                # Update in place
                previous_condition = _condition_to_dict(existing)
                previous_data = {
                    "condition_code": existing.condition_code,
                    "severity": existing.severity,
                    "notes": existing.notes,
                    "source": existing.source,
                }

                existing.condition_code = cc
                existing.severity = sev
                existing.notes = notes
                existing.source = src
                existing.created_by = uid
                action = "update"
                condition_obj = existing
                updated_count += 1
            else:
                # Create new
                previous_data = None
                condition_obj = OdontogramCondition(
                    patient_id=pid,
                    tooth_number=tn,
                    zone=z,
                    condition_code=cc,
                    severity=sev,
                    notes=notes,
                    source=src,
                    created_by=uid,
                    is_active=True,
                )
                db.add(condition_obj)
                # Update the map so subsequent items in the batch see this new condition
                existing_map[(tn, z)] = condition_obj
                action = "add"
                added_count += 1

            await db.flush()

            # Build new_data for history
            new_data = {
                "condition_code": cc,
                "severity": sev,
                "notes": notes,
                "source": src,
            }

            # Create history entry
            history = OdontogramHistory(
                patient_id=pid,
                tooth_number=tn,
                zone=z,
                action=action,
                condition_code=cc,
                previous_data=previous_data,
                new_data=new_data,
                performed_by=uid,
            )
            db.add(history)
            await db.flush()

            results.append({
                "condition_id": str(condition_obj.id),
                "action": action,
                "previous_condition": previous_condition,
                "history_entry_id": str(history.id),
            })

        # Single cache invalidation at the end
        await cache_delete(_odontogram_cache_key(tenant_id, patient_id))

        logger.info(
            "Bulk update: %d processed (%d added, %d updated) for patient=%s",
            len(updates),
            added_count,
            updated_count,
            patient_id[:8],
        )

        return {
            "processed": len(results),
            "added": added_count,
            "updated": updated_count,
            "results": results,
        }

    # ─── 12. Toggle Dentition ────────────────────────────────────────────

    async def toggle_dentition(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
        dentition_type: str,
    ) -> dict[str, Any]:
        """Switch the dentition mode for a patient's odontogram.

        Validates dentition_type against allowed values, updates the state,
        and invalidates the cache.

        Returns the updated state dict.
        """
        if dentition_type not in VALID_DENTITION_TYPES:
            raise OdontogramError(
                error=OdontogramErrors.INVALID_TOOTH_NUMBER,
                message=(
                    f"Tipo de denticion '{dentition_type}' no es valido. "
                    f"Valores permitidos: {', '.join(sorted(VALID_DENTITION_TYPES))}."
                ),
                status_code=422,
            )

        state = await self.ensure_odontogram_exists(db=db, patient_id=patient_id)

        state.dentition_type = dentition_type
        await db.flush()
        await db.refresh(state)

        # Invalidate cache
        await cache_delete(_odontogram_cache_key(tenant_id, patient_id))

        logger.info(
            "Dentition toggled to '%s' for patient=%s",
            dentition_type,
            patient_id[:8],
        )

        return {
            "id": str(state.id),
            "patient_id": str(state.patient_id),
            "dentition_type": state.dentition_type,
            "is_active": state.is_active,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
        }


# Module-level singleton for dependency injection
odontogram_service = OdontogramService()
