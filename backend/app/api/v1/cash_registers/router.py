"""Cash register API routes — GAP-02.

Endpoint map:
  POST /cash-registers/open        — Open a new register session
  POST /cash-registers/close       — Close the current open register
  GET  /cash-registers/current     — Get the currently open register with movements
  GET  /cash-registers/history     — Paginated history of closed registers
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.cash_register import (
    CashRegisterCloseRequest,
    CashRegisterDetailResponse,
    CashRegisterHistoryResponse,
    CashRegisterOpenRequest,
    CashRegisterResponse,
)
from app.services.cash_register_service import cash_register_service

router = APIRouter(prefix="/cash-registers", tags=["cash-registers"])


@router.post("/open", response_model=CashRegisterResponse, status_code=201)
async def open_register(
    body: CashRegisterOpenRequest,
    current_user: AuthenticatedUser = Depends(require_permission("cash_register:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CashRegisterResponse:
    """Open a new cash register session.

    Fails with 409 if another register is already open.
    """
    result = await cash_register_service.open_register(
        db=db,
        user_id=current_user.user_id,
        name=body.name,
        location=body.location,
        opening_balance_cents=body.opening_balance_cents,
    )
    return CashRegisterResponse(**result)


@router.post("/close", response_model=CashRegisterResponse)
async def close_register(
    body: CashRegisterCloseRequest,
    current_user: AuthenticatedUser = Depends(require_permission("cash_register:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CashRegisterResponse:
    """Close the currently open cash register session.

    The register_id is resolved from the single open register; closing_balance_cents
    must be provided by the cashier after a physical count.
    """
    # Resolve the open register id without exposing internals in the request body
    current = await cash_register_service.get_current(db=db)
    if current is None:
        from app.core.error_codes import CashRegisterErrors
        from app.core.exceptions import DentalOSError
        raise DentalOSError(
            error=CashRegisterErrors.NO_OPEN_REGISTER,
            message="No hay ninguna caja abierta.",
            status_code=404,
        )

    import uuid
    result = await cash_register_service.close_register(
        db=db,
        user_id=current_user.user_id,
        register_id=uuid.UUID(current["id"]),
        closing_balance_cents=body.closing_balance_cents,
    )
    return CashRegisterResponse(**result)


@router.get("/current", response_model=CashRegisterDetailResponse | None)
async def get_current_register(
    current_user: AuthenticatedUser = Depends(require_permission("cash_register:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CashRegisterDetailResponse | None:
    """Return the currently open cash register with all its movements and running totals.

    Returns null (HTTP 200) when no register is open.
    """
    data = await cash_register_service.get_current(db=db)
    if data is None:
        return None
    return CashRegisterDetailResponse(**data)


@router.get("/history", response_model=CashRegisterHistoryResponse)
async def get_register_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission("cash_register:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> CashRegisterHistoryResponse:
    """Return a paginated list of closed cash register sessions."""
    result = await cash_register_service.get_history(
        db=db, page=page, page_size=page_size,
    )
    return CashRegisterHistoryResponse(**result)
