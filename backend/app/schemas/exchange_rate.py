"""Exchange rate request/response schemas — VP-14 Multi-Currency Billing."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# ---- Response Schemas --------------------------------------------------------


class CurrencyInfo(BaseModel):
    """Metadata about a supported currency."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="ISO 4217 currency code", examples=["COP"])
    name: str = Field(..., description="Human-readable currency name", examples=["Peso colombiano"])
    symbol: str = Field(..., description="Currency symbol", examples=["$"])


class ExchangeRateResponse(BaseModel):
    """A single exchange rate between two currencies."""

    model_config = ConfigDict(from_attributes=True)

    from_currency: str = Field(..., description="Source currency ISO 4217 code", examples=["USD"])
    to_currency: str = Field(..., description="Target currency ISO 4217 code", examples=["COP"])
    rate: float = Field(..., description="Exchange rate (units of to_currency per 1 from_currency)", examples=[4150.0])
    rate_date: date = Field(..., description="Date the rate was fetched or last updated")
    cached: bool = Field(..., description="Whether the rate was served from cache")


class ExchangeRatesListResponse(BaseModel):
    """List of exchange rates relative to a base currency."""

    rates: list[ExchangeRateResponse]
    base_currency: str = Field(default="COP", description="Base currency for all rates")
