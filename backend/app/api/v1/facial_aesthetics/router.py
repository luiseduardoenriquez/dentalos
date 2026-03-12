"""Facial aesthetics API routes — GAP-12.

Endpoint map (all scoped to /patients/{patient_id}/facial-aesthetics):
  POST   /                                  — Create session (201)
  GET    /                                  — List sessions (200, paginated)
  GET    /{session_id}                      — Get session + injections (200)
  PUT    /{session_id}                      — Update session (200)
  DELETE /{session_id}                      — Soft delete session (200)
  POST   /{session_id}/injections           — Add injection (201)
  PUT    /{session_id}/injections/{inj_id}  — Update injection (200)
  DELETE /{session_id}/injections/{inj_id}  — Remove injection (200)
  GET    /{session_id}/history              — Cursor-paginated history (200)
  POST   /{session_id}/snapshots            — Create snapshot (201)
  GET    /snapshots                         — List patient snapshots (200)
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.facial_aesthetics import (
    HistoryListResponse,
    InjectionCreate,
    InjectionResponse,
    InjectionUpdate,
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionUpdate,
    SnapshotCreate,
    SnapshotListResponse,
    SnapshotResponse,
)
from app.services.facial_aesthetics_service import facial_aesthetics_service

router = APIRouter(
    prefix="/patients/{patient_id}/facial-aesthetics",
    tags=["facial-aesthetics"],
)


# ─── Create session ──────────────────────────────────────────────────────────


@router.post("", response_model=SessionDetailResponse, status_code=201)
async def create_session(
    patient_id: str,
    body: SessionCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SessionDetailResponse:
    """Create a new facial aesthetics session."""
    result = await facial_aesthetics_service.create_session(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        data=body.model_dump(),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create_session",
        resource_type="facial_aesthetics",
        resource_id=patient_id,
    )

    return SessionDetailResponse(**result)


# ─── List sessions ───────────────────────────────────────────────────────────


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SessionListResponse:
    """Return paginated list of facial aesthetics sessions."""
    result = await facial_aesthetics_service.list_sessions(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return SessionListResponse(**result)


# ─── List snapshots (registered before /{session_id} to avoid path conflict) ─


@router.get("/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SnapshotListResponse:
    """Return all snapshots for a patient, ordered newest-first."""
    result = await facial_aesthetics_service.list_snapshots(
        db=db,
        patient_id=patient_id,
    )
    return SnapshotListResponse(**result)


# ─── Get session ─────────────────────────────────────────────────────────────


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    patient_id: str,
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SessionDetailResponse:
    """Return a single session with all active injections."""
    result = await facial_aesthetics_service.get_session(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
    )
    return SessionDetailResponse(**result)


# ─── Update session ──────────────────────────────────────────────────────────


@router.put("/{session_id}", response_model=SessionDetailResponse)
async def update_session(
    patient_id: str,
    session_id: str,
    body: SessionUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SessionDetailResponse:
    """Update session notes or diagram type."""
    result = await facial_aesthetics_service.update_session(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
        data=body.model_dump(exclude_unset=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update_session",
        resource_type="facial_aesthetics",
        resource_id=session_id,
    )

    return SessionDetailResponse(**result)


# ─── Delete session ──────────────────────────────────────────────────────────


@router.delete("/{session_id}", response_model=dict)
async def delete_session(
    patient_id: str,
    session_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Soft-delete a facial aesthetics session."""
    result = await facial_aesthetics_service.delete_session(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="delete_session",
        resource_type="facial_aesthetics",
        resource_id=session_id,
    )

    return result


# ─── Add injection ───────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/injections",
    response_model=InjectionResponse,
    status_code=201,
)
async def add_injection(
    patient_id: str,
    session_id: str,
    body: InjectionCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> InjectionResponse:
    """Add an injection point to a session."""
    result = await facial_aesthetics_service.add_injection(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
        user_id=current_user.user_id,
        data=body.model_dump(),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="add_injection",
        resource_type="facial_aesthetics",
        resource_id=session_id,
    )

    return InjectionResponse(**result)


# ─── Update injection ───────────────────────────────────────────────────────


@router.put(
    "/{session_id}/injections/{injection_id}",
    response_model=InjectionResponse,
)
async def update_injection(
    patient_id: str,
    session_id: str,
    injection_id: str,
    body: InjectionUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> InjectionResponse:
    """Update an existing injection."""
    result = await facial_aesthetics_service.update_injection(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
        injection_id=injection_id,
        user_id=current_user.user_id,
        data=body.model_dump(exclude_unset=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update_injection",
        resource_type="facial_aesthetics",
        resource_id=injection_id,
    )

    return InjectionResponse(**result)


# ─── Remove injection ───────────────────────────────────────────────────────


@router.delete("/{session_id}/injections/{injection_id}", response_model=dict)
async def remove_injection(
    patient_id: str,
    session_id: str,
    injection_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Soft-delete an injection point."""
    result = await facial_aesthetics_service.remove_injection(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
        injection_id=injection_id,
        user_id=current_user.user_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="remove_injection",
        resource_type="facial_aesthetics",
        resource_id=injection_id,
    )

    return result


# ─── History ─────────────────────────────────────────────────────────────────


@router.get("/{session_id}/history", response_model=HistoryListResponse)
async def get_history(
    patient_id: str,
    session_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> HistoryListResponse:
    """Return cursor-paginated injection history for a session."""
    result = await facial_aesthetics_service.get_history(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
        cursor=cursor,
        limit=limit,
    )
    return HistoryListResponse(**result)


# ─── Create snapshot ─────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/snapshots",
    response_model=SnapshotResponse,
    status_code=201,
)
async def create_snapshot(
    patient_id: str,
    session_id: str,
    body: SnapshotCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("aesthetic:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SnapshotResponse:
    """Create a snapshot of the session's current injection state."""
    result = await facial_aesthetics_service.create_snapshot(
        db=db,
        patient_id=patient_id,
        session_id=session_id,
        user_id=current_user.user_id,
        label=body.label,
        linked_record_id=body.linked_record_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create_snapshot",
        resource_type="facial_aesthetics",
        resource_id=session_id,
    )

    return SnapshotResponse(**result)
