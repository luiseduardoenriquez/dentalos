"""Pydantic schemas for compliance endpoints (RIPS, RDA, DIAN e-invoicing)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


# ─── Country Config ────────────────────────────────────────────────────────────


class CountryConfigResponse(BaseModel):
    country_code: str
    country_name: str
    procedure_code_system: str
    document_types: list[dict]
    code_systems: dict
    retention_rules: dict
    regulatory_references: list[dict]
    feature_flags: dict


# ─── RDA (Resolución 1888) ────────────────────────────────────────────────────


class RDAGap(BaseModel):
    field_name: str
    module: str
    severity: str = Field(description="critical, required, or recommended")
    weight: int
    current_count: int
    expected_count: int
    gap_percentage: float
    corrective_action: str


class RDAModuleBreakdown(BaseModel):
    module: str
    label: str
    total_fields: int
    compliant_fields: int
    compliance_percentage: float
    gaps: list[RDAGap]


class RDAStatusResponse(BaseModel):
    overall_compliance_percentage: float
    compliance_level: str = Field(description="compliant, improving, at_risk, or critical")
    deadline: str
    modules: list[RDAModuleBreakdown]
    gaps: list[RDAGap]
    total_records_analyzed: int
    last_computed_at: datetime | None = None
    cached: bool = False


# ─── RIPS ──────────────────────────────────────────────────────────────────────


class RIPSGenerateRequest(BaseModel):
    period_start: date
    period_end: date
    file_types: list[str] = Field(
        default=["AF", "AC", "AP", "AT", "AM", "AN", "AU"],
        description="RIPS file types to generate",
    )


class RIPSBatchFileResponse(BaseModel):
    file_type: str
    storage_path: str | None = None
    download_url: str | None = None
    size_bytes: int = 0
    record_count: int = 0


class RIPSBatchErrorResponse(BaseModel):
    severity: str
    rule_code: str
    message: str
    record_ref: str | None = None
    field_name: str | None = None


class RIPSBatchResponse(BaseModel):
    id: str
    period_start: date
    period_end: date
    status: str
    file_types: list[str]
    files: list[RIPSBatchFileResponse] = []
    errors: list[RIPSBatchErrorResponse] = []
    error_count: int = 0
    warning_count: int = 0
    created_at: datetime
    generated_at: datetime | None = None
    validated_at: datetime | None = None
    failure_reason: str | None = None


class RIPSBatchListResponse(BaseModel):
    items: list[RIPSBatchResponse]
    total: int
    page: int
    page_size: int


class RIPSValidateResponse(BaseModel):
    batch_id: str
    is_valid: bool
    error_count: int
    warning_count: int
    errors: list[RIPSBatchErrorResponse]


# ─── DIAN E-Invoicing ─────────────────────────────────────────────────────────


class EInvoiceCreateRequest(BaseModel):
    invoice_id: str = Field(description="UUID of the invoice to submit electronically")


class EInvoiceStatusResponse(BaseModel):
    id: str
    invoice_id: str
    status: str = Field(description="pending, submitted, accepted, rejected, error")
    cufe: str | None = None
    matias_submission_id: str | None = None
    dian_environment: str = "test"
    xml_url: str | None = None
    pdf_url: str | None = None
    retry_count: int = 0
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime
