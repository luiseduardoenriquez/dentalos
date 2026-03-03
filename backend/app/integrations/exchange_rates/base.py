"""Abstract base for exchange rate services — VP-14 Multi-Currency Billing.

Implementations:
    BancoRepublicaService  — production, calls Banco de la Republica TRM API.
    ExchangeRateServiceMock — development/testing, returns deterministic fixtures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class ExchangeRateServiceBase(ABC):
    """Contract that all exchange rate service implementations must satisfy."""

    @abstractmethod
    async def get_rate(self, *, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate: how many units of *to_currency* per 1 *from_currency*.

        Args:
            from_currency: ISO 4217 currency code (e.g. "USD").
            to_currency: ISO 4217 currency code (e.g. "COP").

        Returns:
            Decimal with up to 6 decimal places.

        Raises:
            ValueError: If the currency pair is not supported.
            httpx.HTTPStatusError: On non-2xx response from upstream API.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the service has the credentials needed to make API calls."""
        ...
