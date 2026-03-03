"""Exchange rate service — VP-14 Multi-Currency Billing.

Provides cached exchange rate lookups with automatic fallback from the
production Banco de la Republica adapter to the mock adapter when the
API is not configured.

Cache strategy:
  - Redis key pattern: ``dentalos:shared:exchange_rates:{from}_{to}``
  - TTL: 3600 s (1 hour) — rates update once per business day.
  - On Redis failure, falls through to direct API call.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.cache import get_cached, set_cached
from app.core.error_codes import ExchangeRateErrors
from app.core.exceptions import DentalOSError
from app.integrations.exchange_rates.banco_republica import banco_republica_service
from app.integrations.exchange_rates.mock_service import exchange_rate_mock_service

logger = logging.getLogger("dentalos.services.exchange_rate")

# Supported currencies with metadata.
SUPPORTED_CURRENCIES: dict[str, dict[str, str]] = {
    "COP": {"name": "Peso colombiano", "symbol": "$"},
    "USD": {"name": "Dolar estadounidense", "symbol": "US$"},
    "EUR": {"name": "Euro", "symbol": "\u20ac"},
    "MXN": {"name": "Peso mexicano", "symbol": "MX$"},
}

# Redis cache TTL: 1 hour.
_CACHE_TTL = 3600


def _cache_key(from_currency: str, to_currency: str) -> str:
    """Build Redis cache key for an exchange rate pair."""
    return f"dentalos:shared:exchange_rates:{from_currency}_{to_currency}"


class ExchangeRateService:
    """Stateless service for exchange rate operations.

    Tries the production adapter first. If the production adapter is not
    configured (no API key), falls back transparently to the mock adapter.
    All responses are cached in Redis to minimize external API calls.
    """

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> dict:
        """Get a single exchange rate, using cache when available.

        Args:
            from_currency: ISO 4217 code (e.g. "USD").
            to_currency: ISO 4217 code (e.g. "COP").

        Returns:
            dict with keys: from_currency, to_currency, rate, rate_date, cached.

        Raises:
            DentalOSError: If the currency is unsupported or the rate
                cannot be obtained.
        """
        from_code = from_currency.upper().strip()
        to_code = to_currency.upper().strip()

        if from_code not in SUPPORTED_CURRENCIES:
            raise DentalOSError(
                error=ExchangeRateErrors.UNSUPPORTED_CURRENCY,
                message=f"Moneda no soportada: {from_code}",
                status_code=400,
                details={"currency": from_code},
            )
        if to_code not in SUPPORTED_CURRENCIES:
            raise DentalOSError(
                error=ExchangeRateErrors.UNSUPPORTED_CURRENCY,
                message=f"Moneda no soportada: {to_code}",
                status_code=400,
                details={"currency": to_code},
            )

        # Identity — no need to cache or call APIs.
        if from_code == to_code:
            return {
                "from_currency": from_code,
                "to_currency": to_code,
                "rate": 1.0,
                "rate_date": date.today().isoformat(),
                "cached": False,
            }

        # Check Redis cache.
        cache_k = _cache_key(from_code, to_code)
        try:
            cached = await get_cached(cache_k)
            if cached is not None:
                # get_cached returns parsed JSON (via json.loads in cache.py).
                cached_data = cached if isinstance(cached, dict) else json.loads(cached)
                cached_data["cached"] = True
                return cached_data
        except Exception:
            logger.debug("Cache read failed for %s, fetching fresh rate", cache_k)

        # Fetch fresh rate.
        rate_decimal = await self._fetch_rate(from_code, to_code)

        result = {
            "from_currency": from_code,
            "to_currency": to_code,
            "rate": float(rate_decimal),
            "rate_date": date.today().isoformat(),
            "cached": False,
        }

        # Store in cache — fire-and-forget on failure.
        try:
            await set_cached(cache_k, result, ttl_seconds=_CACHE_TTL)
        except Exception:
            logger.debug("Cache write failed for %s", cache_k)

        return result

    async def get_all_rates(
        self,
        base_currency: str = "COP",
    ) -> list[dict]:
        """Get exchange rates for all supported currencies relative to *base_currency*.

        Args:
            base_currency: ISO 4217 code to use as the base. Defaults to COP.

        Returns:
            list of dicts, each with from_currency, to_currency, rate, rate_date, cached.
        """
        base = base_currency.upper().strip()
        if base not in SUPPORTED_CURRENCIES:
            raise DentalOSError(
                error=ExchangeRateErrors.UNSUPPORTED_CURRENCY,
                message=f"Moneda base no soportada: {base}",
                status_code=400,
                details={"currency": base},
            )

        rates: list[dict] = []
        for code in SUPPORTED_CURRENCIES:
            if code == base:
                continue
            rate_data = await self.get_rate(code, base)
            rates.append(rate_data)

        return rates

    async def get_rate_for_invoice(
        self,
        currency_code: str,
    ) -> dict | None:
        """Get the exchange rate needed when creating an invoice in *currency_code*.

        If the invoice currency is COP (the tenant's native currency), no
        conversion is needed and None is returned.  Otherwise returns the
        rate from *currency_code* to COP together with the rate date.

        Args:
            currency_code: ISO 4217 code of the invoice currency.

        Returns:
            dict with rate details, or None if currency_code is COP.
        """
        code = currency_code.upper().strip()

        if code == "COP":
            return None

        if code not in SUPPORTED_CURRENCIES:
            raise DentalOSError(
                error=ExchangeRateErrors.UNSUPPORTED_CURRENCY,
                message=f"Moneda no soportada: {code}",
                status_code=400,
                details={"currency": code},
            )

        return await self.get_rate(code, "COP")

    # ---- Internal ----------------------------------------------------------------

    async def _fetch_rate(self, from_code: str, to_code: str) -> Decimal:
        """Fetch rate from production or mock adapter.

        Uses the production adapter if configured, otherwise falls back
        to the mock adapter transparently.
        """
        adapter = (
            banco_republica_service
            if banco_republica_service.is_configured()
            else exchange_rate_mock_service
        )

        try:
            rate = await adapter.get_rate(
                from_currency=from_code,
                to_currency=to_code,
            )
            return rate
        except ValueError as exc:
            raise DentalOSError(
                error=ExchangeRateErrors.RATE_NOT_AVAILABLE,
                message=f"Tasa de cambio no disponible para {from_code}/{to_code}.",
                status_code=502,
                details={"from_currency": from_code, "to_currency": to_code},
            ) from exc
        except Exception as exc:
            logger.error(
                "Exchange rate fetch failed for %s/%s: %s",
                from_code,
                to_code,
                exc,
            )
            # Try mock as ultimate fallback if production failed.
            if adapter is not exchange_rate_mock_service:
                try:
                    return await exchange_rate_mock_service.get_rate(
                        from_currency=from_code,
                        to_currency=to_code,
                    )
                except Exception:
                    pass

            raise DentalOSError(
                error=ExchangeRateErrors.SERVICE_UNAVAILABLE,
                message="Servicio de tasas de cambio no disponible.",
                status_code=503,
                details={"from_currency": from_code, "to_currency": to_code},
            ) from exc


# Module-level singleton — import this in route handlers and other services.
exchange_rate_service = ExchangeRateService()
