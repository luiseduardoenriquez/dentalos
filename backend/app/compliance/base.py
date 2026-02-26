"""Compliance adapter abstract base class (ADR-007).

Defines the interface for all country-specific compliance operations.
Each country implements a concrete adapter. The correct adapter is resolved
at runtime from the tenant's country_code and injected via FastAPI DI.
"""

from abc import ABC, abstractmethod
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession


class ComplianceAdapter(ABC):
    """Abstract interface for country-specific compliance operations.

    Resolved per-request from the tenant's country_code setting.
    See ADR-007 for design rationale and migration path.
    """

    @property
    @abstractmethod
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 country code (e.g. 'CO', 'MX')."""
        ...

    # -- Clinical Record Compliance --

    @abstractmethod
    def validate_clinical_record(self, record_data: dict) -> list[str]:
        """Validate a clinical record against country-specific requirements.

        Returns a list of validation error strings (empty if valid).
        Colombia: RDA fields, Resolucion 1888/1995 requirements.
        Mexico: NOM-024-SSA3 minimum data elements.
        """
        ...

    @abstractmethod
    def format_clinical_record(self, record_data: dict) -> dict:
        """Format a clinical record for country-specific regulatory export.

        Returns a dictionary with the formatted record fields suitable
        for the country's required export format.
        """
        ...

    # -- Odontogram Compliance --

    @abstractmethod
    def validate_odontogram(self, conditions: list[dict]) -> list[str]:
        """Validate odontogram data against country-specific format requirements.

        Colombia (RDA) mandates specific condition codes and recording conventions.
        Returns a list of validation error strings (empty if valid).
        """
        ...

    @abstractmethod
    def format_odontogram_export(
        self, conditions: list[dict], states: list[dict]
    ) -> dict:
        """Format odontogram data for country-specific regulatory export.

        Colombia: RDA-compliant export format.
        Returns a dictionary with the formatted export data.
        """
        ...

    # -- Electronic Invoicing --

    @abstractmethod
    def generate_invoice(self, invoice_data: dict) -> dict:
        """Generate country-specific electronic invoice data.

        Colombia: DIAN UBL 2.1 via MATIAS API.
        Mexico: CFDI 4.0 via PAC.
        Returns a dictionary with generated invoice data.
        """
        ...

    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> bool:
        """Validate a tax identification number for this country.

        Colombia: NIT with optional verification digit.
        Mexico: RFC (Registro Federal de Contribuyentes).
        """
        ...

    # -- Health Service Reporting --

    @abstractmethod
    async def generate_reporting_export(
        self,
        report_type: str,
        period_start: date,
        period_end: date,
        db: AsyncSession,
    ) -> dict:
        """Generate mandatory health service reports for a regulatory period.

        Colombia: RIPS flat files (AC, AP, AM).
        Mexico: SINBA reporting.
        Returns a dictionary with generated report data and file references.
        """
        ...

    # -- Procedure Code System --

    @abstractmethod
    def get_procedure_code_system(self) -> str:
        """Return the name of the procedure code system used in this country.

        Colombia: 'CUPS'. Mexico: 'CIE-9-MC'. Chile: 'FONASA'.
        """
        ...

    @abstractmethod
    def validate_procedure_code(self, code: str) -> bool:
        """Validate a procedure code format for this country's code system.

        Colombia: CUPS format (6-digit numeric).
        Mexico: CIE-9-MC format.
        """
        ...
