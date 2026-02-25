# M5 Beta + Launch Backlog (R-09)

> Sprint 17-20 planning document with task breakdown, estimates, and acceptance criteria.

**Version:** 1.0
**Date:** 2026-02-25
**Sprints:** 17-20
**Duration:** 8 weeks (4 sprints × 2 weeks)
**Month:** 9-10

---

## Sprint Goals

### Sprint 17: Beta Onboarding + Performance + Security Audit
Recruit and onboard 3-5 beta dental clinics in Colombia. Set up the beta environment on Hetzner Cloud. Run load testing, performance optimization, and a security audit. This sprint produces zero new features — it is 100% quality, hardening, and early customer validation.

### Sprint 18: Beta Feedback Iteration + Infrastructure Finalization + Payment Gateway
Triage and fix beta feedback (P0 critical bugs, P1 workflow blockers). Finalize remaining infrastructure: Google Calendar sync, payment gateway (Mercado Pago + PSE), and production monitoring configuration. Polish mobile/tablet UX based on clinical staff feedback.

### Sprint 19: Production Deployment + Marketing Site + Documentation
Provision the Hetzner Cloud production environment, deploy all services, configure monitoring and alerting, and finalize user documentation for all roles (clinic owner, doctor, receptionist, patient portal). Build the marketing landing page and self-service registration flow.

### Sprint 20: Colombia Launch + Post-Launch Monitoring
Execute the Colombia launch: migrate beta clinics to production, announce to target market (Bogota, Medellin, Cali), establish customer support channels, and monitor the first two weeks in production with daily error rate and performance reviews.

---

## Task Breakdown

### Sprint 17: Beta Onboarding + Performance + Security Audit

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Recruit 3-5 beta dental clinics in Colombia (Bogota, Medellin, Cali) | — | P0 | Ongoing | None | Signed beta agreement; clinic owner contact established; NDA/beta terms agreed |
| 2 | Provision Hetzner Cloud beta environment (separate from dev, mirror of prod topology) | I-14 | P0 | 1.5d | I-14 | PostgreSQL managed DB; Redis; RabbitMQ; FastAPI + Next.js containers; SSL; domain (beta.dentalos.co) |
| 3 | Onboard beta clinics: seed initial data, import existing patients from CSV | P-08, T-10 | P0 | 2d per clinic | P-08, T-10 | Each clinic has: tenant provisioned; admin user created; sample patients imported; onboarding wizard completed; demo walkthrough done |
| 4 | Establish beta feedback collection process | — | P0 | 0.5d | None | In-app feedback widget (Canny or similar); weekly video call per clinic; bug report email alias; Slack/WhatsApp group with beta testers |
| 5 | Load test: 500 concurrent users sustained for 30 minutes | I-08 | P0 | 2d | All Sprint 1-16 | k6 or Locust load test; target: p95 API ≤ 200ms; p99 ≤ 500ms; no errors under load; memory stable |
| 6 | Load test: 100 concurrent appointment bookings (simulate receptionist rush hour) | I-08 | P0 | 1d | AP-01 | No double-bookings; availability queries consistent under load; 100 concurrent creates succeed without conflict errors |
| 7 | Load test: odontogram bulk updates under concurrent load | I-08 | P0 | 1d | OD-11 | 50 concurrent bulk updates on same patient: last-write-wins with correct audit; no data corruption |
| 8 | Load test: full-text search (patients, CIE-10, CUPS) under load | I-08 | P0 | 1d | P-06, CR-10, CR-11 | Patient FTS returns ≤ 100ms at 200 concurrent searches; catalog search stable |
| 9 | Database connection pool stress test (100+ concurrent connections) | I-04 | P0 | 1d | I-04 | pgBouncer pool saturation behavior documented; max connections tested; graceful rejection on pool exhaustion |
| 10 | RabbitMQ queue depth test under sustained load | I-06 | P0 | 0.5d | I-06 | Queue depth stable under 1000 messages/minute; DLQ routing verified; worker autoscaling behavior |
| 11 | OWASP Top 10 vulnerability scan | I-10 | P0 | 2d | All Sprint 1-16 | Zero critical or high severity findings. Document medium findings with remediation timeline. Tools: OWASP ZAP, Semgrep. |
| 12 | SQL injection testing (SQLAlchemy parameterization verification) | I-10 | P0 | 1d | None | All queries use ORM or parameterized SQL; no raw string interpolation in queries; verified with sqlmap on staging |
| 13 | XSS prevention testing (frontend and API responses) | I-10 | P0 | 1d | None | All user input sanitized; API responses escape HTML; Content-Security-Policy headers verified |
| 14 | JWT token security audit (RS256 key rotation, token revocation) | I-02 | P0 | 1d | I-02 | RS256 keys in secrets manager; rotation procedure documented; refresh token revocation tested; replay detection verified |
| 15 | File upload security (MIME type + magic bytes validation, size limits) | I-17 | P0 | 0.5d | I-17 | MIME type validated server-side (not just extension); magic bytes checked; max file size enforced per type (X-rays 20MB, PDFs 5MB); virus scan hook documented |
| 16 | PHI (Protected Health Information) access audit | I-10 | P0 | 1d | I-11 | Verify: all clinical endpoints require auth; no PHI in URL parameters (only IDs); no PHI in logs; HTTPS enforced everywhere |
| 17 | Tenant isolation penetration test (cross-tenant data access attempts) | I-01 | P0 | 1d | I-01 | Attempt to access Tenant A data with Tenant B credentials; schema isolation verified at every endpoint; no cross-tenant leakage |
| 18 | Database query optimization: EXPLAIN ANALYZE on top 20 slowest queries | I-04 | P1 | 2d | All Sprint 1-16 | Each of top 20 queries has appropriate index; no sequential scans on large tables; query plan reviewed and optimized |
| 19 | N+1 query detection and resolution | I-04 | P1 | 1.5d | All Sprint 1-16 | Use SQLAlchemy eager loading; identify N+1 patterns with Django Debug Toolbar equivalent for FastAPI (sqlalchemy-query-counter); eliminate top 10 N+1 issues |
| 20 | Redis cache hit rate optimization (target: > 90% on catalog endpoints) | I-05 | P1 | 1d | I-05 | Monitor cache hit rate; increase TTL on stable data (CIE-10, CUPS, conditions catalog); add caching to any uncached analytics aggregations |
| 21 | Frontend bundle size audit (target: < 200KB initial JS) | FE-DS-01 | P1 | 1d | All Sprint 3-16 frontend | Next.js bundle analyzer; tree-shake unused components; lazy load heavy components (odontogram SVG, chart library); code split by route |
| 22 | Image optimization: X-rays lazy loading, progressive JPEG, WebP conversion | I-17 | P1 | 1d | P-13 | Lazy loading on document gallery; progressive JPEG for large X-rays; WebP served where browser supports; loading skeleton shown |

**Sprint 17 total estimate: ~27 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 18: Beta Feedback Iteration + Infrastructure Finalization

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Triage beta feedback: categorize all items by severity (P0/P1/P2/P3) | — | P0 | 1d | Sprint 17 beta onboarding | All feedback items logged in issue tracker; P0 (data loss, security, crash) and P1 (workflow blocker) identified; assigned to sprint |
| 2 | Fix critical bugs P0: data loss, crashes, security issues from beta | — | P0 | 4d | Beta feedback triage | Zero P0 issues remaining after this sprint; all data loss scenarios eliminated |
| 3 | Fix high-priority bugs P1: workflow blockers from beta | — | P0 | 3d | Beta feedback triage | Top 10 P1 issues resolved; re-tested with beta clinics |
| 4 | UX improvements from clinical staff feedback | — | P1 | 2d | Beta feedback | Receptionist workflow: faster appointment creation; doctor workflow: faster odontogram entry; specific friction points addressed |
| 5 | Mobile/tablet usability fixes (iPad clinical use is primary) | — | P1 | 2d | Beta feedback | Touch targets ≥ 44px; odontogram usable on 10-inch tablet; appointment calendar legible on tablet; signature pad works on touchscreen |
| 6 | INT-07: Payment gateway integration — Mercado Pago + PSE Colombia | INT-07 | P1 | 3d | B-07, PP-06 | Mercado Pago REST API integrated; PSE Colombia (bank transfer) supported; payment link generation from invoice; webhook for payment confirmation; portal payment flow live |
| 7 | INT-09: Google Calendar sync — OAuth2 + bi-directional event sync | INT-09 | P2 | 2d | AP-01 | OAuth2 consent; appointment created in DentalOS appears in doctor's Google Calendar; cancellation syncs; conflict resolution: DentalOS is source of truth |
| 8 | Monitoring configuration: custom business metrics dashboard | I-15 | P0 | 1.5d | I-15 | Custom dashboards: tenant count, active users/day, appointments/day, new patients/week, error rate, queue depth; all visible in Grafana or equivalent |
| 9 | Configure production alerting rules | I-15 | P0 | 1d | I-15 | Alerts: p95 API > 500ms; error rate > 1%; disk > 80%; queue depth > 1000; DB connections > 80% pool; on-call rotation configured |
| 10 | On-call rotation and incident response runbook | I-15 | P0 | 1d | None | Runbook: who to call, escalation path, common incident procedures (DB failover, queue restart, memory pressure); tested with simulated incident |
| 11 | Re-run load tests after bug fixes (regression check) | I-08 | P0 | 1d | Sprint 17 load tests | p95 still ≤ 200ms; no regressions introduced by bug fixes |
| 12 | Re-test tenant isolation after any auth/query changes from beta fixes | I-01 | P0 | 0.5d | Sprint 17 isolation test | Cross-tenant access still impossible; any modified auth endpoints re-tested |
| 13 | Finalize blue-green deployment pipeline | I-14 | P0 | 1.5d | I-14 | Blue-green switch with zero downtime verified; rollback procedure tested (switch back in < 2 min); health check used to verify green before switch |
| 14 | API response time audit: identify and fix any endpoint exceeding p95 > 200ms | All | P0 | 1.5d | Load tests | All CRUD endpoints: p95 ≤ 200ms; reports/analytics: p95 ≤ 500ms; documented for production SLA |
| 15 | Uptime target validation: 99.9% during beta period | I-14 | P0 | 0.5d | Beta environment | Uptime monitor configured (e.g., Better Uptime); at least 99.9% uptime demonstrated across 2-week beta period |
| 16 | Accessibility audit: WCAG 2.1 AA for all screens delivered in M2 and M3 | FE-DS-01 | P1 | 1.5d | All frontend | Screen reader compatibility; color contrast ≥ 4.5:1; keyboard navigation; aria labels on interactive elements; axe DevTools scan |
| 17 | Colombian Ley 1581 data protection compliance review | I-12 | P0 | 1d | I-12 | Privacy policy written; data processing purposes documented; data retention periods stated; consent mechanisms audited; ready for legal review |
| 18 | Second beta feedback collection and prioritization cycle | — | P1 | Ongoing | Sprint 18 fixes | Weekly call with each beta clinic; updated issue list; P1 resolution rate > 80% |

**Sprint 18 total estimate: ~29 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 19: Production Deployment + Marketing Site + Documentation

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Provision Hetzner Cloud production environment | I-14 | P0 | 2d | I-14 | Separate production account; VPS sized for 50 clinics at launch; PostgreSQL managed DB (production config, backups enabled); Redis with persistence; RabbitMQ cluster |
| 2 | PostgreSQL production setup: managed DB, connection pooling, backup schedule | I-04, I-16 | P0 | 1d | I-16 | pgBouncer configured; automated daily backups; WAL archiving to object storage; monitoring alerts configured |
| 3 | Load balancer configuration: SSL termination, health checks | I-14 | P0 | 1d | I-14 | HTTPS enforced; HTTP → HTTPS redirect; health check endpoint (`/api/v1/health`) verified; sticky sessions not required (stateless JWT) |
| 4 | DNS and domain setup: dentalos.co (or equivalent) | I-14 | P0 | 0.5d | None | Production domain live; CNAME for `app.dentalos.co` (frontend); `api.dentalos.co` (backend); SPF/DKIM/DMARC for email deliverability |
| 5 | Deploy backend (FastAPI) to production: Docker image, environment variables, secrets | I-14 | P0 | 1d | Sprint 18 finalization | Docker image built from main branch; secrets in Hetzner secrets manager (not .env files); health check passing |
| 6 | Deploy frontend (Next.js) to production: Vercel or Hetzner static hosting | I-14 | P0 | 1d | Sprint 18 finalization | Production build deployed; environment variables for production API URL set; caching headers configured |
| 7 | Rollback strategy tested: deploy → detect issue → rollback in < 5 minutes | I-14 | P0 | 1d | I-14 | Blue-green rollback tested; RDS snapshot rollback documented; git tag for last known good commit; runbook tested |
| 8 | Sentry production configuration: error tracking backend + frontend | I-15 | P0 | 0.5d | I-15 | Production Sentry project; error alerts to on-call email/Slack; sample rate 100% for backend, 10% for frontend (cost control) |
| 9 | User guide: clinic owners (setup, onboarding, daily operations, billing) | — | P0 | 2d | None | Written in Spanish; covers: registration, onboarding wizard, adding team, patient management, billing, RIPS, e-invoices; PDF + in-app help links |
| 10 | User guide: doctors (odontogram, clinical records, treatment plans, prescriptions, voice) | — | P0 | 2d | None | Written in Spanish; covers: charting workflow, odontogram, voice-to-chart (if on plan), prescriptions, signing consents |
| 11 | User guide: receptionists (appointments, patient registration, messaging) | — | P0 | 1.5d | None | Written in Spanish; covers: ≤3-tap appointment booking, patient search, today's view, messaging, waitlist |
| 12 | Patient portal user guide (viewing appointments, signing consents, messaging clinic) | — | P0 | 1d | None | Written in Spanish; covers: portal login, appointment management, consent signing, messaging, odontogram view |
| 13 | API documentation: auto-generated from FastAPI OpenAPI spec | — | P1 | 0.5d | None | OpenAPI spec exported; hosted at `api.dentalos.co/docs`; Redoc UI for public API documentation |
| 14 | Admin runbook: tenant provisioning, support procedures, impersonation, billing | — | P0 | 1d | AD-01–AD-07 | Step-by-step for: provision new tenant; suspend/reactivate; impersonate for support; update plan; handle refund request |
| 15 | Marketing landing page: value proposition, features, pricing | — | P1 | 3d | None | Spanish-language landing page; headline communicates "más rápido que el papel"; features section; pricing table (Free/Starter/Pro/Clinica/Enterprise); SEO meta tags |
| 16 | Pricing page with plan comparison table | — | P1 | 1d | None | Interactive plan comparison; highlight recommended plan; add-on pricing (AI Voice $10, AI Radiograph $20); CTA to register |
| 17 | Self-service registration flow from marketing site | — | P0 | 1d | A-01, FE-A-01 | "Start Free" CTA links to registration; free plan (50 patients, 1 doctor) activates without payment; credit card not required for free tier |
| 18 | SEO optimization: "software dental Colombia" keyword cluster | — | P2 | 1d | Marketing site | Title tags, meta descriptions, H1s optimized; Google Search Console configured; sitemap.xml submitted |
| 19 | Final compliance review: RDA, RIPS, data protection law 1581 | I-12, I-13 | P0 | 1d | Sprint 14 compliance | Legal counsel confirms: RDA fields covered; RIPS generation correct; Ley 1581 compliance documented; ready for Colombia launch |
| 20 | DIAN electronic invoicing certification check (MATIAS "Casa de Software" status confirmed) | INT-10 | P0 | 0.5d | INT-10 | Confirm MATIAS production credentials active; test invoice in MATIAS production environment; CUFE generated with real DIAN response |
| 21 | Customer support channels established | — | P0 | 0.5d | None | WhatsApp Business number for support; support email alias; in-app "Help" button with chat or Intercom widget; SLA: P0 response within 2h, P1 within 8h |

**Sprint 19 total estimate: ~28 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 20: Colombia Launch + Post-Launch Monitoring

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Beta-to-production migration: migrate all beta clinic data to production environment | T-01, P-08 | P0 | 2d | Sprint 19 production deployment | Tenant schemas migrated from beta to production DB; all patients, clinical records, appointments preserved; logins work immediately after cutover |
| 2 | Beta clinic validation: each clinic tests production environment before go-live announcement | — | P0 | 1d | Beta migration | Each beta clinic confirms: login works; data present; existing appointments visible; ready sign-off from clinic owner |
| 3 | Launch announcement to beta participants | — | P0 | 0.5d | Beta validation | Email to all beta clinics: congratulations, production URL, new features since beta, support contacts, escalation path |
| 4 | Enable production payment processing: Mercado Pago + PSE Colombia live keys | INT-07 | P0 | 0.5d | INT-07, Sprint 18 | Mercado Pago production credentials active; test real payment end-to-end; PSE bank list live; payment confirmation webhook receiving events |
| 5 | Outbound sales outreach: dental clinics in Bogota, Medellin, Cali | — | P0 | Ongoing | Marketing site, registration flow | First 10 outbound contacts; sequence: LinkedIn + WhatsApp + email; demo booking link; personalized dental software pitch in Spanish |
| 6 | Day 1 post-launch monitoring: review all production dashboards every 2 hours | I-15 | P0 | 2d | Production monitoring | Error rate < 0.1%; p95 API < 200ms; queue depth stable; database connections healthy; no P0 alerts fired |
| 7 | Day 1: on-call engineer available 9am-10pm Colombia time (GMT-5) | I-15 | P0 | 2d | On-call runbook | Dedicated engineer monitoring Sentry + dashboards; sub-2h response to P0 alerts; incident log maintained |
| 8 | Week 1: daily error rate review and triage | I-15 | P0 | Ongoing | Production monitoring | Daily standup includes production error review; P0 fixed same day; P1 fixed within 48h |
| 9 | Week 1: daily performance metrics review | I-15 | P0 | Ongoing | Production monitoring | Track: p95 API response time; new tenant signups; patient registrations; appointment bookings; voice session usage |
| 10 | User onboarding funnel analysis: registration → onboarding wizard → first patient → first appointment | — | P1 | 1d | Production analytics | Google Analytics or Mixpanel events for each step; identify drop-off points; target: > 70% complete onboarding wizard |
| 11 | First-week retention tracking: day 1, day 3, day 7 active clinics | — | P1 | Ongoing | Production analytics | Track clinics that return on D1, D3, D7; identify at-risk clinics; reach out proactively to inactive new signups |
| 12 | Rapid response to production P0/P1 issues (bug fix + deploy cycle < 4h) | — | P0 | Ongoing | Deployment pipeline | Blue-green deploy pipeline ready for hotfix; tested rollback; fix → PR → CI → deploy in < 4h for P0 |
| 13 | Weekly check-in with each early customer (first 4 weeks) | — | P0 | Ongoing | Customer support | 30-min call per clinic per week; structured feedback form; feature requests logged; NPS collected |
| 14 | Set up customer success metrics tracking | — | P1 | 1d | Production analytics | Monthly Active Users per tenant; clinical records created/week; odontogram update rate; voice session adoption (AI Voice add-on); payment conversion rate (free to paid) |
| 15 | Post-launch blog/content marketing: "Cómo DentalOS cumple con la Resolución 1888" | — | P2 | 1d | Marketing site | Blog post in Spanish targeting dentists researching RDA compliance; SEO optimized; social share to dental Colombia LinkedIn groups |
| 16 | Monitor DIAN e-invoice acceptance rate in production (target: > 98%) | CO-06, INT-10 | P0 | Ongoing | CO-06 production | Track DIAN acceptance vs rejection rate; rejected invoices trigger alert; common rejection reasons documented and fixed |
| 17 | Week 2: collect NPS from all beta clinics now on production | — | P1 | 0.5d | Week 2 check-ins | NPS survey (Promoter/Passive/Detractor); target: NPS > 40 at launch; qualitative comments logged for product roadmap |
| 18 | Compile post-launch retrospective: what worked, what didn't, Mexico prep | — | P1 | 1d | Sprint 20 completion | Retrospective document; sprint velocity review; bug count by sprint; beta feedback resolution rate; Mexico expansion requirements documented |
| 19 | Activate Mexico compliance in feature flags for early Mexico prospects | AD-05, INT-05 | P2 | 0.5d | INT-05, AD-05 | Feature flag `mexico_billing` enabled for opted-in tenants; CFDI adapter live; CURP validation active |
| 20 | Document Mexico expansion requirements based on beta learnings | — | P2 | 1d | Sprint 20 retrospective | List of Mexico-specific requirements from Colombia beta: regulatory gaps, UX differences, SAT CFDI edge cases, NOM-024 compliance gaps |

**Sprint 20 total estimate: ~18 days of engineering work (2 engineers × 2 weeks) + ongoing operations**

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Beta clinic recruitment fails (insufficient candidates found before Sprint 17) | High | Begin recruiting at end of Sprint 13 (month 7). Use personal network, dental association contacts, LinkedIn outreach. Minimum 2 beta clinics is acceptable; 3-5 is target. Offer free Pro plan for 6 months as incentive. |
| Production data migration from beta corrupts data | Critical | Dump beta DB → restore to staging → validate → restore to production. Test migration script twice before go-live. Keep beta environment running for 2 weeks post-launch as backup. |
| DIAN electronic invoicing rejected in production (different from sandbox behavior) | High | Use MATIAS production sandbox for 2 weeks before launch. Generate 10 test invoices with real clinic credentials before migration. MATIAS support contact on speed dial. |
| Load tests reveal architectural bottlenecks requiring major changes | High | If p95 > 500ms at 500 concurrent users, escalate to: read replicas, index additions, connection pool tuning. Major architectural changes (e.g., switching databases) are out of scope — optimize within current architecture. |
| P0 security vulnerability found in security audit | Critical | Halt launch until fixed. No launch with critical or high OWASP findings. Medium findings are acceptable if documented and scheduled for Sprint 19 remediation. |
| WhatsApp Business API revoked or template rejected | Medium | All notification flows designed with email as primary channel. WhatsApp is enhancement. If WhatsApp fails, switch to SMS (Twilio) as secondary. No hard dependency on WhatsApp for core workflows. |
| Payment gateway integration issues at launch (payments failing) | Medium | Payment gateway is opt-in (not required for core workflow). Clinics can launch without payment gateway; use manual payment recording (B-07) with bank transfer. Activate Mercado Pago gradually post-launch. |
| Marketing site SEO takes time (organic traffic not immediate) | Low | SEO is a 3-6 month play. Launch requires: outbound sales to existing networks, dental association partnerships, referral from beta clinics. Paid Google Ads budgeted for first 30 days. |
| Colombia regulatory landscape change (RIPS format or deadline extension) | Medium | Monitor MinSalud communications weekly. RIPS format is well-established; minor changes are common. Architecture (country adapter + separate validation step) makes format updates isolated to the compliance module. |

---

## Beta Onboarding Checklist

Each beta clinic receives the following before going live:

- [ ] Tenant provisioned with production-equivalent settings
- [ ] Clinic owner user created and invited
- [ ] Onboarding wizard completed (clinic info, first doctor, odontogram config)
- [ ] Existing patients imported from CSV (if provided)
- [ ] Demo walkthrough: appointments, odontogram, clinical records, invoicing
- [ ] WhatsApp reminder templates approved (for their Meta Business account)
- [ ] DIAN e-invoicing: NIT and MATIAS credentials configured
- [ ] Beta feedback channel established (WhatsApp group or Slack)
- [ ] Weekly check-in schedule agreed

---

## Definition of Done

- [ ] Zero P0 critical or security vulnerabilities from audit
- [ ] Load test: 500 concurrent users, p95 API ≤ 200ms sustained for 30 minutes
- [ ] 3-5 active beta clinics validated production environment before launch
- [ ] All production infrastructure provisioned and validated (Hetzner)
- [ ] Monitoring: Sentry alerts, uptime monitor, business metrics dashboard all configured
- [ ] User guides written in Spanish for all 4 roles (clinic owner, doctor, receptionist, patient)
- [ ] Marketing landing page and self-service registration live
- [ ] Colombia legal review passed (RDA, RIPS, Ley 1581)
- [ ] DIAN e-invoicing in production: CUFE generated with real DIAN response
- [ ] First paying customers onboarded (target: 5+ paying clinics at launch)
- [ ] Customer support channels live (WhatsApp, email, in-app)
- [ ] Daily production monitoring routine established for weeks 1-2 post-launch

---

## Sprint 17-20 Acceptance Criteria

### Sprint 17
| Criteria | Target |
|----------|--------|
| Beta clinics | 3-5 beta clinics signed beta agreement |
| Load test | 500 concurrent users, 30 minutes, p95 ≤ 200ms |
| Security audit | Zero critical or high OWASP findings |
| Performance | p95 API < 200ms; p99 < 500ms for all CRUD endpoints |
| Tenant isolation | Cross-tenant data access impossible; verified by pen test |

### Sprint 18
| Criteria | Target |
|----------|--------|
| P0 bugs | Zero P0 issues from beta feedback remaining |
| P1 bugs | > 80% of P1 issues resolved |
| Payment gateway | Mercado Pago + PSE Colombia configured and tested |
| Uptime | 99.9% during beta period |
| Monitoring | All production alerts configured; on-call runbook tested |

### Sprint 19
| Criteria | Target |
|----------|--------|
| Production | All infrastructure provisioned and validated |
| Documentation | User guides for all 4 roles complete, in Spanish |
| Marketing site | Landing page, pricing page, registration flow live |
| Compliance | Colombia legal review passed |
| DIAN | Production CUFE generated successfully |

### Sprint 20
| Criteria | Target |
|----------|--------|
| Launch | Beta clinics migrated to production; validated |
| Customers | First paying customers onboarded (target: 5+) |
| Support | Support channels established; SLA documented |
| Monitoring | D1: 2-hour checks; W1: daily checks; W2: operational rhythm |
| Retention | > 70% of new sign-ups complete onboarding wizard |
| NPS | NPS > 40 from beta clinics at end of sprint |

---

## Post-Launch Roadmap (Sprint 21+, not in scope for M5)

The following items are tracked for post-launch iteration based on beta feedback and market response:

- AI Radiograph Analysis add-on ($20/doctor/mo) — Whisper for X-ray, computer vision model
- Mexico full launch — SAT CFDI production, NOM-024 compliance full implementation
- Telehealth add-on ($15/mo) — Video consultation via WebRTC or Whereby/Daily integration
- Marketing automation add-on ($15/mo) — Patient reactivation campaigns, birthday greetings
- Chile, Argentina, Peru compliance adapters — Country-specific RIPS equivalents
- Offline full sync — Complete Service Worker sync implementation (sprint-gated, architecture exists from I-18/I-19)
- Inventory purchase orders and supplier management — Post-MVP scope
- AI Voice accuracy improvements — Active learning from correction feedback (V-05 data)
- Multi-location chains — Enterprise plan; shared patient records across locations

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial backlog — Beta + Launch M5 (Sprints 17-20) |
