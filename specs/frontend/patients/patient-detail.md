# Detalle de Paciente (Patient Detail) — Frontend Spec

## Overview

**Screen:** Patient detail page — the central hub for all clinical information about a patient. A summary card sits at the top with key demographics and quick action buttons. Below it, a tabbed layout gives access to timeline, odontogram, clinical records, treatment plans, appointments, billing, and documents. Each tab is lazy-loaded.

**Route:** `/patients/{id}`

**Priority:** Critical

**Backend Specs:** `specs/patients/patient-get.md` (P-02), `specs/patients/patient-list.md` (P-05)

**Dependencies:** `specs/frontend/patients/patient-list.md`, `specs/frontend/odontogram/classic-grid.md`, `specs/frontend/clinical-records/record-list.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Click patient row in `/patients` list
- Click patient card in global search results
- Redirect from appointment modal "Ver paciente"
- Redirect after creating patient (`/patients/new`)
- Direct URL navigation with patient ID

**Exit Points:**
- "Editar" button → `/patients/{id}/edit`
- "Nuevo turno" quick action → appointment create modal (pre-filled patient)
- "Nueva consulta" quick action → `/patients/{id}/records/new`
- "Nuevo plan" quick action → `/patients/{id}/treatment-plans/new`
- Breadcrumb "Pacientes" → `/patients`

**User Story:**
> As a doctor | assistant | receptionist, I want to see all patient information on one page so that I can quickly assess history and take action without navigating multiple screens.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`, `receptionist`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Pacientes > {Nombre}      |
|          +----------------------------------------|
|          |  [Patient Summary Card]               |
|          |  [Quick Action Buttons Row]            |
|          +----------------------------------------|
|          |  [Tab Bar: 7 tabs]                    |
|          +----------------------------------------|
|          |                                        |
|          |  [Active Tab Content]                  |
|          |  (lazy-loaded per tab)                 |
|          |                                        |
+------------------------------------------+-------+
```

**Sections:**
1. Patient summary card — photo, name, key demographics, status badges, edit button
2. Quick action buttons — 3 primary actions (new appointment, new record, new treatment plan)
3. Tab navigation bar — 7 tabs
4. Tab content area — lazy-loaded component per tab

---

## UI Components

### Component 1: PatientSummaryCard

**Type:** Card (sticky on scroll if desktop)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Content:**

| Element | Details |
|---------|---------|
| Avatar | Patient photo (circular, 64px) or initials avatar `bg-teal-100 text-teal-700 font-bold text-xl`. Online status dot not applicable. |
| Name | `text-2xl font-bold text-gray-900` |
| Document | `text-sm text-gray-500` — tipo + numero |
| Age + Birthdate | `text-sm text-gray-500` — "38 años (15/03/1987)" |
| Phone | `text-sm text-gray-600` with phone icon, tap-to-call on mobile |
| Last visit | `text-sm text-gray-500` — "Ultima visita: hace 3 semanas" or "Sin consultas previas" |
| Balance | `text-sm font-medium` — green if 0 or credit, red if owes. "$45.000 pendiente" or "Al dia" |
| Active alerts | Chip badges — allergies (red `bg-red-100 text-red-700`), medical conditions (amber `bg-amber-100 text-amber-700`) — max 3 shown, "+N mas" overflow |
| Edit button | `variant="outline"` `text-sm` top-right corner of card |

**Alert chips behavior:** Click on allergy/condition chip expands a tooltip showing all values.

### Component 2: QuickActionButtons

**Type:** Horizontal button row

**Buttons:**

| Button | Icon | Action | Role restriction |
|--------|------|--------|-----------------|
| Nuevo Turno | `CalendarPlus` | Open appointment modal pre-filled | All roles |
| Nueva Consulta | `FilePlus` | Navigate to `/patients/{id}/records/new` | doctor, assistant |
| Nuevo Plan | `ClipboardList` | Navigate to `/patients/{id}/treatment-plans/new` | doctor |

**Style:** `variant="primary-outline"` `h-10 px-4 text-sm gap-2` in a `flex gap-3 flex-wrap` row.

### Component 3: TabBar

**Type:** Horizontal tab navigation

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.13

**Tabs:**

| Index | Label | Badge | Component |
|-------|-------|-------|-----------|
| 0 | Resumen | — | `PatientTimeline` |
| 1 | Odontograma | — | `EmbeddedOdontogram` |
| 2 | Consultas | count | `ClinicalRecordList` |
| 3 | Planes de Tratamiento | count | `TreatmentPlanList` |
| 4 | Turnos | count | `AppointmentList` |
| 5 | Facturacion | balance badge | `BillingTab` |
| 6 | Documentos | count | `DocumentList` |

**Tab badge:** `bg-gray-100 text-gray-600 text-xs font-medium px-1.5 py-0.5 rounded-full ml-1.5`

**Active tab indicator:** `border-b-2 border-teal-600 text-teal-700`

**Scroll behavior on mobile:** Tab bar scrolls horizontally with `overflow-x-auto scrollbar-hide`.

### Component 4: EmbeddedOdontogram

**Type:** Embedded component (lazy-loaded)

**Behavior:**
- Renders the full odontogram component (classic or anatomic per clinic config) within the tab
- Read-only unless user is `doctor` or `assistant`
- "Ver odontograma completo" button → dedicated odontogram page
- Includes last-updated timestamp and doctor name

---

## Tab Content Specifications

### Tab 0: Resumen (Timeline)

See `specs/frontend/patients/patient-medical-history.md` (FE-P-07) for full spec.
- Lazy-load `PatientTimeline` component
- Shows last 10 events by default, "Ver historial completo" loads all

### Tab 1: Odontograma

- Embeds `ClassicGrid` or `AnatomicArch` per tenant config (read-only on tablet if not the treating doctor)
- `height: auto` within tab, no fixed height scroll
- Load skeleton: grid of 32 gray rectangles arranged in dental arch pattern

### Tab 2: Consultas

- Table/list of clinical records
- Columns: Fecha, Doctor, Tipo (consulta/procedimiento), Resumen (first 60 chars), Estado
- "Nueva consulta" button at top right of tab
- Paginated: 10 per page

### Tab 3: Planes de Tratamiento

- List of treatment plans with status badge (borrador/activo/completado/cancelado)
- Shows procedure count, total value, completion percentage bar
- "Nuevo plan" button at top right

### Tab 4: Turnos

- List of past + upcoming appointments
- Grouped by upcoming (top) and past (collapsible)
- Status badges: confirmado/pendiente/completado/cancelado/no-asistio

### Tab 5: Facturacion

- Balance summary card: total owed, last payment date, payment method
- Invoice list: date, number, amount, status (pagada/pendiente/vencida)
- "Registrar pago" and "Nueva factura" buttons

### Tab 6: Documentos

- Thumbnail grid of uploaded documents + consent forms
- Type icons: PDF (red), image (blue), consent (teal)
- "Subir documento" button
- "Descargar" and "Ver" actions per item

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get patient | `/api/v1/patients/{id}` | GET | `specs/patients/patient-get.md` | 5min |
| Get timeline | `/api/v1/patients/{id}/history` | GET | `specs/patients/patient-history.md` | 2min |
| Get clinical records | `/api/v1/patients/{id}/records` | GET | `specs/clinical-records/record-list.md` | 2min |
| Get treatment plans | `/api/v1/patients/{id}/treatment-plans` | GET | `specs/treatment-plans/plan-list.md` | 2min |
| Get appointments | `/api/v1/patients/{id}/appointments` | GET | `specs/appointments/appointment-list.md` | 2min |
| Get billing | `/api/v1/patients/{id}/billing` | GET | `specs/billing/patient-balance.md` | 2min |

### State Management

**Local State (useState):**
- `activeTab: number` — current active tab index
- `loadedTabs: Set<number>` — tabs that have been visited (for lazy-load cache)

**Global State (Zustand):**
- `recentPatientsStore` — add patient to "recently viewed" list (max 5 items) on page mount

**Server State (TanStack Query):**
- Patient base query: `useQuery({ queryKey: ['patient', id], staleTime: 5 * 60 * 1000 })`
- Tab queries: each tab uses its own query key, `enabled` only after tab is first visited
- Example: `useQuery({ queryKey: ['patient-records', id, page], enabled: activeTab === 2 })`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click tab | Click or keyboard | Load tab content (if first visit) | Skeleton while loading |
| Click "Editar" | Button | Navigate to `/patients/{id}/edit` | Standard navigation |
| Click "Nuevo Turno" | Button | Open appointment modal | Modal overlay |
| Click phone number | Tap (mobile) | Opens `tel:` link | Native phone dialer |
| Click allergy badge | Click | Tooltip shows all allergies | Popover above badge |
| Click "Ver historial completo" | Link | Load full timeline | Spinner inline |

### Animations/Transitions

- Tab content transition: fade `opacity-0 → opacity-100` 150ms when switching tabs
- Summary card on scroll (desktop): becomes sticky with `shadow-sm` added after 100px scroll
- Balance badge: red pulse animation if balance > 0 (draws attention on first load)

---

## Loading & Error States

### Loading State
- Summary card skeleton: `h-24 animate-pulse bg-gray-100 rounded-xl` + text skeleton lines
- Tab content skeleton: varies by tab, matching expected layout
- Tab badge counts: `h-4 w-6 bg-gray-200 rounded animate-pulse` inline

### Error State
- Patient not found (404): full-page error state with "Paciente no encontrado" + back button
- Network error: toast `"Error al cargar los datos del paciente"` + "Reintentar" button
- Per-tab error: inline error message within tab content + retry button

### Empty State
- No timeline events: illustration + "Sin actividad registrada" + "Crear primera consulta" CTA
- Each tab has its own empty state with relevant CTA

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Summary card shows condensed info (name, phone, balance). Tabs scroll horizontally. Quick actions collapse to overflow `...` menu. |
| Tablet (640-1024px) | Summary card full width. All quick action buttons visible. Tabs fit without scroll. |
| Desktop (> 1024px) | Summary card sticky on scroll. Two-panel layout option: summary left `w-1/3`, tab content right `w-2/3` (if viewport > 1280px). |

**Tablet priority:** Critical — this is the primary clinical workflow screen. All touch targets min 44px. Tab targets min 44px height.

---

## Accessibility

- **Focus order:** Summary card (read) → Edit button → Quick action buttons → Tab bar → Tab content
- **Screen reader:** `role="tablist"` on tab bar, `role="tab"` on each tab, `role="tabpanel"` on content area. `aria-selected` on active tab. `aria-label="Paciente: {nombre}"` on summary card. Balance badge `aria-label="Saldo pendiente: $45.000"` or `aria-label="Sin saldo pendiente"`.
- **Keyboard navigation:** Arrow keys navigate between tabs. Enter/Space activates tab. Tab key moves to tab content from tab bar.
- **Color contrast:** WCAG AA. Red balance text on white meets 4.5:1. Alert chip text on colored background verified.
- **Language:** All labels and UI text in es-419.

---

## Design Tokens

**Colors:**
- Summary card: `bg-white shadow-sm rounded-xl border border-gray-100`
- Quick actions: `border border-teal-600 text-teal-600 hover:bg-teal-50`
- Active tab: `border-b-2 border-teal-600 text-teal-700 font-medium`
- Inactive tab: `text-gray-500 hover:text-gray-700`
- Balance red: `text-red-600 font-medium`
- Allergy badge: `bg-red-100 text-red-700`
- Condition badge: `bg-amber-100 text-amber-700`

**Typography:**
- Patient name: `text-2xl font-bold text-gray-900`
- Key data: `text-sm text-gray-600`
- Tab label: `text-sm font-medium`

**Spacing:**
- Page: `px-4 md:px-6 py-6`
- Summary card padding: `p-5 md:p-6`
- Quick actions margin: `mt-4`
- Tab bar margin: `mt-6`
- Tab content padding: `pt-5`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — CalendarPlus, FilePlus, ClipboardList, Phone, AlertCircle, Edit
- `@tanstack/react-query` — per-tab queries with `enabled` flag

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/page.tsx`
- Components: `src/components/patients/PatientSummaryCard.tsx`, `src/components/patients/PatientTabs.tsx`, `src/components/patients/tabs/TimelineTab.tsx`, `src/components/patients/tabs/OdontogramTab.tsx`, `src/components/patients/tabs/RecordsTab.tsx`, etc.
- Store: `src/stores/recentPatientsStore.ts`

**Hooks Used:**
- `useQuery(['patient', id])` — base patient data
- `useQuery(['patient-{tab}', id])` — per-tab data, `enabled: activeTab === n`
- `useRecentPatientsStore()` — add to recents on mount

---

## Test Cases

### Happy Path
1. View complete patient profile
   - **Given:** Patient with full history exists
   - **When:** Doctor navigates to patient detail
   - **Then:** Summary card loads, default tab (Resumen) shows timeline events

### Edge Cases
1. Patient with no history
   - **Given:** Newly created patient, no appointments or records
   - **When:** Doctor opens patient detail
   - **Then:** Summary card shows "Sin consultas previas", all tabs show empty states

2. Switching tabs rapidly
   - **Given:** Multiple tabs clicked in quick succession
   - **When:** Tabs fire before previous queries complete
   - **Then:** Only the latest active tab shows loading, no duplicate API calls

### Error Cases
1. Patient deleted or not found
   - **Given:** Patient ID in URL is invalid
   - **When:** Page loads
   - **Then:** 404 error state with "Paciente no encontrado" and back button

---

## Acceptance Criteria

- [ ] Summary card shows photo/initials, name, document, age, phone, last visit, balance, alert badges
- [ ] Quick action buttons: new appointment, new record, new treatment plan
- [ ] 7 tabs with correct labels and badge counts
- [ ] Tabs lazy-load on first visit, cache on revisit
- [ ] Embedded odontogram renders in Odontograma tab
- [ ] Each tab shows appropriate empty state when no data
- [ ] Patient added to "recently viewed" store on mount
- [ ] Loading skeletons for summary card and each tab
- [ ] Responsive on mobile (condensed), tablet, and desktop
- [ ] Accessibility: tablist ARIA, keyboard tab navigation
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
