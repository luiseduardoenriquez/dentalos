# Lista de Facturas (Invoice List) — Frontend Spec

## Overview

**Screen:** Searchable, filterable list of all invoices for the current tenant. Table view with status badges, date filters, patient search, and bulk send action.

**Route:** `/billing/invoices`

**Priority:** High

**Backend Specs:** `specs/billing/B-03.md`

**Dependencies:** `specs/frontend/design-system/design-system.md`, `specs/frontend/billing/invoice-detail.md`, `specs/frontend/billing/billing-dashboard.md`

---

## User Flow

**Entry Points:**
- Sidebar navigation "Facturación" → "Facturas"
- Billing dashboard "Ver todas las facturas" link
- Patient detail page "Facturas" tab

**Exit Points:**
- Click invoice row → `/billing/invoices/{id}` (invoice detail)
- Click "Nueva Factura" → `/billing/invoices/new`
- Click patient name link → `/patients/{id}`

**User Story:**
> As a clinic_owner or receptionist, I want to see all invoices with their statuses so that I can track outstanding payments and quickly act on overdue accounts.

**Roles with access:** clinic_owner, receptionist, doctor (own invoices only)

---

## Layout Structure

```
+--------+-------------------------------------------------+
|        |  Header: Clinic Name | Search | Bell             |
|        +-------------------------------------------------+
|        |                                                 |
| Side-  |  "Facturas"                    [+ Nueva Factura]|
|  bar   |                                                 |
|        |  [Buscar paciente...] [Estado ▼] [Fecha rango]  |
|        |                                                 |
|        |  Bulk bar (visible when rows selected):         |
|        |  [Enviar seleccionadas (N)]                     |
|        |                                                 |
|        |  +-------------------------------------------+ |
|        |  | ☐ | # Factura | Paciente | Fecha | Monto  | |
|        |  |   | Estado    | Acciones               | |
|        |  |-------------------------------------------| |
|        |  | ☐ | FAC-001   | Juan P.  | 12 Feb | $120K | |
|        |  |   | Enviada   | [Ver][...] |         | |
|        |  +-------------------------------------------+ |
|        |  Pagination: < 1 2 3 > (20 / página)           |
+--------+-------------------------------------------------+
```

**Sections:**
1. Page header — title "Facturas" with "Nueva Factura" primary button
2. Filter bar — patient search (typeahead), status dropdown, date range picker
3. Bulk action bar — appears when one or more rows selected; shows count and "Enviar seleccionadas"
4. Invoice table — checkbox, invoice number, patient name, date, amount, status badge, actions
5. Pagination — page numbers with items-per-page selector

---

## UI Components

### Component 1: InvoiceTable

**Type:** Table (TanStack Table with row selection)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.5

**Columns:**

| Column | Header (es-419) | Width | Sortable | Content |
|--------|-----------------|-------|----------|---------|
| select | ☐ | 44px | No | Checkbox for bulk selection |
| number | # Factura | 120px | Yes | FAC-0001 (monospace) |
| patient | Paciente | flex-1 | Yes | Patient full name (link to /patients/{id}) |
| date | Fecha | 110px | Yes | dd MMM yyyy |
| amount | Total | 110px | Yes | COP formatted ($120.000) |
| status | Estado | 110px | No | Status badge (see below) |
| actions | Acciones | 100px | No | Icon buttons: Ver, Más opciones |

**Status Badges:**

| Status | Label | Color |
|--------|-------|-------|
| draft | Borrador | gray |
| sent | Enviada | blue |
| paid | Pagada | green |
| overdue | Vencida | red |
| cancelled | Anulada | orange |

**Row behavior:**
- Click row (not checkbox/links) → navigate to `/billing/invoices/{id}`
- Checkbox selects row for bulk actions
- Row height: 52px

### Component 2: InvoiceFilterBar

**Type:** Horizontal filter group

**Filters:**

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| patient | Typeahead input | Patient name/document search | Empty |
| status | Multi-select dropdown | draft, sent, paid, overdue, cancelled | All |
| date_range | Date range picker | Custom start/end | Last 30 days |

### Component 3: BulkActionBar

**Type:** Sticky bar (appears below filter bar when rows selected)

**Content:** "N facturas seleccionadas" + "Enviar seleccionadas" button + "Deseleccionar" link

**Behavior:** Clicking "Enviar seleccionadas" triggers batch send API call; shows progress toast.

### Component 4: InvoiceActionsMenu

**Type:** Dropdown menu (Radix UI DropdownMenu)

**Actions per row:**
- Ver detalle → `/billing/invoices/{id}`
- Enviar (if status = draft/sent)
- Registrar pago (if status = sent/overdue)
- Descargar PDF
- Anular (clinic_owner only; shows confirmation dialog)

---

## Form Fields

Not applicable — this is a list screen. Filters are controlled components, not a form.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List invoices | `/api/v1/billing/invoices` | GET | `specs/billing/B-03.md` | 2min |
| Search patients (filter) | `/api/v1/patients?q={query}` | GET | `specs/patients/P-01.md` | None |
| Bulk send | `/api/v1/billing/invoices/bulk-send` | POST | `specs/billing/B-03.md` | — |

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `patient_id` | uuid | Filter by patient |
| `status` | string[] | Filter by status (comma-separated) |
| `date_from` | ISO date | Invoice date from |
| `date_to` | ISO date | Invoice date to |
| `sort_by` | string | number, date, amount, patient |
| `sort_order` | string | asc / desc |
| `page` | number | 1-based |
| `per_page` | number | 10, 20, 50 |

### State Management

**Local State (useState):**
- `selectedIds: string[]` — selected invoice IDs for bulk actions
- `bulkSending: boolean` — bulk send in progress

**Global State (Zustand):**
- `billingStore.filters` — persisted filter state across navigation

**Server State (TanStack Query):**
- Query key: `['invoices', tenantId, filters, sort, pagination]`
- Stale time: 2 minutes
- `keepPreviousData: true` — prevents table flicker during pagination
- Mutation: `useMutation()` for bulk send; invalidates invoice list on success

**URL State (searchParams):**
- Filters, sort, and pagination synced to URL: `/billing/invoices?status=overdue&date_from=2026-01-01&page=1`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select row checkbox | Click checkbox | Row highlighted, bulk bar appears | Checkbox checked state |
| Select all | Click header checkbox | All visible rows selected | All checkboxes checked |
| Bulk send | Click "Enviar seleccionadas" | POST batch send, refresh list | Progress toast → success/error toast |
| Apply status filter | Select dropdown option | Table refreshes | Dropdown shows selected count |
| Apply date range | Pick dates | Table refreshes | Date range displayed in filter bar |
| Search patient | Type in typeahead | Debounced 300ms, filter table | Spinner in input |
| Sort column | Click header | Toggle asc/desc | Arrow indicator on header |
| Click row | Click row body | Navigate to invoice detail | Standard navigation |
| Click "Nueva Factura" | Click button | Navigate to `/billing/invoices/new` | Standard navigation |
| Anular (void) | Click menu → Anular | Confirmation dialog | Dialog with consequences listed |

### Animations/Transitions

- Table rows: fade in on filter/page change (150ms)
- Bulk bar: slide down from filter bar (200ms, framer-motion)
- Status badge: no animation (static)

---

## Loading & Error States

### Loading State
- Initial load: 8 SkeletonTableRow elements matching column widths
- Filter change: overlay spinner on table (opacity-50 + spinner center)
- Pagination: previous data remains with opacity-60

### Error State
- API failure: error card in table area with "Error al cargar facturas" + "Reintentar" button
- Bulk send failure: error toast "No se pudo enviar N facturas. Intenta de nuevo."

### Empty State
- No invoices at all: illustration + "No hay facturas registradas" + "Crear primera factura" button → `/billing/invoices/new`
- No results for filters: "Sin facturas para los filtros seleccionados" + "Limpiar filtros" button

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table replaced by invoice cards. Each card: invoice #, patient name, date, amount, status badge. Tap card → detail. "Nueva Factura" becomes FAB. Filters in bottom sheet. |
| Tablet (640-1024px) | Table with horizontal scroll. Columns: checkbox, #, patient, amount, status, actions. Date column hidden. Sidebar collapsed. |
| Desktop (> 1024px) | Full table with all columns. Sidebar expanded. Filters and button on same row. |

**Tablet priority:** High — receptionists frequently manage billing on tablets.

---

## Accessibility

- **Focus order:** "Nueva Factura" button → search input → status filter → date range → select-all checkbox → table rows → pagination
- **Screen reader:** `aria-label="Lista de facturas"` on table. Status badges use `aria-label="Estado: Vencida"`. Bulk bar has `aria-live="polite"` for count updates.
- **Keyboard navigation:** Tab through filters and rows. Space to toggle checkbox. Enter to open row detail. Escape to close dropdowns.
- **Color contrast:** WCAG AA. Status badges use both color and text. Overdue (red) also has bold text.
- **Language:** All labels, placeholders, empty states, and ARIA attributes in es-419.

---

## Design Tokens

**Colors:**
- Status draft: `bg-gray-100 text-gray-600`
- Status sent: `bg-blue-50 text-blue-700`
- Status paid: `bg-green-50 text-green-700`
- Status overdue: `bg-red-50 text-red-700`
- Status cancelled: `bg-orange-50 text-orange-700`
- Bulk bar: `bg-blue-50 border-blue-200`
- Selected row: `bg-blue-50/40`

**Typography:**
- Invoice number: `text-sm font-mono font-medium text-gray-900`
- Amount: `text-sm font-semibold text-gray-900`
- Patient name: `text-sm text-blue-600 hover:text-blue-800` (link)

**Spacing:**
- Page padding: `px-4 py-6 md:px-6 lg:px-8`
- Filter bar gap: `gap-3`
- Table cell: `py-3 px-4`

**Border Radius:**
- Table container: `rounded-xl overflow-hidden`
- Status badges: `rounded-full px-2.5 py-0.5`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-table` — row selection, sorting, pagination
- `@tanstack/react-query` — server state + mutations
- `@radix-ui/react-dropdown-menu` — actions menu
- `lucide-react` — Plus, Eye, MoreHorizontal, Send, Download, Ban
- `date-fns` — date formatting with `es` locale

**File Location:**
- Page: `src/app/(dashboard)/billing/invoices/page.tsx`
- Components: `src/components/billing/InvoiceTable.tsx`, `src/components/billing/InvoiceFilterBar.tsx`, `src/components/billing/BulkActionBar.tsx`, `src/components/billing/InvoiceActionsMenu.tsx`
- Hooks: `src/hooks/useInvoices.ts`, `src/hooks/useBulkSend.ts`
- API: `src/lib/api/billing.ts`

**Hooks Used:**
- `useAuth()` — role-based column/action visibility
- `useQuery()` — invoice list
- `useMutation()` — bulk send
- `useSearchParams()` — URL state sync

---

## Test Cases

### Happy Path
1. View invoice list
   - **Given:** Clinic has 45 invoices across all statuses
   - **When:** User navigates to `/billing/invoices`
   - **Then:** Table shows 20 invoices, pagination shows 3 pages, status badges render correctly

2. Filter by overdue
   - **Given:** 8 invoices are overdue
   - **When:** User selects "Vencida" in status filter
   - **Then:** Table shows only 8 overdue invoices with red badges

3. Bulk send
   - **Given:** 3 draft invoices selected
   - **When:** User clicks "Enviar seleccionadas (3)"
   - **Then:** All 3 status badges change to "Enviada", success toast shown

### Edge Cases
1. Mixed status bulk select
   - **Given:** User selects paid and draft invoices
   - **When:** Clicking "Enviar seleccionadas"
   - **Then:** Only draft/sent invoices are sent; paid invoices skipped; toast shows "2 enviadas, 1 omitida (ya pagada)"

2. Large amount formatting
   - **Given:** Invoice total is $12.500.000 COP
   - **When:** Amount renders in table
   - **Then:** Displays as "$12.500.000" with thousands separators

### Error Cases
1. Bulk send partial failure
   - **Given:** Network error during bulk send
   - **When:** Send is attempted
   - **Then:** Error toast "Error al enviar facturas. Intenta de nuevo." Selected rows remain selected.

---

## Acceptance Criteria

- [ ] Invoice table with columns: checkbox, #, patient, date, amount, status badge, actions
- [ ] Status filter dropdown (multi-select: borrador, enviada, pagada, vencida, anulada)
- [ ] Patient search typeahead filter (300ms debounce)
- [ ] Date range filter (date_from / date_to)
- [ ] Bulk action bar: appears on selection, shows count, "Enviar seleccionadas" button
- [ ] Row click navigates to `/billing/invoices/{id}`
- [ ] Actions menu: ver, enviar, registrar pago, descargar PDF, anular
- [ ] Sortable columns: #, patient, date, amount
- [ ] Pagination (10/20/50 per page)
- [ ] URL state sync for all filters/sort/pagination
- [ ] Loading skeletons (8 rows)
- [ ] Empty state with CTA
- [ ] Error state with retry
- [ ] Responsive: cards on mobile, horizontal-scroll table on tablet, full table on desktop
- [ ] Accessibility: ARIA labels, keyboard navigation, es-419 labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
