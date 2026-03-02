"""Unit tests for the RETHUSServiceMock class.

Tests cover deterministic bucket selection based on the first character of
the RETHUS registration number:
  "1..." → found=True, profession="Odontólogo", no specialty, status="active"
  "2..." → found=True, profession="Odontólogo", specialty="Endodoncia", status="active"
  other  → found=False (no professional data)

PHI note: RETHUS numbers used in tests are fictional values chosen only to
hit a deterministic bucket. No real professional data is ever used or asserted.
"""

import pytest

from app.integrations.rethus.mock_service import RETHUSServiceMock


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_mock() -> RETHUSServiceMock:
    """Return a fresh RETHUSServiceMock instance."""
    return RETHUSServiceMock()


# ── verify_professional ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestVerifyProfessionalFound:
    """RETHUS numbers starting with '1' → found, general dentist."""

    async def test_number_starting_with_1_is_found(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="100001234")

        assert result.found is True

    async def test_number_starting_with_1_has_odontologist_profession(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="1XYZ")

        assert result.profession == "Odontólogo"

    async def test_number_starting_with_1_has_no_specialty(self):
        """General dentist bucket has no specialty."""
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="1000ABC")

        assert result.specialty is None

    async def test_number_starting_with_1_has_active_status(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="1-2345")

        assert result.status == "active"

    async def test_number_starting_with_1_verification_date_is_set(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="11111")

        assert result.verification_date is not None

    async def test_number_starting_with_1_echoes_rethus_number(self):
        """The returned rethus_number must match the queried one."""
        mock = _make_mock()
        rethus_number = "1-TEST"

        result = await mock.verify_professional(rethus_number=rethus_number)

        assert result.rethus_number == rethus_number


@pytest.mark.unit
class TestVerifyProfessionalSpecialist:
    """RETHUS numbers starting with '2' → found, endodontist."""

    async def test_number_starting_with_2_is_found(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="200005678")

        assert result.found is True

    async def test_number_starting_with_2_has_endodoncia_specialty(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="2-SPEC")

        assert result.specialty == "Endodoncia"

    async def test_number_starting_with_2_has_odontologist_base_profession(self):
        """Specialist still has Odontólogo as base profession."""
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="22222")

        assert result.profession == "Odontólogo"

    async def test_number_starting_with_2_has_active_status(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="2ABC")

        assert result.status == "active"

    async def test_number_starting_with_2_echoes_rethus_number(self):
        mock = _make_mock()
        rethus_number = "2-ENDO-001"

        result = await mock.verify_professional(rethus_number=rethus_number)

        assert result.rethus_number == rethus_number


@pytest.mark.unit
class TestVerifyProfessionalNotFound:
    """RETHUS numbers with any other first character → not found."""

    async def test_number_starting_with_3_is_not_found(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="300009999")

        assert result.found is False

    async def test_number_starting_with_alpha_is_not_found(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="A12345")

        assert result.found is False

    async def test_not_found_has_no_profession(self):
        """Not-found records should have no profession populated."""
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="999")

        assert result.profession is None

    async def test_not_found_has_no_specialty(self):
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="5-invalid")

        assert result.specialty is None

    async def test_not_found_still_echoes_rethus_number(self):
        """Even not-found results should echo the queried RETHUS number."""
        mock = _make_mock()
        rethus_number = "999-NOT-FOUND"

        result = await mock.verify_professional(rethus_number=rethus_number)

        assert result.rethus_number == rethus_number

    async def test_not_found_has_no_status(self):
        """Not-found records should have status=None."""
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="0-none")

        assert result.status is None

    async def test_not_found_verification_date_is_set(self):
        """verification_date must always be populated even for not-found responses."""
        mock = _make_mock()

        result = await mock.verify_professional(rethus_number="7-missing")

        assert result.verification_date is not None
