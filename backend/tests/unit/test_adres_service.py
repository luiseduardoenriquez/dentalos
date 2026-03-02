"""Unit tests for the ADRESServiceMock class.

Tests cover deterministic bucket selection based on the last digit of the
Colombian document number:
  - 0-5 → activo, contributivo, EPS Sura (EPS010)
  - 6-7 → activo, subsidiado, Capital Salud (EPSC09)
  - 8   → inactivo (last known EPS Sura)
  - 9   → no_afiliado (no EPS data)

PHI note: Document numbers used in test assertions are fictional values
chosen only to hit the required last-digit bucket. No real patient data
is ever used.
"""

import pytest

from app.integrations.adres.mock_service import ADRESServiceMock


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_mock() -> ADRESServiceMock:
    """Return a fresh ADRESServiceMock instance."""
    return ADRESServiceMock()


# ── verify_affiliation ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestVerifyAffiliationActiveContributivo:
    """Documents ending in 0-5 → activo, contributivo, EPS Sura."""

    async def test_last_digit_0_returns_activo_contributivo(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000000",  # ends in 0
        )
        assert result.affiliation_status == "activo"
        assert result.regime == "contributivo"

    async def test_last_digit_3_returns_eps_sura(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000003",  # ends in 3
        )
        assert result.eps_code == "EPS010"
        assert result.eps_name == "EPS Sura"

    async def test_last_digit_5_is_found(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="TI",
            document_number="99999995",  # ends in 5
        )
        assert result.found is True

    async def test_contributivo_has_copay_category_b(self):
        """Contributivo regime patients should be in copay category B."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000001",  # ends in 1
        )
        assert result.copay_category == "B"

    async def test_verification_date_is_populated(self):
        """verification_date must always be set by the mock."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000002",  # ends in 2
        )
        assert result.verification_date is not None

    async def test_document_type_is_echoed_back(self):
        """The returned document_type must match the input."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CE",
            document_number="10000004",  # ends in 4
        )
        assert result.document_type == "CE"


@pytest.mark.unit
class TestVerifyAffiliationActiveSubsidiado:
    """Documents ending in 6-7 → activo, subsidiado, Capital Salud."""

    async def test_last_digit_6_returns_activo_subsidiado(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000006",  # ends in 6
        )
        assert result.affiliation_status == "activo"
        assert result.regime == "subsidiado"

    async def test_last_digit_7_returns_capital_salud(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000007",  # ends in 7
        )
        assert result.eps_code == "EPSC09"
        assert "Capital Salud" in result.eps_name

    async def test_subsidiado_has_copay_category_a(self):
        """Subsidiado regime patients should be in copay category A."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000006",  # ends in 6
        )
        assert result.copay_category == "A"

    async def test_subsidiado_is_found(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="TI",
            document_number="88888887",  # ends in 7
        )
        assert result.found is True


@pytest.mark.unit
class TestVerifyAffiliationInactive:
    """Documents ending in 8 → inactivo, still found in registry."""

    async def test_last_digit_8_returns_inactivo(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000008",  # ends in 8
        )
        assert result.affiliation_status == "inactivo"

    async def test_inactivo_is_found_in_registry(self):
        """Inactive affiliation is still found — just no longer active."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000008",  # ends in 8
        )
        assert result.found is True

    async def test_inactivo_has_no_copay_category(self):
        """Inactive affiliates have no copay category."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="PA",
            document_number="77777778",  # ends in 8
        )
        assert result.copay_category is None

    async def test_inactivo_retains_last_known_eps(self):
        """Inactive records still show the last known EPS (Sura)."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="55555558",  # ends in 8
        )
        assert result.eps_code == "EPS010"


@pytest.mark.unit
class TestVerifyAffiliationNotFound:
    """Documents ending in 9 → no_afiliado, not in registry."""

    async def test_last_digit_9_returns_no_afiliado(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="10000009",  # ends in 9
        )
        assert result.affiliation_status == "no_afiliado"

    async def test_no_afiliado_is_not_found(self):
        """no_afiliado means the person has no EPS registration at all."""
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CC",
            document_number="99999999",  # ends in 9
        )
        assert result.found is False

    async def test_no_afiliado_has_no_eps_name(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="TI",
            document_number="12345679",  # ends in 9
        )
        assert result.eps_name is None
        assert result.eps_code is None

    async def test_no_afiliado_has_no_regime(self):
        mock = _make_mock()
        result = await mock.verify_affiliation(
            document_type="CE",
            document_number="98765439",  # ends in 9
        )
        assert result.regime is None
