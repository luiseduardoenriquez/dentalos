"""Unit tests for patient import and merge schemas (field_validators).

Tests the 8 field_validator decorators in app.schemas.patient_import:
  1. validate_tipo_documento — CC/TI/CE/PA/RC/NIT valid, others raise
  2. validate_numero_documento — 6-12 digits valid, letters/short raise
  3. strip_names — whitespace stripped, blank raises
  4. validate_telefono — LATAM phone valid, letters raise, None passes
  5. validate_genero — male/female/other valid, unknown raises, None passes
  6. normalize_email — lowercased/stripped, empty becomes None
  7. birthdate_not_in_future — past valid, future raises, None passes
  8. patients_must_differ (merge) — same UUID raises, different UUIDs pass
"""

import uuid
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.patient_import import PatientCSVRow, PatientMergeRequest


def _valid_row(**overrides) -> dict:
    """Return a minimal valid PatientCSVRow dict with optional overrides."""
    base = {
        "tipo_documento": "CC",
        "numero_documento": "1234567890",
        "nombres": "Juan",
        "apellidos": "Pérez",
    }
    base.update(overrides)
    return base


# ─── 1. validate_tipo_documento ──────────────────────────────────────────────


@pytest.mark.unit
class TestValidateTipoDocumento:
    @pytest.mark.parametrize("tipo", ["CC", "TI", "CE", "PA", "RC", "NIT"])
    def test_valid_types(self, tipo):
        row = PatientCSVRow(**_valid_row(tipo_documento=tipo))
        assert row.tipo_documento == tipo

    def test_case_insensitive(self):
        row = PatientCSVRow(**_valid_row(tipo_documento="  cc  "))
        assert row.tipo_documento == "CC"

    def test_invalid_type(self):
        with pytest.raises(ValidationError, match="tipo_documento"):
            PatientCSVRow(**_valid_row(tipo_documento="INVALID"))

    def test_empty_string(self):
        with pytest.raises(ValidationError):
            PatientCSVRow(**_valid_row(tipo_documento=""))


# ─── 2. validate_numero_documento ────────────────────────────────────────────


@pytest.mark.unit
class TestValidateNumeroDocumento:
    def test_valid_6_digits(self):
        row = PatientCSVRow(**_valid_row(numero_documento="123456"))
        assert row.numero_documento == "123456"

    def test_valid_12_digits(self):
        row = PatientCSVRow(**_valid_row(numero_documento="123456789012"))
        assert row.numero_documento == "123456789012"

    def test_strips_whitespace(self):
        row = PatientCSVRow(**_valid_row(numero_documento="  1234567890  "))
        assert row.numero_documento == "1234567890"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="numero_documento"):
            PatientCSVRow(**_valid_row(numero_documento="12345"))

    def test_too_long(self):
        with pytest.raises(ValidationError, match="numero_documento"):
            PatientCSVRow(**_valid_row(numero_documento="1234567890123"))

    def test_letters_rejected(self):
        with pytest.raises(ValidationError, match="numero_documento"):
            PatientCSVRow(**_valid_row(numero_documento="ABC123"))


# ─── 3. strip_names ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestStripNames:
    def test_strips_whitespace_nombres(self):
        row = PatientCSVRow(**_valid_row(nombres="  Juan Carlos  "))
        assert row.nombres == "Juan Carlos"

    def test_strips_whitespace_apellidos(self):
        row = PatientCSVRow(**_valid_row(apellidos="  García López  "))
        assert row.apellidos == "García López"

    def test_blank_nombres_raises(self):
        with pytest.raises(ValidationError, match="blank"):
            PatientCSVRow(**_valid_row(nombres="   "))

    def test_blank_apellidos_raises(self):
        with pytest.raises(ValidationError, match="blank"):
            PatientCSVRow(**_valid_row(apellidos="   "))


# ─── 4. validate_telefono ───────────────────────────────────────────────────


@pytest.mark.unit
class TestValidateTelefono:
    def test_valid_colombian_phone(self):
        row = PatientCSVRow(**_valid_row(telefono="+573001234567"))
        assert row.telefono == "+573001234567"

    def test_valid_without_plus(self):
        row = PatientCSVRow(**_valid_row(telefono="3001234567"))
        assert row.telefono == "3001234567"

    def test_none_passes(self):
        row = PatientCSVRow(**_valid_row(telefono=None))
        assert row.telefono is None

    def test_letters_rejected(self):
        with pytest.raises(ValidationError, match="telefono"):
            PatientCSVRow(**_valid_row(telefono="abc"))

    def test_empty_string_becomes_none(self):
        row = PatientCSVRow(**_valid_row(telefono="  "))
        assert row.telefono is None


# ─── 5. validate_genero ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestValidateGenero:
    @pytest.mark.parametrize("genero", ["male", "female", "other"])
    def test_valid_genders(self, genero):
        row = PatientCSVRow(**_valid_row(genero=genero))
        assert row.genero == genero

    def test_case_insensitive(self):
        row = PatientCSVRow(**_valid_row(genero="  MALE  "))
        assert row.genero == "male"

    def test_none_passes(self):
        row = PatientCSVRow(**_valid_row(genero=None))
        assert row.genero is None

    def test_invalid_gender(self):
        with pytest.raises(ValidationError, match="genero"):
            PatientCSVRow(**_valid_row(genero="unknown"))

    def test_empty_string_becomes_none(self):
        row = PatientCSVRow(**_valid_row(genero="  "))
        assert row.genero is None


# ─── 6. normalize_email ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestNormalizeEmail:
    def test_lowercased(self):
        row = PatientCSVRow(**_valid_row(email="TEST@CLINIC.CO"))
        assert row.email == "test@clinic.co"

    def test_stripped(self):
        row = PatientCSVRow(**_valid_row(email="  test@clinic.co  "))
        assert row.email == "test@clinic.co"

    def test_empty_becomes_none(self):
        row = PatientCSVRow(**_valid_row(email="  "))
        assert row.email is None

    def test_none_passes(self):
        row = PatientCSVRow(**_valid_row(email=None))
        assert row.email is None


# ─── 7. birthdate_not_in_future ──────────────────────────────────────────────


@pytest.mark.unit
class TestBirthdateNotInFuture:
    def test_past_date_valid(self):
        row = PatientCSVRow(**_valid_row(fecha_nacimiento=date(1990, 5, 15)))
        assert row.fecha_nacimiento == date(1990, 5, 15)

    def test_today_valid(self):
        row = PatientCSVRow(**_valid_row(fecha_nacimiento=date.today()))
        assert row.fecha_nacimiento == date.today()

    def test_future_raises(self):
        with pytest.raises(ValidationError, match="future"):
            PatientCSVRow(**_valid_row(
                fecha_nacimiento=date.today() + timedelta(days=1)
            ))

    def test_none_passes(self):
        row = PatientCSVRow(**_valid_row(fecha_nacimiento=None))
        assert row.fecha_nacimiento is None


# ─── 8. patients_must_differ (PatientMergeRequest) ───────────────────────────


@pytest.mark.unit
class TestPatientsMustDiffer:
    def test_different_ids_valid(self):
        req = PatientMergeRequest(
            primary_patient_id=uuid.uuid4(),
            secondary_patient_id=uuid.uuid4(),
        )
        assert req.primary_patient_id != req.secondary_patient_id

    def test_same_ids_raises(self):
        same_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="different"):
            PatientMergeRequest(
                primary_patient_id=same_id,
                secondary_patient_id=same_id,
            )
