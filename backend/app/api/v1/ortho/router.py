"""Orthodontics API routes.

Endpoint map (all scoped to /patients/{patient_id}/ortho-cases):
  POST   /patients/{patient_id}/ortho-cases                            -- Create case
  GET    /patients/{patient_id}/ortho-cases                            -- List cases
  GET    /patients/{patient_id}/ortho-cases/{case_id}                  -- Get case detail
  PUT    /patients/{patient_id}/ortho-cases/{case_id}                  -- Update case
  POST   /patients/{patient_id}/ortho-cases/{case_id}/transition       -- Transition status
  GET    /patients/{patient_id}/ortho-cases/{case_id}/summary          -- Aggregated stats
  POST   /patients/{patient_id}/ortho-cases/{case_id}/bonding-records  -- Create bonding
  GET    /patients/{patient_id}/ortho-cases/{case_id}/bonding-records  -- List bonding
  GET    /patients/{patient_id}/ortho-cases/{case_id}/bonding-records/{record_id} -- Get bonding
  POST   /patients/{patient_id}/ortho-cases/{case_id}/visits           -- Create visit
  GET    /patients/{patient_id}/ortho-cases/{case_id}/visits           -- List visits
  PUT    /patients/{patient_id}/ortho-cases/{case_id}/visits/{visit_id} -- Update visit
  POST   /patients/{patient_id}/ortho-cases/{case_id}/materials        -- Add material
  GET    /patients/{patient_id}/ortho-cases/{case_id}/materials        -- List materials
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.ortho import (
    BondingRecordCreate,
    BondingRecordListResponse,
    BondingRecordListItem,
    BondingRecordResponse,
    BondingToothResponse,
    MaterialCreate,
    MaterialListResponse,
    MaterialResponse,
    OrthoCaseCreate,
    OrthoCaseListResponse,
    OrthoCaseListItem,
    OrthoCaseResponse,
    OrthoCaseSummary,
    OrthoCaseUpdate,
    OrthoVisitCreate,
    OrthoVisitListResponse,
    OrthoVisitResponse,
    OrthoVisitUpdate,
    TransitionRequest,
)
from app.services.ortho_service import ortho_service

router = APIRouter(prefix="/patients/{patient_id}/ortho-cases", tags=["orthodontics"])


# ─── Create orthodontic case ───────────────────────────────────────────────


@router.post(
    "",
    response_model=OrthoCaseResponse,
    status_code=201,
)
async def create_ortho_case(
    patient_id: str,
    body: OrthoCaseCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoCaseResponse:
    """Create a new orthodontic case for a patient."""
    result = await ortho_service.create_case(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        data=body.model_dump(exclude_none=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="ortho_case",
        resource_id=result["id"],
    )

    return OrthoCaseResponse(**result)


# ─── List orthodontic cases ────────────────────────────────────────────────
# Registered BEFORE /{case_id} to avoid path collision.


@router.get(
    "",
    response_model=OrthoCaseListResponse,
)
async def list_ortho_cases(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoCaseListResponse:
    """Return a paginated list of orthodontic cases for a patient."""
    result = await ortho_service.list_cases(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return OrthoCaseListResponse(
        items=[OrthoCaseListItem(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── Get case detail ───────────────────────────────────────────────────────


@router.get(
    "/{case_id}",
    response_model=OrthoCaseResponse,
)
async def get_ortho_case(
    patient_id: str,
    case_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoCaseResponse:
    """Return full detail for a single orthodontic case."""
    result = await ortho_service.get_case(
        db=db,
        patient_id=patient_id,
        case_id=case_id,
    )
    return OrthoCaseResponse(**result)


# ─── Update case ────────────────────────────────────────────────────────────


@router.put(
    "/{case_id}",
    response_model=OrthoCaseResponse,
)
async def update_ortho_case(
    patient_id: str,
    case_id: str,
    body: OrthoCaseUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoCaseResponse:
    """Update an existing orthodontic case."""
    result = await ortho_service.update_case(
        db=db,
        patient_id=patient_id,
        case_id=case_id,
        data=body.model_dump(exclude_none=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="ortho_case",
        resource_id=result["id"],
    )

    return OrthoCaseResponse(**result)


# ─── Transition case status ─────────────────────────────────────────────────


@router.post(
    "/{case_id}/transition",
    response_model=OrthoCaseResponse,
)
async def transition_ortho_case(
    patient_id: str,
    case_id: str,
    body: TransitionRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoCaseResponse:
    """Transition an orthodontic case to a new status."""
    result = await ortho_service.transition_case(
        db=db,
        patient_id=patient_id,
        case_id=case_id,
        target_status=body.target_status,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="transition",
        resource_type="ortho_case",
        resource_id=result["id"],
        changes={"status": {"new": body.target_status}},
    )

    return OrthoCaseResponse(**result)


# ─── Case summary ──────────────────────────────────────────────────────────
# Registered BEFORE /{case_id}/bonding-records to avoid path collision.


@router.get(
    "/{case_id}/summary",
    response_model=OrthoCaseSummary,
)
async def get_ortho_case_summary(
    patient_id: str,
    case_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoCaseSummary:
    """Return aggregated financial and visit statistics for a case."""
    result = await ortho_service.get_case_summary(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
    )
    return OrthoCaseSummary(**result)


# ─── Bonding records ────────────────────────────────────────────────────────


@router.post(
    "/{case_id}/bonding-records",
    response_model=BondingRecordResponse,
    status_code=201,
)
async def create_bonding_record(
    patient_id: str,
    case_id: str,
    body: BondingRecordCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> BondingRecordResponse:
    """Create a bonding record with per-tooth bracket data."""
    result = await ortho_service.create_bonding_record(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        recorded_by=current_user.user_id,
        data=body.model_dump(),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="ortho_bonding_record",
        resource_id=result["id"],
    )

    return BondingRecordResponse(
        id=result["id"],
        ortho_case_id=result["ortho_case_id"],
        recorded_by=result["recorded_by"],
        notes=result["notes"],
        teeth=[BondingToothResponse(**t) for t in result["teeth"]],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


@router.get(
    "/{case_id}/bonding-records",
    response_model=BondingRecordListResponse,
)
async def list_bonding_records(
    patient_id: str,
    case_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> BondingRecordListResponse:
    """Return a paginated list of bonding records for a case."""
    result = await ortho_service.list_bonding_records(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return BondingRecordListResponse(
        items=[BondingRecordListItem(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/{case_id}/bonding-records/{record_id}",
    response_model=BondingRecordResponse,
)
async def get_bonding_record(
    patient_id: str,
    case_id: str,
    record_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> BondingRecordResponse:
    """Return full detail for a bonding record with teeth data."""
    result = await ortho_service.get_bonding_record(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        record_id=record_id,
    )
    return BondingRecordResponse(
        id=result["id"],
        ortho_case_id=result["ortho_case_id"],
        recorded_by=result["recorded_by"],
        notes=result["notes"],
        teeth=[BondingToothResponse(**t) for t in result["teeth"]],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


# ─── Visits ─────────────────────────────────────────────────────────────────


@router.post(
    "/{case_id}/visits",
    response_model=OrthoVisitResponse,
    status_code=201,
)
async def create_ortho_visit(
    patient_id: str,
    case_id: str,
    body: OrthoVisitCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoVisitResponse:
    """Create a new adjustment visit for a case."""
    result = await ortho_service.create_visit(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        data=body.model_dump(exclude_none=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="ortho_visit",
        resource_id=result["id"],
    )

    return OrthoVisitResponse(**result)


@router.get(
    "/{case_id}/visits",
    response_model=OrthoVisitListResponse,
)
async def list_ortho_visits(
    patient_id: str,
    case_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoVisitListResponse:
    """Return a paginated list of visits for a case."""
    result = await ortho_service.list_visits(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return OrthoVisitListResponse(
        items=[OrthoVisitResponse(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.put(
    "/{case_id}/visits/{visit_id}",
    response_model=OrthoVisitResponse,
)
async def update_ortho_visit(
    patient_id: str,
    case_id: str,
    visit_id: str,
    body: OrthoVisitUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> OrthoVisitResponse:
    """Update an existing visit."""
    result = await ortho_service.update_visit(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        visit_id=visit_id,
        data=body.model_dump(exclude_none=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="ortho_visit",
        resource_id=result["id"],
    )

    return OrthoVisitResponse(**result)


# ─── Materials ──────────────────────────────────────────────────────────────


@router.post(
    "/{case_id}/materials",
    response_model=MaterialResponse,
    status_code=201,
)
async def add_ortho_material(
    patient_id: str,
    case_id: str,
    body: MaterialCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("ortho:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> MaterialResponse:
    """Record material consumption for a case (decrements inventory)."""
    result = await ortho_service.add_material(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        user_id=current_user.user_id,
        data=body.model_dump(exclude_none=True),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="ortho_case_material",
        resource_id=result["id"],
    )

    return MaterialResponse(**result)


@router.get(
    "/{case_id}/materials",
    response_model=MaterialListResponse,
)
async def list_ortho_materials(
    patient_id: str,
    case_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("ortho:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> MaterialListResponse:
    """Return a paginated list of materials consumed for a case."""
    result = await ortho_service.list_materials(
        db=db,
        case_id=case_id,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return MaterialListResponse(
        items=[MaterialResponse(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
