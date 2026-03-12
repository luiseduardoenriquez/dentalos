"""Admin/superadmin request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from uuid import UUID


# ─── Auth Schemas ─────────────────────────────────────


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    name: str
    totp_required: bool = False


class AdminTOTPSetupRequest(BaseModel):
    pass


class AdminTOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str | None = None


class AdminTOTPVerifyRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


# ─── Tenant Management Schemas ────────────────────────


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    plan_name: str
    status: str
    user_count: int
    patient_count: int
    doctor_count: int = 0
    created_at: str


class TenantListResponse(BaseModel):
    items: list[TenantSummary]
    total: int
    page: int
    page_size: int


class TenantDetailResponse(BaseModel):
    id: str
    name: str
    slug: str
    schema_name: str
    owner_email: str
    owner_user_id: str | None = None
    country_code: str
    timezone: str
    currency_code: str
    locale: str
    plan_id: str
    plan_name: str
    status: str
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None
    onboarding_step: int
    settings: dict
    addons: dict
    trial_ends_at: str | None = None
    suspended_at: str | None = None
    cancelled_at: str | None = None
    user_count: int
    created_at: str
    updated_at: str


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    owner_email: EmailStr
    plan_id: str
    country_code: str = Field(default="CO", min_length=2, max_length=2)
    timezone: str = Field(default="America/Bogota", max_length=50)
    currency_code: str = Field(default="COP", min_length=3, max_length=3)

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.strip().upper()


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    plan_id: str | None = None
    settings: dict | None = None
    is_active: bool | None = None


# ─── Plan Management Schemas ─────────────────────────


class PlanResponse(BaseModel):
    id: str
    name: str
    slug: str
    price_cents: int
    pricing_model: str = "per_doctor"
    included_doctors: int = 1
    additional_doctor_price_cents: int = 0
    max_patients: int
    max_doctors: int
    features: dict
    is_active: bool


class PlanUpdateRequest(BaseModel):
    price_cents: int | None = None
    max_patients: int | None = None
    max_doctors: int | None = None
    features: dict | None = None
    is_active: bool | None = None


# ─── Analytics Schemas ────────────────────────────────


class PlanDistributionItem(BaseModel):
    plan_name: str
    count: int


class TopTenantItem(BaseModel):
    tenant_id: str
    name: str
    mrr_cents: int
    patients: int


class CountryDistributionItem(BaseModel):
    country: str
    count: int


class PlatformAnalyticsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    total_patients: int
    mrr_cents: int
    mau: int
    churn_rate: float
    new_signups_30d: int = 0
    plan_distribution: list[PlanDistributionItem] = []
    top_tenants: list[TopTenantItem] = []
    country_distribution: list[CountryDistributionItem] = []


# ─── Feature Flag Schemas ────────────────────────────


class FeatureFlagResponse(BaseModel):
    id: str
    flag_name: str
    scope: str | None = None
    plan_filter: str | None = None
    tenant_id: str | None = None
    enabled: bool
    description: str | None = None
    expires_at: str | None = None
    reason: str | None = None


class FeatureFlagUpdateRequest(BaseModel):
    enabled: bool | None = None
    scope: str | None = None
    plan_filter: str | None = None
    tenant_id: str | None = None
    description: str | None = None
    expires_at: str | None = None
    reason: str | None = None


class FeatureFlagCreateRequest(BaseModel):
    flag_name: str = Field(min_length=1, max_length=100)
    enabled: bool = False
    scope: str | None = None
    plan_filter: str | None = None
    tenant_id: str | None = None
    description: str | None = None
    expires_at: str | None = None
    reason: str | None = None


# ─── System Health Schemas ────────────────────────────


class ServiceHealthDetail(BaseModel):
    healthy: bool
    latency_ms: float = 0.0
    version: str | None = None
    details: dict = {}


class SystemHealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool
    rabbitmq: bool
    storage: bool
    timestamp: str
    service_details: dict[str, ServiceHealthDetail] = {}


# ─── Impersonation Schemas ────────────────────────────


class ImpersonateRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)
    duration_minutes: int = Field(default=60, ge=15, le=480)


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    impersonated_as: str = "clinic_owner"
    session_id: str | None = None
    expires_at: str | None = None


# ─── Audit Log Schemas ──────────────────────────────


class AuditLogEntry(BaseModel):
    id: str
    admin_id: str
    admin_email: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict = {}
    ip_address: str | None = None
    created_at: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ─── Plan Change History Schemas ─────────────────────


class PlanChangeHistoryEntry(BaseModel):
    id: str
    plan_id: str
    admin_id: str
    field_changed: str
    old_value: str | None = None
    new_value: str | None = None
    created_at: str


class PlanChangeHistoryResponse(BaseModel):
    items: list[PlanChangeHistoryEntry]
    total: int


# ─── Feature Flag Change History ─────────────────────


class FlagChangeHistoryEntry(BaseModel):
    id: str
    flag_id: str
    admin_id: str
    field_changed: str
    old_value: str | None = None
    new_value: str | None = None
    created_at: str


# ─── Export Schemas ──────────────────────────────────


class ExportRequest(BaseModel):
    export_type: str = Field(pattern="^(tenants|audit)$")


# ─── Superadmin CRUD Schemas ────────────────────────


class SuperadminCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(min_length=2, max_length=200)


class SuperadminResponse(BaseModel):
    id: str
    email: str
    name: str
    totp_enabled: bool
    is_active: bool
    last_login_at: str | None = None
    created_at: str


class SuperadminUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None


# ── Notifications ────────────────────────────────────────────────────────────

class AdminNotificationResponse(BaseModel):
    """Single admin notification."""
    id: UUID
    admin_id: UUID | None = None
    title: str
    message: str
    notification_type: str  # info, warning, error, success
    resource_type: str | None = None
    resource_id: UUID | None = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminNotificationListResponse(BaseModel):
    """Paginated notification list."""
    items: list[AdminNotificationResponse]
    unread_count: int
    total: int


# ─── Trial Management Schemas (SA-R02) ────────────────


class TrialTenantItem(BaseModel):
    id: str
    name: str
    slug: str
    plan_name: str
    status: str
    owner_email: str
    trial_ends_at: str | None = None
    days_remaining: int | None = None
    created_at: str


class TrialListResponse(BaseModel):
    items: list[TrialTenantItem]
    total: int
    expiring_soon_count: int = 0
    conversion_rate: float = 0.0
    avg_days_to_conversion: float = 0.0


class ExtendTrialRequest(BaseModel):
    days: int = Field(ge=1, le=90, default=14)


# ─── Maintenance Mode Schemas (SA-O04) ────────────────


class MaintenanceStatusResponse(BaseModel):
    enabled: bool
    message: str | None = None
    scheduled_end: str | None = None
    updated_at: str | None = None


class MaintenanceToggleRequest(BaseModel):
    enabled: bool
    message: str | None = Field(default=None, max_length=500)
    scheduled_end: str | None = None


# ─── Job Monitor Schemas (SA-O01) ──────────────────────


class QueueStatItem(BaseModel):
    name: str
    connected: bool
    messages_ready: int = 0
    consumers: int = 0


class JobMonitorResponse(BaseModel):
    connected: bool
    exchange: str
    queues: list[QueueStatItem]


# ─── Announcement Schemas (SA-E01) ────────────────────


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    body: str
    announcement_type: str
    visibility: str
    visibility_filter: dict = {}
    is_dismissable: bool
    is_active: bool
    starts_at: str | None = None
    ends_at: str | None = None
    created_by: str
    created_at: str
    updated_at: str


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
    total: int


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=2)
    announcement_type: str = Field(default="info", pattern="^(info|warning|critical)$")
    visibility: str = Field(default="all", pattern="^(all|plan|country)$")
    visibility_filter: dict = {}
    is_dismissable: bool = True
    starts_at: str | None = None
    ends_at: str | None = None


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    body: str | None = None
    announcement_type: str | None = Field(default=None, pattern="^(info|warning|critical)$")
    visibility: str | None = Field(default=None, pattern="^(all|plan|country)$")
    visibility_filter: dict | None = None
    is_dismissable: bool | None = None
    is_active: bool | None = None
    starts_at: str | None = None
    ends_at: str | None = None


# ─── Revenue Dashboard Schemas (SA-R01) ───────────────


class RevenueMonthDataPoint(BaseModel):
    month: str
    mrr_cents: int
    active_tenants: int
    churned_tenants: int
    new_tenants: int
    addon_revenue_cents: int = 0


class RevenuePlanBreakdown(BaseModel):
    plan_name: str
    mrr_cents: int
    tenant_count: int


class RevenueCountryBreakdown(BaseModel):
    country: str
    mrr_cents: int
    tenant_count: int


class RevenueKPIs(BaseModel):
    current_mrr_cents: int
    previous_mrr_cents: int
    mrr_growth_pct: float
    arpa_cents: int
    ltv_cents: int
    nrr_pct: float
    total_addon_revenue_cents: int


class RevenueDashboardResponse(BaseModel):
    kpis: RevenueKPIs
    monthly_trend: list[RevenueMonthDataPoint]
    plan_breakdown: list[RevenuePlanBreakdown]
    country_breakdown: list[RevenueCountryBreakdown]


# ─── Add-on Usage Schemas (SA-R03) ────────────────────


class AddonTenantUsage(BaseModel):
    tenant_id: str
    tenant_name: str
    plan_name: str
    voice_enabled: bool = False
    radiograph_enabled: bool = False


class AddonMetrics(BaseModel):
    total_eligible_tenants: int
    voice_adoption_count: int
    voice_adoption_pct: float
    radiograph_adoption_count: int
    radiograph_adoption_pct: float
    total_addon_revenue_cents: int
    upsell_candidates: int


class AddonUsageResponse(BaseModel):
    metrics: AddonMetrics
    tenants: list[AddonTenantUsage]


# ─── Onboarding Funnel Schemas (SA-G03) ───────────────


class OnboardingStepMetric(BaseModel):
    step: int
    label: str
    tenant_count: int
    pct_of_total: float


class OnboardingFunnelResponse(BaseModel):
    total_tenants: int
    steps: list[OnboardingStepMetric]
    stuck_tenants: list[dict]


# ─── Cross-Tenant User Search Schemas (SA-U01) ──────────


class CrossTenantUserItem(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    role: str
    tenant_id: str
    tenant_name: str
    status: str
    last_login_at: str | None = None
    is_multi_clinic: bool = False


class CrossTenantUserListResponse(BaseModel):
    items: list[CrossTenantUserItem]
    total: int
    page: int
    page_size: int


# ─── Database Metrics Schemas (SA-O02) ──────────────────


class TableSizeItem(BaseModel):
    schema_name: str
    table_name: str
    total_size: str
    row_count: int


class SlowQueryItem(BaseModel):
    query: str
    calls: int
    mean_time_ms: float
    total_time_ms: float


class DatabaseMetricsResponse(BaseModel):
    total_db_size: str
    schema_count: int
    connection_pool_active: int
    connection_pool_idle: int
    connection_pool_max: int
    index_hit_ratio: float
    cache_hit_ratio: float
    largest_tables: list[TableSizeItem]
    slow_queries: list[SlowQueryItem]
    dead_tuples_total: int


# ─── Bulk Operations Schemas (SA-A03) ──────────────────


class BulkOperationRequest(BaseModel):
    tenant_ids: list[str] = Field(min_length=1, max_length=50)
    action: str = Field(pattern="^(suspend|unsuspend|change_plan|extend_trial)$")
    plan_id: str | None = None
    trial_days: int | None = Field(default=None, ge=1, le=90)


class BulkOperationResult(BaseModel):
    tenant_id: str
    tenant_name: str
    success: bool
    error: str | None = None


class BulkOperationResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[BulkOperationResult]


# ─── Compliance Dashboard Schemas (SA-C01) ─────────────


class TenantComplianceItem(BaseModel):
    tenant_id: str
    tenant_name: str
    country_code: str
    rips_status: str  # up_to_date, overdue, never
    rda_status: str  # up_to_date, overdue, never
    consent_templates_count: int
    consent_templates_required: int
    doctors_verified: int
    doctors_total: int
    last_rips_at: str | None = None
    last_rda_at: str | None = None


class ComplianceKPIs(BaseModel):
    total_colombian_tenants: int
    rips_compliant: int
    rips_compliant_pct: float
    rda_compliant: int
    rda_compliant_pct: float
    consent_compliant: int
    consent_compliant_pct: float
    rethus_verified_pct: float


class ComplianceDashboardResponse(BaseModel):
    kpis: ComplianceKPIs
    tenants: list[TenantComplianceItem]


# ─── Security Alerts Schemas (SA-C02) ──────────────────


class SecurityAlertItem(BaseModel):
    id: str
    alert_type: str  # failed_login, suspicious_ip, after_hours, rate_limit
    severity: str  # info, warning, critical
    message: str
    source_ip: str | None = None
    admin_id: str | None = None
    tenant_id: str | None = None
    details: dict = {}
    created_at: str


class SecurityAlertListResponse(BaseModel):
    items: list[SecurityAlertItem]
    total: int
    failed_logins_24h: int
    suspicious_ips: int
    after_hours_actions: int


# ─── Data Retention Schemas (SA-C03) ───────────────────


class RetentionPolicyItem(BaseModel):
    data_type: str
    description: str
    retention_days: int
    current_oldest: str | None = None
    records_eligible: int


class ArchivableTenantItem(BaseModel):
    tenant_id: str
    tenant_name: str
    status: str
    cancelled_at: str | None = None
    days_since_cancelled: int


class DataRetentionResponse(BaseModel):
    policies: list[RetentionPolicyItem]
    archivable_tenants: list[ArchivableTenantItem]
    total_archivable: int


# ─── Tenant Usage Analytics Schemas (SA-U02) ───────────


class TenantUsageMetrics(BaseModel):
    tenant_id: str
    tenant_name: str
    plan_name: str
    active_users_7d: int
    patients_created_30d: int
    appointments_30d: int
    invoices_30d: int
    clinical_records_30d: int
    health_score: int  # 0-100 composite score
    risk_level: str  # healthy, at_risk, critical


class TenantHealthListResponse(BaseModel):
    items: list[TenantUsageMetrics]
    total: int
    healthy_count: int
    at_risk_count: int
    critical_count: int


# ─── Cohort Analysis Schemas (SA-G01) ──────────────────


class CohortRow(BaseModel):
    cohort_month: str  # YYYY-MM
    signup_count: int
    retention: list[float]  # retention % at month 0, 1, 2, ...


class CohortAnalysisResponse(BaseModel):
    cohorts: list[CohortRow]
    months_tracked: int
    avg_churn_month: int  # month where most churn happens


# ─── Feature Adoption Schemas (SA-G02) ─────────────────


class TenantFeatureUsage(BaseModel):
    tenant_id: str
    tenant_name: str
    plan_name: str
    odontogram: bool
    appointments: bool
    billing: bool
    portal: bool
    whatsapp: bool
    voice: bool
    ai_reports: bool
    telemedicine: bool
    features_used: int
    features_total: int


class FeatureAdoptionSummary(BaseModel):
    feature_name: str
    adoption_count: int
    adoption_pct: float


class FeatureAdoptionResponse(BaseModel):
    summary: list[FeatureAdoptionSummary]
    tenants: list[TenantFeatureUsage]
    total_tenants: int


# ─── Broadcast Messaging Schemas (SA-E02) ─────────────


class BroadcastCreateRequest(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=10)
    template: str | None = Field(
        default=None,
        pattern="^(welcome|feature_update|payment_reminder|compliance_alert)$",
    )
    filter_plan: str | None = None
    filter_country: str | None = None
    filter_status: str | None = Field(
        default=None, pattern="^(active|trial|suspended)$"
    )


class BroadcastHistoryItem(BaseModel):
    id: str
    subject: str
    body: str
    template: str | None = None
    filter_plan: str | None = None
    filter_country: str | None = None
    filter_status: str | None = None
    recipients_count: int
    sent_by: str
    created_at: str


class BroadcastHistoryResponse(BaseModel):
    items: list[BroadcastHistoryItem]
    total: int


class BroadcastSendResponse(BaseModel):
    broadcast_id: str
    recipients_count: int
    status: str  # queued


# ─── Automated Alerts Schemas (SA-A01) ─────────────────


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    condition: str  # churn_rate_high, queue_depth_high, trial_expiring, etc.
    threshold: str
    channel: str  # in_app, email
    is_active: bool
    last_triggered_at: str | None = None
    created_at: str


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    condition: str = Field(
        pattern="^(churn_rate_high|queue_depth_high|trial_expiring|"
        "health_degraded|signup_spike|revenue_drop)$"
    )
    threshold: str = Field(min_length=1, max_length=50)
    channel: str = Field(default="in_app", pattern="^(in_app|email|both)$")
    is_active: bool = True


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    threshold: str | None = None
    channel: str | None = Field(
        default=None, pattern="^(in_app|email|both)$"
    )
    is_active: bool | None = None


class AlertRuleListResponse(BaseModel):
    items: list[AlertRuleResponse]
    total: int


# ─── Scheduled Reports Schemas (SA-A02) ────────────────


class ScheduledReportResponse(BaseModel):
    id: str
    name: str
    report_type: str  # revenue, tenant_activity, compliance, health
    schedule: str  # daily, weekly, monthly
    recipients: list[str]
    is_active: bool
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str


class ScheduledReportCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    report_type: str = Field(
        pattern="^(revenue|tenant_activity|compliance|health)$"
    )
    schedule: str = Field(pattern="^(daily|weekly|monthly)$")
    recipients: list[str] = Field(min_length=1, max_length=10)
    is_active: bool = True


class ScheduledReportUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    schedule: str | None = Field(
        default=None, pattern="^(daily|weekly|monthly)$"
    )
    recipients: list[str] | None = None
    is_active: bool | None = None


class ScheduledReportListResponse(BaseModel):
    items: list[ScheduledReportResponse]
    total: int


# ─── Support Chat Schemas (SA-E03) ─────────────────────


class SupportThreadItem(BaseModel):
    id: str
    tenant_id: str
    tenant_name: str
    last_message: str | None = None
    last_message_at: str | None = None
    unread_count: int
    status: str  # open, closed
    created_at: str


class SupportMessageItem(BaseModel):
    id: str
    thread_id: str
    sender_type: str  # admin, clinic_owner
    sender_name: str
    content: str
    created_at: str


class SupportMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class SupportThreadListResponse(BaseModel):
    items: list[SupportThreadItem]
    total: int
    unread_total: int


class SupportThreadDetailResponse(BaseModel):
    thread: SupportThreadItem
    messages: list[SupportMessageItem]


# ─── SA-K01: Catalog Administration ──────────────────────

class CatalogCodeItem(BaseModel):
    id: str
    code: str
    description: str
    category: str | None = None
    created_at: str
    updated_at: str


class CatalogCodeListResponse(BaseModel):
    items: list[CatalogCodeItem]
    total: int
    page: int
    page_size: int


class CatalogCodeCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=10)
    description: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=100)


class CatalogCodeUpdateRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=100)


# ─── SA-K02: Global Template Management ──────────────────


class GlobalTemplateItem(BaseModel):
    id: str
    name: str
    template_type: str  # consent, evolution
    category: str | None = None
    version: int
    is_active: bool
    tenant_override_count: int = 0
    created_at: str
    updated_at: str


class GlobalTemplateDetailResponse(BaseModel):
    id: str
    name: str
    template_type: str
    category: str | None = None
    content: str
    version: int
    is_active: bool
    tenant_override_count: int = 0
    created_at: str
    updated_at: str


class GlobalTemplateListResponse(BaseModel):
    items: list[GlobalTemplateItem]
    total: int


class GlobalTemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = None
    category: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None


# ─── SA-K03: Default Price Catalog ────────────────────────


class DefaultPriceItem(BaseModel):
    id: str
    cups_code: str
    cups_description: str
    country_code: str
    price_cents: int
    currency_code: str
    is_active: bool
    updated_at: str


class DefaultPriceListResponse(BaseModel):
    items: list[DefaultPriceItem]
    total: int
    page: int
    page_size: int


class DefaultPriceUpsertRequest(BaseModel):
    cups_code: str = Field(min_length=1, max_length=10)
    cups_description: str = Field(min_length=1, max_length=300)
    country_code: str = Field(default="CO", min_length=2, max_length=2)
    price_cents: int = Field(ge=0)
    currency_code: str = Field(default="COP", min_length=3, max_length=3)


# ─── SA-U03: Tenant Comparison ────────────────────────────


class TenantBenchmarkItem(BaseModel):
    tenant_id: str
    tenant_name: str
    plan_name: str
    patients: int
    active_users: int
    appointments_30d: int
    invoices_30d: int
    mrr_cents: int
    features_used: int


class TenantComparisonResponse(BaseModel):
    tenants: list[TenantBenchmarkItem]
    plan_averages: dict  # {metric: avg_value}


# ─── SA-O03: API Usage Metrics ────────────────────────────


class ApiEndpointMetric(BaseModel):
    endpoint: str
    method: str
    count: int
    avg_latency_ms: float
    error_count: int


class ApiTenantUsage(BaseModel):
    tenant_id: str
    tenant_name: str
    request_count: int


class ApiUsageMetricsResponse(BaseModel):
    total_requests_24h: int
    error_rate_percent: float
    avg_latency_ms: float
    p95_latency_ms: float
    top_endpoints: list[ApiEndpointMetric]
    top_tenants: list[ApiTenantUsage]
    requests_by_hour: list[dict]  # [{hour, count}]


# ─── SA-G04: Geographic Intelligence ─────────────────────


class GeoCountryMetrics(BaseModel):
    country_code: str
    country_name: str
    tenant_count: int
    active_tenant_count: int
    total_mrr_cents: int
    currency_code: str
    signup_trend: list[dict]  # [{month, count}]
    top_plan: str | None = None


class GeoIntelligenceResponse(BaseModel):
    countries: list[GeoCountryMetrics]
    total_countries: int
    primary_market: str  # country_code with most tenants
