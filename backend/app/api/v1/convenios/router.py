"""Convenio API routes — GAP-04.

Endpoint map:
  POST /convenios                              — Create convenio
  GET  /convenios                              — List convenios (paginated)
  PUT  /convenios/{convenio_id}               — Update convenio
  POST /convenios/patients/{patient_id}/convenio — Link patient to convenio
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.convenio import (
    ConvenioCreate,
    ConvenioListResponse,
    ConvenioResponse,
    ConvenioUpdate,
    LinkPatientRequest,
)
from app.services.convenio_service import convenio_service

router = APIRouter(prefix="/convenios", tags=["convenios"])


@router.post("", response_model=ConvenioResponse, status_code=201)
async def create_convenio(
    body: ConvenioCreate,
    current_user: AuthenticatedUser = Depends(require_permission("convenios:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConvenioResponse:
    """Create a new corporate agreement."""
    result = await convenio_service.create(
        db=db,
        data=body.model_dump(),
        created_by=str(current_user.user_id),
    )
    return ConvenioResponse(**result)


@router.get("", response_model=ConvenioListResponse)
async def list_convenios(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("convenios:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConvenioListResponse:
    """List corporate agreements (paginated)."""
    result = await convenio_service.list_convenios(db=db, page=page, page_size=page_size)
    return ConvenioListResponse(**result)


@router.put("/{convenio_id}", response_model=ConvenioResponse)
async def update_convenio(
    convenio_id: str,
    body: ConvenioUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("convenios:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConvenioResponse:
    """Update an existing corporate agreement."""
    result = await convenio_service.update(
        db=db,
        convenio_id=convenio_id,
        data=body.model_dump(exclude_unset=True),
    )
    return ConvenioResponse(**result)


@router.post("/patients/{patient_id}/convenio", status_code=201)
async def link_patient_to_convenio(
    patient_id: str,
    body: LinkPatientRequest,
    current_user: AuthenticatedUser = Depends(require_permission("convenios:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Link a patient to a corporate agreement.

    Path param patient_id identifies the patient.
    Body field patient_id carries the convenio_id to link to.
    """
    return await convenio_service.link_patient(
        db=db,
        convenio_id=body.patient_id,
        patient_id=patient_id,
        employee_id=body.employee_id,
    )
