"""Mock exchange rate service for development and testing — VP-14 Multi-Currency.

Returns deterministic, hardcoded exchange rates so frontend and backend
developers can work without a real exchange rate API key.

Hardcoded rates (per 1 unit of from_currency):
  USD/COP = 4150.00
  EUR/COP = 4520.00
  MXN/COP = 240.00
  (Inverse and cross rates are derived from these base rates.)
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.integrations.exchange_rates.base import ExchangeRateServiceBase

# Supported currency codes.
SUPPORTED_CURRENCIES = {"COP", "USD", "EUR", "MXN"}

# Base rates: how many COP per 1 unit of foreign currency.
_RATES_TO_COP: dict[str, Decimal] = {
    "USD": Decimal("4150.000000"),
    "EUR": Decimal("4520.000000"),
    "MXN": Decimal("240.000000"),
    "COP": Decimal("1.000000"),
}

# 6-decimal precision quantizer.
_PRECISION = Decimal("0.000001")


class ExchangeRateServiceMock(ExchangeRateServiceBase):
    """Mock exchange rate service. Always configured; never makes HTTP calls."""

    def is_configured(self) -> bool:
        return True

    async def get_rate(self, *, from_currency: str, to_currency: str) -> Decimal:
        """Return a deterministic exchange rate for the given pair.

        Strategy: convert from_currency -> COP -> to_currency using the
        hardcoded base rates.

        Args:
            from_currency: ISO 4217 code (uppercase).
            to_currency: ISO 4217 code (uppercase).

        Returns:
            Decimal rate with 6-decimal precision.

        Raises:
            ValueError: If either currency is not supported.
        """
        from_code = from_currency.upper().strip()
        to_code = to_currency.upper().strip()

        if from_code not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {from_code}")
        if to_code not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {to_code}")

        # Identity.
        if from_code == to_code:
            return Decimal("1.000000")

        # Convert: from_currency -> COP -> to_currency.
        # 1 from_currency = _RATES_TO_COP[from] COP
        # 1 COP = 1 / _RATES_TO_COP[to] to_currency
        # So: rate = _RATES_TO_COP[from] / _RATES_TO_COP[to]
        from_to_cop = _RATES_TO_COP[from_code]
        to_to_cop = _RATES_TO_COP[to_code]

        rate = (from_to_cop / to_to_cop).quantize(_PRECISION, rounding=ROUND_HALF_UP)
        return rate


# Module-level singleton.
exchange_rate_mock_service = ExchangeRateServiceMock()
