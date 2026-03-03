"""Exchange rate API routes — VP-14 Multi-Currency Billing.

Endpoint map:
  GET /billing/exchange-rates — List current exchange rates for all supported
                                 currencies relative to a base currency.

Requires ``billing:read`` permission. Exchange rates are tenant-agnostic
(shared cache key) but still require authentication so only staff can
access pricing data.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.exchange_rate import ExchangeRateResponse, ExchangeRatesListResponse
from app.services.exchange_rate_service import exchange_rate_service

router = APIRouter(prefix="/billing", tags=["billing"])


# ---- VP-14: Exchange rates ---------------------------------------------------


@router.get("/exchange-rates", response_model=ExchangeRatesListResponse)
async def list_exchange_rates(
    base_currency: str = Query(
        default="COP",
        max_length=3,
        min_length=3,
        description="Base currency ISO 4217 code",
    ),
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ExchangeRatesListResponse:
    """Return current exchange rates for all supported currencies.

    Rates are relative to the *base_currency* (default COP). Results are
    cached for 1 hour in Redis. No audit event is emitted (read-only).
    """
    rates_data = await exchange_rate_service.get_all_rates(
        base_currency=base_currency.upper().strip(),
    )

    rates = [
        ExchangeRateResponse(
            from_currency=r["from_currency"],
            to_currency=r["to_currency"],
            rate=r["rate"],
            rate_date=r["rate_date"],
            cached=r["cached"],
        )
        for r in rates_data
    ]

    return ExchangeRatesListResponse(
        rates=rates,
        base_currency=base_currency.upper().strip(),
    )
