"""Banco de la Republica TRM exchange rate service — VP-14 Multi-Currency.

Fetches the official Tasa Representativa del Mercado (TRM) for USD/COP from
the Colombian government open data portal (datos.gov.co). For other currency
pairs (EUR, MXN) it derives cross rates via USD or falls back to static
values when the API does not cover the pair directly.

Security:
  - exchange_rate_api_key is never logged.
  - All HTTP calls use a 15 s timeout.
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

import httpx

from app.core.config import settings
from app.integrations.exchange_rates.base import ExchangeRateServiceBase

logger = logging.getLogger("dentalos.integrations.exchange_rates")

# Supported currency codes.
SUPPORTED_CURRENCIES = {"COP", "USD", "EUR", "MXN"}

# Static fallback rates when the API cannot provide a cross rate.
# These are approximate and used only as a last resort.
_STATIC_FALLBACK_RATES: dict[tuple[str, str], Decimal] = {
    ("USD", "COP"): Decimal("4150.000000"),
    ("COP", "USD"): Decimal("0.000241"),
    ("EUR", "COP"): Decimal("4520.000000"),
    ("COP", "EUR"): Decimal("0.000221"),
    ("EUR", "USD"): Decimal("1.089157"),
    ("USD", "EUR"): Decimal("0.918100"),
    ("MXN", "COP"): Decimal("240.000000"),
    ("COP", "MXN"): Decimal("0.004167"),
    ("USD", "MXN"): Decimal("17.291667"),
    ("MXN", "USD"): Decimal("0.057831"),
    ("EUR", "MXN"): Decimal("18.833333"),
    ("MXN", "EUR"): Decimal("0.053097"),
}

# 6-decimal precision quantizer.
_PRECISION = Decimal("0.000001")


class BancoRepublicaService(ExchangeRateServiceBase):
    """Production exchange rate service using Banco de la Republica TRM API.

    Uses a lazily-initialized httpx.AsyncClient so the service can be
    instantiated at module load time without requiring the event loop.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Accept": "application/json",
            }
            # The datos.gov.co Socrata API uses an app token, not Bearer auth.
            if settings.exchange_rate_api_key:
                headers["X-App-Token"] = settings.exchange_rate_api_key

            self._client = httpx.AsyncClient(
                base_url=settings.exchange_rate_api_url,
                timeout=httpx.Timeout(15.0),
                headers=headers,
            )
        return self._client

    def is_configured(self) -> bool:
        """Return True if exchange_rate_api_key is set.

        The datos.gov.co API works without a key (throttled), but having
        a key ensures higher rate limits for production use.
        """
        return bool(settings.exchange_rate_api_key)

    async def _fetch_usd_cop_trm(self) -> Decimal | None:
        """Fetch the most recent USD/COP TRM from datos.gov.co.

        The API returns an array of records sorted by date.  We request
        the single most recent record via ``$order=vigenciadesde DESC``
        and ``$limit=1``.

        Returns:
            Decimal rate, or None if the call failed.
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "",
                params={
                    "$order": "vigenciadesde DESC",
                    "$limit": "1",
                },
            )
            response.raise_for_status()

            data = response.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.warning("TRM API returned empty data set")
                return None

            record = data[0]
            # The field name is "valor" in the datos.gov.co TRM dataset.
            raw_value = record.get("valor")
            if raw_value is None:
                logger.warning("TRM record missing 'valor' field: %s", list(record.keys()))
                return None

            rate = Decimal(str(raw_value)).quantize(_PRECISION, rounding=ROUND_HALF_UP)
            logger.info("TRM USD/COP fetched: %s", rate)
            return rate

        except httpx.TimeoutException:
            logger.warning("TRM API request timed out")
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("TRM API returned HTTP %d", exc.response.status_code)
            return None
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("Failed to parse TRM API response: %s", exc)
            return None

    async def get_rate(self, *, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate for a currency pair.

        Strategy:
          1. If from == to, return 1.
          2. For USD/COP or COP/USD, fetch live TRM.
          3. For other pairs, derive via USD cross rate if possible.
          4. Fall back to static rates if all else fails.

        Args:
            from_currency: ISO 4217 code (uppercase).
            to_currency: ISO 4217 code (uppercase).

        Returns:
            Decimal rate with 6-decimal precision.

        Raises:
            ValueError: If either currency is not in SUPPORTED_CURRENCIES.
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

        # Direct USD/COP from live TRM.
        if (from_code, to_code) == ("USD", "COP"):
            trm = await self._fetch_usd_cop_trm()
            if trm is not None:
                return trm
            return self._static_fallback(from_code, to_code)

        if (from_code, to_code) == ("COP", "USD"):
            trm = await self._fetch_usd_cop_trm()
            if trm is not None and trm > 0:
                return (Decimal("1") / trm).quantize(_PRECISION, rounding=ROUND_HALF_UP)
            return self._static_fallback(from_code, to_code)

        # Cross-rate derivation via USD.
        # E.g. EUR/COP = (EUR/USD) * (USD/COP)
        # We only have live data for USD/COP, so other legs use static rates.
        trm = await self._fetch_usd_cop_trm()

        if from_code == "COP":
            # COP -> X = (COP -> USD) * (USD -> X)
            usd_cop = trm if trm is not None else self._static_fallback("USD", "COP")
            cop_usd = (Decimal("1") / usd_cop).quantize(_PRECISION, rounding=ROUND_HALF_UP)
            usd_to_target = self._static_fallback("USD", to_code)
            return (cop_usd * usd_to_target).quantize(_PRECISION, rounding=ROUND_HALF_UP)

        if to_code == "COP":
            # X -> COP = (X -> USD) * (USD -> COP)
            usd_cop = trm if trm is not None else self._static_fallback("USD", "COP")
            source_to_usd = self._static_fallback(from_code, "USD")
            return (source_to_usd * usd_cop).quantize(_PRECISION, rounding=ROUND_HALF_UP)

        # Neither side is COP (e.g. EUR/MXN) — pure static fallback.
        return self._static_fallback(from_code, to_code)

    @staticmethod
    def _static_fallback(from_code: str, to_code: str) -> Decimal:
        """Return a static fallback rate for the given pair.

        Raises ValueError if the pair is not in the fallback table.
        """
        rate = _STATIC_FALLBACK_RATES.get((from_code, to_code))
        if rate is None:
            raise ValueError(
                f"No fallback rate available for {from_code}/{to_code}"
            )
        logger.debug("Using static fallback rate for %s/%s: %s", from_code, to_code, rate)
        return rate

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton — import this in services and route handlers.
banco_republica_service = BancoRepublicaService()
