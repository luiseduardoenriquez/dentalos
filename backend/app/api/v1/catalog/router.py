"""Catalog API routes — OD-09, CR-10, CR-11.

Endpoint map:
  GET /catalog/conditions — OD-09: Static 12-condition odontogram catalog
  GET /catalog/cie10      — CR-10: CIE-10 diagnostic code search
  GET /catalog/cups       — CR-11: CUPS procedure code search

All catalog endpoints are read-only and require only a valid JWT. No audit
events are emitted — catalog lookups are high-frequency reference reads.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user
from app.core.database import get_tenant_db
from app.core.odontogram_constants import ODONTOGRAM_CONDITIONS
from app.schemas.catalog import CIE10SearchResponse, CUPSSearchResponse, MedicationSearchResponse
from app.schemas.odontogram import CatalogConditionItem, CatalogConditionsResponse
from app.services.catalog_service import catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ─── OD-09: Conditions catalog ───────────────────────────────────────────────


@router.get("/conditions", response_model=CatalogConditionsResponse)
async def get_conditions_catalog(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CatalogConditionsResponse:
    """Return the full 12-condition odontogram catalog.

    The catalog is served directly from in-memory constants — no database
    call is required. The list is stable across releases and used by the
    frontend to render condition pickers and colour legends.
    """
    return CatalogConditionsResponse(
        conditions=[CatalogConditionItem(**c) for c in ODONTOGRAM_CONDITIONS],
    )


# ─── CR-10: CIE-10 search ────────────────────────────────────────────────────


@router.get("/cie10", response_model=CIE10SearchResponse)
async def search_cie10(
    q: str = Query(min_length=2, description="Search query — min 2 characters."),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> CIE10SearchResponse:
    """Search the CIE-10 diagnostic code catalog.

    Performs a full-text search against the public.cie10_catalog table.
    Results are cached in Redis for 24 hours per query string. Returns
    up to 20 matching codes ranked by relevance.
    """
    result = await catalog_service.search_cie10(db=db, q=q)
    return CIE10SearchResponse(**result)


# ─── CR-11: CUPS search ───────────────────────────────────────────────────────


@router.get("/cups", response_model=CUPSSearchResponse)
async def search_cups(
    q: str = Query(min_length=2, description="Search query — min 2 characters."),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> CUPSSearchResponse:
    """Search the CUPS procedure code catalog.

    Performs a full-text search against the public.cups_catalog table.
    Results are cached in Redis for 24 hours per query string. Returns
    up to 20 matching codes ranked by relevance.
    """
    result = await catalog_service.search_cups(db=db, q=q)
    return CUPSSearchResponse(**result)


# ─── RX-05: Medication catalog search ────────────────────────────────────────


@router.get("/medications", response_model=MedicationSearchResponse)
async def search_medications(
    q: str = Query(min_length=2, description="Search query — min 2 characters."),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> MedicationSearchResponse:
    """Search the medication catalog for dental prescriptions.

    Performs a substring match against the in-memory medication catalog.
    Results are cached in Redis for 24 hours per query string. Returns
    up to 20 matching medications ranked by name.
    """
    result = await catalog_service.search_medications(db=db, q=q)
    return MedicationSearchResponse(**result)
