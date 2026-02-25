# ADR-007: Country Compliance Adapter Pattern

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

DentalOS targets five LATAM countries in its initial expansion roadmap: Colombia (CO), Mexico (MX), Chile (CL), Argentina (AR), and Peru (PE). Each country imposes distinct regulatory requirements on clinical dental software across three axes:

### Clinical Record Regulations

| Country | Regulation | Requirements |
|---------|-----------|--------------|
| Colombia | RDA (Registro Dental Automatizado) -- Resolucion 1888 de 2025 | Mandatory odontogram format, required fields in clinical records, data retention policies (minimum 15 years), audit trail requirements |
| Colombia | Resolucion 1995 de 1999 | Clinical record management standards, patient access rights |
| Mexico | NOM-024-SSA3 | Electronic health record standards, minimum data elements, interoperability requirements, security controls |
| Chile | Ley 20.584 | Patient rights and clinical information management |
| Peru | RENHICE | National electronic health records registry, standardized data formats |
| Argentina | Ley 26.529 | Patient rights, clinical record content requirements, digital signature validity |

### Electronic Invoicing

| Country | System | Tax Authority | Format |
|---------|--------|---------------|--------|
| Colombia | Facturacion Electronica | DIAN | UBL 2.1 XML, digital signature with fiscal certificate |
| Mexico | CFDI 4.0 | SAT | XML with digital seal (sello digital) and PAC (Proveedor Autorizado de Certificacion) |
| Chile | DTE | SII | XML with digital signature, specific document types (factura, boleta) |
| Argentina | Factura Electronica | AFIP | WSFE web service, CAE (Codigo de Autorizacion Electronico) |
| Peru | Facturacion Electronica | SUNAT | UBL 2.1, OSE (Operador de Servicios Electronicos) |

### Health Service Reporting

| Country | System | Description |
|---------|--------|-------------|
| Colombia | RIPS (Resolucion 3374) | Mandatory health service records submitted to EPS entities. Includes consultation files (AC), procedure files (AP), medication files (AM). Specific flat-file format with strict field ordering. |
| Mexico | SINBA | National health information system reporting |
| Chile | REM | Monthly statistical reporting to MINSAL |
| Peru | HIS | Health information system reporting |
| Argentina | SISA | Integrated health information system |

### Problem Statement

Country-specific logic -- validation rules, document formats, code systems (CIE-10 subsets, CUPS vs country equivalents), tax calculations, e-invoice generation -- cannot be scattered throughout the codebase with `if country == "CO"` checks. This would:

1. Make every regulatory change a high-risk modification touching dozens of files.
2. Make it impossible to test one country's compliance without regression-testing all others.
3. Create merge conflicts as developers working on different country features modify the same files.
4. Violate the Open/Closed Principle: adding Peru support should not require modifying Colombia code.

### Scale of Country-Specific Logic

Estimated lines of country-specific code per country: 2,000-5,000 (validation rules, format generators, API integrations, test fixtures). This is substantial enough to warrant a formal architectural pattern, not ad-hoc abstractions.

---

## Decision

We will implement a **country compliance adapter pattern**. A Python abstract base class (`ComplianceAdapter`) defines the interface for all country-specific operations. Each country has a concrete adapter implementation. The correct adapter is resolved at runtime from the tenant's `country_code` setting and injected into FastAPI route handlers via dependency injection.

### Adapter Interface (Python Abstract Base Class)

```python
"""
Country compliance adapter interface.
Each country implements this to provide regulatory-specific behavior.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.clinical import ClinicalRecordCreate, ClinicalRecordOut
from app.schemas.invoicing import InvoiceRequest, InvoiceResult
from app.schemas.odontogram import OdontogramSnapshot
from app.schemas.reporting import ReportingExportResult


class ComplianceAdapter(ABC):
    """
    Abstract interface for country-specific compliance operations.
    Resolved per-request from the tenant's country_code.
    """

    @property
    @abstractmethod
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 country code."""
        ...

    # -- Clinical Record Compliance --

    @abstractmethod
    async def validate_clinical_record(
        self, record: ClinicalRecordCreate
    ) -> list[str]:
        """
        Validate a clinical record against country-specific requirements.
        Returns a list of validation error messages (empty if valid).
        """
        ...

    @abstractmethod
    async def format_clinical_record(
        self, record: ClinicalRecordOut
    ) -> dict[str, Any]:
        """
        Format a clinical record for country-specific export/display.
        Returns a dictionary with the formatted record fields.
        """
        ...

    # -- Odontogram Compliance --

    @abstractmethod
    async def validate_odontogram(
        self, snapshot: OdontogramSnapshot
    ) -> list[str]:
        """
        Validate odontogram data against country-specific format requirements.
        Colombia (RDA) mandates specific condition codes and recording conventions.
        """
        ...

    @abstractmethod
    async def format_odontogram_export(
        self, snapshot: OdontogramSnapshot
    ) -> bytes:
        """
        Export odontogram in the country's required format.
        Colombia: RDA-compliant PDF/XML. Others: standard SVG/PDF.
        """
        ...

    # -- Electronic Invoicing --

    @abstractmethod
    async def generate_invoice(
        self, request: InvoiceRequest
    ) -> InvoiceResult:
        """
        Generate a legally valid electronic invoice per country regulations.
        Colombia: DIAN UBL 2.1. Mexico: CFDI 4.0. Chile: DTE. etc.
        """
        ...

    @abstractmethod
    async def validate_tax_id(self, tax_id: str) -> bool:
        """
        Validate a tax identification number format per country.
        Colombia: NIT with verification digit. Mexico: RFC. Chile: RUT. etc.
        """
        ...

    # -- Health Service Reporting --

    @abstractmethod
    async def generate_reporting_export(
        self, tenant_id: str, date_range: tuple
    ) -> ReportingExportResult:
        """
        Generate mandatory health service reports for the regulatory period.
        Colombia: RIPS flat files. Mexico: SINBA. Chile: REM. etc.
        """
        ...

    # -- Procedure Code System --

    @abstractmethod
    def get_procedure_code_system(self) -> str:
        """
        Return the name of the procedure code system used in this country.
        Colombia: 'CUPS'. Mexico: 'CIE-9-MC'. Chile: 'FONASA'. etc.
        """
        ...

    @abstractmethod
    async def validate_procedure_code(self, code: str) -> bool:
        """
        Validate that a procedure code exists in the country's code system.
        """
        ...
```

### Adapter Registry and Resolution

```python
"""
Adapter registry: maps country codes to adapter implementations.
Resolved at runtime via FastAPI dependency injection.
"""
from typing import Dict, Type

from app.compliance.base import ComplianceAdapter
from app.compliance.colombia import ColombiaComplianceAdapter
from app.compliance.mexico import MexicoComplianceAdapter
from app.compliance.chile import ChileComplianceAdapter
from app.compliance.argentina import ArgentinaComplianceAdapter
from app.compliance.peru import PeruComplianceAdapter

_ADAPTER_REGISTRY: Dict[str, Type[ComplianceAdapter]] = {
    "CO": ColombiaComplianceAdapter,
    "MX": MexicoComplianceAdapter,
    "CL": ChileComplianceAdapter,
    "AR": ArgentinaComplianceAdapter,
    "PE": PeruComplianceAdapter,
}


def get_compliance_adapter(country_code: str) -> ComplianceAdapter:
    """
    Resolve the compliance adapter for a country code.
    Raises ValueError if the country is not supported.
    """
    adapter_class = _ADAPTER_REGISTRY.get(country_code)
    if adapter_class is None:
        raise ValueError(
            f"No compliance adapter registered for country: {country_code}. "
            f"Supported countries: {list(_ADAPTER_REGISTRY.keys())}"
        )
    return adapter_class()
```

### FastAPI Dependency Injection

```python
"""
FastAPI dependency that resolves the compliance adapter from the current tenant.
"""
from fastapi import Depends

from app.compliance.base import ComplianceAdapter
from app.compliance.registry import get_compliance_adapter
from app.core.tenant import get_current_tenant, Tenant


async def get_compliance(
    tenant: Tenant = Depends(get_current_tenant),
) -> ComplianceAdapter:
    """
    Resolve the compliance adapter for the current tenant's country.
    Injected into route handlers that perform country-specific operations.
    """
    return get_compliance_adapter(tenant.country_code)
```

### Usage in Route Handlers

```python
from fastapi import APIRouter, Depends
from app.compliance.base import ComplianceAdapter
from app.compliance.deps import get_compliance

router = APIRouter()


@router.post("/clinical-records/")
async def create_clinical_record(
    record: ClinicalRecordCreate,
    compliance: ComplianceAdapter = Depends(get_compliance),
    # ... other dependencies
):
    # Country-specific validation
    errors = await compliance.validate_clinical_record(record)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    # Save record (shared logic)
    saved = await clinical_record_service.create(record)

    # Country-specific post-processing (e.g., queue RIPS generation for CO)
    # Handled by the adapter internally or by caller based on adapter hints
    return saved
```

### File Structure

```
app/
├── compliance/
│   ├── __init__.py
│   ├── base.py              # ComplianceAdapter ABC
│   ├── registry.py          # Adapter registry and lookup
│   ├── deps.py              # FastAPI dependency
│   ├── colombia/
│   │   ├── __init__.py
│   │   ├── adapter.py       # ColombiaComplianceAdapter
│   │   ├── rips.py          # RIPS file generation logic
│   │   ├── dian.py          # DIAN e-invoicing integration
│   │   ├── rda.py           # RDA odontogram validation
│   │   └── validators.py    # NIT validation, CUPS code lookup
│   ├── mexico/
│   │   ├── __init__.py
│   │   ├── adapter.py       # MexicoComplianceAdapter
│   │   ├── cfdi.py          # CFDI 4.0 invoice generation
│   │   ├── nom024.py        # NOM-024 clinical record validation
│   │   └── validators.py    # RFC validation
│   ├── chile/
│   │   ├── __init__.py
│   │   ├── adapter.py       # ChileComplianceAdapter
│   │   ├── dte.py           # DTE invoice generation
│   │   └── validators.py    # RUT validation
│   ├── argentina/
│   │   └── ...
│   └── peru/
│       └── ...
```

### Testing Strategy

Each adapter is independently testable with country-specific test fixtures. Tests do not cross adapter boundaries.

```python
"""
Test strategy: each country adapter has its own test module
with country-specific fixtures and expected outputs.
"""
import pytest
from app.compliance.colombia.adapter import ColombiaComplianceAdapter


@pytest.fixture
def colombia_adapter():
    return ColombiaComplianceAdapter()


class TestColombiaValidation:
    async def test_valid_clinical_record(self, colombia_adapter):
        record = create_test_clinical_record(country="CO")
        errors = await colombia_adapter.validate_clinical_record(record)
        assert errors == []

    async def test_missing_rda_required_field(self, colombia_adapter):
        record = create_test_clinical_record(country="CO", cie10_code=None)
        errors = await colombia_adapter.validate_clinical_record(record)
        assert "CIE-10 code is required for RDA compliance" in errors

    async def test_nit_validation(self, colombia_adapter):
        assert await colombia_adapter.validate_tax_id("900123456-7")  # Valid NIT
        assert not await colombia_adapter.validate_tax_id("123")       # Invalid


class TestColombiaRIPS:
    async def test_rips_generation(self, colombia_adapter):
        result = await colombia_adapter.generate_reporting_export(
            tenant_id="test_tenant",
            date_range=("2026-01-01", "2026-01-31"),
        )
        assert result.format == "RIPS"
        assert "AC" in result.files  # Consultation file
        assert "AP" in result.files  # Procedure file
```

### Migration Path for Adding New Countries

Adding a new country (e.g., Ecuador) requires:

1. Create `app/compliance/ecuador/` directory with `adapter.py` implementing `ComplianceAdapter`.
2. Register the adapter in `registry.py`: `"EC": EcuadorComplianceAdapter`.
3. Add country-specific test fixtures in `tests/compliance/test_ecuador.py`.
4. Add the country code to the `public.tenants.country_code` allowed values.
5. No modifications to existing adapter code. No modifications to route handlers. No modifications to shared business logic.

Estimated effort per new country: 2-4 weeks depending on regulatory complexity.

---

## Alternatives Considered

### Alternative 1: Scattered if/else Country Checks

Embed country-specific logic directly in service functions and route handlers:

```python
# ANTI-PATTERN: scattered country checks
async def create_clinical_record(record, tenant):
    if tenant.country == "CO":
        validate_rda_compliance(record)
    elif tenant.country == "MX":
        validate_nom024(record)
    # ... grows with every country
```

**Why rejected:**

- Violates Open/Closed Principle. Every new country requires modifying existing functions.
- Country-specific logic is scattered across dozens of files. No single place to audit Colombia's compliance implementation.
- Testing one country's logic requires mocking/stubbing all other countries' branches.
- High risk of regression: a change to Mexico's validation accidentally breaks Colombia's path.

### Alternative 2: Microservice per Country

Deploy a separate microservice for each country's compliance logic. The main application calls the country-specific microservice via HTTP/gRPC.

**Why rejected:**

- Extreme operational overhead for 5 country variants. Each microservice needs its own deployment, monitoring, and scaling -- multiplied by 5.
- Network latency for every compliance operation (validation, invoice generation). Clinical record creation would require a synchronous HTTP call to the compliance microservice, adding 10-50ms of latency per request.
- Shared data access: compliance operations often need to read clinical records, patient data, and odontogram state. A separate microservice would need its own database access or API calls to fetch this data.
- The compliance logic is tightly coupled to the domain model. Extracting it into a separate service creates an artificial boundary that increases complexity without meaningful isolation benefits.

**Trade-offs:** Strong isolation between countries. But the operational cost is not justified for the current team size (2-4 backend developers) and the modest request volume.

### Alternative 3: Configuration-Driven Rules Engine

Define compliance rules as JSON/YAML configuration files that are interpreted at runtime by a generic rules engine. Country-specific behavior is driven entirely by configuration, not code.

**Why rejected:**

- Compliance logic is not purely declarative. Generating RIPS files requires procedural code (iterating over records, formatting fixed-width fields, calculating checksums). CFDI generation requires XML construction, digital signature application, and PAC API calls. These operations cannot be expressed as configuration rules.
- A rules engine that is powerful enough to express all compliance logic becomes, in effect, a custom programming language -- harder to debug, test, and maintain than Python code.
- Configuration drift: configuration files that control critical compliance behavior are harder to version-control, review, and test than Python classes with type hints and unit tests.

**Trade-offs:** Maximum flexibility for simple rule changes (e.g., required field lists). But the complexity of actual compliance operations (invoice generation, RIPS exports) exceeds what a configuration engine can handle cleanly.

---

## Consequences

### Positive

- **Open/Closed Principle.** Adding a new country requires only adding new code (a new adapter module), never modifying existing code. This eliminates cross-country regression risk.
- **Encapsulation.** All of Colombia's regulatory logic (RDA, RIPS, DIAN, NIT validation) is in one directory. A developer working on Colombia compliance only needs to understand that adapter.
- **Independent testability.** Each adapter is tested in isolation with country-specific fixtures. Colombia's RIPS tests do not depend on Mexico's CFDI tests passing.
- **Runtime resolution.** The adapter is resolved from the tenant's country setting at request time. No deployment changes needed when a tenant changes country (e.g., a clinic chain expanding from Colombia to Mexico).
- **FastAPI integration.** The adapter plugs into FastAPI's dependency injection system, keeping route handler code clean and country-agnostic.

### Negative

- **Interface design challenge.** The `ComplianceAdapter` interface must be broad enough to accommodate all five countries' regulatory requirements while remaining practical. Overly specific methods (e.g., `generate_rips()`) don't apply to Mexico. Overly generic methods lose type safety. This requires careful interface evolution as new countries are onboarded.
- **Interface evolution.** When adding a country that requires a new compliance operation not in the current interface, we must either add an optional method to the base class or create a country-specific extension interface. This needs to be managed carefully to avoid interface bloat.
- **Upfront design cost.** The adapter pattern requires more initial design work than ad-hoc country checks. The interface, registry, DI wiring, and file structure must be established before writing any country-specific code.
- **Adapter duplication.** Some compliance operations overlap between countries (e.g., CIE-10 validation is similar in all countries). Shared utilities must be extracted into a `compliance/common/` module to avoid duplication across adapters.

### Neutral

- **Colombia-first development.** The MVP targets Colombia. The `ColombiaComplianceAdapter` will be the first and most complete implementation. Other adapters will be stubbed initially and filled in as those countries are prioritized.
- **Adapter granularity.** The current design uses a single adapter per country. If a country's compliance becomes too complex (e.g., Mexico has both federal CFDI and state-level requirements), the adapter can internally delegate to sub-components without changing the external interface.
- **No runtime performance impact.** Adapter resolution is a dictionary lookup by country code. The adapter is instantiated once per request (or cached). There is no measurable performance overhead compared to inline if/else checks.

---

## References

- [Strategy Pattern (Refactoring Guru)](https://refactoring.guru/design-patterns/strategy) -- The underlying design pattern
- [Python ABC Module](https://docs.python.org/3/library/abc.html) -- Abstract Base Classes
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/) -- How adapters plug into request handling
- Colombia: [DIAN Facturacion Electronica](https://www.dian.gov.co/), [RIPS Resolucion 3374](https://www.minsalud.gov.co/)
- Mexico: [SAT CFDI 4.0](https://www.sat.gob.mx/), [NOM-024-SSA3](https://www.dof.gob.mx/)
- Chile: [SII DTE](https://www.sii.cl/)
- DentalOS `ADR-LOG.md` -- ADR-007 summary
- DentalOS `DOMAIN-GLOSSARY.md` -- RIPS, DIAN, CFDI, DTE, CUPS definitions
- DentalOS `infra/multi-tenancy.md` -- Tenant `country_code` field
