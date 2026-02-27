"""Mexico compliance adapter (Sprint 15-16).

Implements ComplianceAdapter for Mexican regulatory requirements:
- NOM-024-SSA3 -- Minimum data elements for clinical records
- CFDI 4.0 -- Electronic invoicing via PAC (MX-01)
- SINBA -- Health service reporting (stub -- not yet integrated)
- RFC validation -- Mexican tax ID (Registro Federal de Contribuyentes)
- CURP validation -- Mexican national ID (Clave Unica de Registro de Poblacion)
- CIE-9-MC -- Mexican procedure code system
"""

import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.base import ComplianceAdapter
from app.compliance.mexico.cfdi import (
    build_cfdi_xml,
    build_conceptos_cadena,
    compute_cadena_original,
    sign_cfdi_xml,
)
from app.compliance.mexico.config import (
    DEFAULT_METODO_PAGO,
    DEFAULT_REGIMEN_FISCAL_PERSONA_FISICA,
    DEFAULT_USO_CFDI,
    PAYMENT_METHOD_TO_FORMA_PAGO,
)

# RFC: 3-4 chars (letters, N, &) + 6 digits (birthdate YYMMDD) + 3 alphanumeric (homoclave).
# Accepts both physical persons (4 chars) and legal entities (3 chars).
_RFC_PATTERN = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$")

# CURP: 4 letters + 6 digits (YYMMDD) + H/M (sex) + 2-letter state code +
#        3 consonants (surname/name) + 2 alphanumeric (differentiator + century).
_CURP_PATTERN = re.compile(r"^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9]{2}$")

# CIE-9-MC: 2-4 digits, optionally followed by dot and 1-2 more digits.
_CIE9MC_PATTERN = re.compile(r"^[0-9]{2,4}(\.[0-9]{1,2})?$")


class MexicoComplianceAdapter(ComplianceAdapter):
    """Concrete compliance adapter for Mexico (MX).

    Sprint 15-16 stub implementation. RFC and CURP validation are fully
    implemented. CFDI 4.0 e-invoicing and SINBA reporting raise
    NotImplementedError until those integrations are built out.
    """

    @property
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 code for Mexico."""
        return "MX"

    # -- Clinical Record Compliance --

    def validate_clinical_record(self, record_data: dict) -> list[str]:
        """Validate clinical record against NOM-024-SSA3 requirements.

        Returns a list of validation error strings (empty if valid).
        NOM-024-SSA3 defines minimum data elements for electronic clinical records.
        """
        # TODO: Sprint future -- full NOM-024-SSA3 validation
        # Will validate: mandatory fields per NOM-024, CURP if available,
        # diagnosis coded in ICD-10 or CIE-9-MC, institution codes.
        return []

    def format_clinical_record(self, record_data: dict) -> dict:
        """Format clinical record for NOM-024-SSA3-compliant export.

        Returns formatted record dictionary.
        """
        # TODO: Sprint future -- full NOM-024-SSA3 field mapping
        return {}

    # -- Odontogram Compliance --

    def validate_odontogram(self, conditions: list[dict]) -> list[str]:
        """Validate odontogram data against Mexican format requirements.

        Returns a list of validation error strings (empty if valid).
        """
        # TODO: Sprint future -- Mexico-specific odontogram validation rules
        return []

    def format_odontogram_export(
        self, conditions: list[dict], states: list[dict]
    ) -> dict:
        """Format odontogram for Mexico-compatible regulatory export.

        Returns formatted export dictionary.
        """
        # TODO: Sprint future -- Mexico-specific export format
        return {}

    # -- Electronic Invoicing --

    def generate_invoice(self, invoice_data: dict) -> dict:
        """Generate CFDI 4.0 electronic invoice data ready for PAC stamping.

        Builds the CFDI 4.0 XML, computes the cadena original, and returns
        a structured dict suitable for submission to the PAC via PACClient.

        Mexico requires all invoices to be stamped by a PAC (Proveedor
        Autorizado de Certificacion) before they are legally valid.

        Expected invoice_data keys:
          - serie (str): Invoice series identifier (e.g. "DEN").
          - folio (str): Sequential invoice number.
          - fecha (str): ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS).
          - payment_method (str): DentalOS payment method key (e.g. "cash").
          - subtotal_cents (int): Subtotal in MXN cents before taxes.
          - total_cents (int): Total in MXN cents (equals subtotal for exempt).
          - metodo_pago (str, optional): "PUE" or "PPD" (default "PUE").
          - lugar_expedicion (str): 5-digit postal code of issuer.
          - rfc_emisor (str): RFC of the issuing dentist or clinic.
          - nombre_emisor (str): Legal name of the issuing entity.
          - regimen_fiscal_emisor (str, optional): SAT regime code (default "612").
          - rfc_receptor (str): RFC of the patient/recipient.
          - nombre_receptor (str): Legal name of the patient/recipient.
          - domicilio_fiscal_receptor (str): 5-digit postal code of recipient.
          - regimen_fiscal_receptor (str): SAT regime code for recipient.
          - uso_cfdi (str, optional): SAT Uso CFDI code (default "D01").
          - line_items (list[dict]): See cfdi.build_cfdi_xml for item keys.
          - no_certificado (str, optional): CSD certificate number.
          - certificado (str, optional): Base64-encoded CSD certificate.

        Returns:
            dict with keys:
              - xml: Unsigned (or CSD-signed) CFDI 4.0 XML string.
              - cadena_original: SHA-256 hex digest of the cadena original.
              - rfc_emisor: Echo of the issuer RFC for PAC submission.
              - ready_for_stamping: True (always — indicates XML is built).
        """
        serie: str = invoice_data.get("serie", "DEN")
        folio: str = str(invoice_data.get("folio", ""))
        fecha: str = invoice_data.get("fecha", "")
        payment_method: str = invoice_data.get("payment_method", "cash")
        subtotal_cents: int = invoice_data.get("subtotal_cents", 0)
        total_cents: int = invoice_data.get("total_cents", 0)
        metodo_pago: str = invoice_data.get("metodo_pago", DEFAULT_METODO_PAGO)
        lugar_expedicion: str = invoice_data.get("lugar_expedicion", "")
        rfc_emisor: str = invoice_data.get("rfc_emisor", "")
        nombre_emisor: str = invoice_data.get("nombre_emisor", "")
        regimen_fiscal_emisor: str = invoice_data.get(
            "regimen_fiscal_emisor", DEFAULT_REGIMEN_FISCAL_PERSONA_FISICA
        )
        rfc_receptor: str = invoice_data.get("rfc_receptor", "XAXX010101000")  # public generic RFC
        nombre_receptor: str = invoice_data.get("nombre_receptor", "PUBLICO EN GENERAL")
        domicilio_fiscal_receptor: str = invoice_data.get("domicilio_fiscal_receptor", "")
        regimen_fiscal_receptor: str = invoice_data.get("regimen_fiscal_receptor", "616")
        uso_cfdi: str = invoice_data.get("uso_cfdi", DEFAULT_USO_CFDI)
        line_items: list[dict] = invoice_data.get("line_items", [])
        no_certificado: str = invoice_data.get("no_certificado", "")
        certificado: str = invoice_data.get("certificado", "")

        # Map DentalOS payment_method string to SAT Forma de Pago code.
        forma_pago: str = PAYMENT_METHOD_TO_FORMA_PAGO.get(payment_method, "01")

        # Build CFDI 4.0 XML (unsigned at this stage).
        xml_content = build_cfdi_xml(
            serie=serie,
            folio=folio,
            fecha=fecha,
            forma_pago=forma_pago,
            subtotal_cents=subtotal_cents,
            total_cents=total_cents,
            metodo_pago=metodo_pago,
            lugar_expedicion=lugar_expedicion,
            rfc_emisor=rfc_emisor,
            nombre_emisor=nombre_emisor,
            regimen_fiscal_emisor=regimen_fiscal_emisor,
            rfc_receptor=rfc_receptor,
            nombre_receptor=nombre_receptor,
            domicilio_fiscal_receptor=domicilio_fiscal_receptor,
            regimen_fiscal_receptor=regimen_fiscal_receptor,
            uso_cfdi=uso_cfdi,
            line_items=line_items,
            sello="",
            no_certificado=no_certificado,
            certificado=certificado,
        )

        # Apply CSD signature (stub for MVP — PAC sandbox accepts unsigned XML).
        xml_content = sign_cfdi_xml(xml_content)

        # Compute cadena original for audit / record-keeping.
        conceptos_cadena = build_conceptos_cadena(line_items)
        cadena_original = compute_cadena_original(
            version="4.0",
            serie=serie,
            folio=folio,
            fecha=fecha,
            forma_pago=forma_pago,
            subtotal=f"{subtotal_cents / 100:.2f}",
            moneda="MXN",
            total=f"{total_cents / 100:.2f}",
            tipo_comprobante="I",
            metodo_pago=metodo_pago,
            lugar_expedicion=lugar_expedicion,
            rfc_emisor=rfc_emisor,
            nombre_emisor=nombre_emisor,
            regimen_fiscal_emisor=regimen_fiscal_emisor,
            rfc_receptor=rfc_receptor,
            nombre_receptor=nombre_receptor,
            domicilio_fiscal_receptor=domicilio_fiscal_receptor,
            regimen_fiscal_receptor=regimen_fiscal_receptor,
            uso_cfdi=uso_cfdi,
            conceptos_cadena=conceptos_cadena,
        )

        return {
            "xml": xml_content,
            "cadena_original": cadena_original,
            "rfc_emisor": rfc_emisor,
            "ready_for_stamping": True,
        }

    def validate_tax_id(self, tax_id: str) -> bool:
        """Validate Mexican RFC (Registro Federal de Contribuyentes).

        Format: 3-4 uppercase letters/symbols + 6-digit birthdate (YYMMDD)
        + 3-char alphanumeric homoclave.
        Physical persons: 4-letter prefix. Legal entities: 3-letter prefix.
        Examples: 'GOME820105AB3' (valid person), 'SAT970701NN3' (valid entity).
        """
        return bool(_RFC_PATTERN.match(tax_id.upper()))

    # -- Health Service Reporting --

    async def generate_reporting_export(
        self,
        report_type: str,
        period_start: date,
        period_end: date,
        db: AsyncSession,
    ) -> dict:
        """Generate SINBA health service reports.

        Raises NotImplementedError until SINBA reporting integration is built.
        SINBA (Sistema de Informacion en Salud para Poblacion Abierta) is
        Mexico's mandatory health service reporting system.
        """
        raise NotImplementedError("SINBA reporting not yet implemented")

    # -- Procedure Code System --

    def get_procedure_code_system(self) -> str:
        """Return 'CIE-9-MC' (Clasificacion Internacional de Enfermedades, 9a revision, Modificacion Clinica)."""
        return "CIE-9-MC"

    def validate_procedure_code(self, code: str) -> bool:
        """Validate CIE-9-MC procedure code format.

        Format: 2-4 digits, optionally followed by a decimal point and 1-2 digits.
        Examples: '9904' (valid), '99.04' (valid), '01' (valid), 'abc' (invalid).
        """
        return bool(_CIE9MC_PATTERN.match(code))

    # -- Mexico-Specific Utilities --

    def validate_curp(self, curp: str) -> bool:
        """Validate Mexican CURP (Clave Unica de Registro de Poblacion).

        Format: 4 letters + 6-digit birthdate (YYMMDD) + H/M (sex) +
        2-letter state code + 3 consonants from surnames/name +
        2 alphanumeric differentiator chars.
        Example: 'GOML820105HDFMRN01' (valid).
        """
        return bool(_CURP_PATTERN.match(curp.upper()))
