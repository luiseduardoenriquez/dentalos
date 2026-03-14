# DentalOS AI Strategy — "IA es el Core"

## Vision

DentalOS will be the **most AI-native dental platform in LATAM**. While competitors bolt AI features onto legacy software, DentalOS is built AI-first: every clinical workflow has an AI layer that makes it faster, smarter, and safer than paper.

**North Star:** "Si no es más rápido que el papel, fallamos — y la IA es lo que nos hace 10x más rápidos."

---

## Competitive Landscape

### Dentalink AI Features (7 total)

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 1 | **Análisis de RX** | Auto radiograph analysis, lesion detection | Live |
| 2 | **Contact Center IA** | WhatsApp + calls + auto appointment scheduling | Live |
| 3 | **Contralor IA** | Clinical/admin workflow supervisor, task monitoring | Live |
| 4 | **Notas Clínicas** | Voice-to-structured clinical notes | Live |
| 5 | **Reportes IA** | Natural language clinic data queries | "Próximamente" |
| 6 | **Resumen Clínico** | Pre-appointment patient summary/briefing | Live |
| 7 | **Simulador de Sonrisas** | AI-generated smile projections (before/after) | Live |

### Global Leaders (US/EU Market)

| Platform | Specialty | Key Feature |
|----------|-----------|-------------|
| **Overjet** | Radiograph AI | FDA-cleared, color overlays, bone-level mm measurements |
| **Pearl** | Radiograph AI | Second Opinion real-time chairside, FDA-cleared |
| **VideaHealth** | Radiograph AI | Multi-algorithm (caries, perio, pediatric) |
| **Denti.AI** | Voice + Imaging | Voice perio charting, clinical notes, imaging |
| **VELMENI** | Unified AI | Only platform with 2D/3D imaging + voice + claims in one |
| **SmileFy** | Smile Design | AI smile projections + 3D print-ready models |
| **Diagnocat** | CBCT/3D | Automated CBCT interpretation, structured reports |
| **DentalMonitoring** | Remote Ortho | Photo-based treatment tracking, aligner monitoring |

### DentalOS Current AI Features (4 built)

| Feature | Add-on | Status | Sprint |
|---------|--------|--------|--------|
| Voice-to-Odontogram | $10/doc/mo | **DONE** | S9-10 |
| AI Treatment Advisor | $5/doc/mo | **DONE** | S27-28 |
| AI Natural Language Reports | Pro+ plan | **DONE** | S27-28 |
| AI Virtual Receptionist (Chatbot) | Pro+ plan | **DONE** | S29-30 |

---

## Gap Analysis: DentalOS vs Dentalink

| Dentalink Feature | DentalOS Equivalent | Status | Action |
|-------------------|---------------------|--------|--------|
| Análisis de RX | AI Radiograph Analysis (planned) | **GAP** | Build — Tier 1 |
| Contact Center IA | Chatbot + WhatsApp + VoIP (separate) | **PARTIAL** | Unify — Tier 2 |
| Contralor IA | Workflow Compliance Monitor (GAP-15) | **PARTIAL** | Enhance — Tier 2 |
| Notas Clínicas (voice) | Voice-to-Odontogram only | **GAP** | Extend to evolution notes — Tier 1 |
| Reportes IA | AI Reports (DONE) | **ADVANTAGE** | Already ahead |
| Resumen Clínico | Not built | **GAP** | Build — Tier 1 |
| Simulador de Sonrisas | Not built | **GAP** | Build — Tier 2 |

### DentalOS Exclusive Advantages (Dentalink doesn't have)

1. **AI Treatment Advisor** — Suggests treatment plans based on conditions + CUPS codes
2. **Voice-to-Odontogram** — More specific than generic "voice notes" — maps to FDI teeth
3. **AI Reports (already live)** — Dentalink says "Próximamente", we already have it
4. **Template-selector security** — Claude never generates SQL (Dentalink security unknown)

---

## AI Feature Roadmap

### Tier 1 — Competitive Parity + Must-Have (Sprint 35-36)

Features that close the gap with Dentalink. Without these, we lose deals.

| # | Feature | Code | Add-on/Plan | Priority |
|---|---------|------|-------------|----------|
| AI-01 | AI Radiograph Analysis | `ai_radiograph` | $20/doc/mo | **Critical** |
| AI-02 | AI Clinical Summary | `ai_clinical_summary` | Pro+ plan | **Critical** |
| AI-03 | AI Voice Clinical Notes | `ai_voice_notes` | $10/doc/mo (bundled with Voice) | **Critical** |

### Tier 2 — Differentiation (Sprint 37-38)

Features that make us better than Dentalink. These win deals.

| # | Feature | Code | Add-on/Plan | Priority |
|---|---------|------|-------------|----------|
| AI-04 | AI Smile Simulator | `ai_smile_sim` | $20/doc/mo (bundled with Radiograph) | **High** |
| AI-05 | AI Contact Center (Unified) | `ai_contact_center` | $25/location/mo | **High** |
| AI-06 | AI Workflow Supervisor (Enhanced) | `ai_workflow_supervisor` | Clinica+ plan | **High** |

### Tier 3 — Leapfrog (Sprint 39-40)

Features that don't exist in any LATAM competitor. These create moat.

| # | Feature | Code | Add-on/Plan | Priority |
|---|---------|------|-------------|----------|
| AI-07 | AI Voice Perio Charting | `ai_voice_perio` | $10/doc/mo (bundled) | **Medium** |
| AI-08 | AI Treatment Acceptance Predictor | `ai_acceptance` | Clinica+ plan | **Medium** |
| AI-09 | AI Patient Risk Score | `ai_risk_score` | Pro+ plan | **Medium** |
| AI-10 | AI Smart Scheduling | `ai_smart_schedule` | Clinica+ plan | **Medium** |
| AI-11 | AI Revenue Optimizer | `ai_revenue` | Enterprise | **Low** |
| AI-12 | AI Radiograph Overlay (Visual) | `ai_radiograph_overlay` | $20/doc/mo (bundled) | **Medium** |

---

## Tier 1 Feature Summaries

### AI-01: AI Radiograph Analysis

**What:** Upload a dental radiograph → AI identifies findings (caries, bone loss, periapical lesions, restorations, impacted teeth, etc.) → Doctor reviews/accepts/rejects each finding → Findings link to patient record.

**How it's better than Dentalink:**
- **FDI tooth mapping** — Each finding mapped to specific tooth (FDI notation), not just "area detected"
- **Severity scoring** — Low/medium/high/critical per finding
- **Treatment suggestion link** — Each finding can auto-create a diagnosis + suggest treatment plan items (ties into AI Treatment Advisor)
- **Structured JSONB output** — Queryable findings for analytics
- **Overlay visualization (Tier 3 upgrade)** — Color-coded overlays on the radiograph image

**Architecture:** Async via RabbitMQ (Claude Vision 15-30s). Adapter pattern (Claude MVP → future: self-hosted/Overjet API). Patient polls for completion.

**Spec:** `specs/ai/radiograph-analysis.md`

### AI-02: AI Clinical Summary

**What:** Before a patient appointment, AI generates a comprehensive briefing: active conditions, pending treatments, last visit summary, allergies/alerts, outstanding balance, upcoming procedures. One-click view for the doctor.

**How it's better than Dentalink:**
- **Appointment-context aware** — Summary tailored to today's appointment type (e.g., if it's an endodontic follow-up, emphasizes relevant tooth history)
- **Risk alerts** — Flags drug interactions, allergies relevant to planned procedure
- **Action suggestions** — "Patient has 3 pending treatment items, consider discussing"
- **Multi-source aggregation** — Pulls from odontogram, diagnoses, treatment plans, billing, appointments, evolution notes, lab orders, medications

**Architecture:** Sync call (cached 5 min). Template-based prompt with patient data injection. No PHI in logs.

**Spec:** `specs/ai/clinical-summary.md`

### AI-03: AI Voice Clinical Notes

**What:** Doctor dictates during/after consultation → AI structures into a proper evolution note with sections: subjective, objective, assessment, plan (SOAP format). Auto-links to diagnoses, procedures, and tooth numbers mentioned.

**How it's better than Dentalink:**
- **SOAP format structuring** — Not just transcription, but structured clinical documentation
- **Auto-linking** — Mentions of "tooth 46" auto-link to FDI 46 in odontogram
- **CIE-10/CUPS extraction** — AI identifies and validates diagnosis/procedure codes from dictation
- **Template-aware** — Respects clinic's evolution note templates
- **Bilingual** — Spanish dictation with medical terminology handling

**Architecture:** Extends existing Voice-to-Odontogram pipeline. Whisper transcription → Claude structuring → doctor review → save as evolution note.

**Spec:** `specs/ai/voice-clinical-notes.md`

---

## Tier 2 Feature Summaries

### AI-04: AI Smile Simulator

**What:** Upload a patient's smile photo → AI generates a realistic visualization of the expected result after treatment (whitening, veneers, orthodontics, implants). Used for patient education and treatment acceptance.

**How it's better than Dentalink:**
- **Treatment-type specific** — Different simulation for whitening vs veneers vs ortho
- **Before/after side-by-side** — Split-screen comparison with slider
- **Shareable via portal** — Patient can review at home, show family
- **Linked to quotation** — Attach simulation to treatment plan/quotation for acceptance flow
- **Multiple variants** — Generate 2-3 options (conservative, moderate, ideal)

**Architecture:** Async via RabbitMQ. Uses generative AI (Claude Vision for analysis + image generation API for output). Adapter pattern for future model swaps.

**Spec:** `specs/ai/smile-simulator.md`

### AI-05: AI Contact Center (Unified)

**What:** Single AI agent that handles WhatsApp, phone calls (VoIP), and web chat. Understands appointment scheduling, rescheduling, cancellation, payment reminders, and general clinic questions. Escalates to human when needed.

**How it's better than Dentalink:**
- **Unified context** — Same AI knows the patient whether they call, WhatsApp, or chat
- **Deep system integration** — Can check real-time availability, create appointments, check balances
- **Proactive outreach** — AI initiates calls/WhatsApp for confirmations, recalls, payment reminders
- **Multilingual** — Spanish + English + Portuguese (future)
- **Analytics** — Conversion tracking: inquiry → appointment → show-up

**Architecture:** Extends existing Chatbot + WhatsApp + VoIP into unified orchestration layer. New `ai_contact_center_service.py` coordinates across channels.

**Spec:** `specs/ai/contact-center.md`

### AI-06: AI Workflow Supervisor (Enhanced)

**What:** Proactively monitors all clinic workflows and alerts when something is off: unsigned consents before procedures, incomplete medical histories, overdue follow-ups, unconfirmed appointments, expired inventory, compliance gaps.

**How it's better than Dentalink:**
- **Regulatory awareness** — Knows Colombia Resolution 1888 requirements
- **Auto-remediation** — Can trigger actions (send reminder, create task, block procedure)
- **Scoring** — Clinic compliance score visible on dashboard
- **Per-doctor metrics** — Track documentation quality per provider
- **Customizable rules** — Clinic owner can add/modify workflow rules

**Architecture:** Extends existing Workflow Compliance Monitor (GAP-15). Scheduled cron + event-driven checks. Redis-cached scores.

**Spec:** `specs/ai/workflow-supervisor.md`

---

## Tier 3 Feature Summaries

### AI-07: AI Voice Perio Charting

**What:** During periodontal examination, doctor dictates probing depths per tooth/site → AI maps measurements to periodontal chart in real-time. "Tooth 16: 3, 2, 3, 4, 5, 3" → auto-fills 6 sites.

**How it beats market:** VELMENI charges premium for this. We bundle with existing Voice add-on.

**Spec:** `specs/ai/voice-perio-charting.md`

### AI-08: AI Treatment Acceptance Predictor

**What:** ML model predicts probability that a patient will accept a treatment plan based on: treatment cost, patient history, payment history, insurance status, procedure type, similar patient behavior. Shows probability score on quotation screen.

**Spec:** `specs/ai/treatment-acceptance-predictor.md`

### AI-09: AI Patient Risk Score

**What:** Composite risk score per patient: caries risk, periodontal risk, no-show risk, payment risk. Updated after each visit. Displayed on patient card. Used for prioritizing recalls and preventive interventions.

**Spec:** `specs/ai/patient-risk-score.md`

### AI-10: AI Smart Scheduling

**What:** AI suggests optimal appointment times based on: doctor preferences, procedure duration history (learned), patient no-show patterns, revenue optimization (high-value procedures in prime slots), buffer time for complex procedures.

**Spec:** `specs/ai/smart-scheduling.md`

### AI-11: AI Revenue Optimizer

**What:** Analyzes clinic data to identify revenue opportunities: unfinished treatment plans, patients due for recalls, underutilized time slots, upsell opportunities (whitening after cleaning), optimal pricing suggestions.

**Spec:** `specs/ai/revenue-optimizer.md`

### AI-12: AI Radiograph Overlay (Visual)

**What:** After radiograph analysis, renders color-coded overlays directly on the image: red=caries, yellow=bone loss, blue=restorations, green=healthy. Toggle-able per finding type. Like Overjet/Pearl but integrated into DentalOS.

**Spec:** `specs/ai/radiograph-overlay.md`

---

## Pricing Strategy

### Current Add-ons

| Add-on | Price | Features Included |
|--------|-------|-------------------|
| AI Voice | $10/doc/mo | Voice-to-Odontogram + Voice Clinical Notes + Voice Perio Charting |
| AI Radiograph | $20/doc/mo | Radiograph Analysis + Radiograph Overlay + Smile Simulator |
| AI Treatment Advisor | $5/doc/mo | Treatment suggestions from conditions |

### Proposed New Add-on

| Add-on | Price | Features Included |
|--------|-------|-------------------|
| AI Contact Center | $25/location/mo | Unified WhatsApp + VoIP + Chat AI agent |

### Plan-Included AI Features (no extra cost)

| Feature | Minimum Plan | Rationale |
|---------|-------------|-----------|
| AI Clinical Summary | Pro | Low cost (text-only), high retention value |
| AI Reports | Pro | Already shipped |
| AI Chatbot | Pro | Already shipped |
| AI Workflow Supervisor | Clinica | Multi-provider clinics benefit most |
| AI Treatment Acceptance Predictor | Clinica | Data-driven, needs volume |
| AI Patient Risk Score | Pro | Preventive care value |
| AI Smart Scheduling | Clinica | Multi-provider scheduling complexity |
| AI Revenue Optimizer | Enterprise | Business intelligence tier |

### Revenue Projections

Assuming 100 clinics, avg 3 doctors, 40% AI Voice adoption, 30% AI Radiograph adoption, 20% AI Contact Center adoption:
- AI Voice: 100 × 3 × 0.40 × $10 = **$1,200/mo**
- AI Radiograph: 100 × 3 × 0.30 × $20 = **$1,800/mo**
- AI Treatment Advisor: 100 × 3 × 0.25 × $5 = **$375/mo**
- AI Contact Center: 100 × 0.20 × $25 = **$500/mo**
- **Total AI Revenue: ~$3,875/mo ($46,500/yr)** from 100 clinics

### Cost Structure (Claude API)

| Feature | Model | Avg tokens/call | Calls/doc/day | Cost/doc/mo |
|---------|-------|-----------------|---------------|-------------|
| Radiograph Analysis | Claude Vision (Sonnet) | ~4K in + ~2K out | 3 | ~$0.90 |
| Clinical Summary | Claude Haiku | ~3K in + ~500 out | 8 | ~$0.30 |
| Voice Clinical Notes | Whisper + Claude Sonnet | ~2K in + ~1K out | 5 | ~$0.50 |
| Treatment Advisor | Claude Sonnet | ~3K in + ~1K out | 2 | ~$0.25 |
| AI Reports | Claude Sonnet | ~2K in + ~500 out | 3 | ~$0.20 |
| Smile Simulator | Claude Vision + DALL-E/Flux | ~5K in + image gen | 1 | ~$1.50 |
| Contact Center | Claude Haiku | ~1K in + ~300 out | 20 | ~$0.15 |
| **Total per doctor** | | | | **~$3.80/mo** |

**Gross margin on AI:** ~$12.75 revenue per doc vs ~$3.80 cost = **70% margin**

---

## Technical Architecture

### Shared AI Infrastructure

```
┌─────────────────────────────────────────────────────────┐
│                    AI Service Layer                       │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ ai_claude_   │  │ ai_whisper_  │  │ ai_image_    │   │
│  │ client.py    │  │ client.py    │  │ gen_client.py│   │
│  │              │  │              │  │              │   │
│  │ • call_claude│  │ • transcribe │  │ • generate   │   │
│  │ • call_vision│  │ • stream     │  │ • edit       │   │
│  │ • extract_*  │  │              │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                  │                  │           │
│  ┌──────┴──────────────────┴──────────────────┴───────┐  │
│  │              Integration Adapter Layer               │  │
│  │                                                      │  │
│  │  radiograph_analysis/  ← ABC → claude/mock/overjet  │  │
│  │  smile_simulator/      ← ABC → claude/mock/smilefy  │  │
│  │  clinical_summary/     ← ABC → claude/mock           │  │
│  │  voice_notes/          ← ABC → whisper+claude/mock   │  │
│  │  contact_center/       ← ABC → claude/mock            │  │
│  │  (existing: voice/, chatbot/, ai_treatment/)          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AI Feature Services                      │  │
│  │                                                      │  │
│  │  radiograph_analysis_service.py                      │  │
│  │  clinical_summary_service.py                          │  │
│  │  voice_clinical_notes_service.py                      │  │
│  │  smile_simulator_service.py                           │  │
│  │  contact_center_service.py                            │  │
│  │  workflow_supervisor_service.py                        │  │
│  │  (existing: ai_treatment_service, ai_report_service,  │  │
│  │   chatbot_service, voice_nlp_service)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AI Workers (RabbitMQ)                     │  │
│  │                                                      │  │
│  │  Queue: clinical                                      │  │
│  │   → radiograph.analyze                                │  │
│  │   → smile.simulate                                    │  │
│  │   → voice_notes.structure                             │  │
│  │                                                      │  │
│  │  Queue: notifications (existing)                      │  │
│  │   → contact_center.* (WhatsApp/SMS/Call)              │  │
│  │                                                      │  │
│  │  Queue: maintenance (existing)                        │  │
│  │   → workflow_supervisor.scan                          │  │
│  │   → risk_score.recalculate                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### AI-Specific Database Tables (Tenant Schema)

| Table | Feature | Key Columns |
|-------|---------|-------------|
| `radiograph_analyses` | AI-01 | patient_id, document_id, status, findings (JSONB), summary, model_used, tokens |
| `clinical_summaries` | AI-02 | patient_id, appointment_id, summary (JSONB), generated_at, cached_until |
| `voice_clinical_notes` | AI-03 | patient_id, session_id, transcription, structured_note (JSONB), status |
| `smile_simulations` | AI-04 | patient_id, original_image_url, result_images (JSONB), treatment_type, status |
| `contact_center_conversations` | AI-05 | patient_id, channel, messages (JSONB), outcome, escalated |
| `ai_usage_logs` | All | tenant_id, feature, model, input_tokens, output_tokens, cost_cents, timestamp |

### AI Usage Tracking & Billing

Every AI call logs to `ai_usage_logs` for:
- Per-tenant cost tracking
- Usage-based billing alerts (approaching limit)
- Model performance monitoring
- A/B testing different models/prompts

### Feature Flag Integration

All AI features gated by feature flags (existing `AD-05` system):

```json
{
  "ai_radiograph": { "category": "ai", "default": false },
  "ai_clinical_summary": { "category": "ai", "default": false },
  "ai_voice_notes": { "category": "ai", "default": false },
  "ai_smile_sim": { "category": "ai", "default": false },
  "ai_contact_center": { "category": "ai", "default": false },
  "ai_workflow_supervisor": { "category": "ai", "default": false },
  "ai_voice_perio": { "category": "ai", "default": false },
  "ai_acceptance_predictor": { "category": "ai", "default": false },
  "ai_risk_score": { "category": "ai", "default": false },
  "ai_smart_schedule": { "category": "ai", "default": false }
}
```

---

## Security & Compliance

### PHI Rules for AI Features

1. **Never send full patient name or document number to AI** — Use anonymized identifiers
2. **Radiograph images:** Strip DICOM metadata (patient name, DOB) before sending to Claude
3. **Clinical summaries:** Generated server-side, never cached in browser
4. **Voice recordings:** Deleted after transcription + structuring (max 24h retention)
5. **AI Usage logs:** No PHI — only token counts, model, feature, tenant_id
6. **Smile simulations:** Original photos stored in tenant-isolated S3, signed URLs only

### Regulatory Considerations

- **Colombia:** AI analysis is a "clinical decision support tool" — always requires doctor review
- **Disclaimers:** "Esta es una sugerencia de IA. El diagnóstico final es responsabilidad del profesional."
- **Audit trail:** Every AI interaction logged in audit_logs (who requested, what was generated, what was accepted/rejected)
- **Consent:** Patient informed consent for AI analysis of their images/records (can be part of general consent)

---

## Implementation Phases

### Phase 1: Sprint 35-36 — Tier 1 (Parity)
- AI-01: Radiograph Analysis (full stack)
- AI-02: Clinical Summary (full stack)
- AI-03: Voice Clinical Notes (extend existing voice pipeline)

### Phase 2: Sprint 37-38 — Tier 2 (Differentiation)
- AI-04: Smile Simulator
- AI-05: Contact Center (unified)
- AI-06: Workflow Supervisor (enhanced)

### Phase 3: Sprint 39-40 — Tier 3 (Leapfrog)
- AI-07 through AI-12 (prioritized by customer demand)

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| AI add-on adoption rate | 40% within 6 months | % of paying clinics with ≥1 AI add-on |
| Radiograph analysis accuracy | >90% sensitivity | Doctor acceptance rate of AI findings |
| Clinical summary time saved | 3 min/patient | Before/after time comparison |
| Voice notes adoption | 60% of AI Voice subscribers | % using voice notes (not just odontogram) |
| Treatment acceptance rate increase | +15% | A/B test with/without smile simulator |
| AI revenue as % of total | 25% | AI add-on revenue / total revenue |
| Patient satisfaction (AI features) | NPS > 50 | Survey after AI-assisted appointments |

---

## References

### Competitor Research
- [Dentalink AI Features](https://www.softwaredentalink.com/funcionalidades/inteligencia-artificial)
- [Dentalink AI Contact Center](https://www.softwaredentalink.com/inteligencia-artificial/contact-center)
- [Dentalink Smile Simulator](https://www.softwaredentalink.com/inteligencia-artificial/simulador-de-sonrisas)
- [Dentalink Clinical Summary](https://www.softwaredentalink.com/inteligencia-artificial/resumen-clinico)

### Market Leaders
- [Overjet - Dental AI Platform](https://www.overjet.com/)
- [Pearl - Second Opinion](https://hellopearl.com/)
- [Denti.AI - Voice + Imaging](https://www.denti.ai/)
- [VELMENI - Unified AI](https://velmeni.ai/)
- [SmileFy - Smile Design](https://smilefy.com/)
- [Diagnocat - CBCT AI](https://diagnocat.com/)

### Industry Analysis
- [Top 6 AI Dental Software 2026 (scanO)](https://scanoai.com/blog/top-6-ai-dental-software-to-watch-in-2026)
- [AI in Dentistry 2026 (Gold Coast)](https://www.goldcoastdental.com/blog/ai-and-digital-dentistry)
- [Best AI Dental Software 2025 (SoftSmile)](https://softsmile.com/blog/ai-dental-solutions/)
