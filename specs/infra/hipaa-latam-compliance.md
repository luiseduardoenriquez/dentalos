# HIPAA / LATAM Compliance Engine Spec

> **Spec ID:** I-13
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Regulatory compliance engine using a country adapter pattern (ADR-007) that provides a unified interface for country-specific healthcare and tax regulations. Each country implementation handles clinical record validation, electronic invoice generation, health reporting data export, odontogram formatting, and required field enforcement. Runtime adapter resolution uses the tenant's country code. Dependency injection via FastAPI.

**Domain:** infra / compliance

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy), ADR-007 (country adapter), billing domain, clinical-records domain, I-12 (data-retention), INT-10 (MATIAS), INT-05 (SAT), INT-06 (SII)

---

## 1. Architecture: Country Adapter Pattern

### Why Country Adapters?

DentalOS targets Colombia first, then Mexico, then Chile. Healthcare regulations differ significantly:
- Colombia: RIPS (health claims), RDA (dental), DIAN invoicing, Resolución 1888
- Mexico: NOM-024 (EHR interoperability), CFDI 4.0 (tax), NOM-004 (expediente clínico)
- Chile: Ficha clínica requirements, DTE (tax), Superintendencia de Salud

A country adapter isolates all country-specific logic into pluggable modules, keeping core DentalOS code country-agnostic.

### Core Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel
from datetime import date


class ClinicalRecordValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    missing_required_fields: List[str] = []


class InvoiceGenerationRequest(BaseModel):
    invoice_id: str
    tenant_id: str
    patient_document: str
    patient_document_type: str
    patient_name: str
    patient_email: str
    services: List[dict]
    subtotal: float
    tax_total: float
    total: float
    payment_method: str
    issue_date: date


class ReportingDataExport(BaseModel):
    format: str           # "RIPS" | "NOM024" | "CSV"
    records: List[dict]
    period_start: date
    period_end: date
    tenant_nit: Optional[str] = None


class ComplianceAdapter(ABC):
    """
    Abstract base class for all country-specific compliance implementations.
    Each method has a default behavior that can be overridden per country.
    """

    @abstractmethod
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 country code."""
        raise NotImplementedError

    @abstractmethod
    def validate_clinical_record(
        self,
        record: dict,
        patient: dict,
        tenant: dict,
    ) -> ClinicalRecordValidationResult:
        """
        Validate a clinical record against country-specific regulations.
        Called before every clinical record save.
        """
        raise NotImplementedError

    @abstractmethod
    def get_required_clinical_fields(self, record_type: str) -> List[str]:
        """
        Return list of required fields for a clinical record type.
        record_type: "consultation" | "procedure" | "evolution" | "odontogram"
        """
        raise NotImplementedError

    @abstractmethod
    def format_odontogram(self, odontogram_data: dict) -> dict:
        """
        Format odontogram data for country-specific export/reporting.
        Colombia uses FDI notation; Mexico may use different coding.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_invoice_payload(
        self,
        request: InvoiceGenerationRequest,
        tenant_config: dict,
    ) -> dict:
        """
        Generate the invoice payload for the country's e-invoicing system.
        Returns the payload ready to send to the country's integration service.
        """
        raise NotImplementedError

    @abstractmethod
    def export_reporting_data(
        self,
        tenant_id: str,
        period_start: date,
        period_end: date,
    ) -> ReportingDataExport:
        """
        Export clinical and billing data in the country-required reporting format.
        Colombia: RIPS. Mexico: NOM-024. Chile: Libro de Prestaciones.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_patient_document(
        self,
        document_number: str,
        document_type: str,
    ) -> bool:
        """Validate patient document number format for the country."""
        raise NotImplementedError

    @abstractmethod
    def get_tax_codes(self) -> dict:
        """Return country-specific tax/service codes."""
        raise NotImplementedError

    def get_appointment_required_fields(self) -> List[str]:
        """Default: appointment fields required by most countries."""
        return ["patient_id", "doctor_id", "scheduled_at", "appointment_type"]

    def get_prescription_format(self) -> dict:
        """Default prescription format — override per country if needed."""
        return {
            "requires_professional_number": True,
            "requires_diagnosis_code": True,
        }
```

---

## 2. Colombia Adapter

```python
import re
from typing import List
from datetime import date
from app.compliance.base import (
    ComplianceAdapter,
    ClinicalRecordValidationResult,
    InvoiceGenerationRequest,
    ReportingDataExport,
)


class ColombiaAdapter(ComplianceAdapter):
    """
    Compliance adapter for Colombia.
    Regulations: Resolución 1888, Resolución 1995/1999, DIAN, RIPS, RDA.
    """

    def country_code(self) -> str:
        return "CO"

    def validate_clinical_record(
        self,
        record: dict,
        patient: dict,
        tenant: dict,
    ) -> ClinicalRecordValidationResult:
        errors = []
        warnings = []
        missing = []

        # Resolución 1888 requirements
        if not record.get("doctor_professional_card"):
            errors.append("Número de tarjeta profesional del médico requerido (Resolución 1888)")
            missing.append("doctor_professional_card")

        if not record.get("diagnosis_cie10"):
            warnings.append("Diagnóstico CIE-10 recomendado para historia clínica completa")

        if record.get("type") == "procedure":
            if not record.get("cups_code"):
                errors.append("Código CUPS requerido para procedimientos facturables")
                missing.append("cups_code")

        if not record.get("signed_at") and record.get("status") == "final":
            errors.append("Firma del profesional requerida para historia clínica definitiva")

        # Patient document validation
        if patient.get("document_type") == "CC":
            if not self.validate_patient_document(
                patient["document_number"], "CC"
            ):
                errors.append("Número de cédula colombiana inválido")

        return ClinicalRecordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_required_fields=missing,
        )

    def get_required_clinical_fields(self, record_type: str) -> List[str]:
        base_fields = [
            "patient_id",
            "doctor_id",
            "date",
            "subjective_notes",
            "objective_notes",
            "assessment",
            "plan",
        ]
        if record_type == "procedure":
            return base_fields + ["cups_code", "diagnosis_cie10", "doctor_professional_card"]
        if record_type == "consultation":
            return base_fields + ["vital_signs", "doctor_professional_card"]
        return base_fields

    def format_odontogram(self, odontogram_data: dict) -> dict:
        """
        Colombia uses FDI (International) notation, which DentalOS uses natively.
        No conversion needed. Add RIPS-required metadata.
        """
        return {
            **odontogram_data,
            "notation_system": "FDI",
            "reporting_format": "RIPS_RDA",
        }

    def generate_invoice_payload(
        self,
        request: InvoiceGenerationRequest,
        tenant_config: dict,
    ) -> dict:
        """Generate MATIAS API invoice payload for DIAN submission."""
        from app.integrations.matias.service import build_matias_payload
        return build_matias_payload(request, tenant_config)

    def export_reporting_data(
        self,
        tenant_id: str,
        period_start: date,
        period_end: date,
    ) -> ReportingDataExport:
        """
        Export RIPS (Registro Individual de Prestación de Servicios de Salud).
        Required format: CSV files CT, AF, AC, AN, AP, AU, AM.
        """
        from app.compliance.colombia.rips_exporter import RIPSExporter
        exporter = RIPSExporter(tenant_id)
        return exporter.export(period_start, period_end)

    def validate_patient_document(
        self,
        document_number: str,
        document_type: str,
    ) -> bool:
        patterns = {
            "CC": r"^[0-9]{6,10}$",      # Cédula de ciudadanía: 6-10 digits
            "TI": r"^[0-9]{8,12}$",       # Tarjeta de identidad
            "NIT": r"^[0-9]{9}$",         # NIT sin dígito verificador
            "CE": r"^[0-9A-Z]{6,15}$",    # Cédula de extranjería
            "PASAPORTE": r"^[A-Z0-9]{6,20}$",
        }
        pattern = patterns.get(document_type)
        if not pattern:
            return True  # Unknown type — pass validation
        return bool(re.match(pattern, document_number))

    def get_tax_codes(self) -> dict:
        return {
            "iva_rate": 0.19,
            "dental_services_iva_exempt": True,
            "invoice_system": "DIAN_UBL21",
            "tax_currency": "COP",
        }

    def get_prescription_format(self) -> dict:
        return {
            "requires_professional_number": True,   # Tarjeta Profesional
            "requires_diagnosis_code": True,         # CIE-10
            "requires_controlled_substance_registration": True,
            "stamp_required": True,
        }
```

---

## 3. Mexico Adapter

```python
import re
from typing import List
from datetime import date


class MexicoAdapter(ComplianceAdapter):
    """
    Compliance adapter for Mexico.
    Regulations: NOM-024-SSA3-2010, NOM-004-SSA3-2012, SAT CFDI 4.0.
    """

    def country_code(self) -> str:
        return "MX"

    def validate_clinical_record(
        self,
        record: dict,
        patient: dict,
        tenant: dict,
    ) -> ClinicalRecordValidationResult:
        errors = []
        warnings = []
        missing = []

        # NOM-004 requirements
        if not record.get("doctor_cedula_profesional"):
            errors.append("Cédula profesional del médico requerida (NOM-004)")
            missing.append("doctor_cedula_profesional")

        if not record.get("institution_name"):
            errors.append("Nombre de la institución médica requerido (NOM-004)")
            missing.append("institution_name")

        # NOM-024 interoperability
        if record.get("type") == "procedure" and not record.get("cups_equivalent"):
            warnings.append("Código de procedimiento CIE-9-MC recomendado para interoperabilidad (NOM-024)")

        return ClinicalRecordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_required_fields=missing,
        )

    def get_required_clinical_fields(self, record_type: str) -> List[str]:
        return [
            "patient_id",
            "doctor_id",
            "date",
            "doctor_cedula_profesional",
            "institution_name",
            "chief_complaint",
            "physical_examination",
            "diagnosis",
            "treatment_plan",
        ]

    def format_odontogram(self, odontogram_data: dict) -> dict:
        """
        Mexico also uses FDI notation.
        Add NOM-024 metadata for interoperability.
        """
        return {
            **odontogram_data,
            "notation_system": "FDI",
            "reporting_format": "NOM024",
        }

    def generate_invoice_payload(
        self,
        request: InvoiceGenerationRequest,
        tenant_config: dict,
    ) -> dict:
        """Generate SAT CFDI 4.0 payload."""
        from app.compliance.mexico.cfdi_builder import build_cfdi_payload
        return build_cfdi_payload(request, tenant_config)

    def export_reporting_data(
        self,
        tenant_id: str,
        period_start: date,
        period_end: date,
    ) -> ReportingDataExport:
        """
        Mexico NOM-024 data export for interoperability.
        Primarily CSV format for government reporting if required.
        """
        from app.compliance.mexico.nom024_exporter import NOM024Exporter
        exporter = NOM024Exporter(tenant_id)
        return exporter.export(period_start, period_end)

    def validate_patient_document(
        self,
        document_number: str,
        document_type: str,
    ) -> bool:
        patterns = {
            "CURP": r"^[A-Z]{4}[0-9]{6}[HM][A-Z]{2}[BCDFGHJKLMNPQRSTVWXYZ]{3}[A-Z0-9]{2}$",
            "RFC": r"^[A-Z]{3,4}[0-9]{6}[A-Z0-9]{3}$",
            "PASAPORTE": r"^[A-Z0-9]{6,20}$",
        }
        pattern = patterns.get(document_type)
        if not pattern:
            return True
        return bool(re.match(pattern, document_number))

    def get_tax_codes(self) -> dict:
        return {
            "iva_rate": 0.16,
            "dental_services_iva_exempt": True,  # Most dental services
            "invoice_system": "SAT_CFDI40",
            "tax_currency": "MXN",
        }
```

---

## 4. Chile Adapter

```python
import re
from typing import List
from datetime import date


class ChileAdapter(ComplianceAdapter):
    """
    Compliance adapter for Chile.
    Regulations: Ley 20.584, Ley 19.628, SII DTE.
    """

    def country_code(self) -> str:
        return "CL"

    def validate_clinical_record(
        self,
        record: dict,
        patient: dict,
        tenant: dict,
    ) -> ClinicalRecordValidationResult:
        errors = []
        warnings = []
        missing = []

        # Ley 20.584 — Ficha Clínica
        if not record.get("doctor_rut"):
            errors.append("RUT del profesional requerido (Ley 20.584)")
            missing.append("doctor_rut")

        if not record.get("fecha_atencion"):
            errors.append("Fecha de atención requerida")
            missing.append("fecha_atencion")

        # Patient rights per Ley 20.584
        if record.get("type") == "sensitive" and not record.get("patient_consent"):
            errors.append("Consentimiento del paciente requerido para datos sensibles (Ley 20.584)")

        return ClinicalRecordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_required_fields=missing,
        )

    def get_required_clinical_fields(self, record_type: str) -> List[str]:
        return [
            "patient_id",
            "doctor_id",
            "doctor_rut",
            "fecha_atencion",
            "motivo_consulta",
            "examen_fisico",
            "diagnostico",
            "tratamiento",
        ]

    def format_odontogram(self, odontogram_data: dict) -> dict:
        return {
            **odontogram_data,
            "notation_system": "FDI",
            "reporting_format": "SII_DTE",
        }

    def generate_invoice_payload(
        self,
        request: InvoiceGenerationRequest,
        tenant_config: dict,
    ) -> dict:
        """Generate SII DTE payload."""
        from app.compliance.chile.dte_builder import build_dte_payload
        return build_dte_payload(request, tenant_config)

    def export_reporting_data(
        self,
        tenant_id: str,
        period_start: date,
        period_end: date,
    ) -> ReportingDataExport:
        """Chile Libro de Prestaciones for Superintendencia de Salud."""
        from app.compliance.chile.prestaciones_exporter import PrestacionesExporter
        exporter = PrestacionesExporter(tenant_id)
        return exporter.export(period_start, period_end)

    def validate_patient_document(
        self,
        document_number: str,
        document_type: str,
    ) -> bool:
        """
        Validate Chilean RUT format (e.g., 12345678-9 or 12345678-K).
        Includes check digit validation algorithm.
        """
        if document_type != "RUT":
            return True

        # Format: digits + hyphen + check digit (0-9 or K)
        if not re.match(r"^[0-9]{7,8}-[0-9Kk]$", document_number):
            return False

        # Check digit validation
        body, check_digit = document_number.split("-")
        return self._validate_rut_check_digit(body, check_digit.upper())

    def _validate_rut_check_digit(self, body: str, check: str) -> bool:
        """Validate RUT check digit using modulo 11 algorithm."""
        sum_ = 0
        multiplier = 2
        for digit in reversed(body):
            sum_ += int(digit) * multiplier
            multiplier = 2 if multiplier == 7 else multiplier + 1
        remainder = 11 - (sum_ % 11)
        expected = {10: "K", 11: "0"}.get(remainder, str(remainder))
        return check == expected

    def get_tax_codes(self) -> dict:
        return {
            "iva_rate": 0.19,
            "dental_services_iva_exempt": True,  # Most dental services
            "invoice_system": "SII_DTE",
            "tax_currency": "CLP",
        }
```

---

## 5. Adapter Registry and Dependency Injection

### Registry

```python
from typing import Dict
from app.compliance.base import ComplianceAdapter
from app.compliance.colombia import ColombiaAdapter
from app.compliance.mexico import MexicoAdapter
from app.compliance.chile import ChileAdapter


ADAPTER_REGISTRY: Dict[str, ComplianceAdapter] = {
    "CO": ColombiaAdapter(),
    "MX": MexicoAdapter(),
    "CL": ChileAdapter(),
}


def get_compliance_adapter(country_code: str) -> ComplianceAdapter:
    """
    Get the compliance adapter for a given country code.
    Raises ValueError if country not supported.
    """
    adapter = ADAPTER_REGISTRY.get(country_code.upper())
    if not adapter:
        raise ValueError(
            f"País '{country_code}' no soportado. "
            f"Países disponibles: {', '.join(ADAPTER_REGISTRY.keys())}"
        )
    return adapter
```

### FastAPI Dependency Injection

```python
from fastapi import Depends, Request
from app.auth.dependencies import get_current_tenant
from app.compliance.registry import get_compliance_adapter
from app.compliance.base import ComplianceAdapter


async def get_adapter(
    tenant=Depends(get_current_tenant),
) -> ComplianceAdapter:
    """
    FastAPI dependency: resolve compliance adapter from tenant country.
    Used in all endpoints that need country-specific behavior.
    """
    return get_compliance_adapter(tenant.country)


# Usage in endpoint:
@router.post("/clinical-records")
async def create_clinical_record(
    record_data: ClinicalRecordCreate,
    patient_id: str,
    current_user: User = Depends(get_current_user),
    adapter: ComplianceAdapter = Depends(get_adapter),
    session: AsyncSession = Depends(get_session),
):
    patient = await get_patient(session, patient_id)

    # Country-specific validation
    validation = adapter.validate_clinical_record(
        record=record_data.dict(),
        patient=patient.dict(),
        tenant=current_user.tenant.dict(),
    )

    if not validation.is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_failed",
                "message": "El registro clínico no cumple los requisitos regulatorios",
                "details": {
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "missing_fields": validation.missing_required_fields,
                }
            }
        )

    # Proceed with creation...
```

---

## 6. RIPS Export (Colombia — Detailed)

RIPS (Registro Individual de Prestación de Servicios de Salud) is a mandatory monthly report submitted to the health insurer and government.

### RIPS File Structure

| File | Content |
|------|---------|
| `CT.txt` | Cabecera de transacción (header) |
| `AF.txt` | Datos del prestador (clinic info) |
| `AC.txt` | Consultas (consultations) |
| `AN.txt` | Urgencias (emergencies) |
| `AP.txt` | Procedimientos (procedures) |
| `AU.txt` | Medicamentos recetados (prescriptions) |
| `AM.txt` | Otros servicios (other services) |

```python
class RIPSExporter:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def export(self, period_start: date, period_end: date) -> ReportingDataExport:
        """Export RIPS files for a billing period."""
        records = self._get_clinical_records(period_start, period_end)

        files = {
            "CT": self._generate_ct(records, period_start, period_end),
            "AF": self._generate_af(),
            "AC": self._generate_ac(records),   # Consultations
            "AP": self._generate_ap(records),   # Procedures
            "AU": self._generate_au(records),   # Prescriptions
        }

        return ReportingDataExport(
            format="RIPS",
            records=[{"files": files}],
            period_start=period_start,
            period_end=period_end,
        )

    def _generate_ac(self, records: list) -> str:
        """
        Generate AC file (consultations).
        Pipe-delimited, one record per consultation.
        Fields: document_type|document_number|age_units|age|gender|
                service_type|primary_diagnosis|secondary_diagnosis|
                injury_type|external_cause|consultation_type|
                value|insurer_code|billing_number
        """
        lines = []
        for record in records:
            if record["type"] == "consultation":
                lines.append(
                    "|".join([
                        record["patient_document_type"],
                        record["patient_document"],
                        "1",  # Age in years
                        str(record["patient_age"]),
                        record["patient_gender"],
                        "01",  # General medicine/dentistry
                        record.get("primary_diagnosis_cie10", ""),
                        record.get("secondary_diagnosis_cie10", ""),
                        "00",  # Not injury
                        "00",  # No external cause
                        "1",   # First-time consultation
                        str(record["value"]),
                        record["insurer_code"],
                        record["invoice_number"],
                    ])
                )
        return "\n".join(lines)
```

---

## 7. Colombian RDA (Resolución de Datos de Atención Odontológica)

The RDA is a Colombia-specific dental data format embedded in RIPS for dental procedures.

```python
class RDAFormatter:
    """
    Format dental odontogram data for RDA (dental RIPS) reporting.
    Each tooth surface treated is reported individually.
    """

    SURFACE_MAP = {
        "O": "oclusal",
        "V": "vestibular",
        "L": "lingual/palatino",
        "M": "mesial",
        "D": "distal",
        "C": "cervical",
    }

    def format_for_rda(self, odontogram: dict, procedures: list) -> list:
        """Convert odontogram procedures to RDA format rows."""
        rda_rows = []
        for procedure in procedures:
            tooth = procedure.get("tooth_number")
            surfaces = procedure.get("surfaces", [])

            for surface in surfaces:
                rda_rows.append({
                    "tooth_number": str(tooth),
                    "surface": surface,
                    "procedure_code": procedure.get("cups_code"),
                    "material": procedure.get("material"),
                    "status": procedure.get("status"),  # realizado | planificado
                })
        return rda_rows
```

---

## 8. Compliance Middleware

A FastAPI middleware validates compliance requirements on clinical write endpoints:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

CLINICAL_WRITE_PATHS = [
    "/api/v1/clinical-records",
    "/api/v1/odontogram",
    "/api/v1/treatment-plans",
    "/api/v1/prescriptions",
    "/api/v1/consents",
]


class ComplianceMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces country-specific compliance on clinical write operations.
    Adds compliance context headers to responses.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add compliance info to response headers for debugging
        if hasattr(request.state, "tenant") and hasattr(request.state, "compliance_warnings"):
            if request.state.compliance_warnings:
                response.headers["X-Compliance-Warnings"] = ",".join(
                    request.state.compliance_warnings[:3]  # Max 3 in header
                )

        return response
```

---

## 9. Testing Compliance Adapters

```python
import pytest
from app.compliance.colombia import ColombiaAdapter
from app.compliance.mexico import MexicoAdapter
from app.compliance.chile import ChileAdapter


class TestColombiaAdapter:
    adapter = ColombiaAdapter()

    def test_validates_cedula_colombiana(self):
        assert self.adapter.validate_patient_document("12345678", "CC") is True
        assert self.adapter.validate_patient_document("abc", "CC") is False

    def test_requires_cups_for_procedure(self):
        result = self.adapter.validate_clinical_record(
            record={"type": "procedure"},
            patient={"document_type": "CC", "document_number": "12345678"},
            tenant={},
        )
        assert not result.is_valid
        assert "cups_code" in result.missing_required_fields

    def test_rips_export_format(self):
        from datetime import date
        export = self.adapter.export_reporting_data(
            "test_tenant", date(2026, 1, 1), date(2026, 1, 31)
        )
        assert export.format == "RIPS"


class TestChileRUTValidation:
    adapter = ChileAdapter()

    def test_valid_rut(self):
        assert self.adapter.validate_patient_document("12345678-9", "RUT") is False  # wrong check digit
        assert self.adapter.validate_patient_document("76543210-5", "RUT") is True

    def test_rut_with_k(self):
        assert self.adapter.validate_patient_document("14569484-K", "RUT") is True
```

---

## 10. Adding a New Country (Extensibility)

To add a new country (e.g., Peru):

1. Create `app/compliance/peru/__init__.py`
2. Implement `PeruAdapter(ComplianceAdapter)`
3. Register in `ADAPTER_REGISTRY["PE"] = PeruAdapter()`
4. Add `PeruRetentionPolicy` in `infra/data-retention-policy.md`
5. Add integration spec for Peru's e-invoicing system
6. Write ADR for any Peru-specific architectural decisions

---

## Out of Scope

- HIPAA (US Health Insurance Portability Act) — US market not in scope for v1
- GDPR (EU) — European market not in scope
- ISO 27001 certification process — future business decision
- Insurance/EPS/HMO billing integration (SOAT, EPS) — future feature
- INVIMA (Colombian drug/device regulator) integration
- Telemedicine-specific regulations

---

## Acceptance Criteria

**This spec is complete when:**

- [ ] `ComplianceAdapter` base class implemented with all abstract methods
- [ ] `ColombiaAdapter` validates required CUPS code for procedures
- [ ] `ColombiaAdapter` RIPS export generates CT, AF, AC, AP files
- [ ] `MexicoAdapter` validates cédula profesional requirement
- [ ] `ChileAdapter` validates RUT format with check digit algorithm
- [ ] FastAPI dependency injection resolves correct adapter from tenant country
- [ ] Unknown country raises clear error with supported country list
- [ ] Unit tests pass for all three adapters
- [ ] Clinical record save endpoint uses adapter validation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
