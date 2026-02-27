"""Mexico compliance adapter (Sprint 15-16 stub).

Implements ComplianceAdapter for Mexican regulatory requirements:
- NOM-024-SSA3 -- Minimum data elements for clinical records
- CFDI 4.0 -- Electronic invoicing via PAC (stub -- not yet integrated)
- SINBA -- Health service reporting (stub -- not yet integrated)
- RFC validation -- Mexican tax ID (Registro Federal de Contribuyentes)
- CURP validation -- Mexican national ID (Clave Unica de Registro de Poblacion)
- CIE-9-MC -- Mexican procedure code system
"""

import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.base import ComplianceAdapter

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
        """Generate CFDI 4.0 electronic invoice data via PAC.

        Raises NotImplementedError until CFDI 4.0 PAC integration is built.
        Mexico requires all invoices to be stamped by a PAC (Proveedor
        Autorizado de Certificacion) before they are legally valid.
        """
        raise NotImplementedError("CFDI 4.0 integration pending for Mexico")

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
