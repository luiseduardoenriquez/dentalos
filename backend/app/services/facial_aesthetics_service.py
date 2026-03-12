"""Facial aesthetics service — injection session management.

Handles the lifecycle of facial aesthetics sessions, injection point tracking,
immutable history, and point-in-time snapshots.

Security invariants:
  - PHI (patient names, clinical notes) is NEVER logged.
  - Soft delete only — clinical data is never hard-deleted (Res. 1888).
  - All injection mutations produce an immutable history entry.
"""

import base64
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.error_codes import FacialAestheticsErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.facial_aesthetics import (
    FacialAestheticsHistory,
    FacialAestheticsInjection,
    FacialAestheticsSession,
    FacialAestheticsSnapshot,
)
from app.models.tenant.patient import Patient
from app.models.tenant.user import User
from app.schemas.facial_aesthetics import VALID_ZONES

logger = logging.getLogger("dentalos.facial_aesthetics")

# ─── Constants ───────────────────────────────────────────────────────────────

_HISTORY_DEFAULT_LIMIT = 50


# ─── Cursor helpers ──────────────────────────────────────────────────────────


def _encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.b64decode(cursor.encode()).decode()
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise ValueError("Malformed cursor")
    created_at = datetime.fromisoformat(parts[0])
    row_id = uuid.UUID(parts[1])
    return created_at, row_id


# ─── Serialization helpers ──────────────────────────────────────────────────


def _injection_to_dict(inj: FacialAestheticsInjection) -> dict[str, Any]:
    return {
        "id": str(inj.id),
        "session_id": str(inj.session_id),
        "patient_id": str(inj.patient_id),
        "zone_id": inj.zone_id,
        "injection_type": inj.injection_type,
        "product_name": inj.product_name,
        "dose_units": float(inj.dose_units) if inj.dose_units is not None else None,
        "dose_volume_ml": float(inj.dose_volume_ml) if inj.dose_volume_ml is not None else None,
        "depth": inj.depth,
        "coordinates_x": float(inj.coordinates_x) if inj.coordinates_x is not None else None,
        "coordinates_y": float(inj.coordinates_y) if inj.coordinates_y is not None else None,
        "notes": inj.notes,
        "created_by": str(inj.created_by) if inj.created_by else None,
        "created_at": inj.created_at.isoformat() if inj.created_at else None,
        "updated_at": inj.updated_at.isoformat() if inj.updated_at else None,
    }


def _session_to_dict(
    session: FacialAestheticsSession,
    *,
    include_injections: bool = True,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(session.id),
        "patient_id": str(session.patient_id),
        "doctor_id": str(session.doctor_id),
        "diagram_type": session.diagram_type,
        "session_date": session.session_date.isoformat() if session.session_date else None,
        "notes": session.notes,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }
    if include_injections:
        active = [i for i in (session.injections or []) if i.is_active]
        result["injections"] = [_injection_to_dict(i) for i in active]
    return result


def _session_to_list_item(
    session: FacialAestheticsSession,
    injection_count: int,
) -> dict[str, Any]:
    return {
        "id": str(session.id),
        "patient_id": str(session.patient_id),
        "doctor_id": str(session.doctor_id),
        "diagram_type": session.diagram_type,
        "session_date": session.session_date.isoformat() if session.session_date else None,
        "notes": session.notes,
        "injection_count": injection_count,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def _history_to_dict(
    hist: FacialAestheticsHistory,
    performed_by_name: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(hist.id),
        "session_id": str(hist.session_id),
        "zone_id": hist.zone_id,
        "action": hist.action,
        "injection_type": hist.injection_type,
        "previous_data": hist.previous_data,
        "new_data": hist.new_data,
        "performed_by": str(hist.performed_by) if hist.performed_by else None,
        "performed_by_name": performed_by_name,
        "created_at": hist.created_at.isoformat() if hist.created_at else None,
    }


def _snapshot_to_dict(
    snap: FacialAestheticsSnapshot,
    *,
    include_data: bool = False,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(snap.id),
        "patient_id": str(snap.patient_id),
        "session_id": str(snap.session_id) if snap.session_id else None,
        "diagram_type": snap.diagram_type,
        "label": snap.label,
        "linked_record_id": str(snap.linked_record_id) if snap.linked_record_id else None,
        "created_by": str(snap.created_by) if snap.created_by else None,
        "created_at": snap.created_at.isoformat() if snap.created_at else None,
    }
    if include_data:
        data["snapshot_data"] = snap.snapshot_data
    return data


# ─── Validation helpers ──────────────────────────────────────────────────────


async def _ensure_patient_active(db: AsyncSession, patient_id: uuid.UUID) -> None:
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


# ─── Service ──────────────────────────────────────────────────────────────────


class FacialAestheticsService:
    """Stateless facial aesthetics service."""

    # ─── Sessions ────────────────────────────────────────────────────────

    async def create_session(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a facial aesthetics session."""
        pid = uuid.UUID(patient_id)
        did = uuid.UUID(doctor_id)

        await _ensure_patient_active(db, pid)

        session = FacialAestheticsSession(
            patient_id=pid,
            doctor_id=did,
            diagram_type=data.get("diagram_type", "face_front"),
            session_date=data["session_date"],
            notes=data.get("notes"),
            is_active=True,
        )
        db.add(session)
        await db.flush()

        logger.info(
            "FacialAestheticsSession created: patient=%s session=%s",
            str(pid)[:8],
            str(session.id)[:8],
        )

        result = _session_to_dict(session, include_injections=False)
        result["injections"] = []
        return result

    async def list_sessions(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return paginated list of sessions for a patient."""
        pid = uuid.UUID(patient_id)

        count_stmt = (
            select(func.count())
            .select_from(FacialAestheticsSession)
            .where(
                FacialAestheticsSession.patient_id == pid,
                FacialAestheticsSession.is_active.is_(True),
            )
        )
        total = (await db.execute(count_stmt)).scalar_one()

        # Injection counts subquery
        inj_count_subq = (
            select(
                FacialAestheticsInjection.session_id,
                func.count().label("injection_count"),
            )
            .where(FacialAestheticsInjection.is_active.is_(True))
            .group_by(FacialAestheticsInjection.session_id)
            .subquery()
        )

        offset = (page - 1) * page_size
        stmt = (
            select(
                FacialAestheticsSession,
                func.coalesce(inj_count_subq.c.injection_count, 0).label("injection_count"),
            )
            .outerjoin(
                inj_count_subq,
                FacialAestheticsSession.id == inj_count_subq.c.session_id,
            )
            .where(
                FacialAestheticsSession.patient_id == pid,
                FacialAestheticsSession.is_active.is_(True),
            )
            .order_by(FacialAestheticsSession.session_date.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).all()

        items = [_session_to_list_item(row[0], row[1]) for row in rows]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_session(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Get a single session with its active injections."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)

        result = await db.execute(
            select(FacialAestheticsSession)
            .options(selectinload(FacialAestheticsSession.injections))
            .where(
                FacialAestheticsSession.id == sid,
                FacialAestheticsSession.patient_id == pid,
                FacialAestheticsSession.is_active.is_(True),
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise ResourceNotFoundError(
                error=FacialAestheticsErrors.SESSION_NOT_FOUND,
                resource_name="FacialAestheticsSession",
            )

        return _session_to_dict(session)

    async def update_session(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update session notes or diagram type."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)

        result = await db.execute(
            select(FacialAestheticsSession)
            .options(selectinload(FacialAestheticsSession.injections))
            .where(
                FacialAestheticsSession.id == sid,
                FacialAestheticsSession.patient_id == pid,
                FacialAestheticsSession.is_active.is_(True),
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise ResourceNotFoundError(
                error=FacialAestheticsErrors.SESSION_NOT_FOUND,
                resource_name="FacialAestheticsSession",
            )

        if "diagram_type" in data and data["diagram_type"] is not None:
            session.diagram_type = data["diagram_type"]
        if "notes" in data:
            session.notes = data["notes"]

        await db.flush()
        await db.refresh(session)
        # Re-fetch with selectinload to get injections
        result = await db.execute(
            select(FacialAestheticsSession)
            .options(selectinload(FacialAestheticsSession.injections))
            .where(FacialAestheticsSession.id == sid)
        )
        session = result.scalar_one()
        return _session_to_dict(session)

    async def delete_session(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Soft-delete a session."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)

        result = await db.execute(
            select(FacialAestheticsSession).where(
                FacialAestheticsSession.id == sid,
                FacialAestheticsSession.patient_id == pid,
                FacialAestheticsSession.is_active.is_(True),
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise ResourceNotFoundError(
                error=FacialAestheticsErrors.SESSION_NOT_FOUND,
                resource_name="FacialAestheticsSession",
            )

        session.is_active = False
        session.deleted_at = datetime.now(UTC)
        await db.flush()

        logger.info(
            "FacialAestheticsSession deleted: session=%s",
            str(sid)[:8],
        )

        return {"message": "Sesión eliminada exitosamente."}

    # ─── Injections ──────────────────────────────────────────────────────

    async def add_injection(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Add an injection point to a session."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)
        uid = uuid.UUID(user_id)

        # Validate session
        session_result = await db.execute(
            select(FacialAestheticsSession.id).where(
                FacialAestheticsSession.id == sid,
                FacialAestheticsSession.patient_id == pid,
                FacialAestheticsSession.is_active.is_(True),
            )
        )
        if session_result.scalar_one_or_none() is None:
            raise ResourceNotFoundError(
                error=FacialAestheticsErrors.SESSION_NOT_FOUND,
                resource_name="FacialAestheticsSession",
            )

        zone_id = data["zone_id"]

        # Validate zone
        if zone_id not in VALID_ZONES:
            raise DentalOSError(
                error=FacialAestheticsErrors.INVALID_ZONE,
                message=f"Zona '{zone_id}' no es válida.",
                status_code=422,
            )

        # Check for duplicate zone in this session
        existing_result = await db.execute(
            select(FacialAestheticsInjection).where(
                FacialAestheticsInjection.session_id == sid,
                FacialAestheticsInjection.zone_id == zone_id,
                FacialAestheticsInjection.is_active.is_(True),
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise DentalOSError(
                error=FacialAestheticsErrors.DUPLICATE_ZONE,
                message=f"Ya existe una inyección en la zona '{zone_id}' para esta sesión.",
                status_code=409,
            )

        injection = FacialAestheticsInjection(
            session_id=sid,
            patient_id=pid,
            zone_id=zone_id,
            injection_type=data["injection_type"],
            product_name=data.get("product_name"),
            dose_units=data.get("dose_units"),
            dose_volume_ml=data.get("dose_volume_ml"),
            depth=data.get("depth"),
            coordinates_x=data.get("coordinates_x"),
            coordinates_y=data.get("coordinates_y"),
            notes=data.get("notes"),
            created_by=uid,
            is_active=True,
        )
        db.add(injection)
        await db.flush()

        # Create history entry
        new_data = {
            "injection_type": data["injection_type"],
            "product_name": data.get("product_name"),
            "dose_units": float(data["dose_units"]) if data.get("dose_units") is not None else None,
            "dose_volume_ml": float(data["dose_volume_ml"]) if data.get("dose_volume_ml") is not None else None,
            "depth": data.get("depth"),
        }

        history = FacialAestheticsHistory(
            patient_id=pid,
            session_id=sid,
            zone_id=zone_id,
            action="add",
            injection_type=data["injection_type"],
            previous_data=None,
            new_data=new_data,
            performed_by=uid,
        )
        db.add(history)
        await db.flush()

        logger.info(
            "Injection added: session=%s zone=%s",
            str(sid)[:8],
            zone_id,
        )

        await db.refresh(injection)
        return _injection_to_dict(injection)

    async def update_injection(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
        injection_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing injection."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)
        iid = uuid.UUID(injection_id)
        uid = uuid.UUID(user_id)

        result = await db.execute(
            select(FacialAestheticsInjection).where(
                FacialAestheticsInjection.id == iid,
                FacialAestheticsInjection.session_id == sid,
                FacialAestheticsInjection.patient_id == pid,
                FacialAestheticsInjection.is_active.is_(True),
            )
        )
        injection = result.scalar_one_or_none()

        if injection is None:
            raise ResourceNotFoundError(
                error=FacialAestheticsErrors.INJECTION_NOT_FOUND,
                resource_name="FacialAestheticsInjection",
            )

        # Capture previous state
        previous_data = {
            "injection_type": injection.injection_type,
            "product_name": injection.product_name,
            "dose_units": float(injection.dose_units) if injection.dose_units is not None else None,
            "dose_volume_ml": float(injection.dose_volume_ml) if injection.dose_volume_ml is not None else None,
            "depth": injection.depth,
        }

        # Apply updates
        if data.get("injection_type") is not None:
            injection.injection_type = data["injection_type"]
        if "product_name" in data:
            injection.product_name = data["product_name"]
        if "dose_units" in data:
            injection.dose_units = data["dose_units"]
        if "dose_volume_ml" in data:
            injection.dose_volume_ml = data["dose_volume_ml"]
        if data.get("depth") is not None:
            injection.depth = data["depth"]
        if "coordinates_x" in data:
            injection.coordinates_x = data["coordinates_x"]
        if "coordinates_y" in data:
            injection.coordinates_y = data["coordinates_y"]
        if "notes" in data:
            injection.notes = data["notes"]

        await db.flush()

        # Build new_data for history
        new_data = {
            "injection_type": injection.injection_type,
            "product_name": injection.product_name,
            "dose_units": float(injection.dose_units) if injection.dose_units is not None else None,
            "dose_volume_ml": float(injection.dose_volume_ml) if injection.dose_volume_ml is not None else None,
            "depth": injection.depth,
        }

        history = FacialAestheticsHistory(
            patient_id=pid,
            session_id=sid,
            zone_id=injection.zone_id,
            action="update",
            injection_type=injection.injection_type,
            previous_data=previous_data,
            new_data=new_data,
            performed_by=uid,
        )
        db.add(history)
        await db.flush()

        logger.info(
            "Injection updated: session=%s zone=%s",
            str(sid)[:8],
            injection.zone_id,
        )

        await db.refresh(injection)
        return _injection_to_dict(injection)

    async def remove_injection(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
        injection_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Soft-delete an injection and record in history."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)
        iid = uuid.UUID(injection_id)
        uid = uuid.UUID(user_id)

        result = await db.execute(
            select(FacialAestheticsInjection).where(
                FacialAestheticsInjection.id == iid,
                FacialAestheticsInjection.session_id == sid,
                FacialAestheticsInjection.patient_id == pid,
                FacialAestheticsInjection.is_active.is_(True),
            )
        )
        injection = result.scalar_one_or_none()

        if injection is None:
            raise ResourceNotFoundError(
                error=FacialAestheticsErrors.INJECTION_NOT_FOUND,
                resource_name="FacialAestheticsInjection",
            )

        previous_data = {
            "injection_type": injection.injection_type,
            "product_name": injection.product_name,
            "dose_units": float(injection.dose_units) if injection.dose_units is not None else None,
            "dose_volume_ml": float(injection.dose_volume_ml) if injection.dose_volume_ml is not None else None,
            "depth": injection.depth,
        }

        injection.is_active = False
        injection.deleted_at = datetime.now(UTC)

        history = FacialAestheticsHistory(
            patient_id=pid,
            session_id=sid,
            zone_id=injection.zone_id,
            action="remove",
            injection_type=injection.injection_type,
            previous_data=previous_data,
            new_data=None,
            performed_by=uid,
        )
        db.add(history)
        await db.flush()

        logger.info(
            "Injection removed: session=%s zone=%s",
            str(sid)[:8],
            injection.zone_id,
        )

        return {"message": "Inyección eliminada exitosamente."}

    # ─── History ─────────────────────────────────────────────────────────

    async def get_history(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
        cursor: str | None = None,
        limit: int = _HISTORY_DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Return cursor-paginated history for a session."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)

        stmt = (
            select(FacialAestheticsHistory, User.name.label("performer_name"))
            .outerjoin(User, FacialAestheticsHistory.performed_by == User.id)
            .where(
                FacialAestheticsHistory.patient_id == pid,
                FacialAestheticsHistory.session_id == sid,
            )
        )

        if cursor is not None:
            try:
                cursor_created_at, cursor_id = _decode_cursor(cursor)
            except (ValueError, Exception):
                raise DentalOSError(
                    error="VALIDATION_failed",
                    message="Cursor de paginación inválido.",
                    status_code=422,
                )
            stmt = stmt.where(
                (FacialAestheticsHistory.created_at < cursor_created_at)
                | (
                    (FacialAestheticsHistory.created_at == cursor_created_at)
                    & (FacialAestheticsHistory.id < cursor_id)
                )
            )

        stmt = stmt.order_by(
            FacialAestheticsHistory.created_at.desc(),
            FacialAestheticsHistory.id.desc(),
        ).limit(limit + 1)

        result = await db.execute(stmt)
        rows = result.all()

        has_more = len(rows) > limit
        rows = rows[:limit]

        items = [
            _history_to_dict(row[0], performed_by_name=row[1])
            for row in rows
        ]

        next_cursor: str | None = None
        if has_more and items:
            last = rows[-1][0]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # ─── Snapshots ───────────────────────────────────────────────────────

    async def create_snapshot(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        session_id: str,
        user_id: str,
        label: str | None = None,
        linked_record_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a snapshot of a session's current injection state."""
        pid = uuid.UUID(patient_id)
        sid = uuid.UUID(session_id)
        uid = uuid.UUID(user_id)

        # Fetch the session with injections
        session_data = await self.get_session(
            db=db, patient_id=patient_id, session_id=session_id
        )

        snapshot = FacialAestheticsSnapshot(
            patient_id=pid,
            session_id=sid,
            snapshot_data=session_data,
            diagram_type=session_data["diagram_type"],
            label=label,
            linked_record_id=uuid.UUID(linked_record_id) if linked_record_id else None,
            created_by=uid,
        )
        db.add(snapshot)
        await db.flush()

        logger.info(
            "Snapshot created: patient=%s session=%s",
            str(pid)[:8],
            str(sid)[:8],
        )

        return _snapshot_to_dict(snapshot, include_data=True)

    async def list_snapshots(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
    ) -> dict[str, Any]:
        """List all snapshots for a patient, ordered newest-first."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(FacialAestheticsSnapshot)
            .where(FacialAestheticsSnapshot.patient_id == pid)
            .order_by(FacialAestheticsSnapshot.created_at.desc())
        )
        snapshots = result.scalars().all()

        return {
            "items": [_snapshot_to_dict(s, include_data=False) for s in snapshots],
            "total": len(snapshots),
        }


# Module-level singleton
facial_aesthetics_service = FacialAestheticsService()
