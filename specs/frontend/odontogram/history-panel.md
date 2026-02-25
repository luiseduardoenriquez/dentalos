# Panel de Historial de Odontograma — Frontend Spec

## Overview

**Screen:** History panel component showing a chronological timeline of all changes made to a patient's odontogram. Displays each change with doctor avatar, tooth number, zone, old and new condition, and source badge (manual or voice). Supports filtering by tooth, condition, and date. Implemented as a sidebar (desktop) or bottom drawer (tablet).

**Route:** Not a standalone route — embedded in `/patients/{id}/odontogram` (both classic and anatomic views)

**Priority:** Medium

**Backend Specs:**
- `specs/odontogram/OD-04` — Get odontogram history (paginated timeline)

**Dependencies:**
- `specs/frontend/odontogram/classic-grid.md` (FE-OD-01) — parent in classic mode
- `specs/frontend/odontogram/anatomic-arch.md` (FE-OD-02) — parent in anatomic mode

---

## User Flow

**Entry Points:**
- Always visible in the odontogram view (sidebar on desktop, bottom drawer on tablet)
- Also accessible filtered by tooth from `ToothDetailModal` (FE-OD-06) via "Ver historial completo" link
- Can be pre-filtered by tooth when opened from tooth detail

**Exit Points:**
- Panel is persistent — user stays in odontogram view
- Clicking an entry with a tooth reference highlights that tooth in the arch/grid

**User Story:**
> As a doctor or clinic owner, I want to see a complete timeline of all condition changes made to a patient's odontogram so that I can audit clinical decisions and track treatment progression.

**Roles with access:** clinic_owner, doctor, assistant (read); receptionist (read)

---

## Layout Structure

### Desktop Sidebar
```
+---------------------------+
|  Historial de cambios     |
|  [Filter bar]             |
|  [Search/filter controls] |
+---------------------------+
| [HistoryEntry 1]          |
|   Dr. Martinez  •  hace 2h|
|   Diente 36 > Oclusal     |
|   [ninguna] → [Caries]    |
|   [MANUAL]                |
+---------------------------+
| [HistoryEntry 2]          |
|   Dra. Lopez  •  ayer     |
|   Diente 16 > Mesial      |
|   [Caries] → [Obturado]   |
|   [VOZ]                   |
+---------------------------+
| [Cargar mas...]           |
+---------------------------+
```

### Tablet (Bottom Drawer)
```
+------------------------------------------+
| Historial  [Filter] [X close]             |
+------------------------------------------+
| [HistoryEntry 1] [HistoryEntry 2] (scroll)|
+------------------------------------------+
| [Swipe down to collapse]                  |
+------------------------------------------+
```

**Sections:**
1. Panel header — title + filter controls + collapse/close button
2. Filter bar — tooth number filter, condition filter, date range filter
3. Scrollable timeline — chronological list of HistoryEntry components
4. Infinite scroll loader — "Cargar mas" button or auto-load sentinel

---

## UI Components

### Component 1: HistoryPanel

**Type:** Sidebar / Bottom Drawer

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6 (Drawer)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Patient UUID for API calls |
| filterByToothId | number \| null | null | Pre-filter to a specific tooth |
| layout | "sidebar" \| "drawer" | "sidebar" | Responsive layout mode |
| onToothHighlight | (toothId: number) => void | — | Highlight tooth in odontogram grid |

**States:**
- Collapsed (tablet) — 40px drag handle visible at bottom
- Expanded (tablet) — slides up to 60% viewport height
- Full sidebar (desktop) — fixed width 260px, full height
- Loading initial — skeleton entries
- Filtering active — spinner in filter bar, entries reload

---

### Component 2: HistoryEntry

**Type:** Timeline card

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| entry | OdontogramHistoryEntry | — | History entry data |
| onToothClick | (toothId: number) => void | — | Highlights tooth in arch/grid |

**Anatomy:**
```
+--------------------------------------+
| [Avatar] Dr. Martinez    hace 2h     |
|          Diente 36 • Oclusal         |
|          [sin condicion] → [Caries]  |
|          [MANUAL]                    |
+--------------------------------------+
```

- **Avatar:** 28px circle with user initials or photo. Tooltip on hover: full name + role.
- **Doctor name:** `text-sm font-medium text-gray-800`
- **Timestamp:** relative time (hace 2h, ayer, 15 feb) with full ISO timestamp in tooltip
- **Tooth reference:** `Diente {FDI} • {zone_name_spanish}` — clickable link that triggers `onToothClick`
- **Old condition:** gray pill badge or `text-gray-400 italic "sin condicion"` if null
- **Arrow:** `→` separator
- **New condition:** colored pill badge with condition color dot + name
- **Source badge:** small badge, two variants:
  - `MANUAL`: `bg-gray-100 text-gray-600 text-xs` — change made via condition panel
  - `VOZ`: `bg-purple-100 text-purple-700 text-xs` with microphone icon — change made via voice input (FE-V-01)

**States:**
- Default: standard card appearance
- Hovered: subtle `bg-gray-50` background
- Tooth highlighted: tooth reference link underlined on hover

---

### Component 3: HistoryFilterBar

**Type:** Filter controls row

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| filters | HistoryFilters | {} | Currently active filters |
| onFiltersChange | (filters) => void | — | Handler when filters change |
| teeth | number[] | [] | Available tooth numbers with entries |
| conditions | Condition[] | [] | Available conditions in history |

**Filter controls:**
1. Tooth filter: `<Select>` dropdown — options "Todos los dientes" + tooth numbers with entry count
2. Condition filter: `<Select>` dropdown — "Todas las condiciones" + condition names
3. Date filter: Quick presets as chip buttons: "Hoy", "Esta semana", "Este mes", "Todo"
4. Clear filters: "Limpiar filtros" link shown when any filter active

**States:**
- No filters: all chips unselected, dropdowns show "Todos..."
- Filter active: active chip/dropdown highlighted; count badge "Filtrado: {N} resultados"
- Loading after filter change: spinner in panel, entries fade out then reload

---

## Form Fields

Not applicable — panel is read-only display with filter controls, no data entry.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load history | `/api/v1/patients/{id}/odontogram/history` | GET | `specs/odontogram/OD-04` | 30s stale |
| Load more (pagination) | `/api/v1/patients/{id}/odontogram/history?cursor={cursor}` | GET | `specs/odontogram/OD-04` | No cache |

### State Management

**Local State (useState):**
- `filters: HistoryFilters` — `{ toothId?: number, conditionId?: string, dateRange?: 'today' | 'week' | 'month' | 'all' }`
- `isDrawerOpen: boolean` — tablet bottom drawer open/closed state

**Global State (Zustand — useOdontogramStore):**
- `changeLog: ChangeEntry[]` — real-time session changes prepended to history list before server data loads

**Server State (TanStack Query — infinite query):**
- Query key: `['odontogram-history', patientId, tenantId, filters]`
- Stale time: 30 seconds
- `useInfiniteQuery` — cursor-based pagination
  - `getNextPageParam`: extracts `next_cursor` from each page response
  - Each page: 20 entries
- New entries from current session (`changeLog`) prepended to the top of the list in memory (not from API until re-fetch)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click tooth reference | Click "Diente {FDI}" link in entry | Calls `onToothHighlight(toothId)` — parent highlights tooth in grid | Tooth ring in arch/grid |
| Change tooth filter | Select from dropdown | Re-runs query with `tooth_id` filter | Spinner + list reload |
| Change condition filter | Select from dropdown | Re-runs query with `condition_id` filter | Spinner + list reload |
| Click date preset chip | Click "Esta semana" etc. | Re-runs query with date filter | Active chip highlighted + reload |
| Scroll to bottom | Scroll past last entry | Triggers next page load if available | "Cargando mas..." indicator |
| Click "Cargar mas" button | Click (fallback for scroll) | Fetches next page | Button spinner |
| Collapse drawer (tablet) | Swipe down or close button | Drawer collapses to 40px handle | Smooth slide down animation |
| Expand drawer (tablet) | Tap handle or swipe up | Drawer expands to 60% height | Smooth slide up animation |

### Animations/Transitions

- New entry from current session: slides in from top with `motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}` — 150ms ease-in
- Drawer expand/collapse (tablet): `motion.div` height animation — 250ms spring
- Filter change transition: entries fade out 100ms → spinner → new entries fade in 150ms
- Infinite scroll loader: `<Loader2 className="animate-spin">` at bottom while fetching

---

## Loading & Error States

### Loading State
- Initial load: 5 skeleton HistoryEntry cards — gray avatar circle + three gray text lines + two gray condition badges, `animate-pulse`
- Infinite scroll "load more": single `<Loader2>` spinner centered below last entry
- Filter re-load: existing entries fade to `opacity-50` + overlay spinner in panel header

### Error State
- Initial load fails: centered error state in panel
  - Message: "No se pudo cargar el historial. Intenta de nuevo."
  - Button: "Reintentar" → re-runs query
- Pagination load fails: toast error at bottom
  - Message: "Error al cargar mas entradas. Intenta de nuevo."
  - "Cargar mas" button re-enabled

### Empty State
- No history at all: `HistoryEntry` list is empty
  - Illustration: clock/calendar icon (gray)
  - Message: "Sin cambios registrados. Los cambios en el odontograma apareceran aqui."
- No history matching filters: filtered empty state
  - Message: "Sin resultados para los filtros seleccionados."
  - CTA: "Limpiar filtros" link

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Not shown — odontogram not supported on mobile |
| Tablet (640-1024px) | Bottom drawer pattern. Collapsed by default (40px handle). Tap/swipe to expand to 60% height. Horizontal scroll of entries in expanded state optional. Date filter chips wrap to 2 rows. |
| Desktop (> 1024px) | Fixed right sidebar — 260px wide, full height, always visible. Vertical scroll. All filter controls visible without collapsing. |

**Tablet priority:** High — drawer must be fluid and not block the odontogram while collapsed. Swipe gesture must have 44px+ drag handle. Avatar circles 32px minimum.

---

## Accessibility

- **Focus order:** Panel header → Filter controls (tooth → condition → date presets → clear) → History entries (top to bottom) → Load more button
- **Screen reader:** Panel has `role="complementary"` with `aria-label="Historial de cambios del odontograma"`. Each HistoryEntry has `role="article"` and `aria-label="Cambio por {doctor_name} en diente {FDI}, zona {zone}: {old} a {new}, {timestamp}"`. New real-time entries announced via `aria-live="polite"` region.
- **Keyboard navigation:** Tab navigates between entries; Enter/Space on tooth reference link triggers highlight. Filter selects accessible via standard keyboard. Drawer collapse/expand: Escape collapses, Enter on handle expands.
- **Color contrast:** Condition color badges include text name (not color only). WCAG AA for all text. Source badges: gray-100/gray-600 and purple-100/purple-700 both pass.
- **Language:** All labels in es-419. "sin condicion" for null old condition. Relative timestamps in Spanish: "hace 2 horas", "ayer", "el 15 de febrero". Source badges: "MANUAL", "VOZ".

---

## Design Tokens

**Colors:**
- Panel background: `bg-white dark:bg-gray-900`
- Panel border: `border-l border-gray-200 dark:border-gray-700`
- Entry hover: `hover:bg-gray-50 dark:hover:bg-gray-800`
- Condition badge (old/removed): `bg-gray-100 text-gray-600`
- Source badge manual: `bg-gray-100 text-gray-600`
- Source badge voice: `bg-purple-100 text-purple-700`
- Tooth reference link: `text-blue-600 hover:text-blue-700 underline cursor-pointer`
- Timestamp text: `text-xs text-gray-400`

**Typography:**
- Panel title: `text-sm font-semibold text-gray-800 dark:text-gray-100`
- Doctor name: `text-sm font-medium text-gray-800`
- Entry detail: `text-xs text-gray-600`
- Filter label: `text-xs font-medium text-gray-500 uppercase tracking-wide`

**Spacing:**
- Panel width (desktop): `w-[260px]`
- Entry padding: `p-3`
- Entry gap: `gap-0 divide-y divide-gray-100`
- Avatar size: `w-7 h-7` (28px)
- Drawer handle: `h-10` (40px)

**Border Radius:**
- Condition badges: `rounded-full`
- Source badge: `rounded-full`
- Drawer handle: `rounded-t-xl`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — `useInfiniteQuery` for cursor-based pagination
- `zustand` — read `changeLog` from `useOdontogramStore`
- `framer-motion` — new entry slide animation; drawer slide on tablet
- `lucide-react` — Mic (voice badge), Clock, AlertTriangle, Loader2, ChevronUp/Down

**File Location:**
- Component: `src/components/odontogram/HistoryPanel.tsx`
- Sub-components:
  - `src/components/odontogram/HistoryEntry.tsx`
  - `src/components/odontogram/HistoryFilterBar.tsx`
- Store: `src/stores/odontogramStore.ts`
- Types: `src/types/odontogram.ts`
- API: `src/lib/api/odontogram.ts`

**Hooks Used:**
- `useInfiniteQuery(['odontogram-history', patientId, filters])` — paginated history
- `useOdontogramStore()` — reads `changeLog` for real-time session prepend
- `useAuth()` — role check (no role restrictions, all read)
- `useMediaQuery('(min-width: 1024px)')` — switch between sidebar and drawer

**Infinite scroll implementation:**
- Use `IntersectionObserver` on a sentinel div at the bottom of the list
- When sentinel enters viewport: call `fetchNextPage()` if `hasNextPage`
- Fallback: "Cargar mas" button for accessibility (when JS scroll detection unavailable)

**Real-time prepend:**
- `changeLog` entries from `useOdontogramStore` are prepended to the rendered list before server data
- On next query refetch, server data includes these entries and `changeLog` is cleared

---

## Test Cases

### Happy Path
1. Doctor opens odontogram — history panel shows existing entries
   - **Given:** Patient has 15 change history entries from 3 doctors
   - **When:** Odontogram page loads
   - **Then:** Panel shows 15 entries with doctor avatars, timestamps, condition changes, source badges

2. Real-time entry appears after saving a condition
   - **Given:** History panel loaded, doctor saves a condition change in panel
   - **When:** "Registrar" clicked and PATCH succeeds
   - **Then:** New entry slides in at top of history within 100ms; no full refetch needed

3. Filter by tooth narrows entries
   - **Given:** Panel shows 15 entries across 8 teeth
   - **When:** Doctor selects "Diente 36" in tooth filter dropdown
   - **Then:** List reloads showing only entries for tooth 36 (e.g., 4 entries); filter chip shows active state

4. Infinite scroll loads more entries
   - **Given:** Patient has 45 history entries; first 20 loaded
   - **When:** Doctor scrolls to bottom of history panel
   - **Then:** "Cargando mas..." spinner appears; next 20 entries append to list

5. Tooth link highlights tooth in arch
   - **Given:** History entry shows "Diente 36"
   - **When:** Doctor clicks "Diente 36" link in entry
   - **Then:** `onToothHighlight(36)` called; tooth 36 gets highlight ring in arch/grid

### Edge Cases
1. Patient with no odontogram history
   - **Given:** Brand new patient with no condition changes recorded
   - **When:** Panel loads
   - **Then:** Empty state: clock icon + "Sin cambios registrados..."

2. Filter returns no results
   - **Given:** Filter by "Diente 99" (no entries for that tooth)
   - **When:** Filter applied
   - **Then:** Filtered empty state: "Sin resultados para los filtros seleccionados." + "Limpiar filtros"

3. All date filters applied simultaneously
   - **Given:** Tooth filter + condition filter + date preset all active
   - **When:** Entries load
   - **Then:** Only entries matching ALL active filters shown; "Filtrado: N resultados" badge visible

### Error Cases
1. OD-04 fails on initial load
   - **Given:** History API returns 503
   - **When:** Panel renders
   - **Then:** Error state in panel; "No se pudo cargar el historial. Reintentar."

2. Pagination load fails
   - **Given:** Scrolled to bottom, next page request returns 500
   - **When:** Fetch next page triggered
   - **Then:** Toast error; "Cargar mas" button re-enabled; existing entries remain

---

## Acceptance Criteria

- [ ] History panel renders as right sidebar (desktop) and bottom drawer (tablet)
- [ ] Each entry shows: doctor avatar, name, relative timestamp, tooth + zone, old → new condition, source badge
- [ ] Source badge: "MANUAL" for manual changes, "VOZ" for voice input changes
- [ ] Real-time entries from current session appear at top without page reload
- [ ] Filter by tooth, condition, and date works correctly
- [ ] Inactive filters show "Todos..." dropdowns; active filters show highlight
- [ ] "Limpiar filtros" clears all active filters
- [ ] Infinite scroll: auto-loads next page when scrolled to bottom
- [ ] "Cargar mas" fallback button works for accessibility
- [ ] Empty state with message when no history
- [ ] Filtered empty state with "Limpiar filtros" CTA
- [ ] Loading skeleton: 5 skeleton entries on initial load
- [ ] Error state with retry button
- [ ] Tablet: bottom drawer with swipe gesture and 40px handle
- [ ] Drawer collapses without blocking odontogram
- [ ] Tooth reference links trigger `onToothHighlight` in parent
- [ ] All labels and timestamps in Spanish (es-419)
- [ ] Accessibility: ARIA roles, live region for new entries, keyboard navigation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
