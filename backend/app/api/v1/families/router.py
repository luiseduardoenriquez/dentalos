"""Families API routes — GAP-10 Family Groups.

Endpoint map:
  POST   /families                               — Create family group (201)
  GET    /families/{family_id}                   — Get family with members
  POST   /families/{family_id}/members           — Add member to family
  DELETE /families/{family_id}/members/{patient_id} — Soft-remove member
  GET    /families/{family_id}/billing           — Consolidated billing view
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.family import (
    FamilyBillingSummary,
    FamilyGroupCreate,
    FamilyResponse,
    MemberAdd,
)
from app.services.family_service import family_service

router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=FamilyResponse, status_code=201)
async def create_family(
    body: FamilyGroupCreate,
    current_user: AuthenticatedUser = Depends(require_permission("families:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FamilyResponse:
    """Create a new family group and add the primary contact as its first member."""
    result = await family_service.create(
        db=db,
        name=body.name,
        primary_contact_patient_id=body.primary_contact_patient_id,
    )
    return FamilyResponse(**result)


@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(
    family_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("families:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FamilyResponse:
    """Retrieve a family group with all active members."""
    result = await family_service.get(db=db, family_id=family_id)
    return FamilyResponse(**result)


@router.post("/{family_id}/members", response_model=FamilyResponse)
async def add_member(
    family_id: str,
    body: MemberAdd,
    current_user: AuthenticatedUser = Depends(require_permission("families:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FamilyResponse:
    """Add a patient to an existing family group."""
    result = await family_service.add_member(
        db=db,
        family_id=family_id,
        patient_id=body.patient_id,
        relationship=body.relationship,
    )
    return FamilyResponse(**result)


@router.delete("/{family_id}/members/{patient_id}", response_model=FamilyResponse)
async def remove_member(
    family_id: str,
    patient_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("families:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FamilyResponse:
    """Soft-remove a patient from a family group.

    The primary contact of the group cannot be removed. Assign a new primary
    contact before removing this member.
    """
    result = await family_service.remove_member(
        db=db,
        family_id=family_id,
        patient_id=patient_id,
    )
    return FamilyResponse(**result)


@router.get("/{family_id}/billing", response_model=FamilyBillingSummary)
async def get_family_billing(
    family_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("families:read")),
    _billing_perm: AuthenticatedUser = Depends(require_permission("billing:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> FamilyBillingSummary:
    """Get a consolidated billing summary across all members of a family group.

    Requires both families:read and billing:read permissions.
    """
    result = await family_service.get_family_billing(db=db, family_id=family_id)
    return FamilyBillingSummary(**result)
