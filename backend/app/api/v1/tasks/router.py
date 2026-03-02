"""Staff task endpoints — GAP-05 (Delinquency) + GAP-06 (Acceptance).

Endpoint map:
  GET  /tasks          — list tasks with filters
  POST /tasks          — create a manual task
  PUT  /tasks/{id}     — update task status, assignee, or priority
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.staff_task import (
    StaffTaskCreate,
    StaffTaskListResponse,
    StaffTaskResponse,
    StaffTaskUpdate,
)
from app.services.staff_task_service import staff_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=StaffTaskListResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    task_type: str | None = Query(
        default=None,
        pattern=r"^(delinquency|acceptance|manual)$",
    ),
    status: str | None = Query(
        default=None,
        pattern=r"^(open|in_progress|completed|dismissed)$",
    ),
    assigned_to: UUID | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("tasks:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """List staff tasks with optional filters (type, status, assignee)."""
    return await staff_task_service.list_tasks(
        db=db,
        page=page,
        page_size=page_size,
        task_type=task_type,
        status=status,
        assigned_to=assigned_to,
    )


@router.post("", response_model=StaffTaskResponse, status_code=201)
async def create_task(
    body: StaffTaskCreate,
    current_user: AuthenticatedUser = Depends(require_permission("tasks:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Create a manual staff task."""
    return await staff_task_service.create_task(
        db=db,
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        priority=body.priority,
        assigned_to=UUID(body.assigned_to) if body.assigned_to else None,
        patient_id=UUID(body.patient_id) if body.patient_id else None,
        due_date=body.due_date,
    )


@router.put("/{task_id}", response_model=StaffTaskResponse)
async def update_task(
    task_id: UUID,
    body: StaffTaskUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("tasks:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Update task status, assignee, or priority.

    Invalid status transitions return 422 with TASK_invalid_status_transition.
    """
    return await staff_task_service.update_task(
        db=db,
        task_id=task_id,
        **body.model_dump(exclude_unset=True),
    )
