"""Colombia compliance adapter implementation.

Implements ComplianceAdapter for Colombian regulatory requirements:
- RDA (Registro Dental Automatizado) -- Resolucion 1888 de 2025
- RIPS (Resolucion 3374) -- mandatory health service reporting
- DIAN e-invoicing -- UBL 2.1 via MATIAS API
- NIT validation -- Colombian tax ID
- CUPS -- Colombian Unified Procedure Code System
"""

import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.base import ComplianceAdapter

# Colombian NIT: 6-12 digits, optional dash and single check digit.
_NIT_PATTERN = re.compile(r"^[0-9]{6,12}(-[0-9])?$")

# CUPS codes are exactly 6 digits.
_CUPS_PATTERN = re.compile(r"^[0-9]{6}$")


class ColombiaComplianceAdapter(ComplianceAdapter):
    """Concrete compliance adapter for Colombia (CO).

    Tax ID and procedure code validation are implemented inline. Full RIPS,
    RDA, and DIAN logic lives in dedicated services (rips_service, rda_service,
    einvoice_service) called directly from API routes — not through this
    adapter. The stub methods below preserve the ComplianceAdapter interface
    contract but are intentionally no-ops.
    """

    @property
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 code for Colombia."""
        return "CO"

    # -- Clinical Record Compliance --

    def validate_clinical_record(self, record_data: dict) -> list[str]:
        """Validate clinical record against RDA/Resolucion 1888 requirements.

        Returns a list of validation error strings (empty if valid).
        No-op: actual validation lives in rda_service.validate_record().
        """
        return []

    def format_clinical_record(self, record_data: dict) -> dict:
        """Format clinical record for RDA-compliant export.

        Returns formatted record dictionary.
        No-op: actual formatting lives in rda_service.format_export().
        """
        return {}

    # -- Odontogram Compliance --

    def validate_odontogram(self, conditions: list[dict]) -> list[str]:
        """Validate odontogram data against RDA condition code requirements.

        Returns a list of validation error strings (empty if valid).
        No-op: actual validation lives in rda_service.validate_odontogram().
        """
        return []

    def format_odontogram_export(
        self, conditions: list[dict], states: list[dict]
    ) -> dict:
        """Format odontogram for RDA-compliant export.

        Returns formatted export dictionary.
        No-op: actual export lives in rda_service.export_odontogram().
        """
        return {}

    # -- Electronic Invoicing --

    def generate_invoice(self, invoice_data: dict) -> dict:
        """Generate DIAN UBL 2.1 electronic invoice data via MATIAS API.

        Returns generated invoice dictionary.
        No-op: actual e-invoicing lives in einvoice_service.submit_invoice().
        """
        return {}

    def validate_tax_id(self, tax_id: str) -> bool:
        """Validate Colombian NIT (Numero de Identificacion Tributaria).

        Format: 6-12 digits, optional dash followed by single check digit.
        Examples: '900123456', '900123456-7'.
        """
        return bool(_NIT_PATTERN.match(tax_id))

    # -- Health Service Reporting --

    async def generate_reporting_export(
        self,
        report_type: str,
        period_start: date,
        period_end: date,
        db: AsyncSession,
    ) -> dict:
        """Generate RIPS flat files for mandatory health service reporting.

        Colombia Resolucion 3374 requires: AC (consultation), AP (procedure),
        AM (medication) files with strict field ordering.
        Returns a dictionary with generated report data and file references.
        No-op: actual RIPS generation lives in rips_service.generate_export().
        """
        return {}

    # -- Procedure Code System --

    def get_procedure_code_system(self) -> str:
        """Return 'CUPS' (Clasificacion Unica de Procedimientos en Salud)."""
        return "CUPS"

    def validate_procedure_code(self, code: str) -> bool:
        """Validate CUPS code format (exactly 6 digits).

        Examples: '997010' (valid), '99701' (invalid -- too short).
        """
        return bool(_CUPS_PATTERN.match(code))
