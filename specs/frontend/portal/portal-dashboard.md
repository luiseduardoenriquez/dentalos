# Inicio — Portal del Paciente (Portal Dashboard) — Frontend Spec

## Overview

**Screen:** Patient portal home screen. Shows cards for: next appointment (with confirm button), active treatment plans (with progress bar), unread messages badge, pending consent forms, and outstanding balance. Uses plain, non-clinical language accessible to all patients.

**Route:** `/portal/[clinicSlug]/dashboard`

**Priority:** High

**Backend Specs:** `specs/portal/PP-02.md`

**Dependencies:** `specs/frontend/portal/portal-login.md`, `specs/frontend/portal/portal-appointments.md`, `specs/frontend/portal/portal-treatment-plans.md`

---

## User Flow

**Entry Points:**
- Redirect from successful portal login
- "Inicio" in portal navigation bar

**Exit Points:**
- "Ver cita" → `/portal/[clinicSlug]/appointments`
- "Ver plan" → `/portal/[clinicSlug]/treatment-plans`
- "Ver mensajes" → `/portal/[clinicSlug]/messages`
- "Firmar" → `/portal/[clinicSlug]/consents/{id}`
- "Ver estado de cuenta" → `/portal/[clinicSlug]/invoices`
- "Agendar nueva cita" → `/portal/[clinicSlug]/book` (public booking)

**User Story:**
> As a patient, I want to see a summary of my pending actions and upcoming appointment when I open the portal so that I never miss an appointment or forget to sign documents.

**Roles with access:** patient (authenticated in portal)

---

## Layout Structure

```
+------------------------------------------+
|  [Logo]  Mi portal de salud    [Menú]    |
+------------------------------------------+
|                                           |
|  Hola, Ana 👋                             |
|  {clinicName}                             |
|                                           |
|  [PRÓXIMA CITA]                           |
|  Martes 3 de marzo • 10:00 AM            |
|  Dr. Carlos López — Revisión General      |
|  [Confirmar asistencia]  [Ver cita]       |
|                                           |
|  [Plan de Tratamiento]  [Mensajes (3)]   |
|  2 procedimientos       Sin leer          |
|  pendientes                               |
|  ████████░░ 60%                           |
|                                           |
|  [Documentos por firmar]  [Mi cuenta]    |
|  1 consentimiento         Saldo: $80.000  |
|  pendiente                                |
|                                           |
|  [Agendar nueva cita]                     |
+------------------------------------------+
```

**Sections:**
1. Portal navigation — clinic logo, "Mi portal de salud" title, hamburger menu
2. Greeting — personalized "Hola, {firstName}" with clinic name
3. Next appointment card — prominent card with date, time, doctor, type, confirm + view buttons
4. Secondary action cards — 2×2 grid: treatment plan, messages, pending documents, account balance
5. CTA button — "Agendar nueva cita" (always visible)

---

## UI Components

### Component 1: PortalNavbar

**Type:** Mobile-first top navigation bar

**Content:**
- Left: clinic logo (small, 32px) + clinic name (truncated)
- Center: "Mi portal de salud" (hidden on mobile)
- Right: hamburger menu icon (opens side drawer)

**Drawer navigation items:**
- Inicio
- Mis citas
- Mi plan de tratamiento
- Documentos
- Mis mensajes
- Mi cuenta
- Cerrar sesión

**Styling:** Background: `bg-white border-b border-gray-100`. Primary color on active item.

### Component 2: NextAppointmentCard

**Type:** Large prominent card

**States:**
1. **Has upcoming appointment:** Shows date/time (localized to es-419), doctor name, appointment type. "Confirmar asistencia" button (primary, if not yet confirmed). "Ver cita" link.
2. **No upcoming appointment:** Shows "No tienes citas programadas." with "Agendar cita" CTA.
3. **Appointment today:** Shows pulsing orange dot + "Tu cita es HOY a las 10:00 AM".

**Confirm attendance:**
- PATCH `/api/v1/portal/appointments/{id}/confirm`
- On success: button changes to "✓ Asistencia confirmada" (disabled, green)

### Component 3: TreatmentPlanCard

**Type:** Summary card with progress bar

**Content:**
- "Plan de Tratamiento" title
- Active plan name (if any): e.g., "Ortodoncia completa"
- Progress: "3 de 8 procedimientos completados"
- Progress bar: `bg-primary-500` fill on `bg-gray-200` track
- "Ver plan" link button

**No active plan state:** "Sin plan activo. Consulta con tu doctor."

### Component 4: MessagesCard

**Type:** Summary card with unread badge

**Content:**
- "Mensajes" title
- Unread count badge (red): "3 sin leer" or "Todo al día ✓" (green)
- Latest message preview (1 line, truncated): "Dr. López: Tu próxima cita es..."
- "Ver mensajes" link

### Component 5: PendingDocumentsCard

**Type:** Summary card with action

**Content:**
- "Documentos por firmar" title
- Pending consent count: "1 consentimiento pendiente" (orange badge)
- "Firmar ahora" button → consent form
- If 0 pending: "Sin documentos pendientes ✓" (green)

### Component 6: AccountBalanceCard

**Type:** Summary card

**Content:**
- "Mi cuenta" title
- Outstanding balance: "$80.000" in red if > 0, "Al día ✓" in green if $0
- "Ver estado de cuenta" link

### Component 7: BookAppointmentCTA

**Type:** Full-width button (primary)

**Label:** "Agendar nueva cita"

**Route:** `/portal/[clinicSlug]/book`

---

## Form Fields

Not applicable — dashboard is informational. Appointment confirmation is a single-action button (no form).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Dashboard summary | `/api/v1/portal/dashboard` | GET | `specs/portal/PP-02.md` | 2min |
| Confirm appointment | `/api/v1/portal/appointments/{id}/confirm` | PATCH | `specs/portal/PP-08.md` | — |

**Dashboard response shape:**
```json
{
  "patient": { "first_name": "Ana", "last_name": "López" },
  "next_appointment": { "id": "...", "date": "...", "time": "...", "doctor": "...", "type": "...", "confirmed": false },
  "active_treatment_plan": { "name": "...", "total": 8, "completed": 3 },
  "unread_messages": 3,
  "pending_consents": 1,
  "outstanding_balance": 80000
}
```

### State Management

**Local State (useState):**
- `confirming: boolean` — appointment confirm in progress

**Global State (Zustand):**
- `portalStore.patient` — authenticated patient data

**Server State (TanStack Query):**
- Query key: `['portal-dashboard', patientId, clinicSlug]` — stale 2 minutes
- Auto-refresh every 5 minutes (portal patients leave tab open)
- Mutation: `confirmAppointment` — optimistic update on button state

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Confirmar asistencia" | Button click | PATCH confirm | Button spinner → changes to "✓ Asistencia confirmada" |
| Click "Ver cita" | Link | Navigate to appointments | Standard navigation |
| Click "Ver plan" | Link | Navigate to treatment plans | Standard navigation |
| Click "Ver mensajes" | Link | Navigate to messages | Standard navigation |
| Click "Firmar ahora" | Button | Navigate to pending consent | Standard navigation |
| Click "Ver estado de cuenta" | Link | Navigate to invoices | Standard navigation |
| Click "Agendar nueva cita" | Button | Navigate to public booking | Standard navigation |
| Click hamburger | Icon | Open navigation drawer | Drawer slides from right |

### Animations/Transitions

- Page load: cards stagger fade in (100ms each, 50ms delay between)
- Appointment confirmation: button animates from primary to green (300ms)
- Unread badge: subtle pulse animation (CSS pulse, 2s loop)
- "Hoy" indicator: pulsing orange dot (CSS animation)

---

## Loading & Error States

### Loading State
- Full dashboard: skeleton cards in each section position
- Next appointment card: large skeleton (3 lines + 2 button skeletons)
- Summary cards: 4 skeleton cards in 2×2 grid

### Error State
- Dashboard load failure: error card "No pudimos cargar tu información. Intenta de nuevo." with retry button
- Confirm attendance failure: button reverts to original state + toast "No se pudo confirmar. Intenta de nuevo."

### Empty State
- No upcoming appointment: card shows "No tienes citas programadas" with "Agendar cita" button
- All secondary cards with zero counts: green "Todo al día ✓" state

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-screen, single column. All cards stack vertically. "Agendar nueva cita" pinned above bottom navigation. Navigation via hamburger drawer. |
| Tablet (640-1024px) | 2-column grid for secondary cards. Next appointment card full width. |
| Desktop (> 1024px) | Portal stays single-column max-width 640px (portal is designed for patients, primarily mobile). Left sidebar navigation replaces hamburger. |

---

## Accessibility

- **Focus order:** Navbar → greeting → next appointment card (confirm button, view link) → treatment plan → messages → documents → balance → book CTA
- **Screen reader:** `aria-live="polite"` on unread messages count. "Confirmar asistencia" button has `aria-busy` during loading. Balance card has `aria-label="Saldo pendiente: $80.000 pesos colombianos"`.
- **Keyboard navigation:** Tab through all interactive elements. Enter on all buttons/links.
- **Color contrast:** Red balance and orange counts meet WCAG AA. Green "Al día" text meets contrast.
- **Language:** Non-clinical language throughout. "Plan de tratamiento" not "odontograma". "Cuenta" not "factura". es-419.

---

## Design Tokens

**Colors (portal branded):**
- Navbar: `bg-white border-b` with clinic primary color on active items
- Next appointment card: prominent `bg-primary-50 border border-primary-200 rounded-2xl`
- Secondary cards: `bg-white border border-gray-100 rounded-xl`
- Unread badge: `bg-red-500 text-white rounded-full`
- Pending documents badge: `bg-orange-500 text-white rounded-full`
- Balance positive (owed): `text-red-600 font-bold`
- Balance zero: `text-green-600 font-semibold`
- Today indicator dot: `bg-orange-400 animate-pulse`

**Typography:**
- Greeting: `text-2xl font-bold text-gray-900`
- Card titles: `text-sm font-semibold text-gray-500 uppercase tracking-wide`
- Next appointment date: `text-lg font-bold text-gray-900`
- Doctor name: `text-base text-gray-700`
- Progress bar label: `text-sm text-gray-500`
- Balance amount: `text-xl font-bold`

**Spacing:**
- Page padding: `px-4 py-6`
- Between sections: `space-y-4`
- Card grid gap: `gap-4`
- Card internal padding: `p-4`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — dashboard data
- `lucide-react` — Calendar, MessageCircle, FileText, CreditCard, Plus, CheckCircle
- `framer-motion` — stagger card animation
- `date-fns` — appointment date formatting with es locale

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/dashboard/page.tsx`
- Components: `src/components/portal/NextAppointmentCard.tsx`, `src/components/portal/TreatmentPlanCard.tsx`, `src/components/portal/MessagesCard.tsx`, `src/components/portal/PendingDocumentsCard.tsx`, `src/components/portal/AccountBalanceCard.tsx`, `src/components/portal/PortalNavbar.tsx`
- Hooks: `src/hooks/usePortalDashboard.ts`, `src/hooks/useConfirmAppointment.ts`
- API: `src/lib/api/portal.ts`

**Hooks Used:**
- `usePortalAuth()` — patient session
- `useQuery(['portal-dashboard', ...])` — dashboard data
- `useMutation(confirmAppointment)` — with optimistic update

---

## Test Cases

### Happy Path
1. Patient with upcoming appointment
   - **Given:** Ana has cita on March 3 at 10:00 AM, not yet confirmed
   - **When:** Portal dashboard loads
   - **Then:** Large card shows "Martes 3 de marzo • 10:00 AM", "Confirmar asistencia" button visible

2. Confirm appointment attendance
   - **Given:** Next appointment card shown with confirm button
   - **When:** Patient taps "Confirmar asistencia"
   - **Then:** Button changes to "✓ Asistencia confirmada" (green, disabled). Toast: "Asistencia confirmada."

### Edge Cases
1. Today's appointment
   - **Given:** Appointment is today at 15:00
   - **When:** Dashboard loads
   - **Then:** Card shows pulsing orange dot + "Tu cita es HOY a las 3:00 PM"

2. All zeros (new patient, no activity)
   - **Given:** Patient just created, no appointments, plan, messages, or balance
   - **When:** Dashboard loads
   - **Then:** All secondary cards show "Al día ✓" or "Sin datos". "Agendar nueva cita" CTA prominent.

### Error Cases
1. Appointment confirm fails
   - **Given:** Network error during confirm
   - **When:** Patient taps confirm
   - **Then:** Button reverts to "Confirmar asistencia". Toast: "No se pudo confirmar. Intenta de nuevo."

---

## Acceptance Criteria

- [ ] Clinic logo + name in portal navbar
- [ ] Personalized greeting: "Hola, {firstName}"
- [ ] Next appointment card: date/time, doctor, type, confirm button, "Ver cita" link
- [ ] Appointment confirmation: PATCH → button state change → toast
- [ ] Today indicator on same-day appointment
- [ ] No upcoming appointment state with "Agendar cita" CTA
- [ ] Treatment plan card: plan name, progress bar, "X de Y completados", "Ver plan" link
- [ ] Messages card: unread count badge, last message preview, "Ver mensajes" link
- [ ] Pending documents card: count with orange badge, "Firmar ahora" button
- [ ] Account balance card: amount (red if >0, green if 0), "Ver estado de cuenta" link
- [ ] "Agendar nueva cita" CTA always visible
- [ ] Loading skeletons for all cards
- [ ] Error state with retry
- [ ] Dashboard data auto-refreshes every 5 minutes
- [ ] Non-clinical language throughout
- [ ] Responsive: single column mobile, portal-width desktop
- [ ] Accessibility: focus order, aria-live, keyboard navigation
- [ ] Spanish (es-419) labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
