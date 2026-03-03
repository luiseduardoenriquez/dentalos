"""Unit tests for the ExchangeRateService class.

Tests cover:
  - get_rate: returns cached value when Redis hit
  - get_rate: fetches from adapter when cache miss
  - get_rate: same currency returns 1.0 immediately
  - get_rate: unsupported currency raises DentalOSError
  - get_all_rates: returns all pairs for base currency
  - get_rate_for_invoice: COP invoice returns None (no conversion needed)
  - mock adapter determinism
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import ExchangeRateErrors
from app.core.exceptions import DentalOSError
from app.services.exchange_rate_service import ExchangeRateService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_rate_dict(from_c: str, to_c: str, rate: float) -> dict:
    return {
        "from_currency": from_c,
        "to_currency": to_c,
        "rate": rate,
        "rate_date": date.today().isoformat(),
        "cached": False,
    }


# ── get_rate ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetRate:
    """Tests for ExchangeRateService.get_rate."""

    async def test_get_rate_returns_cached(self):
        """If Redis returns a cached value, it must be returned without calling the adapter."""
        cached_data = _make_rate_dict("USD", "COP", 4150.0)

        with patch("app.services.exchange_rate_service.get_cached", new_callable=AsyncMock, return_value=cached_data):
            with patch("app.services.exchange_rate_service.set_cached", new_callable=AsyncMock):
                service = ExchangeRateService()
                result = await service.get_rate("USD", "COP")

        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "COP"
        assert result["rate"] == 4150.0
        assert result["cached"] is True

    async def test_get_rate_fetches_from_api(self):
        """Cache miss must trigger adapter fetch and cache write."""
        with patch("app.services.exchange_rate_service.get_cached", new_callable=AsyncMock, return_value=None):
            with patch("app.services.exchange_rate_service.set_cached", new_callable=AsyncMock) as mock_set:
                with patch.object(ExchangeRateService, "_fetch_rate", new_callable=AsyncMock, return_value=Decimal("4150.0")):
                    service = ExchangeRateService()
                    result = await service.get_rate("USD", "COP")

        assert result["rate"] == 4150.0
        assert result["cached"] is False
        # Must write to cache after successful fetch
        mock_set.assert_called_once()

    async def test_get_rate_cop_to_cop_returns_one(self):
        """Same currency (COP -> COP) must return rate=1.0 without any IO."""
        with patch("app.services.exchange_rate_service.get_cached", new_callable=AsyncMock) as mock_cache:
            service = ExchangeRateService()
            result = await service.get_rate("COP", "COP")

        assert result["rate"] == 1.0
        assert result["from_currency"] == "COP"
        assert result["to_currency"] == "COP"
        # Cache must NOT be consulted for identity conversions
        mock_cache.assert_not_called()

    async def test_get_rate_unsupported_currency_raises(self):
        """Unsupported currency code must raise DentalOSError with status 400."""
        service = ExchangeRateService()

        with pytest.raises(DentalOSError) as exc_info:
            await service.get_rate("XYZ", "COP")

        assert exc_info.value.error == ExchangeRateErrors.UNSUPPORTED_CURRENCY
        assert exc_info.value.status_code == 400

    async def test_get_rate_unsupported_target_currency_raises(self):
        """Unsupported target currency also raises DentalOSError."""
        service = ExchangeRateService()

        with pytest.raises(DentalOSError) as exc_info:
            await service.get_rate("COP", "BTC")

        assert exc_info.value.error == ExchangeRateErrors.UNSUPPORTED_CURRENCY

    async def test_get_rate_case_insensitive(self):
        """Currency codes must be normalized to upper-case."""
        with patch("app.services.exchange_rate_service.get_cached", new_callable=AsyncMock, return_value=None):
            with patch("app.services.exchange_rate_service.set_cached", new_callable=AsyncMock):
                with patch.object(ExchangeRateService, "_fetch_rate", new_callable=AsyncMock, return_value=Decimal("4150.0")):
                    service = ExchangeRateService()
                    result = await service.get_rate("usd", "cop")

        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "COP"


# ── get_all_rates ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetAllRates:
    """Tests for ExchangeRateService.get_all_rates."""

    async def test_get_all_rates(self):
        """get_all_rates returns a list excluding base/base pair."""
        with patch.object(ExchangeRateService, "get_rate", new_callable=AsyncMock) as mock_get_rate:
            mock_get_rate.return_value = _make_rate_dict("USD", "COP", 4150.0)

            service = ExchangeRateService()
            rates = await service.get_all_rates(base_currency="COP")

        # 3 supported currencies other than COP (USD, EUR, MXN)
        assert len(rates) == 3

    async def test_get_all_rates_unsupported_base_raises(self):
        """Unsupported base currency must raise DentalOSError."""
        service = ExchangeRateService()

        with pytest.raises(DentalOSError) as exc_info:
            await service.get_all_rates(base_currency="ZZZ")

        assert exc_info.value.error == ExchangeRateErrors.UNSUPPORTED_CURRENCY


# ── get_rate_for_invoice ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetRateForInvoice:
    """Tests for ExchangeRateService.get_rate_for_invoice."""

    async def test_get_rate_for_invoice_cop_returns_none(self):
        """COP invoice needs no conversion — must return None."""
        service = ExchangeRateService()
        result = await service.get_rate_for_invoice("COP")

        assert result is None

    async def test_get_rate_for_invoice_usd_returns_rate(self):
        """Non-COP invoice must return a rate dict."""
        with patch.object(ExchangeRateService, "get_rate", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _make_rate_dict("USD", "COP", 4150.0)

            service = ExchangeRateService()
            result = await service.get_rate_for_invoice("USD")

        assert result is not None
        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "COP"

    async def test_get_rate_for_invoice_unsupported_raises(self):
        """Unsupported invoice currency must raise DentalOSError."""
        service = ExchangeRateService()

        with pytest.raises(DentalOSError) as exc_info:
            await service.get_rate_for_invoice("BTC")

        assert exc_info.value.error == ExchangeRateErrors.UNSUPPORTED_CURRENCY


# ── mock service determinism ──────────────────────────────────────────────────


@pytest.mark.unit
class TestMockServiceDeterminism:
    """Tests for the mock exchange rate adapter."""

    async def test_mock_service_deterministic(self):
        """Mock adapter must return consistent rates across calls."""
        from app.integrations.exchange_rates.mock_service import exchange_rate_mock_service

        rate1 = await exchange_rate_mock_service.get_rate("USD", "COP")
        rate2 = await exchange_rate_mock_service.get_rate("USD", "COP")

        assert rate1 == rate2
        assert rate1 > 0
