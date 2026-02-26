# M2 Clinical Core Backlog (R-06)

> Sprint 5-8 planning document with task breakdown, estimates, and acceptance criteria.

**Version:** 1.0
**Date:** 2026-02-25
**Sprints:** 5-8
**Duration:** 8 weeks (4 sprints × 2 weeks)
**Month:** 3-4

---

## Sprint Goals

### Sprint 5: Odontogram + Clinical Foundation
Build the core differentiator: the interactive odontogram (classic mode), CIE-10/CUPS catalogs, anamnesis, evolution templates, and the service/price catalog. This sprint unlocks all subsequent clinical work. The odontogram must be faster than sketching on paper.

### Sprint 6: Odontogram Completion + Clinical Base
Complete anatomic odontogram mode, tooth photo attachments, voice infrastructure groundwork, and finish the base clinical records API (record CRUD, anamnesis, catalog search). Deliver all odontogram frontend screens so doctors can begin real charting workflows.

### Sprint 7: Diagnoses, Procedures, Treatment Plans, Auto-Quotation
Implement the full treatment planning flow: diagnoses (CIE-10 linked), procedure recording (CUPS coded), treatment plan creation, and the auto-quotation pipeline (Odontogram → Plan → Quotation → Invoice draft). This sprint delivers the "no triple-digitación" auto-flow.

### Sprint 8: Consents, Prescriptions, Digital Signatures, Clinical Frontend
Complete the clinical data capture loop: consent management, prescriptions, digital signature infrastructure, and all clinical frontend screens (records, treatment plans, consents, prescriptions). Sprint ends with a fully working clinical workflow from odontogram to signed consent.

---

## Task Breakdown

### Sprint 5: Odontogram + Clinical Foundation

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement `GET /odontogram` — returns 32/20 teeth with conditions per zone, tenant mode (classic/anatomic) | OD-01 | P0 | 2d | P-01, T-06 | Returns correct FDI-numbered teeth; zone conditions included; adult/pediatric flag respected |
| 2 | Implement `POST /odontogram/conditions` — add/update condition on tooth zone | OD-02 | P0 | 1.5d | OD-01 | All 12 condition codes accepted; history entry created; audit logged |
| 3 | Implement `DELETE /odontogram/conditions/{id}` — remove condition | OD-03 | P0 | 0.5d | OD-02 | Soft removal; history entry created; doctor-only RBAC enforced |
| 4 | Implement `GET /odontogram/history` — timeline of all odontogram changes | OD-04 | P1 | 1d | OD-02 | Filterable by tooth, condition, date range, doctor; paginated |
| 5 | Implement `POST/GET /odontogram/snapshots` + list — point-in-time snapshot | OD-05, OD-06, OD-07 | P1 | 1.5d | OD-01 | Snapshot stores full state; linked to clinical record or plan; retrievable by ID |
| 6 | Implement `GET /odontogram/compare` — diff between two snapshots | OD-08 | P1 | 1d | OD-05 | Returns added/removed/changed conditions per tooth; correct diff logic |
| 7 | Implement `GET /odontogram/conditions` — static conditions catalog (12 conditions) | OD-09 | P0 | 0.5d | None | Returns all 12 conditions with codes, colors, SVG data; publicly cached per tenant |
| 8 | Implement `GET /odontogram/teeth/{tooth_number}` — single tooth detail | OD-10 | P1 | 0.5d | OD-01 | Returns conditions, full history, linked treatments, X-rays for tooth |
| 9 | Implement `POST /odontogram/bulk` — bulk update multiple teeth/zones | OD-11 | P1 | 1d | OD-02 | Transactional (all-or-nothing); used for initial examination entry |
| 10 | Implement `POST /odontogram/dentition` — toggle adult/pediatric | OD-12 | P0 | 0.5d | OD-01 | Switches 32↔20 teeth; patient age hint used for default; manual override allowed |
| 11 | Load CIE-10 dental subset into catalog — Spanish FTS with PostgreSQL | CR-10 | P0 | 1.5d | None | ~500 dental-relevant codes seeded; FTS search returns results in ≤100ms |
| 12 | Load CUPS procedure code catalog — dental subset | CR-11 | P0 | 1.5d | None | ~200 dental CUPS codes seeded; searchable by code and description |
| 13 | Implement `POST /api/v1/patients/{id}/anamnesis` + `GET` | CR-05, CR-06 | P0 | 1d | P-01 | Structured fields (medications, allergies, conditions, habits); history-of-changes tracked |
| 14 | Implement evolution template list/create/get (`GET /evolution-templates`, `POST`, `GET /{id}`) | CR-15, CR-16, CR-17 | P0 | 2d | None | Built-in 7 templates seeded (resina, endodoncia x3, exodoncia x2, profilaxis, corona, blanqueamiento, consulta); custom templates creatable |
| 15 | Seed 7 built-in evolution templates at tenant provisioning | CR-15 | P0 | 1d | T-01, CR-15 | All 7 templates present on new tenant schema; variables use `{{bracket}}` notation |
| 16 | Implement service/price catalog `GET /billing/services` + `PUT /{id}` | B-14, B-15 | P0 | 1d | CR-11 | CUPS-linked catalog; per-doctor price override supported; clinic_owner only for updates |
| 17 | ADR-005: SVG odontogram rendering approach — document decision | I-24 | P0 | 0.5d | None | Decision recorded: classic grid (CSS/HTML) for Sprint 5; SVG anatomic deferred to Sprint 6 |
| 18 | Write odontogram unit tests (conditions, snapshots, diff, bulk) | I-08 | P0 | 1.5d | OD-01–OD-12 | 85%+ coverage on odontogram module; diff logic edge cases covered |

**Sprint 5 total estimate: ~20 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 6: Odontogram Completion + Clinical Base

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Build classic grid odontogram component — 32/20 teeth, 5 crown zones + root, color-coded | FE-OD-01 | P0 | 3d | OD-01, FE-DS-01 | All conditions render correctly with correct color; zone click opens condition panel |
| 2 | Build anatomic arch odontogram (SVG-based, interactive) — Starter+ plan only | FE-OD-02 | P1 | 3d | OD-01, I-24 | Upper/lower SVG arches; click zones; plan gate enforced; zoom functional |
| 3 | Build condition selection panel (12 conditions, quick-select, notes field) | FE-OD-03 | P0 | 1.5d | OD-02, FE-DS-19 | Opens on zone click; condition icons correct colors; notes saved; closes on confirm |
| 4 | Build odontogram history panel — sidebar timeline, filterable | FE-OD-04 | P1 | 1.5d | OD-04 | Chronological list; filter by date/condition; correct tooth FDI labels |
| 5 | Build comparison view — side-by-side snapshot diff | FE-OD-05 | P1 | 2d | OD-08 | Visual diff (added = green, removed = red, changed = yellow); snapshot selector |
| 6 | Build tooth detail panel — conditions, history, linked treatments, X-rays | FE-OD-06 | P1 | 1.5d | OD-10 | Slide-in panel; all linked data visible; opens from clicking tooth |
| 7 | Build odontogram toolbar — mode toggle, adult/pediatric, zoom, print, snapshot | FE-OD-07 | P0 | 1d | OD-01 | All actions functional; print triggers PDF-optimized view |
| 8 | Build FE-DS-18: interactive tooth selector widget (FDI notation) | FE-DS-18 | P0 | 1d | OD-09 | Reusable; click selects tooth by FDI number; mini odontogram visual |
| 9 | Build FE-DS-19: condition icon/badge component (color-coded per condition) | FE-DS-19 | P0 | 0.5d | OD-09 | 12 condition icons with correct clinical colors; used in odontogram + lists |
| 10 | Implement `POST/GET/DELETE` tooth photo attachment (`/teeth/{num}/photos`) | P-16 | P1 | 1.5d | OD-10, I-17 | S3 upload with tenant isolation; thumbnail generated; linked to tooth + odontogram version |
| 11 | Implement clinical record create/get/list/update (CR-01 through CR-04) | CR-01, CR-02, CR-03, CR-04 | P0 | 2d | P-01, I-11 | All record types (anamnesis/examination/diagnosis/evolution/procedure) accepted; 24h edit window; audit logged |
| 12 | Implement `GET /catalog/cie10` — typeahead search endpoint | CR-10 | P0 | 0.5d | None | ≤100ms response; dental subset prioritized; results cached in Redis |
| 13 | Implement `GET /catalog/cups` — CUPS procedure code search | CR-11 | P0 | 0.5d | None | ≤100ms; FTS on code + description; dental subset only |
| 14 | Build FE-CR-01: clinical records list (table with type icon, expandable) | FE-CR-01 | P1 | 1d | CR-03 | Type icon per record; expandable preview; sortable by date |
| 15 | Build FE-CR-02: create clinical record form (dynamic per type, template selector) | FE-CR-02 | P0 | 2d | CR-01 | Form changes fields based on selected type; evolution template selector shown for evolution notes |
| 16 | Build FE-CR-03: anamnesis questionnaire form (structured sections) | FE-CR-03 | P0 | 1.5d | CR-05 | Sections: medications, allergies, conditions, surgical history, habits; validation per field |
| 17 | Build FE-CR-06 and FE-CR-07: CIE-10 and CUPS autocomplete components | FE-CR-06, FE-CR-07 | P0 | 1d | CR-10, CR-11 | Async loading; debounced 300ms; shows code + Spanish description; max 10 results |
| 18 | Implement `POST /patients/{id}/clinical-records/from-template` — create record from evolution template | CR-15 | P1 | 1d | CR-01, CR-15 | Template variables replaced with patient/tooth data; audit logged |
| 19 | Write integration tests: odontogram frontend + API | I-08 | P0 | 1d | OD-01–OD-12, FE-OD-01–07 | Round-trip: add condition → appears in UI; bulk update → history correct |

**Sprint 6 total estimate: ~28 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 7: Diagnoses, Procedures, Treatment Plans, Auto-Quotation

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement `POST /patients/{id}/diagnoses` — create diagnosis (CIE-10, tooth link) | CR-07 | P0 | 1d | P-01, CR-10 | CIE-10 code validated; tooth_number optional; severity field; status (active/resolved) |
| 2 | Implement `GET /patients/{id}/diagnoses` — list diagnoses (active/resolved) | CR-08 | P0 | 0.5d | CR-07 | Filter by status, date range; returns linked teeth |
| 3 | Implement `PUT /patients/{id}/diagnoses/{id}` — update diagnosis | CR-09 | P0 | 0.5d | CR-07 | Status transitions valid; notes appended; audit logged |
| 4 | Implement `POST /patients/{id}/procedures` — record procedure (CUPS, tooth, auto-update odontogram) | CR-12 | P0 | 1.5d | P-01, CR-11, OD-02 | CUPS code required; links to treatment plan item if provided; odontogram auto-updated for applicable conditions (e.g., exodoncia marks tooth absent) |
| 5 | Implement `GET /patients/{id}/procedures` and `GET /procedures/{id}` | CR-13, CR-14 | P0 | 0.5d | CR-12 | List filterable by date, doctor, CUPS code, tooth; detail includes all fields |
| 6 | Implement `POST /patients/{id}/treatment-plans` — create plan | TP-01 | P0 | 1d | P-01, CR-07 | Title, description, linked diagnoses, priority, estimated duration |
| 7 | Implement `GET /treatment-plans/{id}` and `GET /treatment-plans` | TP-02, TP-03 | P0 | 0.5d | TP-01 | Detail includes items + costs + progress; list filterable by status |
| 8 | Implement `PUT /treatment-plans/{id}` — update plan metadata/status | TP-04 | P0 | 0.5d | TP-01 | Status transitions: draft → active → completed enforced |
| 9 | Implement `POST /treatment-plans/{id}/items` — add item to plan | TP-05 | P0 | 1d | TP-01, CR-11 | CUPS code, tooth, zone, estimated_cost, priority_order; auto-price from service catalog |
| 10 | Implement `PUT /items/{id}` and `POST /items/{id}/complete` | TP-06, TP-07 | P0 | 1d | TP-05, CR-12 | Item complete links to procedure record; plan progress% recalculated |
| 11 | Implement `POST /treatment-plans/{id}/approve` — digital signature capture | TP-08 | P0 | 1d | TP-01, DS-01 | Signature image (base64 PNG); timestamp + IP + user-agent stored; Ley 527/1999 metadata logged |
| 12 | Implement `GET /treatment-plans/{id}/pdf` — generate branded PDF | TP-09 | P1 | 1.5d | TP-02, OD-05 | Includes procedures, costs, odontogram snapshot, clinic branding, patient info; Playwright headless Chromium |
| 13 | Implement `POST /treatment-plans/{id}/share` — share via email/WhatsApp | TP-10 | P1 | 0.5d | TP-09 | Queued email via RabbitMQ; temporary portal link with 7-day expiry |
| 14 | Implement DS-01: digital signature service (canvas PNG + SHA-256 + audit) | DS-01 | P0 | 1.5d | I-11 | `POST /api/v1/signatures`; signer name, role, timestamp (UTC), IP, user-agent logged; audit entry created |
| 15 | Implement auto-quotation `POST /quotations` from treatment plan | B-16 | P0 | 1.5d | TP-01, B-14 | Pulls prices from service catalog; creates line items; status: draft |
| 16 | Implement `GET /quotations/{id}` — quotation detail | B-17 | P0 | 0.5d | B-16 | Line items, discounts, totals, expiry date |
| 17 | Implement `POST /quotations/{id}/send` — share quotation via email/WhatsApp | B-18 | P1 | 0.5d | B-16 | Queued delivery; portal link for patient review |
| 18 | Implement `POST /quotations/{id}/approve` — convert approved quotation to invoice draft | B-19 | P0 | 1d | B-16, TP-01 | Treatment plan activated; invoice draft created; all linked |
| 19 | Build FE-CR-04: diagnosis form (CIE-10 autocomplete, severity, tooth link) | FE-CR-04 | P0 | 1d | CR-07, CR-10 | CIE-10 search works; tooth selector (FE-DS-18) integrated; severity selector |
| 20 | Build FE-CR-05: procedure recording form (CUPS autocomplete, tooth/zone, materials) | FE-CR-05 | P0 | 1.5d | CR-12, CR-11 | CUPS autocomplete; tooth selector; zone multi-select; link to treatment plan item optional |
| 21 | Build FE-TP-01: treatment plan list (cards with status, progress bar, cost) | FE-TP-01 | P0 | 0.5d | TP-03 | Status badge; progress bar (% complete); total cost; date range |
| 22 | Build FE-TP-02: create treatment plan form (CUPS search, drag reorder, auto-price) | FE-TP-02 | P0 | 2d | TP-01, TP-05 | Add items with CUPS search; drag to reorder; total auto-calculates from catalog prices |
| 23 | Build FE-TP-03: treatment plan detail page (items, progress, quotation button) | FE-TP-03 | P0 | 1.5d | TP-02 | Item statuses shown; progress bar; "Generate Quotation" button; share/PDF actions |
| 24 | Write integration tests: treatment plan + quotation auto-flow | I-08 | P0 | 1d | TP-01–TP-10, B-16–B-19 | Odontogram condition → suggest procedure → plan item → quotation → approved → invoice draft: full chain test passes |

**Sprint 7 total estimate: ~24 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 8: Consents, Prescriptions, Digital Signatures, Clinical Frontend

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement consent template list/create/get (IC-01, IC-02, IC-03) | IC-01, IC-02, IC-03 | P0 | 1.5d | None | Built-in templates seeded (general, surgery, sedation, orthodontics, implants); custom templates creatable by clinic_owner |
| 2 | Seed built-in consent templates at tenant provisioning | IC-01 | P0 | 0.5d | T-01 | 5 built-in templates present on every new tenant |
| 3 | Implement `POST /patients/{id}/consents` — create consent from template | IC-04 | P0 | 1d | IC-01, P-01 | Pre-fills patient name/date; status: draft |
| 4 | Implement `POST /consents/{id}/sign` — patient signs consent | IC-05 | P0 | 1.5d | IC-04, DS-01 | Signature (base64 or typed name); timestamp + IP + device_info stored; generates signed PDF; record immutable after signing |
| 5 | Implement `GET /consents/{id}`, `GET /consents` (list), `GET /consents/{id}/pdf` | IC-06, IC-07, IC-08 | P0 | 1d | IC-04 | Detail includes signature status and PDF link; list filterable by status/template/date; PDF generated with clinic branding |
| 6 | Implement `POST /consents/{id}/void` — void signed consent | IC-09 | P1 | 0.5d | IC-05, I-11 | Audit entry created; original preserved; clinic_owner only |
| 7 | Implement `POST /patients/{id}/prescriptions` — create prescription | RX-01 | P0 | 1d | P-01, CR-07 | Multiple medications per prescription; linked diagnosis; doctor digital signature |
| 8 | Implement `GET /prescriptions/{id}`, `GET /prescriptions` (list) | RX-02, RX-03 | P0 | 0.5d | RX-01 | Detail includes all medications with dosage/frequency/duration |
| 9 | Implement `GET /prescriptions/{id}/pdf` — prescription PDF generation | RX-04 | P0 | 1d | RX-01 | Clinic branding; doctor info; patient info; formatted like prescription pad; print-optimized |
| 10 | Implement `GET /catalog/medications` — medication catalog search | RX-05 | P0 | 1d | None | Dental-relevant subset (antibiotics, analgesics, antiseptics, anesthetics); FTS on name + active ingredient; cached |
| 11 | Implement `GET /patients/{id}/medical-history` — full medical timeline | P-07 | P1 | 1.5d | P-01, CR-01, OD-01 | Ordered list of all clinical events; paginated; links to each record |
| 12 | Build FE-TP-04: treatment plan approval flow (signature pad, mobile-optimized) | FE-TP-04 | P0 | 1.5d | TP-08, FE-DS-14 | Full plan summary displayed; FE-DS-14 signature pad; "I accept" checkbox; mobile-first layout |
| 13 | Build FE-IC-01: consent forms list (status badges, template name, date) | FE-IC-01 | P0 | 0.5d | IC-07 | Status badges (draft/signed/void); template name shown; download PDF action |
| 14 | Build FE-IC-02: create consent form (select template, preview, send/sign) | FE-IC-02 | P0 | 1d | IC-04 | Template selector with preview; "Sign in clinic" vs "Send to patient" options |
| 15 | Build FE-IC-03: consent signing screen (scroll-to-read, signature pad, submit) | FE-IC-03 | P0 | 1.5d | IC-05, FE-DS-14 | Scroll progress indicator; signature pad; submit disabled until document fully scrolled; mobile-optimized |
| 16 | Build FE-IC-04: custom consent template editor (rich text, placeholders) | FE-IC-04 | P1 | 1.5d | IC-02 | Rich text editor (Tiptap); placeholder insertion (`{{patient_name}}`, `{{date}}`); preview mode |
| 17 | Build FE-RX-01: create prescription form (medication autocomplete, multiple meds) | FE-RX-01 | P0 | 1d | RX-01, RX-05 | Medication autocomplete from catalog; add multiple medications; dosage/frequency/duration per med |
| 18 | Build FE-RX-02 and FE-RX-03: prescription list + preview/print view | FE-RX-02, FE-RX-03 | P0 | 1d | RX-03, RX-04 | List shows date, medications summary, doctor; print view formatted as prescription pad |
| 19 | Build FE-P-07: medical history timeline within patient detail tab | FE-P-07 | P1 | 1d | P-07 | Chronological events; type icon per event; filter by type (appointment, record, diagnosis, procedure) |
| 20 | Email templates: E-09 (treatment plan shared) and E-10 (consent signature request) | E-09, E-10 | P0 | 1d | TP-10, IC-04 | HTML emails with clinic branding; portal link with correct expiry; tested with SendGrid sandbox |
| 21 | Write end-to-end tests: consent lifecycle + prescription + signature | I-08 | P0 | 1d | IC-01–IC-09, RX-01–RX-05, DS-01 | Create consent → sign → PDF downloadable; create prescription → PDF generated; signature metadata complete |
| 22 | Performance validation: odontogram load ≤300ms; CIE-10/CUPS ≤100ms | OD-01, CR-10, CR-11 | P0 | 0.5d | All Sprint 5-8 backend | EXPLAIN ANALYZE on all catalog queries; Redis cache verified for catalogs |

**Sprint 8 total estimate: ~24 days of engineering work (2 engineers × 2 weeks)**

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SVG anatomic odontogram complexity overruns Sprint 6 | High | Classic grid (CSS) is shipped in Sprint 5 and is the clinical blocker; anatomic can slip to Sprint 6+. Time-box anatomic at 3 days and cut if needed. |
| CIE-10/CUPS catalog data quality (Spanish translations, dental subset selection) | Medium | Use WHO official ICD-10 Spanish translation; supplement dental subset from Colombia MinSalud RIPS reference. Validate with at least one dentist before seeding. |
| PDF generation performance (treatment plans with odontogram snapshots) | Medium | Use async PDF generation via RabbitMQ worker; return job_id immediately; poll for completion. Never block on PDF in request cycle. |
| Digital signature legal validity (Ley 527/1999 compliance) | High | Store: base64 PNG + SHA-256 hash + UTC timestamp + IP + user-agent. Log everything. Review with Colombian legal counsel before Sprint 9. |
| Auto-quotation price accuracy (service catalog not pre-configured by clinic) | Medium | Show explicit warning if catalog prices are zero/empty when generating quotation. Prompt clinic_owner to configure catalog during onboarding. |
| Medication catalog scope (which medications to seed for dental) | Low | Seed: antibiotics (amoxicillin, metronidazole, clindamycin), analgesics (ibuprofen, acetaminophen, naproxen), topical (benzocaine, chlorhexidine). Expandable by clinic. |

---

## Definition of Done

- [ ] All spec'd backend endpoints implemented, tested, and documented in FastAPI OpenAPI
- [ ] All frontend screens match spec (responsive, mobile-first, WCAG 2.1 AA)
- [ ] All clinical data writes produce audit log entries in `audit_log` table
- [ ] Odontogram state loads in < 300ms (p95)
- [ ] CIE-10 and CUPS search returns in ≤ 100ms (p95)
- [ ] Treatment plan PDF generates correctly with clinic branding
- [ ] Digital signature captures SHA-256 hash + timestamp + IP per Ley 527/1999
- [ ] Auto-quotation: odontogram conditions → plan items → prices from catalog → quotation PDF: full chain working
- [ ] 85%+ test coverage on odontogram module; 80%+ on clinical records, treatment plans, consents
- [ ] Evolution templates seeded for 7 common procedures; creatable by clinic_owner and doctors
- [ ] Security: no cross-tenant data leakage (tenant isolation tests passing)

---

## Sprint 5-8 Acceptance Criteria

### Sprint 5
| Criteria | Target |
|----------|--------|
| Odontogram API | All 12 conditions accepted; OD-01 through OD-12 implemented |
| Catalog load | CIE-10 dental subset (~500 codes) + CUPS (~200 codes) seeded |
| Evolution templates | 7 built-in templates seeded at tenant provisioning |
| Service catalog | GET/PUT implemented; CUPS-linked |
| Performance | Odontogram GET ≤ 300ms; catalog search ≤ 100ms |
| Test coverage | 85% odontogram module |

### Sprint 6
| Criteria | Target |
|----------|--------|
| Odontogram UI | Classic grid renders all 12 conditions; anatomic arch functional |
| Condition panel | Opens on zone click; all 12 conditions selectable |
| History panel | Timeline filterable by tooth/condition/date |
| Clinical records | CR-01 through CR-06 API complete |
| Tooth photos | Attachable to specific tooth in ≤ 2 taps |

### Sprint 7
| Criteria | Target |
|----------|--------|
| Auto-flow | Odontogram → plan items → quotation → invoice draft: complete chain |
| Treatment plan | Create/approve/PDF/share all functional |
| Digital signature | Ley 527/1999 metadata stored on every signature |
| Quotation PDF | Generates with clinic branding |
| Treatment plan UI | List, create, detail, approval screens complete |

### Sprint 8
| Criteria | Target |
|----------|--------|
| Consents | IC-01 through IC-09 complete; 5 built-in templates seeded |
| Prescriptions | RX-01 through RX-05 complete; PDF generates |
| Consent signing screen | Scroll-to-read + signature pad; mobile-optimized |
| Medical history | Full timeline in patient detail |
| Email templates | E-09 and E-10 tested and delivered |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial backlog — Clinical Core M2 (Sprints 5-8) |
