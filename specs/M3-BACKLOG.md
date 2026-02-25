# M3 Operations Backlog (R-07)

> Sprint 9-12 planning document with task breakdown, estimates, and acceptance criteria.

**Version:** 1.0
**Date:** 2026-02-25
**Sprints:** 9-12
**Duration:** 8 weeks (4 sprints × 2 weeks)
**Month:** 5-6

---

## Sprint Goals

### Sprint 9: Appointments + Scheduling + Voice v1
Implement the full appointment lifecycle (AP-01 through AP-11), doctor schedule management, availability queries, and Voice-to-Odontogram v1 (V-01 through V-05). This sprint delivers the two biggest differentiators: ≤3-tap appointment booking and voice dictation. The agenda must be measurably faster than paper.

### Sprint 10: Waitlist + Public Booking + Reminders + Agenda UI
Complete waitlist management, patient self-booking (public endpoint), reminder configuration, all agenda frontend screens, and voice UI. Sprint ends with a fully functional scheduling system that a receptionist can run entirely from the calendar screen.

### Sprint 11: Billing + Notifications + Messaging + WhatsApp
Implement the full billing stack (B-01 through B-13), notification dispatch engine, in-app messaging, WhatsApp and SMS integrations, patient referral system, and patient portal access provisioning. Sprint ends with invoicing and patient communication fully operational.

### Sprint 12: Patient Portal + Billing UI + Portal UI + Integrations Polish
Complete the patient portal API (PP-01 through PP-13), all billing frontend screens, all portal frontend screens, payment gateway integration groundwork, and inter-specialist referral. Sprint ends with patients able to log in to their portal and clinics able to invoice and receive payments.

---

## Task Breakdown

### Sprint 9: Appointments + Scheduling + Voice v1

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement `POST /appointments` — create appointment with conflict validation | AP-01 | P0 | 2d | P-01, U-07 | Validates doctor schedule; blocks double-booking; appointment type auto-sets duration (eval 20min, endo 1h20, etc.) |
| 2 | Implement `GET /appointments/{id}` and `GET /appointments` — list with calendar grouping | AP-02, AP-03 | P0 | 1d | AP-01 | Filters: doctor, patient, date_range, status; returns grouped-by-date for calendar view |
| 3 | Implement `PUT /appointments/{id}` — reschedule with availability check + notification | AP-04 | P0 | 1d | AP-01 | Validates new slot; sends notification to patient if time changes |
| 4 | Implement `POST /appointments/{id}/cancel` — cancel with reason + patient notification | AP-05 | P0 | 0.5d | AP-01 | Reason required; patient notification queued; slot freed for waitlist check |
| 5 | Implement `POST /appointments/{id}/confirm`, `/complete`, `/no-show` — status transitions | AP-06, AP-07, AP-08 | P0 | 1d | AP-01, CR-01 | Complete links to clinical records; no-show increments patient counter |
| 6 | Implement `GET /users/{id}/schedule` and `PUT /users/{id}/schedule` — doctor weekly schedule | U-07, U-08 | P0 | 1.5d | U-01 | Day-of-week, start/end times, break times, appointment duration defaults per type |
| 7 | Implement `GET /appointments/availability` — available slot query | AP-09 | P0 | 1.5d | U-07, AP-01 | Params: doctor_id, date_range, duration; returns array of available time slots; respects breaks and blocked times |
| 8 | Implement `POST /appointments/availability/block` — block time slot | AP-10 | P1 | 0.5d | U-07 | Doctor or admin; creates unavailable block; reason field |
| 9 | Implement `PUT /appointments/{id}/reschedule` — quick drag-and-drop reschedule | AP-11 | P1 | 0.5d | AP-01, AP-09 | Minimal payload (new start_time, optional new doctor_id); conflict check |
| 10 | Implement Voice-to-Odontogram: `POST /voice/sessions` — start session, return presigned S3 URL | V-01 | P0 | 1d | P-01, OD-01 | Returns session_id + presigned upload URL; plan check (AI Voice add-on required); context stored |
| 11 | Implement `POST /voice/sessions/{id}/transcribe` — submit audio to Whisper API (async) | V-02 | P0 | 2d | V-01 | Uploads to S3; queues Whisper Large v3 transcription via RabbitMQ worker; raw Spanish text returned |
| 12 | Implement `GET /voice/sessions/{id}/result` — poll for Whisper + LLM parse result | V-03 | P0 | 2d | V-02 | Calls Anthropic Claude API to parse dental NLP; returns structured JSON (tooth_number FDI, zone, condition, action); status: processing/ready/failed |
| 13 | Implement `POST /voice/sessions/{id}/apply` — apply confirmed voice changes to odontogram | V-04 | P0 | 1d | V-03, OD-11 | Bulk-updates odontogram with `source: voice` flag; audit logged; review-before-apply mode enforced |
| 14 | Implement `GET/PUT /settings/voice` — voice feature configuration | V-05 | P1 | 0.5d | T-06 | Enable/disable; default language; confirmation mode (review-first default); plan gate |
| 15 | Implement `POST /voice/sessions/{id}/feedback` — correction feedback for quality tracking | V-05 | P1 | 0.5d | V-03 | Logs: correction type (tooth number wrong, condition wrong, false positive); tracked for accuracy monitoring |
| 16 | Set up OpenAI Whisper API integration + Anthropic Claude API integration | V-02, V-03 | P0 | 1d | None | API keys configured; Whisper Large v3 Spanish model; Claude prompt: extract FDI tooth numbers, zones, conditions from dental dictation |
| 17 | Design LLM prompt for dental Spanish dictation parsing | V-03 | P0 | 1d | None | Prompt extracts: tooth_number (FDI), zone (mesial/distal/vestibular/lingual/oclusal/raiz), condition (from 12 known codes); handles filler words; tested on 20 sample utterances; >90% accuracy on tooth numbers |
| 18 | Write appointment unit tests: conflict detection, status transitions, availability | I-08 | P0 | 1.5d | AP-01–AP-11 | No double-booking possible; intelligent duration: eval=20min, profilaxis=45min, endodoncia=80min |
| 19 | Write voice pipeline tests: audio → transcription → parse → apply | I-08 | P0 | 1d | V-01–V-05 | Mock Whisper/Claude APIs; parse output validated; apply creates correct odontogram conditions |

**Sprint 9 total estimate: ~23 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 10: Waitlist + Public Booking + Reminders + Agenda UI

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement waitlist: `POST /waitlist`, `GET /waitlist`, `POST /waitlist/{id}/notify` | AP-12, AP-13, AP-14 | P1 | 1.5d | P-01 | Patient added with preferred doctor/time/procedure; notification sent (WhatsApp/email) when slot opens |
| 2 | Implement `POST /public/booking/{slug}` — patient self-booking (public endpoint) | AP-15 | P1 | 1.5d | AP-09, P-01 | No auth required; creates appointment + patient record if new; conflict-safe; rate limited (5/hour per IP) |
| 3 | Implement `GET /public/booking/{slug}/config` — clinic booking page config | AP-16 | P1 | 0.5d | T-06 | Clinic name, logo, available doctors, services, business hours; publicly cached |
| 4 | Implement `GET/PUT /settings/reminders` — reminder configuration | AP-17, AP-18 | P1 | 0.5d | T-06 | Timing (24h, 2h before); channels (WhatsApp, SMS, email); per-channel templates |
| 5 | Implement appointment reminder scheduler — background job fires reminders | AP-17 | P0 | 2d | AP-01, I-06, N-05 | Cron-based; scans upcoming appointments; queues email/WhatsApp/SMS at configured intervals; idempotent (no double-sends) |
| 6 | Build FE-DS-13: calendar component (day/week/month views, event rendering, drag-and-drop) | FE-DS-13 | P0 | 3d | FE-DS-01 | Day/week/month views; events color-coded by type and status; drag-and-drop fires reschedule API; time grid |
| 7 | Build FE-AG-01: main calendar view (multi-doctor columns, daily view DEFAULT) | FE-AG-01 | P0 | 2d | AP-03, FE-DS-13 | **Daily view is the default.** Multi-doctor column view in week mode; click to create; color-coded |
| 8 | Build FE-AG-02: create appointment modal (3-tap UX, auto-duration, availability) | FE-AG-02 | P0 | 2d | AP-01 | **Whole flow completable in ≤3 taps from calendar screen.** Patient search → time slot → confirm. Appointment type auto-fills duration. Availability shown in real-time. |
| 9 | Build FE-AG-03: appointment detail modal (patient info, status, actions) | FE-AG-03 | P0 | 1d | AP-02 | Patient info; status; confirm/complete/cancel/no-show buttons; linked clinical records |
| 10 | Build FE-AG-04: doctor schedule editor (weekly template, drag to adjust) | FE-AG-04 | P1 | 1.5d | U-08 | Day-by-day start/end times; break time blocks; slot duration per type; drag to adjust |
| 11 | Build FE-AG-05: waitlist sidebar panel (waiting patients, one-click scheduling) | FE-AG-05 | P1 | 1d | AP-13 | Filterable by doctor; one-click opens create appointment modal with patient pre-filled |
| 12 | Build FE-AG-06: today's appointments view (timeline, patient status, quick actions) | FE-AG-06 | P0 | 1d | AP-03 | Timeline format; patient status (waiting/in-chair/done); quick action buttons |
| 13 | Build FE-PP-10: public booking page (clinic-branded, doctor selection, time picker) | FE-PP-10 | P1 | 1.5d | AP-15, AP-16 | No login required; clinic-branded; doctor selection; available time slots; form for contact info |
| 14 | Build FE-V-01: voice recording button (floating action, waveform animation) | FE-V-01 | P0 | 1d | V-01 | Floating button on odontogram screen; tap to start/stop; waveform animation during recording; recording indicator |
| 15 | Build FE-V-02: transcription review panel (diff over odontogram, confirm/reject) | FE-V-02 | P0 | 2d | V-03, V-04 | Parsed teeth + conditions shown as diff; each change individually confirm/reject-able; "Apply All" button; review-before-apply mode |
| 16 | Build FE-V-03: voice session history (past sessions, transcription, feedback) | FE-V-03 | P1 | 1d | V-05 | List of past sessions; transcription text; applied/rejected status; accuracy feedback form |
| 17 | Build FE-S-04: odontogram configuration settings | FE-S-04 | P1 | 0.5d | T-07 | Mode selector (classic/anatomic); default view; condition color customization |
| 18 | Build FE-S-05: notification settings (reminder timing, channels, templates) | FE-S-05 | P1 | 1d | AP-17, U-09 | Clinic-wide reminder config; per-user channel overrides; preview reminder templates |
| 19 | Email templates: E-05 through E-08 and E-18 (appointment lifecycle emails) | E-05, E-06, E-07, E-08, E-18 | P0 | 1.5d | AP-01, INT-03 | Confirmation; 24h reminder; 2h reminder; cancellation; waitlist slot available. Tested in SendGrid sandbox. |
| 20 | End-to-end test: full appointment lifecycle (create → confirm → complete → clinical record linked) | I-08 | P0 | 1d | AP-01–AP-18, FE-AG-01–06 | Full flow test; intelligent duration verified; no-double-booking verified; reminder queued in RabbitMQ |

**Sprint 10 total estimate: ~28 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 11: Billing + Notifications + Messaging + WhatsApp

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement invoice CRUD: `POST`, `GET /{id}`, `GET` (list), `PUT` draft update | B-01, B-02, B-03, B-04 | P0 | 2d | P-01, CR-12, TP-05 | Line items from procedures or treatment plan items; tax calculation per country; draft status until sent |
| 2 | Implement `POST /invoices/{id}/send` — send invoice to patient | B-05 | P0 | 0.5d | B-01, N-05 | Status → sent; email + optional WhatsApp; PDF attached or portal link |
| 3 | Implement `GET /invoices/{id}/pdf` — generate invoice PDF | B-06 | P0 | 1d | B-01 | Clinic branding; patient info; line items; tax; totals; payment instructions |
| 4 | Implement `POST /invoices/{id}/payments` — record payment (partial supported) | B-07 | P0 | 1d | B-01 | Amount, method (cash/card/transfer/insurance), date, reference; partial payment leaves balance |
| 5 | Implement `GET /patients/{id}/payments`, `GET /patients/{id}/balance` | B-08, B-09 | P0 | 0.5d | B-07 | Payment list; balance = sum(invoices) - sum(payments) |
| 6 | Implement `POST /payment-plans` + `GET /payment-plans/{id}` | B-10, B-11 | P1 | 1.5d | P-01, B-01 | Installment schedule auto-generated; frequency (weekly/biweekly/monthly); status per installment |
| 7 | Implement `GET /billing/commissions` — doctor commissions report | B-12 | P1 | 1d | CR-12, B-07 | Filter by date range; per-doctor: procedures count, revenue, commission %, amount due |
| 8 | Implement `GET /billing/summary` — billing dashboard data | B-13 | P1 | 1d | B-01, B-07 | Revenue by month/quarter/year; outstanding balance; top procedures by revenue; payment method breakdown |
| 9 | Implement notification dispatch engine — routes events to in-app/email/WhatsApp/SMS | N-05 | P0 | 2d | I-06, U-09 | Accepts event_type + recipient + data; routes per user preferences; async via RabbitMQ; fallback chain (WhatsApp → email if WhatsApp fails) |
| 10 | Implement `GET /notifications`, `POST /{id}/read`, `POST /read-all`, `GET /preferences` | N-01, N-02, N-03, N-04 | P0 | 1d | I-02, N-05 | Paginated; unread count in header; read-all clears badge; preferences per channel and event type |
| 11 | Implement `PUT /users/me/notifications` — update notification preferences | U-09 | P0 | 0.5d | U-01 | Per-event toggle (appointment reminders, new patient, etc.) per channel (email/WhatsApp/SMS/in-app) |
| 12 | INT-01: WhatsApp Business API integration — template messages, webhooks, sessions | INT-01 | P0 | 3d | I-06, N-05 | Template messages (appointment reminder, treatment plan, invoice) send successfully; incoming message webhook received; Meta Business verification documented |
| 13 | INT-02: Twilio SMS integration — appointment reminders, verification codes | INT-02 | P1 | 1d | I-06, N-05 | SMS sends in Colombia; fallback for WhatsApp failures; two-way verification code support |
| 14 | Implement patient referral: `POST/GET/PUT /patients/{id}/referrals` | P-15 | P1 | 1.5d | P-01, U-03, N-05 | Referring doctor → receiving specialist; urgency field; notification to receiving doctor on creation; status (pending/accepted/completed) |
| 15 | Implement `POST /patients/{id}/portal-access` — grant/revoke portal access | P-11 | P1 | 1d | P-01, A-09 | Sends invitation email/WhatsApp with registration link; portal access token with 72h expiry |
| 16 | Implement messaging: `POST /messages/threads`, `GET /threads`, `POST /threads/{id}/messages`, `GET /messages`, `POST /read` | MS-01, MS-02, MS-03, MS-04, MS-05 | P1 | 2d | P-01 | Thread per patient; message list paginated; mark-read per thread; clinic staff and patient-side endpoints |
| 17 | Write billing tests: invoice creation, payment recording, balance accuracy, commissions | I-08 | P0 | 1.5d | B-01–B-13 | Balance calculation correct with partial payments; commission math verified; PDF generation stable |
| 18 | Write notification dispatch tests: WhatsApp, SMS, email routing per preferences | I-08 | P0 | 1d | N-05, INT-01, INT-02 | Mock WhatsApp API; correct channel routing verified; fallback chain tested |

**Sprint 11 total estimate: ~25 days of engineering work (2 engineers × 2 weeks)**

---

### Sprint 12: Patient Portal + Billing UI + Portal UI + Integrations Polish

| # | Task | Spec Ref | Priority | Estimate | Dependencies | Acceptance Criteria |
|---|------|----------|----------|----------|--------------|---------------------|
| 1 | Implement patient portal auth: `POST /portal/auth/login` — email/phone + magic link | PP-01 | P0 | 1.5d | P-11 | Email/phone login; magic link option; portal JWT (scoped to patient, limited permissions) |
| 2 | Implement portal endpoints: `GET /portal/me`, `/appointments`, `/treatment-plans`, `plan approve` | PP-02, PP-03, PP-04, PP-05 | P0 | 2d | PP-01, AP-01, TP-01 | Patient sees only own data; treatment plan read-only + approve with digital signature |
| 3 | Implement portal endpoints: `GET /portal/invoices`, `/documents`, book/cancel appointment | PP-06, PP-07, PP-08, PP-09 | P0 | 1.5d | PP-01, B-01, P-12 | Invoice + payment history; document viewer (X-rays, consents, prescriptions); book via AP-15 flow |
| 4 | Implement portal messaging: `GET/POST /portal/messages`, `POST /portal/consents/{id}/sign`, `GET /portal/odontogram` | PP-10, PP-11, PP-12, PP-13 | P0 | 1.5d | PP-01, MS-01, IC-05, OD-01 | Message threads with clinic; consent signing from portal; odontogram read-only with legend |
| 5 | Build FE-B-01: invoice list page (table, filters, bulk actions) | FE-B-01 | P0 | 1d | B-03 | Status filter (draft/sent/paid/overdue/cancelled); date filter; bulk send action |
| 6 | Build FE-B-02: create invoice form (patient, line items, tax, total) | FE-B-02 | P0 | 1.5d | B-01 | Patient selector; line items from procedures or manual; tax shown per country; total auto-calculated |
| 7 | Build FE-B-03: invoice detail page (line items, payments, balance, PDF, send) | FE-B-03 | P0 | 1d | B-02 | Payment history; remaining balance; "Record Payment" and "Send" actions; PDF preview |
| 8 | Build FE-B-04: record payment modal (amount, method, partial support) | FE-B-04 | P0 | 0.5d | B-07 | Method selector (cash/card/transfer/insurance); reference field; partial payment flag |
| 9 | Build FE-B-05: payment plan creation and management | FE-B-05 | P1 | 1d | B-10, B-11 | Installment schedule visualized as timeline; payment status per installment |
| 10 | Build FE-B-06: service/price catalog management | FE-B-06 | P1 | 0.5d | B-14 | Table with inline price editing; clinic_owner only; CUPS code shown |
| 11 | Build FE-B-07: doctor commissions report page | FE-B-07 | P1 | 1d | B-12 | Date filter; per-doctor table; total commission column |
| 12 | Build FE-B-08: billing overview dashboard (revenue charts, aging report) | FE-B-08 | P1 | 1.5d | B-13 | Line chart for revenue trend; pie chart for payment methods; aging table (0-30, 31-60, 60+ days) |
| 13 | Build FE-PP-01 through FE-PP-03: portal login + dashboard + appointments | FE-PP-01, FE-PP-02, FE-PP-03 | P0 | 2d | PP-01, PP-02, PP-03 | Clinic-branded login; dashboard shows next appointment + pending plans; appointments with confirm/cancel |
| 14 | Build FE-PP-04 through FE-PP-06: portal treatment plans + documents + chat | FE-PP-04, FE-PP-05, FE-PP-06 | P0 | 2d | PP-04, PP-07, PP-10 | Treatment plan progress + approve with signature; document viewer (PDF + images); chat interface with clinic |
| 15 | Build FE-PP-07 through FE-PP-09: portal invoices + consent signing + odontogram | FE-PP-07, FE-PP-08, FE-PP-09 | P0 | 1.5d | PP-06, PP-12, PP-13 | Invoice + payment history; consent signing (scroll + signature pad); odontogram read-only with legend |
| 16 | Build FE-S-06: consent template management settings page | FE-S-06 | P1 | 0.5d | IC-01, IC-02 | List, create, edit, preview consent templates; clinic_owner only |
| 17 | Build FE-S-08: integrations settings (WhatsApp, Google Calendar, payment gateway) | FE-S-08 | P1 | 1d | INT-01, INT-09 | WhatsApp Business setup wizard; Google Calendar OAuth toggle; payment gateway config placeholder |
| 18 | Email templates: E-11 through E-15 (billing + portal + messaging emails) | E-11, E-12, E-13, E-14, E-15 | P0 | 1.5d | B-05, B-07, P-11, MS-03 | Invoice sent; payment received; overdue reminder; portal invite; new message notification. All tested. |
| 19 | Integration tests: WhatsApp reminder send, portal login, consent sign from portal | I-08 | P0 | 1d | PP-01–PP-13, INT-01 | Patient logs into portal; views appointment; signs consent; message received by clinic |
| 20 | Performance validation: billing summary ≤500ms; portal login ≤200ms | B-13, PP-01 | P0 | 0.5d | Sprint 11-12 backend | EXPLAIN ANALYZE; Redis caching for billing summary verified |

**Sprint 12 total estimate: ~29 days of engineering work (2 engineers × 2 weeks)**

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| WhatsApp Business API Meta approval timeline (can take 2-4 weeks) | High | Start Meta Business verification at beginning of Sprint 11. Build with email as primary channel; WhatsApp as enhancement. All notification flows must work without WhatsApp. |
| Voice transcription accuracy for dental Spanish (accents, terminology) | High | Use Whisper Large v3 (best Spanish model). Claude prompt must include all 12 condition names in Spanish + FDI notation. Review-before-apply mode prevents bad data reaching odontogram. Log correction rate from day 1. |
| OpenAI Whisper API latency for voice pipeline | Medium | Target async pipeline: submit audio → poll for result. Set user expectation: "Processing... usually 10-20 seconds." Do not block UI. |
| Patient portal security: patient can only see own data | High | Separate portal JWT with patient_id baked in. All PP-* endpoints filter strictly by authenticated patient_id. Penetration test portal isolation before Sprint 13. |
| Payment gateway integration complexity (Mercado Pago + PSE Colombia) | Medium | Defer full payment gateway to Sprint 12 frontend/config only. Real payment flows activate in Sprint 17 after security audit. Collect gateway credentials during Sprint 11. |
| Calendar drag-and-drop reliability on tablet (clinical use case) | Medium | Use a proven library (FullCalendar or similar). Test on iPad Safari specifically — common tablet for dental use. Touch events must be reliable. |
| Billing calculation correctness under Colombian tax rules (IVA exemptions on health services) | Medium | Health services (dental) are IVA-exempt in Colombia. Default tax rate = 0% for dental procedures. Document in tenant settings. Edge cases: cosmetic procedures may have tax. |

---

## Definition of Done

- [ ] All spec'd backend endpoints implemented, tested, and documented
- [ ] Appointment booking completable in ≤ 3 taps from calendar screen
- [ ] Daily view is the default calendar view (not weekly, not monthly)
- [ ] Intelligent appointment duration: type auto-fills slot length
- [ ] No double-booking possible under concurrent load
- [ ] Voice pipeline: audio → Whisper → Claude → structured JSON → review panel: full flow working
- [ ] Voice accuracy: > 90% correct tooth number extraction on test set
- [ ] Review-before-apply mode enforced: user must confirm before odontogram is written
- [ ] Invoice creation, payment recording, and balance calculation accurate
- [ ] Patient portal: patient logs in and can view appointments, sign consents, message clinic
- [ ] WhatsApp template messages send successfully for appointment reminders
- [ ] 75%+ test coverage on billing, portal, messaging, notifications
- [ ] Inter-specialist referral: doctor can create referral; receiving doctor notified

---

## Sprint 9-12 Acceptance Criteria

### Sprint 9
| Criteria | Target |
|----------|--------|
| Appointment API | AP-01 through AP-11 implemented |
| Intelligent duration | Appointment type auto-fills slot (eval 20min, endo 80min, etc.) |
| No double-booking | Concurrent booking tests pass |
| Voice pipeline | Full chain: capture → transcribe → parse → apply functional |
| Voice accuracy | > 90% correct tooth number extraction on 20-utterance test set |
| Review-before-apply | User must confirm before any odontogram change is committed |

### Sprint 10
| Criteria | Target |
|----------|--------|
| 3-tap booking | Appointment creation completable in ≤ 3 taps from calendar |
| Default view | Calendar opens to daily view |
| Waitlist | Patient added; notified when slot opens |
| Public booking | Patient self-books via public URL without login |
| Reminders | Email sends at 24h and 2h before appointment |
| Voice UI | Recording button, review panel, session history all functional |

### Sprint 11
| Criteria | Target |
|----------|--------|
| Billing | B-01 through B-13 implemented; balance calculation accurate |
| WhatsApp | Template messages send successfully |
| Notifications | Dispatch engine routes correctly per user preferences |
| Referral | Create referral; receiving doctor receives in-app notification |
| Messaging | Clinic can message patient; patient receives notification |

### Sprint 12
| Criteria | Target |
|----------|--------|
| Patient portal | Patient logs in; views appointments; signs consent; messages clinic |
| Billing UI | Full billing workflow from invoice list to payment recorded |
| Portal UI | FE-PP-01 through FE-PP-09 complete |
| Test coverage | 75%+ billing, portal, messaging, notifications |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial backlog — Operations M3 (Sprints 9-12) |
