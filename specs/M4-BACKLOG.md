# M4 Compliance + Advanced Features Backlog (R-08)

> Sprint 13-16 planning document with task breakdown, estimates, and acceptance criteria.

**Version:** 1.0
**Date:** 2026-02-25
**Sprints:** 13-16
**Duration:** 8 weeks (4 sprints × 2 weeks)
**Month:** 7-8

---

## Sprint Goals

### Sprint 13: Colombia Compliance — RIPS, RDA, DIAN via MATIAS
Implement Colombia-specific compliance: RIPS file generation (AF, AC, AP, AT, AM, AN, AU), RDA compliance status check (Resolución 1888), and DIAN electronic invoicing via the MATIAS API (DentalOS as "Casa de Software"). Establish the country compliance adapter architecture. This sprint must be complete before April 2026 regulatory deadline.

### Sprint 14: Compliance Audit + Data Retention + Compliance Frontend + Analytics Core
Complete audit trail verification (100% clinical data access logged), 15-year data retention enforcement, compliance settings screens, and the analytics API (AN-01 through AN-07). Begin superadmin tools. Sprint ends with clinic owners able to generate and validate RIPS, view RDA compliance score, and issue DIAN e-invoices with multiple authorized roles.

### Sprint 15: Analytics UI + Patient Advanced Operations + Inventory MVP
Deliver all analytics frontend screens (FE-AN-01 through FE-AN-04), patient import/export/merge operations, and the inventory management system (INV-01 through INV-07) with semaphore alerts, sterilization cycle logging, and implant traceability. Begin Mexico compliance adapter.

### Sprint 16: Admin/Superadmin + Mexico + Offline Groundwork + Infrastructure Hardening
Complete the superadmin panel (AD-01 through AD-07), Mexico SAT CFDI integration groundwork (INT-05), offline-first architecture (I-18), PWA configuration (I-19), and production infrastructure hardening (I-15, I-16). Sprint ends with a deployment-ready platform.

---

## Task Breakdown

### Sprint 13: Colombia Compliance — RIPS, RDA, DIAN via MATIAS

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement country compliance adapter architecture (adapter interface + Colombia adapter) | I-13 | P0 | 2d | I-01 | `ComplianceAdapter` interface defined; Colombia adapter registered; adapter resolved per tenant.country setting; pluggable for MX, CL, AR, PE |
| 2 | ADR-007: Document country compliance adapter decision | I-26 | P0 | 0.5d | I-13 | Decision recorded: adapter pattern selected; rationale documented |
| 3 | Implement `POST /compliance/rips/generate` — generate RIPS batch (AF, AC, AP, AT, AM, AN, AU) | CO-01 | P0 | 4d | CR-01, CR-07, CR-12, P-01, I-13 | Generates all 7 RIPS file types; period-based (monthly); validates structure against MinSalud rules; async via RabbitMQ worker for large clinics |
| 4 | Implement `GET /compliance/rips/{batch_id}` — download RIPS batch (ZIP or individual files) | CO-02 | P0 | 0.5d | CO-01 | ZIP download; individual file download; includes validation errors if any |
| 5 | Implement `GET /compliance/rips` — RIPS generation history | CO-03 | P0 | 0.5d | CO-01 | Paginated; status (generated/validated/submitted/rejected); period shown |
| 6 | Implement `POST /compliance/rips/{batch_id}/validate` — validate RIPS against MinSalud rules | CO-04 | P0 | 2d | CO-01 | Returns error list with specific record references; structural validation (field formats, required fields, code validity); linkage validation (procedures reference valid diagnoses, etc.) |
| 7 | Implement `GET /compliance/rda/status` — RDA compliance check (Resolución 1888) | CO-05 | P0 | 2d | OD-01, CR-01, P-01 | Returns compliance percentage; gaps list (missing fields, missing signatures, missing anamnesis); field-level validation per RDA requirements |
| 8 | Implement `GET /compliance/config` — country compliance configuration | CO-08 | P1 | 0.5d | I-13, T-06 | Required fields, document types, code systems (CIE-10 version), retention rules; per-tenant country |
| 9 | INT-10: MATIAS API integration for DIAN electronic invoicing | INT-10 | P0 | 4d | B-01, CO-06 | DentalOS registered as "Casa de Software"; multi-client package; invoice XML generated (UBL 2.1); submitted to MATIAS; CUFE generated and stored per invoice; XML + PDF retrievable after DIAN acceptance |
| 10 | Implement `POST /compliance/e-invoice` — create e-invoice via MATIAS API | CO-06 | P0 | 1.5d | B-01, INT-10, I-13 | RBAC: clinic_owner, doctor, assistant with `billing:invoice:create` permission can generate (not restricted to single role); CUFE stored; status tracking |
| 11 | Implement `GET /compliance/e-invoice/{id}/status` — e-invoice status from MATIAS | CO-07 | P0 | 0.5d | CO-06, INT-10 | Polls MATIAS API; returns DIAN status (accepted/rejected/pending); stores result |
| 12 | Write RIPS generation tests: valid AF, AC, AP, AT, AM, AN, AU files | I-08 | P0 | 2d | CO-01–CO-04 | Generate RIPS for a tenant with 50 patients + 200 procedures; validate all 7 file types pass MinSalud structural rules |
| 13 | Write MATIAS API integration tests (mock MATIAS sandbox) | I-08 | P0 | 1d | INT-10, CO-06 | Mock MATIAS responses; CUFE generation verified; XML structure validated against UBL 2.1 schema |
| 14 | Research and implement RIPS data mapping: clinical records → RIPS fields | CO-01 | P0 | 2d | CR-01, CR-07, CR-12 | Map: patient → AF; appointment → AC; procedure → AP; diagnosis → AT; etc. Document mapping table. Edge cases handled (pediatric patients, multiple procedures per appointment). |
| 15 | Document MATIAS API setup requirements (NIT, authorization, pricing) | INT-10 | P0 | 0.5d | None | Documentation: MATIAS package cost (~$400K COP/year), NIT registration process, API credentials setup, "Casa de Software" certification steps |

**Sprint 13 total estimate: ~22 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 14: Compliance Audit + Data Retention + Compliance Frontend + Analytics

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Audit logging verification: validate 100% of clinical data access/write is logged | I-11 | P0 | 2d | I-11 | Audit every endpoint in CR-*, OD-*, TP-*, IC-*, RX-*, B-*; add missing audit calls; verified via test coverage |
| 2 | Implement data retention policy enforcement (15-year rule for Colombia) | I-12 | P0 | 2d | I-11 | PostgreSQL row-level retention policy; clinical records cannot be hard-deleted within retention window; patient data deletion request workflow (GDPR-Colombia Ley 1581 compliant) |
| 3 | Implement right-to-be-forgotten vs clinical retention logic | I-12 | P0 | 1.5d | I-12 | Personal data (name, phone, email) anonymizable per Ley 1581; clinical records (diagnoses, procedures, odontogram) preserved for 15 years; anonymized record maintains clinical validity |
| 4 | Audit trail immutability verification: ensure audit_log table is append-only | I-11 | P0 | 1d | I-11 | PostgreSQL row security policy: no UPDATE or DELETE on audit_log; verified with tests attempting manipulation |
| 5 | Build FE-CO-01: RIPS generation page (period selection, generate, validate, download) | FE-CO-01 | P0 | 2d | CO-01, CO-04 | Period selector (monthly); "Generate" button triggers async job; progress indicator; validation error list with links to source records; ZIP download |
| 6 | Build FE-CO-02: RDA compliance dashboard (compliance score, gaps, action items) | FE-CO-02 | P0 | 2d | CO-05 | Compliance percentage gauge; gap list (missing anamnesis, missing odontogram, etc.); each gap links to the specific patient/record needing attention |
| 7 | Build FE-CO-03: electronic invoice list (status tracking, resend, download XML/PDF) | FE-CO-03 | P0 | 1.5d | CO-06, CO-07 | Status badges (pending/accepted/rejected); resend action; download CUFE XML; download PDF; **accessible to clinic_owner, doctor, assistant** |
| 8 | Build FE-S-07: compliance settings per country (RDA config, required fields) | FE-S-07 | P1 | 1d | CO-08, T-07 | Country selector; required field toggles per RDA; RDA section mappings |
| 9 | Implement analytics API: `GET /analytics/dashboard` — clinic dashboard metrics | AN-01 | P1 | 1.5d | P-01, AP-01, B-01 | Patients (new/total); appointments today/week/month; revenue; no-shows; top procedures; occupancy rate. Date range support. Cached 5 minutes in Redis. |
| 10 | Implement `GET /analytics/patients` — patient analytics | AN-02 | P1 | 1d | P-01, AP-01 | New patients per period; retention rate; average visits per patient; demographics breakdown; referral sources |
| 11 | Implement `GET /analytics/appointments` — appointment analytics | AN-03 | P1 | 1d | AP-01 | Utilization rate per doctor; average duration; cancellation rate; no-show rate; peak hours heatmap |
| 12 | Implement `GET /analytics/revenue` — revenue analytics | AN-04 | P1 | 1d | B-01, B-07 | Revenue by period, doctor, procedure type, payment method; accounts receivable aging |
| 13 | Implement `GET /analytics/clinical` — clinical analytics | AN-05 | P1 | 1d | CR-07, CR-12, TP-01 | Most common diagnoses; most performed procedures; average treatment plan duration; completion rates |
| 14 | Implement `GET /analytics/export` — export analytics to CSV/Excel | AN-06 | P2 | 1d | AN-01–AN-05 | Customizable report; streaming response; Excel with multiple sheets per analytics domain |
| 15 | Implement `GET /analytics/audit-trail` — audit trail viewer (clinic_owner only) | AN-07 | P1 | 1d | I-11 | Filter by user, action, resource type, date range; paginated; exportable |
| 16 | Performance test: analytics dashboard ≤1s for clinic with 10K patients | AN-01 | P0 | 1d | AN-01–AN-05 | Pre-aggregate heavy queries; denormalized analytics tables or materialized views for key metrics |
| 17 | Write compliance tests: 15-year retention, anonymization, audit immutability | I-08 | P0 | 1d | I-11, I-12 | Test: delete attempt blocked; anonymization removes PII; audit log append-only |

**Sprint 14 total estimate: ~23 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 15: Analytics UI + Patient Advanced Operations + Inventory MVP

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Build FE-AN-01: analytics main dashboard (KPI cards, charts, period selector) | FE-AN-01 | P1 | 2d | AN-01 | Period selector; KPI cards (patients, revenue, appointments, no-shows); line chart for trends; loads ≤1s |
| 2 | Build FE-AN-02: patient analytics page (trends, retention, demographics) | FE-AN-02 | P1 | 1.5d | AN-02 | New patient trend line chart; retention rate gauge; demographics pie; referral source bar |
| 3 | Build FE-AN-03: appointment analytics (utilization, cancellations, peak hours heatmap) | FE-AN-03 | P1 | 1.5d | AN-03 | Utilization bar per doctor; cancellation/no-show trend; heatmap (day × hour) |
| 4 | Build FE-AN-04: revenue analytics (trends, by doctor, by procedure, payment methods) | FE-AN-04 | P1 | 1.5d | AN-04 | Revenue trend line; by-doctor bar; by-procedure table; payment method donut |
| 5 | Build FE-S-09: audit log viewer (searchable, filterable) | FE-S-09 | P1 | 1d | AN-07 | Search by user, action, resource, date; expandable rows for old/new value diff; clinic_owner only |
| 6 | Implement `POST /patients/import` — bulk CSV/Excel import (async, with validation) | P-08 | P1 | 2d | P-01, I-06 | Upload CSV; validate: required fields, duplicate detection by document number, format errors; error report returned; async via RabbitMQ; 5K patients in < 60s |
| 7 | Implement `GET /patients/export` — export patient list to CSV (streaming) | P-09 | P1 | 0.5d | P-03 | Same filters as patient list; streaming response (no memory bloat); column headers in Spanish |
| 8 | Implement `POST /patients/merge` — merge duplicate patient records | P-10 | P1 | 2d | P-01, I-11 | Clinic_owner only; preserves all clinical data from both records under primary; audit logged with old record IDs; secondary record marked merged |
| 9 | Build FE-P-06: patient import page (upload, column mapping, validation, progress) | FE-P-06 | P1 | 2d | P-08 | File upload (CSV/Excel); column mapping UI; validation preview (first 10 rows with error highlighting); import progress bar; error report download |
| 10 | Implement `POST /inventory/items` — create inventory item | INV-01 | P1 | 1d | I-01 | Fields: name, category (material/instrument/implant/medication), quantity, unit, lot_number, expiry_date, manufacturer, supplier, cost |
| 11 | Implement `GET /inventory/items` — list with semaphore status | INV-02 | P1 | 1d | INV-01 | Semaphore: green (OK), yellow (≤60d to expiry or ≤ min_stock), orange (≤30d to expiry), red (expired or out of stock); filterable by category and status |
| 12 | Implement `PUT /inventory/items/{id}` — update item (quantity, lot, expiry) | INV-03 | P1 | 0.5d | INV-01 | Stock adjustment; update expiry; mark consumed; audit logged |
| 13 | Implement `POST /inventory/items/{id}/movements` — record stock movement | INV-04 | P1 | 0.5d | INV-01 | Type: consumption, restock, waste; links to procedure if consumption during treatment |
| 14 | Implement `GET /inventory/alerts` — active alerts (low stock + expiry within 30d) | INV-04 | P1 | 0.5d | INV-01, N-05 | Returns expiring + low stock items; triggers push/email notification for critical items |
| 15 | Implement `POST /inventory/sterilization` and `GET /inventory/sterilization` — sterilization log | INV-05, INV-06 | P1 | 1.5d | INV-01 | Autoclave_id, load_number, temperature, duration, biological/chemical indicators, instruments[], responsible_user, digital_signature; exportable PDF for audits |
| 16 | Implement `POST /inventory/implants/{id}/link` — implant traceability to patient procedure | INV-07 | P1 | 1d | INV-01, CR-12 | Serial + lot + manufacturer linked to procedure → patient → tooth; `GET /patients/{id}/implants` returns traceability report |
| 17 | Build FE-INV-01: inventory dashboard (semaphore list, search, filter) | FE-INV-01 | P1 | 1.5d | INV-02 | Traffic-light color per item; filter by category and status; search by name |
| 18 | Build FE-INV-02: sterilization log registration and history | FE-INV-02 | P1 | 1d | INV-05, INV-06 | Cycle registration form; history table; digital signature for responsible user; PDF export |
| 19 | Build FE-INV-03: implant traceability tracker (linked to patient) | FE-INV-03 | P1 | 1d | INV-07 | Link implant form; patient + tooth selection; traceability report per patient |
| 20 | Mexico compliance adapter groundwork: SAT CFDI integration research | INT-05 | P2 | 1d | I-13 | PAC provider selected; UBL equivalent for CFDI documented; NOM-024 requirements listed; CURP + RFC validation rules documented |

**Sprint 15 total estimate: ~26 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 16: Admin/Superadmin + Mexico + Offline Groundwork + Infrastructure Hardening

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement superadmin login: `POST /admin/auth/login` with MFA | AD-01 | P0 | 1.5d | I-02 | Separate auth context; TOTP MFA required; rate limited (3 attempts/15min per IP); session shorter than regular sessions (8h) |
| 2 | Implement `GET /admin/tenants` — platform-wide tenant management with metrics | AD-02 | P0 | 1.5d | T-01 | All tenants with plan, status, patient count, MAU, MRR; search/filter; matches T-01 through T-05 with additional metrics |
| 3 | Implement `GET/PUT /admin/plans` — manage subscription plans | AD-03 | P0 | 1d | None | Update pricing, feature flags, patient/doctor limits; changes propagate to new subscriptions immediately |
| 4 | Implement `GET /admin/analytics` — platform-level analytics | AD-04 | P0 | 1.5d | T-01 | MRR, MAU, tenant count by plan, tenant count by country, churn rate (30-day), feature usage rates |
| 5 | Implement `GET/PUT /admin/feature-flags` — feature flag management | AD-05 | P0 | 1d | None | Global on/off; per-tenant override; flags: anatomic_odontogram, voice_ai, radiograph_ai, offline_mode, mexico_billing; used for gradual rollouts |
| 6 | Implement `GET /admin/health` — system health dashboard | AD-06 | P0 | 1d | I-15 | Database connections (pool usage); RabbitMQ queue depths; Redis cache hit rate; error rates per tenant (top 10 errors last 24h) |
| 7 | Implement `POST /admin/tenants/{id}/impersonate` — tenant impersonation for support | AD-07 | P1 | 1d | T-01, I-11 | Time-limited session (2h); full audit trail; impersonation indicator in all audit logs; revoke button |
| 8 | INT-05: Mexico SAT CFDI integration — PAC setup, XML stamping, UUID | INT-05 | P2 | 3d | I-13, B-01 | PAC provider API integrated (e.g., Facturama); CFDI XML generated; UUID assigned by PAC; stamped XML retrievable; CURP + RFC validation |
| 9 | Mexico compliance adapter: NOM-024 requirements, CURP validation, document types | INT-05 | P2 | 1.5d | I-13, INT-05 | Mexico adapter registered; required document fields (CURP, RFC); NOM-024 clinical record requirements documented; CFDI adapter plugged into CO-06 flow |
| 10 | ADR-006: Document offline sync approach decision | I-25 | P1 | 0.5d | None | Decision recorded: Service Workers + IndexedDB; sync queue strategy; conflict resolution (last-write-wins for clinical edits with audit trail) |
| 11 | I-18: Offline-first architecture — Service Worker setup, IndexedDB schema | I-18 | P1 | 3d | I-25, I-19 | Service Worker registered; offline fallback page served; IndexedDB schema designed (patients, odontogram, appointments tables); sync queue structure |
| 12 | I-19: PWA configuration — manifest.json, cache strategies, push notification setup | I-19 | P1 | 1.5d | I-18 | manifest.json with dental-themed icons; install prompt; cache-first for static assets; network-first for API calls; push notification permission setup |
| 13 | I-15: Monitoring and observability — Sentry, structured logging, APM | I-15 | P0 | 2d | I-14 | Sentry error tracking on backend (FastAPI) + frontend (Next.js); structured JSON logging; custom metrics: tenant count, active users, appointments/day; health check endpoints |
| 14 | I-16: Backup and disaster recovery — WAL archiving, PITR, cross-region backup | I-16 | P0 | 2d | I-04 | PostgreSQL WAL archiving enabled; point-in-time recovery tested (restore to 5min ago); cross-region backup schedule (daily full, hourly WAL); RTO ≤4h, RPO ≤1h documented |
| 15 | Email templates: E-16 and E-17 (daily clinic summary + plan upgrade prompt) | E-16, E-17 | P2 | 1d | AN-01, T-09 | Daily summary: appointments, revenue, new patients; upgrade prompt: limit approaching with upgrade CTA |
| 16 | INT-09: Google Calendar sync groundwork (OAuth2 setup, event mapping design) | INT-09 | P2 | 1d | AP-01 | OAuth2 consent flow; appointment-to-GCal event mapping designed; bi-directional conflict resolution strategy documented; implementation deferred to Sprint 17 if time |
| 17 | Security hardening: OWASP checklist, CSP headers, file upload scanning | I-10 | P0 | 1.5d | None | CSP headers enforced; file uploads scanned (MIME type + magic bytes validation); SQL parameterization verified on all queries; CORS config reviewed |
| 18 | Write superadmin tests: impersonation, tenant isolation, MFA | I-08 | P0 | 1d | AD-01–AD-07 | Impersonation creates audit trail; impersonated session cannot access other tenants; MFA enforced |

**Sprint 16 total estimate: ~27 days of engineering work (2 engineers × 2 weeks)**

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| RIPS generation complexity — MinSalud validation rules are underdocumented | High | Engage a Colombian dental compliance consultant before Sprint 13. Source RIPS technical spec from MinSalud SISPRO portal. Test with sample data from a real clinic. Build validation as a separate step (CO-04) so errors are actionable. |
| MATIAS API registration and "Casa de Software" certification timeline | High | Start MATIAS registration at the beginning of Sprint 13. Certification may take 2-4 weeks. Build with MATIAS sandbox first; swap to production credentials when certified. Cost: ~$400K COP/year. |
| DIAN RIPS deadline (April 2026) — Sprint 13 must complete before April | Critical | Sprint 13 starts in month 7. April 2026 deadline gives roughly 1 month of buffer. If RIPS generation or MATIAS slips, delay inventory (Sprint 15) not compliance. |
| 15-year data retention implementation: conflict with patient deletion requests | High | Colombia Ley 1581 (data protection) vs. clinical record retention mandate. Resolution: anonymize personal data (name, phone, email) on deletion request; preserve clinical records with anonymous patient reference. Legal review before Sprint 14. |
| Analytics performance at scale: 10K patient clinic with 3 years of data | Medium | Pre-aggregate key metrics in background jobs (nightly). Use materialized views for revenue/appointment summaries. Redis TTL cache for dashboard (5 min). Target: dashboard ≤1s. |
| Mexico CFDI PAC provider selection and cost | Low | SAT-authorized PAC providers: Facturama, Trasmisiones, Diverza. Select Facturama (REST API, reasonable pricing). Budget: ~$2-5 USD per 100 invoices. |
| Offline sync conflict resolution complexity | Medium | This sprint only delivers the architecture and Service Worker setup (I-18, I-19). Full sync logic is post-launch. Clinical data integrity requires careful conflict resolution — last-write-wins with audit trail is the minimum viable approach. |
| Superadmin impersonation security | High | Impersonation logs every action with `impersonating_admin_id` in audit log. Time-limited (2h). Cannot be used to change billing or impersonate another admin. Penetration test before Sprint 17. |

---

## Definition of Done

- [ ] RIPS generates valid AF, AC, AP, AT, AM, AN, AU files for a test clinic
- [ ] RIPS validation returns actionable errors linked to source records
- [ ] RDA compliance check returns accurate percentage and gap list
- [ ] DIAN e-invoice via MATIAS: CUFE generated; XML retrievable; multiple roles can invoice
- [ ] 100% of clinical data access and writes logged in audit_log table
- [ ] 15-year retention policy enforced: clinical records cannot be hard-deleted
- [ ] Analytics dashboard loads in ≤ 1s for clinic with 10K patients
- [ ] CSV import handles 5K patients in < 60s
- [ ] Inventory semaphore (green/yellow/orange/red) visible in dashboard
- [ ] Sterilization cycle log functional with digital signature
- [ ] Implant registered to patient + tooth; traceability report available
- [ ] Superadmin can manage tenants, plans, feature flags, impersonate clinics
- [ ] Sentry error tracking live on backend and frontend
- [ ] PostgreSQL WAL archiving + PITR tested
- [ ] Service Worker registered; offline fallback page served

---

## Sprint 13-16 Acceptance Criteria

### Sprint 13
| Criteria | Target |
|----------|--------|
| RIPS | Generates valid AF, AC, AP, AT, AM, AN, AU files |
| RIPS validation | Returns specific error references linkable to patient/procedure |
| RDA | Compliance check returns percentage and gap list |
| MATIAS | E-invoice generates CUFE; XML retrievable from MATIAS |
| Multi-role invoicing | clinic_owner, doctor, assistant can generate e-invoices |

### Sprint 14
| Criteria | Target |
|----------|--------|
| Audit coverage | 100% of clinical data access and writes logged |
| Data retention | 15-year rule enforced at DB level; anonymization workflow functional |
| Compliance UI | RIPS page, RDA dashboard, e-invoice list complete |
| Analytics API | AN-01 through AN-07 implemented |
| Analytics performance | Dashboard ≤1s for 10K patient clinic |

### Sprint 15
| Criteria | Target |
|----------|--------|
| Analytics UI | FE-AN-01 through FE-AN-04 + FE-S-09 complete |
| Patient import | 5K patients imported in < 60s; error report accurate |
| Inventory | Semaphore colors correct; sterilization log functional; implant traceability working |
| Inventory UI | FE-INV-01, FE-INV-02, FE-INV-03 complete |

### Sprint 16
| Criteria | Target |
|----------|--------|
| Superadmin | MFA login; tenant management; impersonation with audit trail |
| Monitoring | Sentry live; structured logging; health dashboard functional |
| Backup/DR | WAL archiving enabled; PITR tested to 5-minute recovery |
| Offline | Service Worker registered; IndexedDB schema defined; offline fallback page served |
| Security | OWASP checklist items addressed; file upload validation hardened |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial backlog — Compliance + Advanced Features M4 (Sprints 13-16) |
