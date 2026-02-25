# Dashboard del Doctor (Doctor Dashboard) — Frontend Spec

## Overview

**Screen:** Doctor-specific dashboard shown when authenticated user has `role = doctor`. Compact, action-oriented layout with 5 widgets: today's appointments timeline, next appointment countdown, patient count this week, recent procedures, and monthly revenue (if commissions enabled). Prioritizes at-a-glance clinical information over administrative data.

**Route:** `/dashboard` (conditional render based on role)

**Priority:** High

**Backend Specs:** `specs/analytics/dashboard.md` (AN-01)

**Dependencies:** `specs/frontend/dashboard/dashboard.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Login redirect for users with `role = doctor`
- Sidebar "Inicio" link from any authenticated page
- Post-appointment-complete redirect

**Exit Points:**
- Click appointment in timeline → appointment detail view
- Click patient name in timeline → patient detail `/patients/{id}`
- "Ver todos los turnos" → `/agenda`
- "Ver historial completo" → `/patients/{id}/records`
- "Ver ingresos" → `/billing/revenue`

**User Story:**
> As a doctor, I want to see my clinical day at a glance so that I can quickly know my next patient, review today's schedule, and check recent procedures without navigating multiple screens.

**Roles with access:** `doctor` only. `clinic_owner` with doctor role sees this view. Other roles redirect to their own dashboard variant.

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | "Buenos dias, Dr. {nombre}" 09:30 AM  |
|          +---------------------------------------+
|          |                                       |
|          |  Row 1: [Widget: Next Appt]  [Widget: Week Patients] [Widget: Revenue?] |
|          |                                       |
|          |  Row 2: [Widget: Today's Appointments - tall] | [Widget: Recent Procedures] |
|          |                                       |
+------------------------------------------+-------+
```

**Desktop grid:** `grid grid-cols-3 gap-4` for top row; `grid grid-cols-5 gap-4` for bottom row with appointments taking `col-span-3` and procedures `col-span-2`.

**Tablet grid:** `grid grid-cols-2 gap-4` throughout, appointments full-width (`col-span-2`).

**Mobile:** Single column, cards stacked vertically.

---

## UI Components

### Component 1: WelcomeHeader

**Type:** Page header

**Content:**
- Greeting: `"Buenos dias"` / `"Buenas tardes"` / `"Buenas noches"` based on time
- Doctor name: `"Dr. {nombre}"` (first name only)
- Current date + time: `"Martes, 25 de febrero de 2026 — 09:30 AM"` `text-sm text-gray-500`
- Formatted: `new Intl.DateTimeFormat('es-419', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(now)`

---

### Widget 1: Proximo Turno (Next Appointment Countdown)

**Type:** Card — prominently sized

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Content when appointment upcoming:**
- Label: `"Proximo Turno"` `text-xs uppercase font-semibold text-gray-400`
- Patient avatar (circular, 48px) + patient full name `text-lg font-bold`
- Time: `"10:30 AM"` `text-2xl font-bold text-teal-600`
- Countdown: `"en 12 minutos"` or `"en 1 hora 15 minutos"` `text-sm text-gray-500`
- Appointment type badge: `"Consulta general"` or `"Limpieza"` etc.
- "Ver perfil →" link to patient detail
- "Ver detalle →" link to appointment detail

**Countdown logic:**
- If next appt < 60 min away: show minutes `"en X minutos"` with yellow background `bg-amber-50 border-amber-200`
- If next appt < 15 min: red urgent style `bg-red-50 border-red-300 text-red-700`
- If next appt > 60 min: show `"en X horas Y minutos"` — normal styling

**Content when no upcoming appointments today:**
- `"Sin turnos pendientes hoy"` `text-sm text-gray-400`
- `"¡Disfruta tu dia!"` with CalendarCheck icon
- Card background: `bg-gray-50`

**Auto-refresh:** Component polls every 60 seconds to update countdown. Uses `useInterval` hook.

---

### Widget 2: Mis Pacientes Esta Semana (Weekly Patient Count)

**Type:** KPI card

**Content:**
- Label: `"Mis Pacientes Esta Semana"` `text-xs uppercase text-gray-400`
- Main number: `{N}` `text-4xl font-bold text-gray-900`
- Trend: `"+{X} vs semana anterior"` with arrow icon
  - `ArrowUpRight text-green-500` if positive
  - `ArrowDownRight text-red-500` if negative
  - `Minus text-gray-400` if equal
- Subtext: `"pacientes atendidos"` `text-sm text-gray-500`
- Sparkline: simple 7-day bar chart, `h-8`, bars `bg-teal-200 hover:bg-teal-400` last bar `bg-teal-600`

**Sparkline implementation:** SVG-based, 7 bars, data from last 7 days of appointments completed.

---

### Widget 3: Ingresos del Mes (Monthly Revenue) — Conditional

**Type:** KPI card

**Visibility:** Only shown if `tenant.commissions_enabled === true` AND doctor has commission rates configured.

**Content:**
- Label: `"Mis Ingresos Este Mes"` `text-xs uppercase text-gray-400`
- Amount: `"$1.450.000"` COP formatted with `Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })`
- Trend vs last month: `"+12%"` with arrow
- Subtext: `"en comisiones"` `text-sm text-gray-500`
- "Ver detalle →" link

**If commissions not enabled:**
- Widget not rendered, space collapsed (not empty card placeholder)

---

### Widget 4: Turnos de Hoy (Today's Appointments Timeline)

**Type:** Tall card with vertical timeline list

**Header:**
- Title: `"Mis Turnos de Hoy"` + date in parentheses
- Count badge: `"X turnos"` `bg-teal-100 text-teal-700 text-xs rounded-full px-2`
- "Ver agenda →" link

**Timeline list:**

Each appointment row:
```
[Status dot]  [Time]  [Patient name + type badge]  [Status badge]  [Actions]
```

| Element | Details |
|---------|---------|
| Status dot | `w-3 h-3 rounded-full` color by status |
| Time | `"10:30"` `text-sm font-mono font-medium text-gray-700` |
| Patient name | `text-sm font-semibold text-gray-900` — click → patient detail |
| Type badge | `text-xs rounded-full px-2 py-0.5` by appointment type |
| Status badge | See status table below |
| Actions | `...` overflow menu: "Iniciar consulta", "Marcar como no asistio", "Reagendar" |

**Status colors:**

| Status | Dot color | Badge |
|--------|-----------|-------|
| `pending` | `bg-gray-300` | — (not shown) |
| `confirmed` | `bg-blue-400` | `"Confirmado"` `bg-blue-100 text-blue-700` |
| `in_progress` | `bg-teal-500 animate-pulse` | `"En consulta"` `bg-teal-100 text-teal-700` |
| `completed` | `bg-green-500` | `"Completado"` `bg-green-100 text-green-700` |
| `cancelled` | `bg-gray-400` | `"Cancelado"` `bg-gray-100 text-gray-500` |
| `no_show` | `bg-red-400` | `"No asistio"` `bg-red-100 text-red-600` |

**Time groupings:** Past appointments subtly dimmed `opacity-60`. Current/upcoming at full opacity. "Ahora" marker: horizontal dashed line at current time position if between two appointments.

**Max display:** 10 appointments. "Ver X mas →" link if more.

**Empty state:** `"Sin turnos programados para hoy"` + CalendarX icon + "Ir a la agenda" CTA.

---

### Widget 5: Procedimientos Recientes (Recent Procedures)

**Type:** Card with compact list

**Header:**
- Title: `"Procedimientos Recientes"`
- "Ver todos →" link → `/patients` (with filter for doctor's patients)

**List:** Last 5 procedures performed by this doctor (across all patients).

Each item:
```
[Patient initials avatar]  [Patient name]    [CUPS code badge]
                           [Procedure name]  [Date]
```

| Element | Details |
|---------|---------|
| Avatar | 32px circle, initials, `bg-teal-100 text-teal-600 text-xs font-bold` |
| Patient name | `text-sm font-medium text-gray-800` — click → `/patients/{id}` |
| CUPS badge | `bg-gray-100 text-gray-600 text-xs font-mono rounded px-1.5` |
| Procedure name | `text-xs text-gray-500` — truncated at 30 chars with ellipsis |
| Date | `text-xs text-gray-400` — relative: "hace 2 horas", "ayer", "20 feb" |

**Relative date logic:**
- < 1 hour: `"hace {n} minutos"`
- 1-24 hours: `"hace {n} horas"`
- Yesterday: `"ayer"`
- < 7 days: `"hace {n} dias"`
- Older: formatted date `"20 feb"`

**Empty state:** `"Sin procedimientos recientes"` with Clipboard icon.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get today's appointments | `/api/v1/appointments?date=today&doctor_id=me&limit=15` | GET | `specs/analytics/dashboard.md` | 2min |
| Get weekly patient count | `/api/v1/analytics/doctor/weekly-patients` | GET | `specs/analytics/dashboard.md` | 10min |
| Get revenue (if enabled) | `/api/v1/analytics/doctor/monthly-revenue` | GET | `specs/analytics/dashboard.md` | 10min |
| Get recent procedures | `/api/v1/clinical-records/procedures?doctor_id=me&limit=5` | GET | `specs/analytics/dashboard.md` | 5min |

### State Management

**Local State (useState):**
- `currentTime: Date` — updated every 60 seconds for countdown

**Global State (Zustand):**
- `authStore.user.id` — used as `doctor_id` in queries

**Server State (TanStack Query):**
- Appointments: `useQuery(['today-appointments', doctorId], { staleTime: 2 * 60 * 1000, refetchInterval: 60 * 1000 })`
- Analytics: `useQuery(['doctor-weekly-patients', doctorId], { staleTime: 10 * 60 * 1000 })`
- Revenue (conditional): `useQuery(['doctor-monthly-revenue', doctorId], { enabled: tenant.commissions_enabled, staleTime: 10 * 60 * 1000 })`
- Procedures: `useQuery(['recent-procedures', doctorId], { staleTime: 5 * 60 * 1000 })`

**Auto-refresh:** Appointments widget refetches every 60 seconds (`refetchInterval: 60000`). Next appointment countdown computed client-side from cached data using `useInterval(1000)`.

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click patient name (timeline) | Click | Navigate to patient detail | Standard navigation |
| Click appointment row | Click | Navigate to appointment detail | Standard navigation |
| Click "Iniciar consulta" | Overflow menu | Appointment status → in_progress + navigate to new record form | Optimistic update on status dot |
| Click "Marcar no asistio" | Overflow menu | Confirm dialog → PATCH status | Appointment dims |
| Click sparkline bar | Hover/click | Tooltip: "{date}: {N} pacientes" | Tooltip overlay |
| Refetch trigger (60s) | Auto | Silent background refetch | No visible loading if data unchanged |

### Animations/Transitions

- Page load: widgets fade in staggered `delay: index * 80ms, opacity 0 → 1`
- Countdown update: `text-2xl` time text number changes with subtle scale `1 → 1.05 → 1` 200ms
- Status change (in_progress): dot gains `animate-pulse` class when appointment status changes
- New procedure added (from subscription/refetch): item slides in from top of list `y: -10 → 0`

---

## Loading & Error States

### Loading State
- Initial load: each widget shows skeleton matching its layout:
  - KPI cards: `h-24 animate-pulse rounded-xl bg-gray-100`
  - Timeline: 5 row skeletons `h-12 animate-pulse bg-gray-100 rounded-lg mb-2`
  - Procedures: 5 row skeletons same as timeline

### Error State
- Per-widget error: small `"Error al cargar"` text + inline `RefreshCw` retry icon
- Does not block other widgets — each widget fails/succeeds independently

### Empty State
- Today's appointments: see Widget 4 empty state
- Recent procedures: see Widget 5 empty state
- Weekly patients: shows `"0"` with neutral trend `"Igual que la semana anterior"`

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | All widgets stacked vertically. Today's Appointments shows only next 3 with "Ver todos". Sparkline hidden on KPI cards. Revenue widget last in order. |
| Tablet (640-1024px) | 2-column grid. Today's Appointments full-width on second row. KPI cards in row 1 (2-wide). |
| Desktop (> 1024px) | 3-column KPI row. Today's Appointments `col-span-3` of 5, Procedures `col-span-2`. |

**Tablet priority:** High — doctors review dashboard on clinic tablets between patients. All interactive elements min 44px.

---

## Accessibility

- **Focus order:** Welcome header (read) → Widget 1 (Next Appt) → Widget 2 → Widget 3 (if shown) → Widget 4 (appointments list, each row focusable) → Widget 5 (procedures list, each row focusable)
- **Screen reader:** Each widget has `role="region" aria-label="{widget title}"`. KPI values: `aria-label="Mis pacientes esta semana: {N}, {trend} vs semana anterior"`. Countdown: `aria-live="polite"` updates when minutes change. Timeline rows: keyboard-activatable `role="button"`.
- **Keyboard navigation:** Tab through all interactive elements. Enter activates links and buttons. Overflow menu opens with Enter/Space, arrow keys navigate items.
- **Color contrast:** Status dots supplemented by text badges (color not sole indicator). Revenue green/red trend arrow + text percentage.
- **Language:** Greeting, date, all widget labels in es-419.

---

## Design Tokens

**Colors:**
- Welcome header: `text-gray-900`
- KPI number: `text-4xl font-bold text-gray-900`
- KPI trend positive: `text-green-600`
- KPI trend negative: `text-red-500`
- Teal sparkline bar: `bg-teal-200`, active: `bg-teal-600`
- Next appt time: `text-teal-600`
- Next appt urgent: `bg-red-50 border-red-300`
- Next appt near: `bg-amber-50 border-amber-200`
- Timeline "Ahora" line: `border-teal-400 border-dashed`

**Typography:**
- Greeting: `text-2xl font-bold font-inter text-gray-900`
- Widget title: `text-sm font-semibold uppercase tracking-wide text-gray-400`
- KPI value: `text-4xl font-bold`
- Timeline time: `text-sm font-mono font-medium`
- Timeline patient: `text-sm font-semibold`
- Procedure patient: `text-sm font-medium`

**Spacing:**
- Page: `px-4 md:px-6 py-6`
- Widget card: `p-5 rounded-2xl bg-white shadow-sm border border-gray-100`
- Widget gap: `gap-4`
- Timeline row: `py-3 px-1` with `gap-3`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — CalendarCheck, CalendarX, ArrowUpRight, ArrowDownRight, Minus, RefreshCw, MoreHorizontal, Clock
- `@tanstack/react-query` — multiple queries with independent `refetchInterval`
- `framer-motion` — stagger fade-in on load

**File Location:**
- Component: `src/components/dashboard/DoctorDashboard.tsx`
- Widgets: `src/components/dashboard/widgets/NextAppointmentWidget.tsx`, `src/components/dashboard/widgets/WeeklyPatientsWidget.tsx`, `src/components/dashboard/widgets/RevenueWidget.tsx`, `src/components/dashboard/widgets/TodayTimelineWidget.tsx`, `src/components/dashboard/widgets/RecentProceduresWidget.tsx`
- Hook: `src/hooks/useInterval.ts`

**Hooks Used:**
- `useQuery()` × 4 — each widget's data
- `useInterval(callback, 60000)` — auto-refetch appointments
- `useInterval(callback, 1000)` — countdown second tick
- `useAuthStore()` — get `user.id` for doctor-scoped queries

---

## Test Cases

### Happy Path
1. Doctor logs in with appointments today
   - **Given:** Doctor has 5 appointments today, next in 20 minutes
   - **When:** Dashboard loads
   - **Then:** Timeline shows 5 appointments, Next Appt card shows patient name + "en 20 minutos" + amber styling

### Edge Cases
1. No appointments today
   - **Given:** Doctor has no scheduled appointments
   - **When:** Dashboard loads
   - **Then:** Timeline shows empty state. Next Appt card shows "Sin turnos pendientes hoy"

2. Commissions disabled
   - **Given:** `tenant.commissions_enabled = false`
   - **When:** Dashboard loads
   - **Then:** Revenue widget not rendered, grid adjusts to 2 KPI cards

3. Appointment becomes in_progress during viewing
   - **Given:** Dashboard open, next appointment time arrives
   - **When:** 60s auto-refetch fires
   - **Then:** Status dot for that appointment gains `animate-pulse` (or shows in_progress badge)

### Error Cases
1. Analytics API error
   - **Given:** AN-01 endpoint unavailable
   - **When:** Dashboard loads
   - **Then:** KPI cards show "Error al cargar" + retry. Today's appointments still shows if that endpoint works.

---

## Acceptance Criteria

- [ ] Shows only for users with `role = doctor`
- [ ] Welcome greeting based on time of day in Spanish
- [ ] Widget 1: Next appointment with countdown, patient name, urgent styling < 15min
- [ ] Widget 2: Weekly patient count with sparkline and trend
- [ ] Widget 3: Monthly revenue widget only if commissions enabled
- [ ] Widget 4: Today's appointments timeline with status dots and badges
- [ ] Widget 4: "Ahora" time marker between appointments
- [ ] Widget 5: Last 5 procedures with CUPS code, patient name, relative date
- [ ] Auto-refresh appointments every 60 seconds
- [ ] All widgets fail/recover independently
- [ ] Loading skeletons match widget layouts
- [ ] Responsive: mobile stack, 2-col tablet, 3-col desktop
- [ ] Accessibility: region ARIA, live countdown, keyboard navigation
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
