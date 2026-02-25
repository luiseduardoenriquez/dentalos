# Historial Medico del Paciente (Patient Medical History) — Frontend Spec

## Overview

**Screen:** Chronological medical history timeline displayed within the "Resumen" tab of the patient detail page. Lists all clinical events: appointments, diagnoses, procedures, odontogram changes, prescriptions, and consent signatures. Supports filtering by event type, date range, and doctor. Uses infinite scroll. Event cards expand on click to show full details.

**Route:** Embedded in `/patients/{id}` (Resumen tab, Tab 0)

**Priority:** High

**Backend Specs:** `specs/patients/patient-history.md` (P-07)

**Dependencies:** `specs/frontend/patients/patient-detail.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Patient detail page opening on default "Resumen" tab
- Direct link `#tab-resumen` from other tabs (e.g., "Ver historial" link in clinical records tab)

**Exit Points:**
- Click appointment event → appointment detail view
- Click procedure event → clinical record detail
- Click odontogram change event → odontogram with that date's snapshot
- Click prescription event → prescription PDF preview
- Click consent event → consent document viewer
- "Nueva consulta" CTA (empty state) → `/patients/{id}/records/new`

**User Story:**
> As a doctor | assistant, I want to see a chronological history of everything that has happened with a patient so that I can quickly understand their clinical progression without opening each record individually.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`, `receptionist`

---

## Layout Structure

```
+--------------------------------------------------+
|  [Filter bar: Type | Date range | Doctor]        |
|  [Active filter chips]                           |
+--------------------------------------------------+
|                                                  |
|  2026                                            |
|  | (timeline line)                               |
|  O  [Event card: Appointment]     Feb 20         |
|  |                                               |
|  O  [Event card: Procedure]       Feb 15         |
|  |                                               |
|  O  [Event card: Odontogram]      Feb 10         |
|  |                                               |
|  2025                                            |
|  |                                               |
|  O  [Event card: Appointment]     Dec 12         |
|  |                                               |
|  [Cargar mas eventos btn / infinite scroll]      |
|                                                  |
+--------------------------------------------------+
```

**Sections:**
1. Filter bar — type filter, date range picker, doctor selector
2. Active filter chips — shows applied filters with X to remove each
3. Timeline — year dividers + event cards arranged chronologically (newest first)
4. Load more — infinite scroll trigger or "Cargar mas eventos" button fallback

---

## UI Components

### Component 1: FilterBar

**Type:** Horizontal filter row

**Filters:**

| Filter | Type | Options |
|--------|------|---------|
| Tipo de evento | Multi-select dropdown | Todos / Cita / Diagnostico / Procedimiento / Odontograma / Receta / Consentimiento |
| Fecha | Date range picker | Custom start + end date, or presets: Ultima semana / Ultimo mes / Ultimo año |
| Doctor | Single-select dropdown | All doctors in tenant |

**Active filter chips:** Each applied filter shows as `bg-teal-100 text-teal-800 text-xs rounded-full px-3 py-1` chip with `X` button to clear.
"Limpiar filtros" link clears all when any filter is active.

**Mobile filter behavior:** Filters collapse into a "Filtrar" icon button that opens a bottom sheet with all filter controls.

### Component 2: TimelineYearDivider

**Type:** Visual separator

**Design:** `"2026"` in `text-sm font-bold text-gray-400 uppercase` centered with horizontal lines on either side: `flex items-center gap-3`. Sticky while scrolling past year events.

### Component 3: TimelineLine

**Type:** Visual vertical connector

**Design:** `w-px bg-gray-200 dark:bg-gray-700 absolute left-[19px] top-0 bottom-0` within a `relative` parent. Event dots sit on this line.

### Component 4: EventCard

**Type:** Expandable card

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Collapsed state:**
```
[Icon circle] [Event type badge] [Summary text]       [Date]
                                [Doctor name]
```

**Expanded state (on click):**
- Full detail content for the event type
- "Ver completo" link to full record/appointment page

**Event type configurations:**

| Type | Icon | Badge color | Badge label | Collapsed summary |
|------|------|-------------|-------------|-------------------|
| `appointment` | `Calendar` | `bg-blue-100 text-blue-700` | Cita | "Cita con Dr. {name} — {type}" |
| `diagnosis` | `Stethoscope` | `bg-purple-100 text-purple-700` | Diagnostico | "{CIE-10 code}: {description}" |
| `procedure` | `Wrench` | `bg-teal-100 text-teal-700` | Procedimiento | "{CUPS code}: {description}" |
| `odontogram_change` | `Grid2x2` | `bg-indigo-100 text-indigo-700` | Odontograma | "{N} cambios — Dientes {list}" |
| `prescription` | `Pill` | `bg-green-100 text-green-700` | Receta | "{N} medicamentos prescritos" |
| `consent` | `FileCheck` | `bg-gray-100 text-gray-700` | Consentimiento | "{consent type} — {Firmado/Pendiente}" |

**Icon circle:** `w-10 h-10 rounded-full` with event-type background color, icon centered, sits on timeline line.

**Expanded content per event type:**

- **Appointment:** Status badge, duration, notes summary, attending doctor, reason for visit, paid/pending indicator
- **Diagnosis:** Full CIE-10 code + description, notes, doctor, severity
- **Procedure:** CUPS code + description, tooth numbers (FDI), anesthesia used, materials, cost, doctor
- **Odontogram change:** Before/after summary table — tooth FDI | condition | action (added/removed)
- **Prescription:** Table: Medicamento | Dosis | Frecuencia | Duracion
- **Consent:** Document type, status (Firmado / Pendiente), signature date, "Ver documento" link

**Animation:** `motion.div` height expand on click, `overflow-hidden`, 250ms ease-out.

### Component 5: InfiniteScrollTrigger

**Type:** Intersection Observer trigger

**Behavior:**
- `div` at bottom of timeline list
- When scrolled into viewport: fires next page query `useInfiniteQuery`
- Shows `Loader2 animate-spin` while loading next page
- "Has llegado al final del historial" when no more pages

---

## Form Fields / Filters

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| tipo_evento | multi-select | All event types | "Todos" (none selected = all) |
| fecha_inicio | date | YYYY-MM-DD | null |
| fecha_fin | date | YYYY-MM-DD | null (today) |
| doctor_id | select | Tenant doctors | null (all) |

**Preset ranges:**
- "Ultima semana": `fecha_inicio = today - 7d`
- "Ultimo mes": `fecha_inicio = today - 30d`
- "Ultimos 3 meses": `fecha_inicio = today - 90d`
- "Ultimo año": `fecha_inicio = today - 365d`
- "Personalizado": activates date pickers

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get history | `/api/v1/patients/{id}/history` | GET | `specs/patients/patient-history.md` | 2min |
| Get next page | `/api/v1/patients/{id}/history?cursor={cursor}` | GET | `specs/patients/patient-history.md` | 2min |

### Query Parameters

```
?limit=20
&cursor={cursor_token}
&event_types=appointment,procedure
&date_from=2025-01-01
&date_to=2026-02-25
&doctor_id={uuid}
```

### Response Shape

```typescript
{
  events: HistoryEvent[];
  next_cursor: string | null;
  total_count: number;
}
```

### State Management

**Local State (useState):**
- `expandedEventId: string | null` — currently expanded event card
- `filters: { eventTypes, dateFrom, dateTo, doctorId }`

**Server State (TanStack Query):**
- `useInfiniteQuery({
    queryKey: ['patient-history', patientId, filters],
    queryFn: ({ pageParam: cursor }) => fetchHistory(patientId, { ...filters, cursor }),
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    staleTime: 2 * 60 * 1000,
  })`

**Filter change:** Query key includes filters object — changing any filter resets to page 1.

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click event card | Click | Expand detail inline | Height animation 250ms |
| Click same card again | Click | Collapse detail | Height animation 250ms |
| Click "Ver completo" | Click (expanded card) | Navigate to record detail | Standard navigation |
| Select filter | Dropdown change | Refetch with new filters | Spinner replaces timeline |
| Add date range | Date pickers | Refetch | Active filter chip appears |
| Click X on filter chip | Click | Remove that filter | Refetch, chip disappears |
| Scroll to bottom | Intersection | Load next 20 events | Loader at bottom |
| Click "Nuevo turno" (empty state) | Click | Open appointment modal | Modal |

### Animations/Transitions

- Event card expansion: `motion.div` `height: 0 → auto` 250ms `ease-out`
- Filter chip appear: `scale 0.8 → 1, opacity 0 → 1` 150ms
- New events loaded (infinite scroll): slide in from bottom `y: 16 → 0, opacity 0 → 1` staggered 50ms per card

---

## Loading & Error States

### Loading State

**Initial load:**
- 5 skeleton event cards: each `h-16 animate-pulse bg-gray-100 rounded-xl mx-4 mb-3` with icon circle skeleton on left

**Refetch (filter change):**
- Timeline area: `opacity-50 pointer-events-none` while refetching
- Spinner centered over timeline area

**Next page (infinite scroll):**
- `Loader2 animate-spin text-teal-600` centered at bottom of list

### Error State

- API error: inline banner above timeline: `bg-red-50 border-red-200` + "Error al cargar el historial. [Reintentar]" button
- Empty filtered results: illustration + "Sin eventos con los filtros seleccionados" + "Limpiar filtros" CTA

### Empty State

- No history at all (new patient): centered illustration (medical clipboard) + `"Sin historial clinico"` `text-lg font-semibold text-gray-400` + `"Cuando se registren consultas, procedimientos y citas, apareceran aqui."` + "Crear primera consulta" button → `/patients/{id}/records/new`

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Filter bar collapses to single "Filtrar" button opening bottom sheet. Timeline line hidden; event cards full-width without left margin. Date shown at top of each card instead of right-aligned. |
| Tablet (640-1024px) | Filter bar full horizontal. Timeline line visible, cards with left padding `pl-12`. Year dividers sticky. |
| Desktop (> 1024px) | Same as tablet. Cards `max-w-2xl`. Filter bar includes all controls inline. |

**Tablet priority:** High — doctors review history on tablets during consultation. Touch targets min 44px for event cards. Filter dropdowns min 44px height.

---

## Accessibility

- **Focus order:** Filter controls → active filter chips → timeline events top-to-bottom → "Cargar mas" button
- **Screen reader:** `aria-label` per event card: "Evento: {type}, {date}, {summary}". Expanded detail: `aria-expanded="true/false"` on card button. Timeline list: `role="list"`. Year dividers: `role="separator" aria-label="Eventos de {year}"`. Filter chips: `aria-label="Filtro activo: {filter name}. Clic para eliminar"`.
- **Keyboard navigation:** Enter/Space expands/collapses event cards. Arrow keys navigate between filter chip X buttons. Tab follows filter → chips → events → load more.
- **Color contrast:** Event type badge text on colored backgrounds verified WCAG AA. Icon circles use sufficient contrast for icons.
- **Language:** All labels, event type names, and messages in es-419.

---

## Design Tokens

**Colors:**
- Timeline line: `bg-gray-200`
- Event card: `bg-white border border-gray-100 hover:border-gray-200 shadow-xs hover:shadow-sm`
- Appointment badge: `bg-blue-100 text-blue-700`
- Procedure badge: `bg-teal-100 text-teal-700`
- Diagnosis badge: `bg-purple-100 text-purple-700`
- Odontogram badge: `bg-indigo-100 text-indigo-700`
- Prescription badge: `bg-green-100 text-green-700`
- Consent badge: `bg-gray-100 text-gray-700`
- Active filter chip: `bg-teal-100 text-teal-800`
- Year divider: `text-gray-400`

**Typography:**
- Event summary: `text-sm font-medium text-gray-800`
- Doctor name: `text-xs text-gray-500`
- Date: `text-xs text-gray-400`
- Expanded detail key: `text-xs font-semibold text-gray-500 uppercase`
- Expanded detail value: `text-sm text-gray-800`
- Year divider: `text-sm font-bold uppercase tracking-wide`

**Spacing:**
- Timeline left padding: `pl-12` (for icon + line)
- Event card: `p-4 rounded-xl mb-3`
- Expanded content: `pt-3 mt-3 border-t border-gray-100`
- Icon circle: `w-10 h-10 absolute left-0`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — `useInfiniteQuery`
- `framer-motion` — card expand/collapse, new events slide-in
- `lucide-react` — Calendar, Stethoscope, Wrench, Grid2x2, Pill, FileCheck, Loader2
- `react-intersection-observer` — `useInView` for infinite scroll trigger

**File Location:**
- Component: `src/components/patients/MedicalHistoryTimeline.tsx`
- Sub-components: `src/components/patients/timeline/EventCard.tsx`, `src/components/patients/timeline/FilterBar.tsx`, `src/components/patients/timeline/TimelineYearDivider.tsx`
- API: `src/lib/api/patients.ts`

**Hooks Used:**
- `useInfiniteQuery(['patient-history', patientId, filters])` — paginated history
- `useInView({ threshold: 0.5 })` — infinite scroll trigger
- `useState(filters)` — local filter state

---

## Test Cases

### Happy Path
1. Doctor views full timeline
   - **Given:** Patient with 3 years of history
   - **When:** Doctor opens Resumen tab
   - **Then:** Last 20 events shown chronologically, year dividers present, scroll loads more

2. Filter by procedure type
   - **Given:** Patient has mix of appointments and procedures
   - **When:** Doctor selects "Procedimiento" filter
   - **Then:** Only procedure events shown, filter chip displayed, count updates

### Edge Cases
1. Expand and collapse event
   - **Given:** Timeline with multiple events visible
   - **When:** Click procedure event to expand, click again to collapse
   - **Then:** Height animates open and closed, only one event expanded at a time

2. Filter combination returns no results
   - **Given:** Filter: doctor = "Dr. Lopez", date = last week, type = "Receta"
   - **When:** No prescriptions by that doctor in that range
   - **Then:** Empty state "Sin eventos con los filtros seleccionados" with clear filters link

### Error Cases
1. API timeout on filter change
   - **Given:** Slow network
   - **When:** User applies date filter, API takes > 5s
   - **Then:** Timeline stays visible at 50% opacity with spinner, after timeout: error banner + retry button

---

## Acceptance Criteria

- [ ] Chronological timeline newest-first with year dividers
- [ ] 7 event types rendered with correct icons, badge colors, and labels
- [ ] Each event card shows type badge, summary, date, and doctor name
- [ ] Click to expand shows full event detail inline
- [ ] "Ver completo" link on expanded card navigates to full record
- [ ] Filter by event type (multi-select), date range, and doctor
- [ ] Active filters shown as removable chips
- [ ] Infinite scroll loads next 20 events when scrolled to bottom
- [ ] "Cargar mas" fallback button for non-scroll environments
- [ ] Loading skeletons for initial load
- [ ] Empty state for new patients with "crear primera consulta" CTA
- [ ] Filtered empty state with "limpiar filtros" CTA
- [ ] Responsive: mobile bottom-sheet filters, full bar on tablet+
- [ ] Accessibility: ARIA roles, keyboard expand/collapse, live announcements
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
