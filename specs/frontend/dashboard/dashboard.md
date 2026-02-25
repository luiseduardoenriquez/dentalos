# Panel Principal (Dashboard) -- Frontend Spec

## Overview

**Screen:** Main dashboard displaying role-specific widgets for clinic staff. Each role sees a tailored set of KPI cards, lists, and action shortcuts relevant to their daily workflow.

**Route:** `/dashboard`

**Priority:** Critical

**Backend Specs:** `specs/M1-NAVIGATION-MAP.md` Section 4 (Dashboard Widgets per Role), `specs/infra/authentication-rules.md`

**Dependencies:** `specs/frontend/auth/login.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Redirect after successful login
- Sidebar navigation click "Panel Principal"
- Direct navigation to `/dashboard`

**Exit Points:**
- Sidebar navigation to any other section (Pacientes, Agenda, Facturacion, etc.)
- Click on widget items (e.g., appointment -> `/agenda`, patient -> `/patients/{id}`)
- Header notification bell -> `/notifications`
- User avatar -> profile or logout

**User Story:**
> As a clinic_owner, I want to see today's appointments, monthly revenue, and team activity so that I can monitor my clinic's performance at a glance.
> As a doctor, I want to see my appointments for today and pending treatment plans so that I can prepare for my patients.
> As a receptionist, I want to see today's check-in queue, pending invoices, and unread messages so that I can manage the front desk efficiently.

**Roles with access:** clinic_owner, doctor, assistant, receptionist

---

## Layout Structure

```
+--------+-----------------------------------------+
|        |  Header: Clinic Name | Search | Bell | Avatar |
|        +-----------------------------------------+
|        |                                         |
| Side-  |  Page Title: "Panel Principal"          |
|  bar   |                                         |
|        |  +----------+  +----------+  +--------+ |
|        |  | KPI Card |  | KPI Card |  | KPI    | |
|        |  | (metric) |  | (metric) |  | Card   | |
|        |  +----------+  +----------+  +--------+ |
|        |                                         |
|        |  +---------------------+  +-----------+ |
|        |  | Appointments List   |  | Activity  | |
|        |  | (today)             |  | Feed      | |
|        |  |                     |  |           | |
|        |  +---------------------+  +-----------+ |
|        |                                         |
|        |  +-------------------------------------+|
|        |  | Plan Usage / Upgrade Prompt         ||
|        |  +-------------------------------------+|
+--------+-----------------------------------------+
```

**Sections:**
1. App Header -- sticky top bar with clinic name, global search, notification bell with badge, user avatar dropdown
2. Sidebar -- role-based navigation items (collapsed on tablet, expanded on desktop)
3. KPI row -- 3-4 metric cards in a horizontal grid
4. Content area -- role-specific widgets in a 2-column grid (tablet/desktop)
5. Footer widget (clinic_owner only) -- plan usage bar and upgrade prompt

---

## UI Components

### Component 1: AppHeader

**Type:** Layout component (sticky header)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.11

**Content:**
- Clinic name (from `authStore.tenant.name`): `text-lg font-semibold text-gray-700`
- Hamburger menu button (mobile only): `md:hidden`
- Notification bell (Lucide `Bell` icon) with red badge for unread count
- User avatar (`Avatar` component, `md` size) with dropdown: profile, settings (clinic_owner), logout

### Component 2: KPICard

**Type:** Card

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | string | -- | Metric label (e.g., "Citas de Hoy") |
| value | string/number | -- | Primary metric value |
| icon | LucideIcon | -- | Decorative icon |
| trend | object | null | `{ direction: 'up'|'down', percentage: number }` |
| color | string | "blue" | Accent color for icon background |

**States:**
- Loading: `SkeletonCard` with pulsing blocks for value and label
- Loaded: metric displayed with optional trend indicator
- Error: shows "--" as value with subtle error icon

### Component 3: AppointmentListWidget

**Type:** Card with embedded list

**Content:** Today's appointments sorted by time. Each row shows: time (`text-sm font-mono`), patient name (avatar + name), appointment type badge, status badge. Click row navigates to patient detail.

**Max items:** 8 visible, "Ver todas" link to `/agenda?date=today`.

### Component 4: PlanUsageBar

**Type:** Custom progress bar (clinic_owner only)

**Content:** Horizontal bar showing usage vs. limit for key plan metrics: doctors, patients. Label: "3 de 5 doctores" / "120 de 500 pacientes". Bar color: `bg-blue-500` when < 80%, `bg-amber-500` at 80-95%, `bg-red-500` at 95%+.

**Upgrade Prompt:** Appears when any metric exceeds 80%. Card with `bg-amber-50 border border-amber-200`. Text: "Estas cerca del limite de tu plan." CTA: "Mejorar plan" button linking to `/settings/billing`.

---

## Form Fields

Not applicable -- dashboard is a read-only display screen.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Today's appointments | `/api/v1/appointments?date=today` | GET | `specs/M1-NAVIGATION-MAP.md` 6.6 | 2min |
| Revenue this month | `/api/v1/analytics/revenue?period=month` | GET | `specs/M1-NAVIGATION-MAP.md` 6.12 | 5min |
| New patients this week | `/api/v1/analytics/patients?period=week` | GET | `specs/M1-NAVIGATION-MAP.md` 6.12 | 5min |
| Team activity | `/api/v1/analytics/team-activity` | GET | `specs/M1-NAVIGATION-MAP.md` 6.12 | 5min |
| Subscription info | `/api/v1/settings/subscription` | GET | `specs/M1-NAVIGATION-MAP.md` 6.11 | 10min |
| Pending invoices | `/api/v1/invoices?status=sent,overdue` | GET | `specs/M1-NAVIGATION-MAP.md` 6.7 | 2min |
| Unread messages | `/api/v1/messages?unread=true` | GET | `specs/M1-NAVIGATION-MAP.md` 6.10 | 1min |
| My appointments (doctor) | `/api/v1/appointments?doctor_id=me&date=today` | GET | `specs/M1-NAVIGATION-MAP.md` 6.6 | 2min |
| Pending treatment plans | `/api/v1/treatment-plans?status=draft&doctor_id=me` | GET | `specs/M1-NAVIGATION-MAP.md` 6.5 | 5min |

### State Management

**Local State (useState):**
- None significant -- widgets are independent query-driven components

**Global State (Zustand):**
- `authStore.user.role` -- determines which widget set to render
- `authStore.tenant` -- provides clinic name, plan, country for display and currency formatting

**Server State (TanStack Query):**
- Query key: `['appointments', 'today', tenantId]` -- staleTime: 2min
- Query key: `['analytics', 'revenue', 'month', tenantId]` -- staleTime: 5min
- Query key: `['analytics', 'patients', 'week', tenantId]` -- staleTime: 5min
- Query key: `['analytics', 'team-activity', tenantId]` -- staleTime: 5min
- Query key: `['subscription', tenantId]` -- staleTime: 10min
- Query key: `['invoices', 'pending', tenantId]` -- staleTime: 2min
- Query key: `['messages', 'unread', tenantId]` -- staleTime: 1min
- Query key: `['treatment-plans', 'draft', 'me', tenantId]` -- staleTime: 5min

### Widgets per Role

**clinic_owner:**
1. KPI: Citas de Hoy (appointment count + status breakdown)
2. KPI: Ingresos del Mes (revenue in local currency: COP/MXN/CLP/ARS/PEN)
3. KPI: Nuevos Pacientes (count this week vs. last week trend)
4. Widget: Citas de Hoy (appointment list with patient names)
5. Widget: Actividad del Equipo (recent team actions feed)
6. Widget: Plan Usage Bar + Upgrade Prompt

**doctor:**
1. KPI: Mis Citas Hoy (my appointment count)
2. KPI: Pacientes en Espera (checked-in, waiting)
3. KPI: Planes Pendientes (draft treatment plans count)
4. Widget: Mis Citas Hoy (list with times and patient names)
5. Widget: Registros Recientes (last 5 clinical records)

**assistant:**
1. KPI: Agenda de Hoy (total appointments)
2. KPI: Pacientes por Preparar (confirmed, arriving soon)
3. Widget: Agenda de Hoy (full schedule, all doctors)
4. Widget: Tareas Rapidas (quick action buttons: check-in, new record)

**receptionist:**
1. KPI: Citas de Hoy (total appointments with status)
2. KPI: Facturas Pendientes (count + total amount)
3. KPI: Mensajes sin Leer (unread count)
4. Widget: Cola de Llegadas (patients to check in)
5. Widget: Proximas Citas (next 3 upcoming)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click appointment row | Click | Navigate to `/patients/{patientId}` | Row highlight on hover |
| Click "Ver todas" on appointments | Click link | Navigate to `/agenda?date=today` | Standard navigation |
| Click notification bell | Click | Navigate to `/notifications` | Badge disappears |
| Click "Mejorar plan" | Click button | Navigate to `/settings/billing` | Standard navigation |
| Click patient name in feed | Click | Navigate to `/patients/{id}` | Standard navigation |
| Pull to refresh (mobile) | Swipe down | Invalidate all dashboard queries | Spinner at top |

### Animations/Transitions

- KPI cards: staggered fade-in on load (`framer-motion` stagger, 50ms delay between cards)
- KPI value: counter animation from 0 to final value (300ms ease-out)
- Widget content: fade in after skeleton placeholder (200ms)
- Page-level: standard page transition per design system Section 8.1

---

## Loading & Error States

### Loading State
- KPI cards: `SkeletonCard` -- pulsing rectangle for value (h-8 w-20) and label (h-4 w-32)
- Appointment list: `SkeletonTableRow` repeated 5 times
- Activity feed: 4 skeleton rows with avatar circle + two text lines
- All skeletons use `animate-pulse bg-gray-200 dark:bg-gray-700 rounded`

### Error State
- Per-widget error handling: if a single API call fails, that widget shows a compact error message: "Error al cargar datos" with "Reintentar" button
- Other widgets continue to function independently
- Full-page error only if authentication fails (redirect to `/login`)

### Empty State
- Appointments empty: "Sin citas programadas para hoy" with `Calendar` icon and "Agendar cita" CTA -> `/agenda/new`
- Patients empty (new clinic): "Bienvenido a DentalOS" with onboarding checklist widget
- Messages empty: "Sin mensajes nuevos" with `MessageCircle` icon

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Single column layout. KPI cards stack vertically (2-col grid). Sidebar hidden (hamburger menu). Widgets full width, stacked. |
| Tablet (640-1024px) | KPI cards in 2x2 grid. Sidebar collapsed (icon-only, w-16). Widgets in 2-column grid. |
| Desktop (> 1024px) | KPI cards in single row (3-4 columns). Sidebar expanded (w-64). Widgets in 2-column grid with wider cards. |

**Tablet priority:** High -- doctors and assistants use the dashboard on tablets between patients. Touch targets 48px on all interactive widget elements.

---

## Accessibility

- **Focus order:** Sidebar nav items -> Header (search, bell, avatar) -> KPI cards (left to right) -> Widget content (top to bottom, left to right)
- **Screen reader:** Each KPI card has `aria-label="{label}: {value}"`. Appointment list uses `role="list"` with `role="listitem"`. Activity feed uses `aria-live="polite"` for new items.
- **Keyboard navigation:** Tab through KPI cards and widget interactive elements. Enter activates links and buttons. Arrow keys for list navigation within widgets.
- **Color contrast:** WCAG AA. Trend indicators use both color and direction icon (up/down arrow) for colorblind accessibility.
- **Language:** All widget titles, labels, empty states, and ARIA attributes in es-419.

---

## Design Tokens

**Colors:**
- Page background: `bg-gray-50 dark:bg-gray-950`
- KPI card background: `bg-white dark:bg-gray-900`
- KPI icon backgrounds: `bg-blue-50` (appointments), `bg-green-50` (revenue), `bg-teal-50` (patients), `bg-amber-50` (invoices)
- Trend up: `text-green-600`
- Trend down: `text-red-600`
- Header: `bg-white dark:bg-gray-900 border-b border-gray-200`
- Notification badge: `bg-red-500 text-white text-xs`

**Typography:**
- Page title: `text-xl md:text-2xl font-bold text-gray-700`
- KPI value: `text-2xl md:text-3xl lg:text-4xl font-bold text-gray-900`
- KPI label: `text-sm text-gray-500`
- Widget title: `text-lg font-semibold text-gray-700`
- Appointment time: `text-sm font-mono text-gray-500`
- Revenue: formatted with locale -- COP: `$1.250.000`, MXN: `$12,500.00`

**Spacing:**
- KPI grid gap: `gap-4 md:gap-6`
- Widget grid gap: `gap-4 md:gap-6`
- KPI card padding: `p-4 md:p-6`
- Widget card padding: `p-4 md:p-6`
- Page padding: `px-4 py-6 md:px-6 lg:px-8`

**Border Radius:**
- Cards: `rounded-xl`
- Badges: `rounded-full`
- Notification badge: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` -- Calendar, DollarSign, Users, Activity, Bell, MessageCircle, TrendingUp, TrendingDown, AlertTriangle
- `framer-motion` -- stagger animations, counter animation
- `date-fns` -- relative time formatting ("hace 3 horas")
- `@tanstack/react-query` -- all widget data fetching

**File Location:**
- Page: `src/app/(dashboard)/dashboard/page.tsx`
- Components: `src/components/dashboard/KPICard.tsx`, `src/components/dashboard/AppointmentListWidget.tsx`, `src/components/dashboard/TeamActivityWidget.tsx`, `src/components/dashboard/PlanUsageBar.tsx`, `src/components/dashboard/UpgradePrompt.tsx`, `src/components/dashboard/CheckInQueueWidget.tsx`
- Role-specific layouts: `src/components/dashboard/OwnerDashboard.tsx`, `src/components/dashboard/DoctorDashboard.tsx`, `src/components/dashboard/AssistantDashboard.tsx`, `src/components/dashboard/ReceptionistDashboard.tsx`

**Hooks Used:**
- `useAuth()` -- current user role and tenant context
- `useQuery()` -- multiple queries for each widget
- `useCurrencyFormatter()` -- custom hook for locale-aware currency formatting based on `tenant.country`
- `useMediaQuery()` -- responsive widget layout decisions

**Currency Formatting:**
```typescript
function formatCurrency(amount: number, country: string): string {
  const config: Record<string, Intl.NumberFormatOptions & { locale: string }> = {
    CO: { locale: 'es-CO', style: 'currency', currency: 'COP', maximumFractionDigits: 0 },
    MX: { locale: 'es-MX', style: 'currency', currency: 'MXN' },
    CL: { locale: 'es-CL', style: 'currency', currency: 'CLP', maximumFractionDigits: 0 },
    AR: { locale: 'es-AR', style: 'currency', currency: 'ARS' },
    PE: { locale: 'es-PE', style: 'currency', currency: 'PEN' },
  };
  const c = config[country] || config.CO;
  return new Intl.NumberFormat(c.locale, c).format(amount);
}
```

---

## Test Cases

### Happy Path
1. Clinic owner sees full dashboard
   - **Given:** User is logged in as clinic_owner
   - **When:** User navigates to `/dashboard`
   - **Then:** KPI cards (appointments, revenue, new patients), appointment list, team activity feed, and plan usage bar are displayed

2. Doctor sees clinical dashboard
   - **Given:** User is logged in as doctor
   - **When:** User navigates to `/dashboard`
   - **Then:** My appointments today, pending treatment plans, and recent records are displayed

### Edge Cases
1. New clinic with no data
   - **Given:** Clinic was just created, no patients or appointments
   - **When:** clinic_owner visits dashboard
   - **Then:** KPI cards show "0" values. Appointment widget shows empty state with "Agendar cita" CTA.

2. Widget API failure
   - **Given:** Revenue endpoint returns 500
   - **When:** Dashboard loads
   - **Then:** Revenue KPI shows "--" with error icon. Other widgets load normally.

### Error Cases
1. Token expired mid-session
   - **Given:** Access token expires while viewing dashboard
   - **When:** A widget attempts to refetch data
   - **Then:** Refresh token flow triggers. If refresh fails, redirect to `/login`.

---

## Acceptance Criteria

- [ ] Role-based widget rendering (clinic_owner, doctor, assistant, receptionist)
- [ ] KPI cards with real data from API endpoints
- [ ] Currency formatting based on tenant country (COP, MXN, CLP, ARS, PEN)
- [ ] Appointment list widget with clickable rows
- [ ] Plan usage bar with upgrade prompt at 80%+ (clinic_owner)
- [ ] Notification bell with unread count badge
- [ ] Loading skeletons for all widgets
- [ ] Per-widget error handling (independent failure)
- [ ] Empty states with CTAs for new clinics
- [ ] Responsive: single column mobile, 2-column tablet/desktop
- [ ] Sidebar navigation with role-based items
- [ ] Accessibility: ARIA labels, keyboard navigation, screen reader support
- [ ] Spanish (es-419) labels and messages throughout
- [ ] Touch targets 48px on tablet

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
