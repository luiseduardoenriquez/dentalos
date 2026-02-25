# Busqueda Global de Pacientes (Patient Search) — Frontend Spec

## Overview

**Screen:** Global patient search component permanently displayed in the application header bar. Provides instant typeahead with 300ms debounce, shows recent patients (last 5 viewed) when input is empty, and returns mini-card results on search. Supports keyboard navigation with arrow keys and Enter. Always accessible from any screen in the dashboard layout.

**Route:** Persistent component in header (no dedicated route). Clicking a result navigates to `/patients/{id}`.

**Priority:** Critical

**Backend Specs:** `specs/patients/patient-search.md` (P-06)

**Dependencies:** `specs/frontend/patients/patient-detail.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Keyboard shortcut: `Cmd+K` (Mac) / `Ctrl+K` (Windows/Linux) — focuses search input from any screen
- Click on the search bar in the header
- Tab navigation to header search area

**Exit Points:**
- Select patient from results → `/patients/{id}`
- Press Escape → close dropdown, return focus to trigger element
- Click outside dropdown → close dropdown
- "Ver todos los resultados" link → `/patients?q={query}`

**User Story:**
> As a receptionist | doctor | assistant, I want to quickly find a patient by name or document number so that I can open their profile in under 3 taps or keystrokes.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`, `receptionist`

---

## Layout Structure

```
Header Bar:
+--------------------------------------------------+
|  [Logo] | [Search Bar: Buscar paciente...] | [Icons] |
+--------------------------------------------------+

Dropdown (when active):
+--------------------------------------------------+
|  [Search input — in-place, full width on mobile] |
+--------------------------------------------------+
|  Recientes:                                      |
|  [Mini-card: patient 1]                          |
|  [Mini-card: patient 2]                          |
|  [Mini-card: patient 3]                          |
|  ---                                             |
|  Resultados: "{query}"                           |
|  [Mini-card: result 1]                           |
|  [Mini-card: result 2]                           |
|  [Mini-card: ...]                                |
|  ---                                             |
|  [Ver todos los resultados →]                    |
+--------------------------------------------------+
```

**Sections:**
1. Search trigger — styled input in header, always visible on desktop; icon button on mobile
2. Dropdown panel — floats below search, contains recent patients and search results
3. Mini-cards — compact patient representations with avatar, name, document, phone
4. Footer link — "Ver todos los resultados"

---

## UI Components

### Component 1: GlobalSearchTrigger

**Type:** Input field (desktop) / IconButton (mobile)

**Desktop behavior:**
- Styled as `input` with `SearchIcon` on left: `bg-gray-100 dark:bg-gray-800 rounded-lg h-9 pl-9 pr-4 w-56 lg:w-72 text-sm placeholder:text-gray-400`
- Keyboard shortcut hint: `Cmd+K` badge on right `text-xs text-gray-400 bg-gray-200 px-1.5 rounded font-mono`
- On focus: expands to `w-80`, drops down result panel

**Mobile behavior (< 640px):**
- Shows `SearchIcon` button only in header
- Click opens full-screen search overlay: `fixed inset-0 z-50 bg-white dark:bg-gray-900`
- Overlay has its own back button + search input at top

### Component 2: SearchDropdown

**Type:** Floating panel (Popover)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.14

**Positioning:** `absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-100 z-50`
- Min-width matches trigger width; max-width `384px` on desktop
- Max-height `480px` with `overflow-y-auto`

**States:**
- `idle` (input empty, no focus) — dropdown hidden
- `focused-empty` (focused, no query) — shows "Recientes" section
- `searching` (query > 0 chars, debounce pending) — shows previous results grayed out + spinner in input
- `results` — shows "Recientes" (collapsed) + "Resultados" section
- `no-results` — shows "Sin resultados para '{query}'" with illustration

### Component 3: PatientMiniCard

**Type:** List item / button

**Layout:**
```
[Avatar 36px] | [Name bold] [Document type + number]
               | [Phone] [City/location]
```

**Props:**

| Element | Details |
|---------|---------|
| Avatar | 36px circle — photo or initials `bg-teal-100 text-teal-700 text-sm font-semibold` |
| Name | `text-sm font-semibold text-gray-900` — query match highlighted: wrap in `<mark class="bg-yellow-100 rounded">` |
| Document | `text-xs text-gray-500` — "CC 12345678" |
| Phone | `text-xs text-gray-400` |

**States:**
- Default: `hover:bg-gray-50`
- Keyboard focus: `bg-teal-50 outline-none ring-2 ring-teal-500 ring-inset`
- Clicked: brief scale `1 → 0.98` feedback before navigation

**Touch target:** Full card `min-h-[56px]` with `px-4 py-3`

### Component 4: RecentPatientsSection

**Type:** Section header + mini-card list

**Header:** `"Recientes"` in `text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 pt-3 pb-1`

**Behavior:**
- Shows last 5 patients viewed, in reverse chronological order
- Sourced from Zustand `recentPatientsStore` (client-side only, no API)
- Hidden when query is 2+ characters and search results are present
- "Borrar recientes" link in header (right-aligned): clears store

---

## Form Fields / Search Input

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| query | text | No | Min 2 chars to trigger API; max 100 | — | "Buscar por nombre o documento..." |

**Debounce:** 300ms after last keystroke before API call fires.

**Search scope:**
- Patient first + last name (partial match, accent-insensitive)
- Document number (exact prefix match)
- Phone number (partial match from start)

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Search patients | `/api/v1/patients/search?q={query}&limit=8` | GET | `specs/patients/patient-search.md` | 30s |

### State Management

**Local State (useState):**
- `query: string` — current input value
- `isOpen: boolean` — dropdown visibility
- `activeIndex: number` — keyboard-selected item index (-1 = none)
- `isSearching: boolean` — debounce pending or request in flight

**Global State (Zustand):**
- `recentPatientsStore.recents: PatientSummary[]` — max 5 items, persisted to `localStorage`
  - `addRecent(patient)` — adds to front, deduplicates, trims to 5
  - `clearRecents()` — empties list

**Server State (TanStack Query):**
- Query key: `['patient-search', query]`
- Enabled: `query.length >= 2`
- Stale time: 30s
- `keepPreviousData: true` — previous results shown while new search loads

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Focus search input | Click or Tab | Open dropdown showing recents | Dropdown slides down |
| Type 1 char | Keystroke | Show recents only (< 2 chars threshold) | No API call |
| Type 2+ chars | Keystroke | Debounce 300ms → API search | Spinner in input |
| Arrow Down | Key | Focus next mini-card | Card highlighted |
| Arrow Up | Key | Focus previous mini-card | Card highlighted |
| Enter on focused card | Key | Navigate to patient | Dropdown closes |
| Click card | Click | Navigate to patient | Brief scale feedback |
| Escape | Key | Close dropdown, return focus to input | Dropdown closes |
| Click outside | Click | Close dropdown | Dropdown closes |
| Cmd+K / Ctrl+K | Global shortcut | Focus search input | Input focuses, dropdown opens |
| "Borrar recientes" | Click | Clear recent patients list | Recents section hides |
| "Ver todos los resultados" | Click | Navigate to `/patients?q={query}` | Full page navigation |

### Keyboard Navigation Detail

- `ArrowDown` from input: `activeIndex = 0` (first item)
- `ArrowDown` from last item: wrap to `activeIndex = 0`
- `ArrowUp` from first item: wrap to last item
- `ArrowUp` from input (activeIndex = -1): go to last item
- Tab from dropdown: close dropdown, move focus naturally
- Items: when `activeIndex >= 0`, item has `role="option" aria-selected="true"` + visual ring

### Animations/Transitions

- Dropdown open: `motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}` 150ms
- Dropdown close: `opacity: 0` 100ms
- Input expansion (desktop): `transition-all duration-200` width change
- Mobile overlay: `motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}` full-screen

---

## Loading & Error States

### Loading State
- While debounce pending: show previous results dimmed `opacity-50` + small `Loader2 animate-spin` icon in input right side
- After debounce but before response: shimmer mini-card skeletons (3 rows `h-14 animate-pulse bg-gray-100 rounded-lg mx-4 mb-2`)

### Error State
- Network error: `"Error de conexion"` text below dropdown in `text-sm text-red-500 px-4 py-2`; recents still shown
- No results: illustration (stethoscope icon) + `"Sin resultados para '{query}'"` + `"¿El paciente es nuevo?"` link to `/patients/new`

### Empty State (recents)
- No recent patients: `"No hay pacientes recientes"` in `text-sm text-gray-400 px-4 py-6 text-center`

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Search icon in header opens full-screen overlay. Input at top of overlay, full-width. Results fill screen. Keyboard shortcut hint hidden. |
| Tablet (640-1024px) | Search bar visible in header `w-56`. Dropdown `max-w-sm`. |
| Desktop (> 1024px) | Search bar `w-72` expands to `w-80` on focus. Dropdown `max-w-96`. Keyboard shortcut hint visible. |

**Tablet priority:** High — clinical staff search patients on tablets constantly. Mini-card touch target `min-h-[56px]` for easy tap.

---

## Accessibility

- **Focus order:** Search trigger in header tab order. When dropdown open: input → recent cards → result cards → "Ver todos" link. Escape closes and returns to trigger.
- **Screen reader:** `role="combobox"` on input, `aria-expanded`, `aria-haspopup="listbox"`, `aria-controls="patient-search-listbox"`. Listbox: `role="listbox" id="patient-search-listbox"`. Each mini-card: `role="option"`, `aria-selected`. Section headers: `role="group"` with `aria-label="Recientes"` / `"Resultados"`. Live region `aria-live="polite"` announces result count: "X pacientes encontrados" after results load.
- **Keyboard navigation:** Full keyboard-only operation. See interaction table above.
- **Color contrast:** Search icon `text-gray-400` on `bg-gray-100` meets 3:1 (non-text element). Text matches WCAG AA.
- **Language:** Placeholder, labels, section headers, and messages in es-419.

---

## Design Tokens

**Colors:**
- Search input: `bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100`
- Dropdown: `bg-white dark:bg-gray-900 border-gray-100 shadow-xl`
- Card hover: `hover:bg-gray-50 dark:hover:bg-gray-800`
- Card keyboard focus: `bg-teal-50 ring-2 ring-inset ring-teal-500`
- Match highlight: `bg-yellow-100 text-yellow-900 rounded`
- Section header: `text-gray-400`
- Shortcut badge: `bg-gray-200 text-gray-500 font-mono`

**Typography:**
- Patient name: `text-sm font-semibold text-gray-900`
- Document + phone: `text-xs text-gray-500`
- Section header: `text-xs font-semibold uppercase tracking-wider text-gray-400`
- "Ver todos" link: `text-sm text-teal-600 font-medium`

**Spacing:**
- Dropdown padding: `py-2`
- Mini-card padding: `px-4 py-3`
- Section header padding: `px-4 pt-3 pb-1`
- Footer link padding: `px-4 py-3 border-t border-gray-100`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — Search, X, Clock, ArrowRight, Loader2
- `@tanstack/react-query` — `keepPreviousData` for smooth transitions
- `framer-motion` — dropdown animation
- `use-debounce` — `useDebounceValue(query, 300)`

**File Location:**
- Component: `src/components/layout/GlobalSearch.tsx`
- Mini-card: `src/components/patients/PatientMiniCard.tsx`
- Store: `src/stores/recentPatientsStore.ts`
- API: `src/lib/api/patients.ts`

**Hooks Used:**
- `useDebounceValue(query, 300)` — debounce input
- `useQuery(['patient-search', debouncedQuery], { enabled: debouncedQuery.length >= 2, keepPreviousData: true })`
- `useRecentPatientsStore()` — read/write recents
- `useHotkeys('meta+k, ctrl+k', () => inputRef.current?.focus())` — keyboard shortcut
- `useClickOutside(dropdownRef, closeDropdown)` — outside click handler

---

## Test Cases

### Happy Path
1. Search by name and navigate to patient
   - **Given:** Patients exist in the tenant
   - **When:** Receptionist types "Carlos" in search bar, selects first result with Enter
   - **Then:** Mini-card shows highlighted "Carlos", pressing Enter navigates to patient detail, patient added to recents

2. Keyboard-only workflow
   - **Given:** Search bar focused via Cmd+K
   - **When:** Type "1234", ArrowDown to first result, Enter
   - **Then:** Patient detail page loads

### Edge Cases
1. Query shorter than 2 chars
   - **Given:** Input focused
   - **When:** User types 1 character
   - **Then:** Only recents shown, no API call fired

2. Rapid typing then pause
   - **Given:** User types "Maria Ga" quickly
   - **When:** 300ms after last keystroke
   - **Then:** Single API call with "Maria Ga", not 8 separate calls

3. Empty recents list
   - **Given:** First time using app, no recent patients
   - **When:** Input focused with empty query
   - **Then:** Empty state "No hay pacientes recientes" shown

### Error Cases
1. Network unavailable during search
   - **Given:** Offline connection
   - **When:** User types query and debounce fires
   - **Then:** Error message shown below dropdown, cached recents still visible

---

## Acceptance Criteria

- [ ] Search input always visible in header on tablet/desktop
- [ ] Mobile: icon button opens full-screen overlay
- [ ] Cmd+K / Ctrl+K global shortcut focuses search
- [ ] Recent patients (last 5) shown when input empty
- [ ] API search triggered after 2+ chars with 300ms debounce
- [ ] Match text highlighted in results (yellow background)
- [ ] Keyboard navigation: ArrowUp/Down, Enter, Escape fully functional
- [ ] Mini-cards show avatar/initials, name, document, phone
- [ ] "Ver todos los resultados" link to `/patients?q={query}`
- [ ] Loading: spinner in input + dimmed previous results
- [ ] No results: illustration + message + "nuevo paciente" link
- [ ] Recent patients persisted to localStorage via Zustand
- [ ] Responsive: full-screen on mobile, floating panel on tablet/desktop
- [ ] ARIA combobox/listbox pattern fully implemented
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
