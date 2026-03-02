"""Unit tests for Mexico compliance adapters and CFDI builder.

Tests:
  - RFC validation regex (MexicoComplianceAdapter.validate_tax_id)
  - CURP validation regex (MexicoComplianceAdapter.validate_curp)
  - CIE-9-MC procedure code validation (validate_procedure_code)
  - get_procedure_code_system returns "CIE-9-MC"
  - country_code returns "MX"
  - build_cfdi_xml returns valid XML with CFDI 4.0 structure
  - compute_cadena_original returns non-empty SHA-256 hex digest
  - build_conceptos_cadena returns pipe-delimited string
"""

import pytest

from app.compliance.mexico.adapter import MexicoComplianceAdapter
from app.compliance.mexico.cfdi import (
    build_cfdi_xml,
    build_conceptos_cadena,
    compute_cadena_original,
)


@pytest.fixture
def adapter():
    return MexicoComplianceAdapter()


# ─── Country code ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCountryCode:
    def test_country_code_is_mx(self, adapter):
        assert adapter.country_code == "MX"

    def test_procedure_code_system(self, adapter):
        assert adapter.get_procedure_code_system() == "CIE-9-MC"


# ─── RFC Validation ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRFCValidation:
    def test_valid_physical_person(self, adapter):
        assert adapter.validate_tax_id("GOME820105AB3") is True

    def test_valid_legal_entity(self, adapter):
        assert adapter.validate_tax_id("SAT970701NN3") is True

    def test_valid_with_ampersand(self, adapter):
        assert adapter.validate_tax_id("A&C010101AAA") is True

    def test_valid_with_ene(self, adapter):
        assert adapter.validate_tax_id("GOÑE820105AB3") is True

    def test_case_insensitive(self, adapter):
        assert adapter.validate_tax_id("gome820105ab3") is True

    def test_invalid_too_short(self, adapter):
        assert adapter.validate_tax_id("GO820105AB3") is False

    def test_invalid_no_digits(self, adapter):
        assert adapter.validate_tax_id("GOMEABCDEFAB3") is False

    def test_invalid_empty(self, adapter):
        assert adapter.validate_tax_id("") is False

    def test_invalid_special_chars(self, adapter):
        assert adapter.validate_tax_id("GOME82@105AB3") is False


# ─── CURP Validation ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCURPValidation:
    def test_valid_male(self, adapter):
        assert adapter.validate_curp("GOML820105HDFMRN01") is True

    def test_valid_female(self, adapter):
        assert adapter.validate_curp("GOML820105MDFMRN01") is True

    def test_case_insensitive(self, adapter):
        assert adapter.validate_curp("goml820105hdfmrn01") is True

    def test_invalid_too_short(self, adapter):
        assert adapter.validate_curp("GOML820105HDF") is False

    def test_invalid_wrong_sex_char(self, adapter):
        assert adapter.validate_curp("GOML820105XDFMRN01") is False

    def test_invalid_empty(self, adapter):
        assert adapter.validate_curp("") is False


# ─── CIE-9-MC Procedure Code Validation ─────────────────────────────────────


@pytest.mark.unit
class TestCIE9MCValidation:
    def test_valid_4_digit(self, adapter):
        assert adapter.validate_procedure_code("9904") is True

    def test_valid_2_digit(self, adapter):
        assert adapter.validate_procedure_code("01") is True

    def test_valid_with_decimal(self, adapter):
        assert adapter.validate_procedure_code("99.04") is True

    def test_valid_3_digit_with_decimal(self, adapter):
        assert adapter.validate_procedure_code("123.4") is True

    def test_invalid_letters(self, adapter):
        assert adapter.validate_procedure_code("abc") is False

    def test_invalid_empty(self, adapter):
        assert adapter.validate_procedure_code("") is False

    def test_invalid_single_digit(self, adapter):
        assert adapter.validate_procedure_code("1") is False


# ─── CFDI XML Builder ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildCFDIXML:
    def test_returns_xml_string(self):
        xml = build_cfdi_xml(
            serie="DEN",
            folio="001",
            fecha="2026-01-15T10:30:00",
            forma_pago="01",
            subtotal_cents=150000,
            total_cents=150000,
            lugar_expedicion="06600",
            rfc_emisor="GOME820105AB3",
            nombre_emisor="Dr. Test",
            regimen_fiscal_emisor="612",
            rfc_receptor="XAXX010101000",
            nombre_receptor="PUBLICO EN GENERAL",
            domicilio_fiscal_receptor="06600",
            regimen_fiscal_receptor="616",
            line_items=[
                {
                    "description": "Limpieza dental",
                    "quantity": 1,
                    "unit_value_cents": 150000,
                    "line_total_cents": 150000,
                }
            ],
        )
        assert isinstance(xml, str)
        assert "<?xml" in xml
        assert "Comprobante" in xml
        assert "Version" in xml

    def test_contains_emisor_and_receptor(self):
        xml = build_cfdi_xml(
            serie="A",
            folio="1",
            fecha="2026-01-01T00:00:00",
            forma_pago="01",
            subtotal_cents=10000,
            total_cents=10000,
            lugar_expedicion="06600",
            rfc_emisor="TEST820105AB3",
            nombre_emisor="Test Dentist",
            regimen_fiscal_emisor="612",
            rfc_receptor="XAXX010101000",
            nombre_receptor="Patient Name",
            domicilio_fiscal_receptor="06600",
            regimen_fiscal_receptor="616",
            line_items=[],
        )
        assert "Emisor" in xml
        assert "Receptor" in xml

    def test_monetary_values_formatted(self):
        xml = build_cfdi_xml(
            serie="DEN",
            folio="002",
            fecha="2026-01-15T10:30:00",
            forma_pago="01",
            subtotal_cents=150050,
            total_cents=150050,
            lugar_expedicion="06600",
            rfc_emisor="GOME820105AB3",
            nombre_emisor="Dr. Test",
            regimen_fiscal_emisor="612",
            rfc_receptor="XAXX010101000",
            nombre_receptor="Patient",
            domicilio_fiscal_receptor="06600",
            regimen_fiscal_receptor="616",
            line_items=[],
        )
        assert "1500.50" in xml


# ─── Cadena Original ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestComputeCadenaOriginal:
    def test_returns_sha256_hex(self):
        result = compute_cadena_original(
            version="4.0",
            serie="DEN",
            folio="001",
            fecha="2026-01-15T10:30:00",
            forma_pago="01",
            subtotal="1500.00",
            moneda="MXN",
            total="1500.00",
            tipo_comprobante="I",
            metodo_pago="PUE",
            lugar_expedicion="06600",
            rfc_emisor="GOME820105AB3",
            nombre_emisor="Dr. Test",
            regimen_fiscal_emisor="612",
            rfc_receptor="XAXX010101000",
            nombre_receptor="PUBLICO EN GENERAL",
            domicilio_fiscal_receptor="06600",
            regimen_fiscal_receptor="616",
            uso_cfdi="D01",
            conceptos_cadena="85121500|ACT|1|Limpieza dental|1500.00|1500.00",
        )
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex = 64 chars

    def test_deterministic(self):
        kwargs = dict(
            version="4.0",
            serie="A",
            folio="1",
            fecha="2026-01-01T00:00:00",
            forma_pago="01",
            subtotal="100.00",
            moneda="MXN",
            total="100.00",
            tipo_comprobante="I",
            metodo_pago="PUE",
            lugar_expedicion="06600",
            rfc_emisor="TEST820105AB3",
            nombre_emisor="Test",
            regimen_fiscal_emisor="612",
            rfc_receptor="XAXX010101000",
            nombre_receptor="Public",
            domicilio_fiscal_receptor="06600",
            regimen_fiscal_receptor="616",
            uso_cfdi="D01",
            conceptos_cadena="",
        )
        result1 = compute_cadena_original(**kwargs)
        result2 = compute_cadena_original(**kwargs)
        assert result1 == result2


# ─── Build Conceptos Cadena ──────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildConceptosCadena:
    def test_single_item(self):
        result = build_conceptos_cadena([
            {
                "description": "Limpieza dental",
                "quantity": 1,
                "unit_value_cents": 150000,
                "line_total_cents": 150000,
            }
        ])
        assert isinstance(result, str)
        assert "Limpieza dental" in result
        assert "|" in result

    def test_empty_list(self):
        result = build_conceptos_cadena([])
        assert result == ""

    def test_multiple_items(self):
        result = build_conceptos_cadena([
            {"description": "Item A", "quantity": 1, "unit_value_cents": 10000, "line_total_cents": 10000},
            {"description": "Item B", "quantity": 2, "unit_value_cents": 5000, "line_total_cents": 10000},
        ])
        assert "Item A" in result
        assert "Item B" in result
