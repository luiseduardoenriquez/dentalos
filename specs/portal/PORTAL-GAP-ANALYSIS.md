# Patient Portal — Gap Analysis & Value-Add Features

**Date:** 2026-03-12
**Scope:** 16 pages, 24 endpoints, 1 layout
**Status:** Implementation in progress

---

## Gaps (Bugs / Stubs)

| ID | Title | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| G1 | Postop Instructions Stub | High | [x] Fixed | `GET /portal/postop` returned hardcoded `{"items": [], "total": 0}`. Created `postop_instructions` model + migration + wired endpoint. |
| G2 | Digital Signatures Not Stored | High | [x] Fixed | `approve_treatment_plan` and `sign_consent` received `signature_data` but never called `digital_signature_service.create_signature()`. Now wired. |
| G3 | Clinic Notifications Missing | Medium | [x] Fixed | 6 write actions had `# TODO: Dispatch notification to clinic` — all now dispatch via `notification_dispatch.py`. |
| G4 | Magic Link Never Sent | High | [x] Fixed | Token generated and stored in Redis but never dispatched via email/WhatsApp. Now publishes to RabbitMQ `notifications` queue. |
| G5 | Public Booking Empty Doctors | Medium | [x] Fixed | `GET /public/booking/{slug}` returned `doctors: []` and only 2 hardcoded types. Now queries tenant schema for active doctors and returns all 4 types. |
| G7 | Video Page Wrong API Client | Medium | [x] Fixed | `/portal/video/[sessionId]` imported `apiGet` (staff JWT) instead of `portalApiGet`. |
| G8 | Invoices Missing Pay Button | Low | [x] Fixed | Invoice list had no link to the existing pay page at `/portal/invoices/[id]/pay`. Added "Pagar ahora" button for unpaid invoices. |

---

## Value-Add Features

| ID | Title | Impact | Status | Description |
|----|-------|--------|--------|-------------|
| V1 | Patient Profile Edit | High | [x] Done | `PUT /portal/me` — patients can update phone, email, address, emergency contact. Excludes regulatory fields (document_number, names). New profile page + nav item. |
| V2 | Notification Preferences | High | [x] Done | `GET/PUT /portal/notifications/preferences` — patients can opt in/out of email, WhatsApp, SMS per event type. Stored in `patient.metadata["notification_preferences"]`. New settings page + nav item. |
| V3 | Appointment Rescheduling | Medium-High | [x] Done | `POST /portal/appointments/{id}/reschedule` — atomic reschedule (validate new slot → create new → cancel old). "Reagendar" button with date/time picker. |
| V4 | Patient Document Upload | Medium | [x] Done | `POST /portal/documents` — patients upload X-rays, insurance cards, IDs. Max 10MB, types: JPEG/PNG/PDF. S3 storage with `source=patient` flag. |
| V5 | Odontogram History Timeline | Medium | [x] Done | `GET /portal/odontogram/history` — patients see how teeth changed over time via `odontogram_snapshots` table. Timeline selector on odontogram page. |

---

## Files Modified / Created

### Backend
- **Created:** `backend/app/models/tenant/postop_instruction.py`
- **Created:** `backend/alembic_tenant/versions/018_postop_instructions.py`
- **Modified:** `backend/app/services/portal_data_service.py` — G1, V1, V2, V5
- **Modified:** `backend/app/services/portal_action_service.py` — G2, G3, V3, V4
- **Modified:** `backend/app/services/portal_auth_service.py` — G4
- **Modified:** `backend/app/api/v1/portal/data_router.py` — G1, V1, V2, V5
- **Modified:** `backend/app/api/v1/portal/action_router.py` — V3, V4
- **Modified:** `backend/app/api/v1/appointments/public_router.py` — G5
- **Modified:** `backend/app/schemas/portal.py` — G1, V1, V2, V3, V4, V5
- **Modified:** `backend/app/schemas/appointment.py` — G5

### Frontend
- **Modified:** `frontend/app/portal/video/[sessionId]/page.tsx` — G7
- **Modified:** `frontend/app/portal/invoices/page.tsx` — G8
- **Modified:** `frontend/app/portal/appointments/page.tsx` — V3
- **Modified:** `frontend/app/portal/odontogram/page.tsx` — V5
- **Modified:** `frontend/app/portal/layout.tsx` — V1, V2 nav items
- **Modified:** `frontend/lib/hooks/use-portal.ts` — G1, V1, V2, V3, V4, V5
- **Created:** `frontend/app/portal/profile/page.tsx` — V1
- **Created:** `frontend/app/portal/notifications/page.tsx` — V2
- **Modified:** `frontend/app/portal/documents/page.tsx` — V4

---

## Priority Matrix

```
         HIGH IMPACT
            │
     V1 ●   │   ● G2
     V2 ●   │   ● G4
            │   ● G1
     V3 ●   │   ● G3
            │
  LOW ──────┼────── HIGH URGENCY
            │
     V5 ●   │   ● G5
     V4 ●   │   ● G7
            │   ● G8
         LOW IMPACT
```

---

## Implementation Order

| Wave | Items | Priority |
|------|-------|----------|
| 1 | G1, G2, G3, G4 | Critical backend fixes |
| 2 | G7, G8 | Frontend quick fixes |
| 3 | G5 | Public booking fix |
| 4 | V1, V2, V3, V4, V5 | Value-add features |
