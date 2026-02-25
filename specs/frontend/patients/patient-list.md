# Lista de Pacientes (Patient List) -- Frontend Spec

## Overview

**Screen:** Searchable, filterable patient list with pagination. Displays all patients in the current tenant. Search bar with typeahead, status filters, and a table view (desktop/tablet) or card layout (mobile).

**Route:** `/patients`

**Priority:** Critical

**Backend Specs:** `specs/M1-NAVIGATION-MAP.md` Section 6.2 (Patient Management endpoints)

**Dependencies:** `specs/frontend/design-system/design-system.md`, `specs/frontend/dashboard/dashboard.md`

---

## User Flow

**Entry Points:**
- Sidebar navigation "Pacientes"
- Dashboard widget links (patient name clicks)
- Direct navigation to `/patients`

**Exit Points:**
- Click patient row -> `/patients/{id}` (patient detail)
- Click "Nuevo Paciente" button -> `/patients/new`
- Sidebar navigation to any other section

**User Story:**
> As a clinic_owner | doctor | assistant | receptionist, I want to search and browse my clinic's patients so that I can quickly find a patient's record.

**Roles with access:** clinic_owner, doctor, assistant, receptionist (all staff)

---

## Layout Structure

```
+--------+-----------------------------------------+
|        |  Header: Clinic Name | Search | Bell    |
|        +-----------------------------------------+
|        |                                         |
| Side-  |  Page Title: "Pacientes"    [+ Nuevo]   |
|  bar   |                                         |
|        |  +-------------------------------------+|
|        |  | Search bar (typeahead)              ||
|        |  +-------------------------------------+|
|        |                                         |
|        |  Filters: [Activos/Todos] [Fecha rango] |
|        |                                         |
|        |  +-------------------------------------+|
|        |  | Table Header                        ||
|        |  |  Name | Documento | Tel | Ult.Visita||
|        |  |-----------------------------------  ||
|        |  |  Row 1                              ||
|        |  |  Row 2                              ||
|        |  |  Row 3                              ||
|        |  |  ...                                ||
|        |  +-------------------------------------+|
|        |                                         |
|        |  Pagination: < 1 2 3 ... 10 >           |
|        |                                         |
+--------+-----------------------------------------+
```

**Sections:**
1. Page header -- title "Pacientes" with "Nuevo Paciente" primary button (right-aligned)
2. Search bar -- full-width typeahead search input with magnifying glass icon
3. Filters row -- toggle for active/all patients, optional date range picker
4. Data table -- sortable columns, clickable rows
5. Pagination -- page numbers with prev/next navigation

---

## UI Components

### Component 1: PatientSearchBar

**Type:** Input (searchable, async)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| placeholder | string | "Buscar por nombre, documento o telefono..." | Search placeholder |
| debounceMs | number | 300 | Debounce delay before API call |
| minChars | number | 2 | Minimum characters before search triggers |

**Behavior:**
- Typeahead search with 300ms debounce
- Triggers GET `/api/v1/patients?q={query}` after 2+ characters
- Shows inline dropdown with top 5 quick results (patient name + document). Click result navigates directly to `/patients/{id}`.
- Pressing Enter or clicking search icon applies the search as a filter on the table.
- Clear button (X icon) resets search

### Component 2: PatientTable

**Type:** Table (TanStack Table)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.5

**Columns:**

| Column | Header (es-419) | Width | Sortable | Content |
|--------|-----------------|-------|----------|---------|
| name | Paciente | flex-1 (min 200px) | Yes | Avatar (sm, 32px) + full name (`nombre apellido`) |
| document | Documento | 140px | Yes | Document type prefix + number (e.g., "CC 1234567890") |
| phone | Telefono | 140px | No | Phone number formatted with country code |
| last_visit | Ultima Visita | 120px | Yes | Relative date ("hace 3 dias") or absolute if > 30 days |
| status | Estado | 100px | Yes | Badge: "Activo" (green) or "Inactivo" (gray) |

**Row behavior:**
- Entire row is clickable -> navigates to `/patients/{id}`
- Hover: `bg-gray-50 transition-colors duration-100`
- Row height: 52px (default density)
- Avatar uses initials fallback with deterministic color from name hash

### Component 3: FilterBar

**Type:** Horizontal filter group

**Filters:**

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| is_active | Toggle (pills) | "Activos" / "Todos" | "Activos" |
| date_range | Date range picker | Custom start/end dates | None (all dates) |

### Component 4: NuevoPacienteButton

**Type:** Button (primary)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props:** `variant="primary"`, `size="default"`. Icon: `Plus` (Lucide). Label: "Nuevo Paciente".
**Behavior:** Click navigates to `/patients/new`.
**Visibility:** Shown for roles with `patients:write` permission (clinic_owner, receptionist, doctor). Hidden for assistant.

### Component 5: PatientCard (Mobile)

**Type:** Card

**Used on:** Mobile breakpoint (< 640px) instead of table rows.

**Content per card:**
- Avatar (md, 40px) + full name (bold) + status badge
- Document number
- Phone number
- Last visit date (relative)
- Chevron right icon indicating tap action

**Tap:** Navigates to `/patients/{id}`

---

## Form Fields

Not applicable -- this is a list/search screen. Search input is not a form field but a controlled component.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| List patients | `/api/v1/patients` | GET | `specs/M1-NAVIGATION-MAP.md` 6.2 | 2min |
| Search patients | `/api/v1/patients?q={query}` | GET | `specs/M1-NAVIGATION-MAP.md` 6.2 | None |

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Search query (name, document, phone) |
| `is_active` | boolean | Filter by active status (default: true) |
| `date_from` | ISO date | Filter patients with last visit after this date |
| `date_to` | ISO date | Filter patients with last visit before this date |
| `sort_by` | string | Column to sort by (name, last_visit, created_at) |
| `sort_order` | string | "asc" or "desc" |
| `page` | number | Page number (1-based) |
| `per_page` | number | Items per page (10, 20, 50) |

### State Management

**Local State (useState):**
- `searchQuery: string` -- current search input value
- `debouncedQuery: string` -- debounced value for API calls

**Global State (Zustand):**
- None specific -- auth context provides tenant and role

**Server State (TanStack Query):**
- Query key: `['patients', tenantId, { q, is_active, date_from, date_to, sort_by, sort_order, page, per_page }]`
- Stale time: 2 minutes
- `keepPreviousData: true` -- prevents flicker during pagination
- Prefetch next page on hover over pagination button

**URL State (searchParams):**
- All filter/sort/pagination state synced to URL query parameters using `useSearchParams()`
- Enables bookmarkable/shareable filtered views
- Example: `/patients?q=garcia&is_active=true&page=2&sort_by=name`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Type in search | Keyboard input | Debounced search after 300ms, inline dropdown after 2+ chars | Loading spinner in search input |
| Click search result | Click dropdown item | Navigate to `/patients/{id}` | Direct navigation |
| Press Enter in search | Keyboard | Apply search as table filter | Table refreshes with filtered results |
| Click table row | Click | Navigate to `/patients/{id}` | Row hover highlight |
| Click column header | Click | Sort by column (toggle asc/desc) | Sort indicator arrow on header |
| Toggle "Activos"/"Todos" | Click pill | Filter table by active status | Table refreshes, pill highlight changes |
| Change page | Click pagination button | Load next/prev page | Table content replaces (keepPreviousData) |
| Click "Nuevo Paciente" | Click button | Navigate to `/patients/new` | Standard navigation |
| Clear search | Click X in search bar | Reset search filter, reload default list | Table refreshes |

### Animations/Transitions

- Table rows: fade in on load/filter change (200ms opacity transition)
- Search dropdown: slide down with opacity (`framer-motion` or CSS transition)
- Page transition: standard page fade per design system Section 8.1
- Pagination: content crossfade (old data dims, new data fades in)

---

## Loading & Error States

### Loading State
- Initial load: 5 `SkeletonTableRow` elements matching column layout
- Search loading: spinner icon inside the search input (replaces magnifying glass)
- Pagination: previous data stays visible with slight opacity reduction (`opacity-60`) while new page loads
- Mobile: 4 skeleton cards with avatar circle + text lines

### Error State
- API failure: full-width error card in the table area. `bg-red-50 rounded-xl p-6` with `AlertTriangle` icon, "Error al cargar pacientes" message, and "Reintentar" button that invalidates the query.
- Network error: same error card with "Error de conexion" message.

### Empty State
- No patients at all (new clinic): centered empty state illustration. Title: "No hay pacientes registrados". Description: "Agrega tu primer paciente para comenzar." CTA button: "Agregar paciente" -> `/patients/new`.
- No search results: "Sin resultados para '{query}'". Description: "Intenta con otro nombre, documento o telefono." CTA: "Limpiar busqueda" button that resets the search field.
- No patients matching filters: "No hay pacientes que coincidan con los filtros." CTA: "Limpiar filtros" button.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table replaced by card list. Each patient rendered as a card. Search bar full width. "Nuevo Paciente" button becomes FAB (floating action button) at bottom-right. Filters collapse into a "Filtros" dropdown button. |
| Tablet (640-1024px) | Table with horizontal scroll if needed. Sticky first column (patient name). 4-5 columns visible. Search bar and filters on same row. Sidebar collapsed (w-16). |
| Desktop (> 1024px) | Full table with all columns visible. Sidebar expanded (w-64). Search bar, filters, and button on same row. Sortable headers. |

**Tablet priority:** High -- receptionists and assistants use the patient list frequently on tablets. Touch targets 52px row height. Search input 48px height.

---

## Accessibility

- **Focus order:** Search input -> Filter toggles -> "Nuevo Paciente" button -> Table headers (sortable) -> Table rows -> Pagination controls
- **Screen reader:** `aria-label="Lista de pacientes"` on table. Each table row has `aria-label="{patient name}, documento {document}, ultima visita {date}"`. Search input: `aria-label="Buscar pacientes"`. Sort headers: `aria-sort="ascending|descending|none"`. Pagination: `aria-label="Paginacion de pacientes"` with `aria-current="page"` on active page.
- **Keyboard navigation:** Tab through interactive elements. Enter on table row navigates to detail. Arrow Up/Down to navigate between rows. Enter on sort header toggles sort. Escape closes search dropdown.
- **Color contrast:** WCAG AA. Status badges use both color and text label. Sort indicators use directional arrow icons in addition to color.
- **Language:** All headers, labels, empty states, pagination labels, and ARIA attributes in es-419.

---

## Design Tokens

**Colors:**
- Page background: `bg-gray-50 dark:bg-gray-950`
- Table background: `bg-white dark:bg-gray-900`
- Table header: `bg-gray-50 dark:bg-gray-800 text-gray-600 text-sm font-medium`
- Row hover: `hover:bg-gray-50 dark:hover:bg-gray-800`
- Row border: `border-b border-gray-100 dark:border-gray-800`
- Search input: `bg-white border-gray-200 focus:ring-blue-500`
- Active filter pill: `bg-blue-50 text-blue-700 border-blue-200`
- Inactive filter pill: `bg-white text-gray-600 border-gray-200`
- Status badge active: `bg-green-50 text-green-700`
- Status badge inactive: `bg-gray-100 text-gray-500`

**Typography:**
- Page title: `text-xl md:text-2xl font-bold text-gray-700`
- Table header: `text-sm font-medium text-gray-500 uppercase tracking-wider`
- Patient name: `text-sm font-medium text-gray-900`
- Table cells: `text-sm text-gray-600`
- Document number: `text-sm font-mono text-gray-500`
- Relative date: `text-sm text-gray-400`
- Search placeholder: `text-sm text-gray-400`

**Spacing:**
- Page padding: `px-4 py-6 md:px-6 lg:px-8`
- Search to filters: `mt-4`
- Filters to table: `mt-4`
- Table cell padding: `py-3 px-4`
- Card gap (mobile): `gap-3`
- Card padding (mobile): `p-4`

**Border Radius:**
- Table container: `rounded-xl overflow-hidden`
- Search input: `rounded-md`
- Filter pills: `rounded-full`
- Cards (mobile): `rounded-xl`
- Status badges: `rounded-full`
- Avatar: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-table` -- headless table logic (sorting, pagination)
- `@tanstack/react-query` -- server state management
- `lucide-react` -- Search, Plus, ChevronLeft, ChevronRight, ArrowUpDown, X, Users
- `date-fns` -- `formatDistanceToNow` for relative dates, with `es` locale
- `framer-motion` -- list animations

**File Location:**
- Page: `src/app/(dashboard)/patients/page.tsx`
- Components: `src/components/patients/PatientTable.tsx`, `src/components/patients/PatientSearchBar.tsx`, `src/components/patients/PatientCard.tsx`, `src/components/patients/PatientFilters.tsx`
- Hooks: `src/hooks/usePatients.ts` (TanStack Query wrapper), `src/hooks/useDebounce.ts`
- API: `src/lib/api/patients.ts`

**Hooks Used:**
- `useAuth()` -- current user role and permissions
- `useQuery()` -- patient list fetching with pagination/sort/filter params
- `useDebounce()` -- custom hook for search input debouncing (300ms)
- `useSearchParams()` -- Next.js search params for URL state sync
- `useMediaQuery()` -- switch between table and card layout

**Conditional Rendering:**
```typescript
const isTabletOrAbove = useMediaQuery('(min-width: 640px)');
const canCreatePatient = user.permissions.includes('patients:write');

return isTabletOrAbove
  ? <PatientTable data={patients} columns={columns} />
  : <PatientCardList patients={patients} />;
```

**Date Formatting:**
```typescript
import { formatDistanceToNow, format } from 'date-fns';
import { es } from 'date-fns/locale';

function formatLastVisit(date: string): string {
  const d = new Date(date);
  const daysDiff = differenceInDays(new Date(), d);
  if (daysDiff <= 30) {
    return formatDistanceToNow(d, { addSuffix: true, locale: es });
  }
  return format(d, 'dd MMM yyyy', { locale: es });
}
```

---

## Test Cases

### Happy Path
1. View patient list with data
   - **Given:** Clinic has 50 patients
   - **When:** User navigates to `/patients`
   - **Then:** Table shows first 10 patients with pagination showing 5 pages

2. Search for a patient
   - **Given:** Patient "Maria Garcia" exists
   - **When:** User types "Garcia" in the search bar
   - **Then:** Typeahead dropdown shows "Maria Garcia" after 300ms. Table filters to matching results.

3. Navigate to patient detail
   - **Given:** Patient list is displayed
   - **When:** User clicks on a patient row
   - **Then:** User is navigated to `/patients/{id}`

### Edge Cases
1. Search with no results
   - **Given:** No patient matches the search query "ZZZZZ"
   - **When:** User searches for "ZZZZZ"
   - **Then:** Empty state: "Sin resultados para 'ZZZZZ'" with "Limpiar busqueda" button

2. Long patient name truncation
   - **Given:** Patient named "Maria del Carmen Gutierrez Rodriguez de la Cruz"
   - **When:** Name column is rendered
   - **Then:** Name is truncated with ellipsis (`truncate` class) but full name visible on hover (tooltip)

3. Pagination boundary
   - **Given:** 10 patients total, 10 per page
   - **When:** User views the list
   - **Then:** Pagination shows page 1 of 1. Next button is disabled.

### Error Cases
1. API failure
   - **Given:** Backend returns 500
   - **When:** Patient list attempts to load
   - **Then:** Error card with "Error al cargar pacientes" and "Reintentar" button

2. Permission denied for create
   - **Given:** User is assistant (no patients:write permission)
   - **When:** User views the patient list
   - **Then:** "Nuevo Paciente" button is not rendered

---

## Acceptance Criteria

- [ ] Patient table with columns: name (avatar), document, phone, last visit, status
- [ ] Search bar with 300ms debounce typeahead and inline dropdown (top 5 results)
- [ ] Filter toggle: "Activos" / "Todos"
- [ ] Sortable columns: name, document, last visit, status
- [ ] Pagination with 10/20/50 per page options
- [ ] Click row navigates to `/patients/{id}`
- [ ] "Nuevo Paciente" button visible only for roles with patients:write permission
- [ ] Empty state: "No hay pacientes registrados" with CTA for new clinics
- [ ] Empty search state: "Sin resultados" with "Limpiar busqueda" button
- [ ] Loading skeletons: table rows (desktop), cards (mobile)
- [ ] Error state with retry button
- [ ] Mobile: card layout instead of table
- [ ] URL state sync: search, filters, sort, page in query params
- [ ] Responsive on all breakpoints (mobile, tablet, desktop)
- [ ] Accessibility: ARIA labels, keyboard navigation, screen reader support
- [ ] Spanish (es-419) labels and messages throughout
- [ ] Touch targets: 52px row height, 48px search input

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
