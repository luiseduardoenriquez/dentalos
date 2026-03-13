# Portal Phase 2 — 13 New Features

**Status:** In Progress
**Started:** 2026-03-12

Portal has 17 pages, 29 endpoints, 19 hooks — core flows complete.
Phase 1 fixed 8 gaps + 5 value-adds. Phase 2 adds 13 features for competitive parity.

---

## Wave 1: Frontend-Only (Backend Exists)

- [x] **F1. Membership Page** — `frontend/app/portal/membership/page.tsx`
  - Shows plan name, benefits, billing date, cancel-request button
  - Endpoints exist: `GET /portal/membership`, `POST /portal/membership/cancel-request`

- [x] **F2. Clinic Branding Fix** — service + layout
  - `portal_data_service.get_profile()` populates logo_url, phone, address from Tenant
  - Layout shows clinic logo when available

- [x] **F3. Dashboard Enrichment** — `frontend/app/portal/dashboard/page.tsx`
  - Unread messages count, outstanding balance highlight, confirm attendance button
  - Treatment plan progress summary, auto-refresh (5 min)

## Wave 2: New Portal Pages for Existing Backend Services

- [x] **F4. Portal Intake Form** — `frontend/app/portal/intake/page.tsx`
  - `GET /portal/intake/form` returns intake config
  - Dynamic form builder, skips identity section (patient authenticated)

- [x] **F5. Chatbot Widget** — `frontend/components/portal/ChatbotWidget.tsx`
  - Floating chat button in portal layout, calls `POST /public/{slug}/chatbot/message`
  - No auth needed, auto-generates session_id

- [x] **F6. Survey History** — `frontend/app/portal/surveys/page.tsx`
  - `GET /portal/surveys` returns patient's NPS/CSAT responses
  - List with scores, comments, dates

## Wave 3: New Portal Endpoints for Existing Staff Services

- [x] **F7. Financing Tracker** — `frontend/app/portal/financing/page.tsx`
  - `GET /portal/financing` returns patient's financing applications
  - Status, provider, amount, installments, timeline

- [x] **F8. Family Billing View** — `frontend/app/portal/family/page.tsx`
  - `GET /portal/family` returns family group + billing summary
  - Members list, relationship badges, consolidated billing

- [x] **F9. Lab Order Tracking** — `frontend/app/portal/lab-orders/page.tsx`
  - `GET /portal/lab-orders` returns patient's lab orders
  - Status timeline: pending→sent→in_progress→ready→delivered

- [x] **F10. Tooth Photos Gallery** — `frontend/app/portal/photos/page.tsx`
  - `GET /portal/photos` returns tooth photos grouped by tooth number
  - Gallery with lightbox, date captions

## Wave 4: Enhanced Features

- [x] **F11. Health History Update** — `frontend/app/portal/health/page.tsx`
  - `GET /portal/health-history` + `PUT /portal/health-history`
  - Editable form: allergies, medications, conditions, surgeries

- [x] **F12. Financing Calculator** — embedded in treatment-plans page
  - `POST /portal/financing/simulate` accepts amount + provider
  - Inline calculator showing Addi/Sistecrédito options

- [x] **F13. Before/After Timeline** — `frontend/app/portal/timeline/page.tsx`
  - `GET /portal/treatment-timeline` combines procedures + photos
  - Vertical timeline with procedure cards, photo thumbnails

---

## Summary

| Wave | Features | New Pages | New Endpoints | Status |
|------|----------|-----------|---------------|--------|
| 1 | F1, F2, F3 | 1 | 0 (fix existing) | Done |
| 2 | F4, F5, F6 | 3 | 2 | Done |
| 3 | F7, F8, F9, F10 | 4 | 4 | Done |
| 4 | F11, F12, F13 | 2 | 4 | Done |

**Total: 10 new pages + ~10 new endpoints + 1 embedded widget + enriched dashboard**
