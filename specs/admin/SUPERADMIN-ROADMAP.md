# Superadmin Portal — Feature Roadmap

> DentalOS multi-tenant dental SaaS for LATAM.
> This document tracks all proposed, in-progress, and completed superadmin features.
> Last updated: 2026-03-12

---

## Current State (Baseline)

### What exists today

| Page | Endpoints | Description |
|------|-----------|-------------|
| Dashboard | 2 | KPI cards (tenants, MRR, MAU, patients), service status, recent tenants |
| Clinicas | 6 | CRUD + impersonation + suspend, advanced filters (plan/country/sort) |
| Analiticas | 1 | Real MRR, churn, plan distribution, top tenants, country distribution |
| Planes | 3 | Plan CRUD with field-level change history |
| Feature Flags | 4 | CRUD with inheritance (tenant→plan→global), expiry, history |
| Salud del Sistema | 1 | PG/Redis/RabbitMQ/S3 with latency, version, memory details |
| Registro de Auditoria | 2 | Paginated audit log with action/admin/date filters, CSV export |
| Superadmins | 4 | CRUD with self-deletion guard, TOTP status |
| Seguridad | 2 | TOTP enrollment and verification |
| Notificaciones | 3 | Bell in header, mark read/all-read, auto-refetch 60s |

**Totals:** 11 pages, 31 endpoints, 36 hooks, 27 service methods, 35 schemas

### Infrastructure available

- **13 integration adapters:** Nequi, Daviplata, Mercado Pago, ADRES, RETHUS, EPS Claims, Financing (Addi/Sistecredito), Telemedicine (Daily.co), Twilio VoIP, SMS, WhatsApp, Google Calendar, Exchange Rates
- **4 RabbitMQ queues:** notifications, clinical, import, maintenance (+ 4 DLQ)
- **7 workers:** notification, compliance, import, maintenance, voice, base, main
- **Redis:** caching with `dentalos:{tid}:{domain}:{resource}:{id}` key pattern
- **AI:** Claude client (`ai_claude_client.py`), treatment advisor, AI reports (template-selector), chatbot, voice-to-odontogram

---

## Feature Roadmap

### P0 — Revenue Intelligence (high business impact)

#### SA-R01: Revenue Dashboard
**Why:** MRR is a single number today. Founders/admins need trends to make decisions.
**What:**
- MRR trend chart (last 12 months, line graph)
- MRR breakdown by plan (stacked area)
- Churn trend (last 12 months)
- Net revenue retention (NRR) metric
- Average Revenue Per Account (ARPA)
- LTV estimate (ARPA / monthly churn rate)
- Revenue by country (bar chart)
- New MRR vs churned MRR vs expansion MRR per month

**Backend:**
- New service method: `get_revenue_timeseries(months=12)` — query `plan_change_history` + `tenants` by month
- New schema: `RevenueTimeseriesResponse` with monthly data points
- New endpoint: `GET /admin/analytics/revenue`
- Store monthly snapshots in a new `admin_revenue_snapshots` table (cron via maintenance worker)

**Frontend:** New page `/admin/revenue` with Recharts line/area/bar charts

**Depends on:** maintenance_worker for monthly snapshot generation

---

#### SA-R02: Trial Management & Conversion Funnel
**Why:** Trials are the main acquisition channel. Need visibility into conversion.
**What:**
- List all active trials with days remaining
- Extend trial with one click (new endpoint)
- Conversion funnel: trial → paid, by plan
- Trial-to-paid conversion rate (30d rolling)
- Average time to conversion
- Trials expiring in next 7 days (alert)

**Backend:**
- `GET /admin/trials` — active trials with `trial_ends_at` countdown
- `POST /admin/tenants/{id}/extend-trial` — extend trial_ends_at
- `GET /admin/analytics/conversion` — funnel metrics
- Query: tenants where `status='trial'` with `trial_ends_at` field

**Frontend:** New page `/admin/trials` or section in analytics

---

#### SA-R03: Add-on Usage Tracking
**Why:** AI Voice ($10/doc/mo) and AI Radiograph ($20/doc/mo) are revenue drivers. Need to see adoption.
**What:**
- Which tenants have which add-ons enabled
- Usage metrics per tenant: voice commands processed, radiographs analyzed
- Revenue from add-ons (separate from plan MRR)
- Adoption rate (% of eligible tenants using each add-on)
- Upsell candidates (active tenants without add-ons)

**Backend:**
- `GET /admin/analytics/addons` — aggregated add-on metrics
- Cross-schema query: count AI voice/radiograph usage per tenant

**Frontend:** Section in analytics or dedicated page

---

### P1 — Operations & Monitoring (keep platform healthy)

#### SA-O01: Background Job Monitor
**Why:** Failed jobs = broken notifications, stale compliance reports, lost imports.
**What:**
- Queue depths per queue (notifications, clinical, import, maintenance)
- Failed jobs count with details (expandable JSON)
- Dead letter queue (DLQ) viewer with retry button
- Job processing rate (jobs/min per queue)
- Average job latency per queue
- Worker status (connected/disconnected)

**Backend:**
- `GET /admin/jobs` — queue stats from RabbitMQ management API (`queue.get_queue_json_stats()` already exists)
- `GET /admin/jobs/dlq` — list dead-lettered messages
- `POST /admin/jobs/dlq/{id}/retry` — republish to original queue
- Uses existing `queue.py` infrastructure

**Frontend:** New page `/admin/jobs`

---

#### SA-O02: Database Metrics Dashboard
**Why:** As tenant count grows, DB becomes the bottleneck. Need early warning.
**What:**
- Connection pool stats (active, idle, max)
- Table sizes per schema (top 10 largest)
- Slow queries (pg_stat_statements top 10)
- Index hit ratio (should be >99%)
- Dead tuples / autovacuum status
- Replication lag (if applicable)
- Schema count and total DB size

**Backend:**
- `GET /admin/metrics/database` — aggregate DB metrics
- Queries against `pg_stat_user_tables`, `pg_stat_statements`, `pg_database_size()`
- Cache in Redis (TTL 5min, these are expensive queries)

**Frontend:** New page `/admin/database` or section in health page

---

#### SA-O03: API Usage Metrics
**Why:** Understand platform load, detect abuse, plan capacity.
**What:**
- Requests per minute (RPM) trend
- Error rate (4xx, 5xx) trend
- P50/P95/P99 latency
- Top endpoints by volume
- Top tenants by API usage
- Rate limit hits per tenant

**Backend:**
- Middleware that logs request metrics to Redis (lightweight counter)
- `GET /admin/metrics/api` — aggregated API stats
- Alternative: integrate with existing logging/Sentry data

**Frontend:** Section in analytics or `/admin/api-metrics`

---

#### SA-O04: Maintenance Mode
**Why:** Need to safely take platform down for upgrades without confusing users.
**What:**
- Global toggle: all tenants see maintenance banner
- Per-tenant toggle: specific clinic under maintenance
- Scheduled maintenance windows (start/end datetime)
- Custom message text
- Auto-enable/disable based on schedule
- Bypass for superadmins (always have access)

**Backend:**
- `POST /admin/maintenance` — toggle global or per-tenant
- `GET /admin/maintenance` — current status
- Redis flag: `dentalos:global:maintenance` = `{enabled, message, ends_at}`
- Middleware check on every tenant request
- New schema: `MaintenanceConfig`

**Frontend:** Toggle switch in health page or dedicated section

---

### P2 — User & Tenant Intelligence (understand your customers)

#### SA-U01: Cross-Tenant User Search
**Why:** Support needs to find any user quickly without impersonating each clinic.
**What:**
- Search by email, name, phone across ALL tenants
- Results show: user name, email, role, tenant(s), last login, status
- Quick actions: reset password, block/unblock, view tenant detail
- Multi-clinic users highlighted (via `user_tenant_memberships`)

**Backend:**
- `GET /admin/users?search=...` — cross-schema user search
- Query `public.user_tenant_memberships` joined with per-schema users
- `POST /admin/users/{id}/reset-password` — trigger password reset email
- `POST /admin/users/{id}/block` — deactivate across all tenants

**Frontend:** New page `/admin/users`

---

#### SA-U02: Tenant Usage Analytics
**Why:** Identify power users, at-risk tenants, and upsell opportunities.
**What:**
- Per-tenant metrics: active users (7d), patients created (30d), appointments (30d), invoices (30d)
- Storage usage per tenant (S3 path size)
- Feature adoption matrix (which features each tenant uses)
- "Health score" per tenant (composite of activity metrics)
- At-risk tenants (declining usage, approaching limits)
- Upsell candidates (hitting plan limits)

**Backend:**
- `GET /admin/tenants/{id}/usage` — detailed usage metrics for one tenant
- `GET /admin/analytics/tenant-health` — aggregated health scores
- Cross-schema queries with Redis caching (TTL 30min)

**Frontend:** Section in tenant detail page + new analytics tab

---

#### SA-U03: Tenant Comparison / Benchmarking
**Why:** Help CS team understand which tenants are under/over-performing.
**What:**
- Compare 2-5 tenants side by side
- Metrics: patients, appointments, revenue, active users, feature usage
- Percentile ranking (this tenant is in top 20% for patient count)
- Benchmark against plan average

**Backend:**
- `GET /admin/analytics/benchmark?tenant_ids=...` — comparative data

**Frontend:** Comparison view in analytics

---

### P3 — Compliance & Security (regulatory requirements)

#### SA-C01: Compliance Dashboard
**Why:** Colombia Resolucion 1888 deadline April 2026. Must track which clinics comply.
**What:**
- RIPS generation status per tenant (up-to-date, overdue, never generated)
- RDA status per tenant
- Consent template compliance (all required templates present)
- Professional credential status (RETHUS verification per doctor)
- Data retention policy adherence
- Export compliance report (PDF)

**Backend:**
- `GET /admin/compliance` — aggregated compliance status across tenants
- Cross-schema query: check `rips_reports`, `consent_records`, `rethus_verifications`
- Highlight tenants with compliance gaps

**Frontend:** New page `/admin/compliance`

**Critical:** Resolucion 1888 deadline April 2026 — this is legally required for Colombian clinics.

---

#### SA-C02: Security Alerts
**Why:** Detect brute force, suspicious logins, compromised accounts.
**What:**
- Failed login attempts by IP (threshold alerting)
- Suspicious patterns: login from new country, multiple concurrent sessions
- Admin actions outside business hours
- Rate limit violations per tenant
- Integration with audit log (filters for security events)

**Backend:**
- Analysis layer on top of existing `admin_audit_logs` and Redis rate limit data
- `GET /admin/security/alerts` — recent security events
- Notification triggers: create admin_notification on suspicious activity

**Frontend:** Section in security page or dedicated `/admin/security/alerts`

---

#### SA-C03: Data Retention Management
**Why:** HABEAS DATA (Colombia data protection law) requires data lifecycle management.
**What:**
- View data retention policies per data type (clinical records, audit logs, messages)
- Trigger data archival for old tenants (cancelled >1 year)
- HABEAS DATA request tracking (data deletion/export requests from patients)
- Anonymization tools for exported data

**Backend:**
- `GET /admin/retention` — current policies and pending actions
- `POST /admin/retention/archive/{tenant_id}` — archive old tenant data
- Leverage existing `maintenance_worker` for background archival

**Frontend:** New page `/admin/data-retention`

---

### P4 — Communication & Engagement (reach your customers)

#### SA-E01: System Announcements
**Why:** Need to communicate new features, planned maintenance, policy changes.
**What:**
- Create announcement with title, body (rich text), type (info/warning/critical), visibility (all/plan/country)
- Schedule publish/expire dates
- Banner displayed in all clinic dashboards
- Dismissable vs persistent banners
- Announcement history

**Backend:**
- New table: `admin_announcements` (id, title, body, type, visibility_filter, starts_at, ends_at, created_by, created_at)
- `GET/POST /admin/announcements` — CRUD
- `GET /api/v1/announcements/active` — clinic-facing endpoint (filtered by tenant plan/country)

**Frontend:** New page `/admin/announcements` + banner component in clinic dashboard

---

#### SA-E02: Broadcast Messaging
**Why:** Direct communication channel to clinic owners for urgent matters.
**What:**
- Send email to all clinic_owners (or filtered by plan/country/status)
- Pre-built templates: welcome, feature update, payment reminder, compliance alert
- Send history with delivery stats
- Preview before send
- Opt-out management

**Backend:**
- `POST /admin/broadcast` — queue broadcast emails via notification worker
- `GET /admin/broadcast/history` — sent broadcasts with stats
- Uses existing `notification_worker` + email adapter

**Frontend:** New page `/admin/broadcast`

---

#### SA-E03: In-App Chat with Clinic Owners
**Why:** Faster than email for support, more personal than announcements.
**What:**
- Simple chat thread between admin and clinic_owner
- Tenant-scoped (one thread per tenant)
- Notification when new message
- Chat history preserved
- Quick access from tenant detail page

**Backend:**
- New table: `admin_support_threads` + `admin_support_messages`
- WebSocket or SSE for real-time updates
- `GET /admin/support/threads` — list threads
- `POST /admin/support/threads/{tenant_id}/messages` — send message

**Frontend:** Chat panel in tenant detail + `/admin/support` inbox

---

### P5 — Content & Catalog Management (platform configuration)

#### SA-K01: Catalog Administration
**Why:** CIE-10/CUPS codes need periodic updates. Currently requires DB migration.
**What:**
- Search and browse CIE-10 codes (diagnostic codes)
- Search and browse CUPS codes (procedure codes)
- Add/edit/deactivate codes without deployment
- Bulk import from CSV (Ministry of Health updates)
- View which tenants use which codes (usage stats)

**Backend:**
- `GET/POST/PUT /admin/catalog/cie10` — manage CIE-10 codes
- `GET/POST/PUT /admin/catalog/cups` — manage CUPS codes
- `POST /admin/catalog/import` — bulk CSV import
- Tables already exist in public schema (`cie10_codes`, `cups_codes`)

**Frontend:** New page `/admin/catalogs`

---

#### SA-K02: Global Template Management
**Why:** Consent templates, evolution templates should have platform-wide defaults.
**What:**
- Manage default consent templates (legal text, required for compliance)
- Manage evolution note templates
- Push template updates to all tenants
- Version tracking per template
- Tenant override tracking (which tenants customized defaults)

**Backend:**
- `GET/POST/PUT /admin/templates` — manage global templates
- `POST /admin/templates/{id}/push` — push to all tenant schemas

**Frontend:** New page `/admin/templates`

---

#### SA-K03: Default Price Catalog
**Why:** New clinics need a starting point for procedure pricing.
**What:**
- Manage default prices per procedure (CUPS code)
- Different defaults per country (COP vs MXN vs PEN)
- Applied to new tenants during onboarding
- Price update propagation (optional push to existing tenants)

**Backend:**
- `GET/PUT /admin/catalog/prices` — manage default price lists
- Integrated with tenant creation flow

**Frontend:** Section in catalogs page

---

### P6 — Growth & Intelligence (data-driven decisions)

#### SA-G01: Cohort Analysis
**Why:** Understand retention by signup month, plan, country.
**What:**
- Monthly cohort retention grid (signup month vs months since signup)
- Filter by plan, country, signup source
- Highlight: which cohorts retain best
- Identify: when do tenants typically churn

**Backend:**
- `GET /admin/analytics/cohorts` — cohort retention matrix
- Query: group tenants by created_at month, check status at each subsequent month

**Frontend:** Cohort heatmap in analytics

---

#### SA-G02: Feature Adoption Dashboard
**Why:** Know which features drive retention and which are ignored.
**What:**
- Matrix: tenants (rows) × features (columns) × usage (cells)
- Features tracked: odontogram, appointments, billing, portal, whatsapp, voice, AI, telemedicine
- Correlation: feature usage vs retention
- Identify: features that drive upgrades

**Backend:**
- `GET /admin/analytics/feature-adoption` — cross-schema feature usage matrix
- Per-tenant: count records in key tables (appointments, invoices, clinical_records, etc.)

**Frontend:** Heatmap or table in analytics

---

#### SA-G03: Onboarding Funnel
**Why:** Track where new tenants get stuck in setup.
**What:**
- Onboarding steps completion rate (each `onboarding_step` value)
- Time to first patient, first appointment, first invoice
- Tenants stuck at each step (with ability to contact)
- Automated nudge emails for stuck tenants

**Backend:**
- `GET /admin/analytics/onboarding` — funnel metrics
- Tenant model already has `onboarding_step` field

**Frontend:** Funnel chart in analytics

---

#### SA-G04: Geographic Expansion Intelligence
**Why:** Plan LATAM expansion (MX, PE, CL, AR after Colombia).
**What:**
- Signups by country over time
- Revenue by country
- Feature usage patterns by country
- Compliance readiness by country
- Market sizing estimates

**Backend:**
- Aggregations from existing tenant data grouped by `country_code`
- `GET /admin/analytics/geo` — geographic intelligence

**Frontend:** Map visualization + country breakdown tables

---

### P7 — Automation & Efficiency (reduce manual work)

#### SA-A01: Automated Alerts
**Why:** Admins shouldn't have to check dashboards constantly.
**What:**
- Configurable alert rules: "Notify when churn > 5%", "Alert when queue depth > 100", "Warn when trial expires in 3 days"
- Alert channels: in-app notification, email
- Alert history
- Snooze/acknowledge functionality
- Pre-built rules for common scenarios

**Backend:**
- New table: `admin_alert_rules` (condition, threshold, channel, active)
- Evaluation via maintenance_worker (periodic check)
- Creates `admin_notifications` when triggered

**Frontend:** Alert rules management in `/admin/alerts`

---

#### SA-A02: Scheduled Reports
**Why:** Weekly/monthly summaries for stakeholders without manual export.
**What:**
- Schedule: daily/weekly/monthly email reports
- Report types: revenue summary, tenant activity, compliance status, health summary
- Recipients: one or more admin emails
- PDF or CSV attachment
- Configurable content (which sections to include)

**Backend:**
- New table: `admin_scheduled_reports` (type, schedule, recipients, config)
- Generation via maintenance_worker
- PDF generation using existing clinical PDF infrastructure

**Frontend:** Report scheduler in `/admin/reports`

---

#### SA-A03: Bulk Operations
**Why:** Managing 100+ tenants one-by-one is slow.
**What:**
- Bulk plan change (select tenants → change plan)
- Bulk suspend/unsuspend
- Bulk email (select tenants → send message)
- Bulk feature flag toggle (enable feature for a cohort)
- Dry-run mode (preview changes before applying)

**Backend:**
- `POST /admin/bulk/{action}` — generic bulk action endpoint
- Actions: `change_plan`, `suspend`, `unsuspend`, `toggle_flag`, `send_email`
- Audit logged as single action with affected_ids in details
- Processed via import_worker for large batches

**Frontend:** Checkbox selection in tenant list + bulk action dropdown

---

## Implementation Priority Matrix

| ID | Feature | Impact | Effort | Priority |
|----|---------|--------|--------|----------|
| SA-R01 | Revenue Dashboard | Very High | Medium | P0 |
| SA-R02 | Trial Management | High | Low | P0 |
| SA-R03 | Add-on Usage | High | Medium | P0 |
| SA-O01 | Job Monitor | High | Low | P1 |
| SA-O02 | Database Metrics | Medium | Medium | P1 |
| SA-O03 | API Usage Metrics | Medium | High | P1 |
| SA-O04 | Maintenance Mode | High | Low | P1 |
| SA-U01 | User Search | High | Medium | P2 |
| SA-U02 | Tenant Usage Analytics | High | High | P2 |
| SA-U03 | Tenant Comparison | Medium | Medium | P2 |
| SA-C01 | Compliance Dashboard | Very High | High | P3 |
| SA-C02 | Security Alerts | Medium | Medium | P3 |
| SA-C03 | Data Retention | Medium | High | P3 |
| SA-E01 | Announcements | High | Low | P4 |
| SA-E02 | Broadcast Messaging | Medium | Medium | P4 |
| SA-E03 | Support Chat | Medium | High | P4 |
| SA-K01 | Catalog Admin | Medium | Medium | P5 |
| SA-K02 | Template Management | Medium | Medium | P5 |
| SA-K03 | Default Prices | Low | Low | P5 |
| SA-G01 | Cohort Analysis | High | Medium | P6 |
| SA-G02 | Feature Adoption | High | High | P6 |
| SA-G03 | Onboarding Funnel | Medium | Low | P6 |
| SA-G04 | Geo Intelligence | Medium | Low | P6 |
| SA-A01 | Automated Alerts | High | Medium | P7 |
| SA-A02 | Scheduled Reports | Medium | Medium | P7 |
| SA-A03 | Bulk Operations | High | Medium | P7 |

---

## Suggested Implementation Order

### Wave 1 (Quick Wins — 1-2 days each) ✅ COMPLETE
1. **SA-R02** Trial Management — ✅ list trials, extend trial, KPI cards, frontend page
2. **SA-O04** Maintenance Mode — ✅ Redis flag toggle, GET/POST, frontend page
3. **SA-O01** Job Monitor — ✅ queue stats endpoint, frontend page with cards
4. **SA-E01** Announcements — ✅ CRUD + migration 007 + model + frontend page

### Wave 2 (Revenue Focus — 2-3 days each) ✅ COMPLETE
5. **SA-R01** Revenue Dashboard — ✅ migration 008, KPI cards (MRR/ARPA/LTV/NRR), trend chart, plan/country breakdowns
6. **SA-R03** Add-on Usage — ✅ cross-schema aggregation, adoption metrics, upsell candidates, tenant table
7. **SA-G03** Onboarding Funnel — ✅ step funnel visualization, stuck tenants table, step labels

### Wave 3 (Operations — 2-3 days each) ✅ COMPLETE
8. **SA-U01** Cross-Tenant User Search — ✅ cross-schema UNION query, role/status badges, multi-clinic indicator, pagination
9. **SA-O02** Database Metrics — ✅ pg_stat queries (connections, ratios, largest tables, slow queries), auto-refresh, color-coded thresholds
10. **SA-A03** Bulk Operations — ✅ suspend/unsuspend/change_plan/extend_trial endpoint, per-tenant error handling, audit logging

### Wave 4 (Compliance — critical deadline April 2026) ✅ COMPLETE
11. **SA-C01** Compliance Dashboard — ✅ RIPS/RDA/consent/RETHUS per-tenant status, KPI cards, compliance table
12. **SA-C02** Security Alerts — ✅ failed logins, suspicious IPs, after-hours actions, severity cards, auto-refresh
13. **SA-C03** Data Retention — ✅ retention policies, archivable tenants (cancelled >1yr), HABEAS DATA

### Wave 5 (Intelligence — 3-5 days each) ✅ COMPLETE
14. **SA-U02** Tenant Usage Analytics — ✅ per-tenant health scores, 5 activity metrics, risk levels (healthy/at_risk/critical), Redis cache 30min
15. **SA-G01** Cohort Analysis — ✅ monthly retention matrix, months selector (6/12/18/24), avg churn month, color-coded heatmap
16. **SA-G02** Feature Adoption — ✅ 8-feature adoption bars, per-tenant usage matrix, adoption percentages sorted by adoption

### Wave 6 (Communication & Automation) ✅ COMPLETE
17. **SA-E02** Broadcast Messaging — ✅ filtered broadcasts (plan/country/status), notification worker queue, history with pagination
18. **SA-A01** Automated Alerts — ✅ CRUD alert rules, condition/threshold/channel config, toggle active, last_triggered tracking
19. **SA-A02** Scheduled Reports — ✅ CRUD scheduled reports, type/schedule/recipients, active toggle, next_run tracking
20. **SA-E03** Support Chat — ✅ thread-per-tenant, admin/clinic_owner messages, unread counts, open/close status, chat UI

### Wave 7 (Content Management & Intelligence) ✅ COMPLETE
21. **SA-K01** Catalog Administration — ✅ tab-switched CIE-10/CUPS management, search, pagination, inline add/edit
22. **SA-K02** Template Management — ✅ global consent/evolution templates, filter by type, edit name/status, version tracking
23. **SA-K03** Default Prices — ✅ CUPS-based pricing per country, upsert, country filter, migration 010
24. **SA-U03** Tenant Comparison — ✅ compare 2-5 tenants side-by-side, metrics rows, plan averages, color-coded
25. **SA-O03** API Usage Metrics — ✅ 24h totals, error rate, avg/P95 latency, hourly chart, Redis counters
26. **SA-G04** Geo Intelligence — ✅ country breakdown, MRR per country, signup trends, activation rates

---

## Technical Notes

### Shared Patterns
- All new endpoints follow: `GET/POST /admin/{resource}` with pagination (`page`, `page_size`)
- All mutations logged via `log_admin_action()` to audit trail
- All new tables in `public` schema (admin is not tenant-scoped)
- Cross-schema queries use `information_schema.schemata` → per-schema SELECT → Redis cache
- Frontend hooks follow `useAdmin{Resource}()` naming convention
- All UI text in Spanish (es-419), code in English

### Database Considerations
- Cross-schema queries are expensive — always Redis-cache with appropriate TTL
- Revenue snapshots should be pre-computed (maintenance_worker) not calculated live
- `pg_stat_statements` requires extension enabled in PostgreSQL
- Large tenant count (100+) will need query optimization for cross-schema aggregations

### Infrastructure Dependencies
- Revenue snapshots → maintenance_worker cron
- Broadcast emails → notification_worker
- Bulk operations → import_worker
- Automated alerts → maintenance_worker periodic check
- Support chat → Redis pub/sub (same pattern as WhatsApp SSE)
- Compliance checks → cross-schema queries + compliance_worker

### New Tables Needed (estimated)
- `admin_revenue_snapshots` (SA-R01)
- `admin_announcements` (SA-E01)
- `admin_alert_rules` (SA-A01)
- `admin_scheduled_reports` (SA-A02)
- `admin_support_threads` + `admin_support_messages` (SA-E03)

### New Pages Needed (estimated)
- `/admin/revenue` (SA-R01)
- `/admin/trials` (SA-R02)
- `/admin/jobs` (SA-O01)
- `/admin/users` (SA-U01)
- `/admin/compliance` (SA-C01)
- `/admin/announcements` (SA-E01)
- `/admin/broadcast` (SA-E02)
- `/admin/support` (SA-E03)
- `/admin/catalogs` (SA-K01)
- `/admin/alerts` (SA-A01)
- `/admin/reports` (SA-A02)

### Sidebar Navigation (proposed order)
```
Panel
Clinicas
Usuarios          ← NEW (SA-U01)
Analiticas
  → Revenue       ← NEW (SA-R01)
  → Trials        ← NEW (SA-R02)
  → Cohortes      ← NEW (SA-G01)
Planes
Feature Flags
Compliance        ← NEW (SA-C01)
Salud del Sistema
  → Jobs          ← NEW (SA-O01)
  → Base de Datos ← NEW (SA-O02)
Comunicacion      ← NEW section
  → Anuncios      ← NEW (SA-E01)
  → Broadcast     ← NEW (SA-E02)
  → Soporte       ← NEW (SA-E03)
Catalogos         ← NEW (SA-K01)
Operaciones       ← NEW section
  → Alertas       ← NEW (SA-A01)
  → Reportes      ← NEW (SA-A02)
  → Mantenimiento ← NEW (SA-O04)
Registro de Auditoria
Superadmins
Seguridad
```
