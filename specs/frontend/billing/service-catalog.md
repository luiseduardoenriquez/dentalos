# Catálogo de Servicios (Service Catalog) — Frontend Spec

## Overview

**Screen:** Management page for the clinic's procedure/service price catalog. Table with CUPS codes, procedure names, prices, and active/inactive status. Supports inline price editing, name/code search, CSV import/export, and adding new entries. Restricted to clinic_owner.

**Route:** `/billing/catalog`

**Priority:** Medium

**Backend Specs:** `specs/billing/B-14.md`, `specs/billing/B-15.md`

**Dependencies:** `specs/frontend/billing/invoice-create.md`, `specs/frontend/settings/clinic-settings.md`

---

## User Flow

**Entry Points:**
- Sidebar "Facturación" → "Catálogo de Servicios"
- Settings page "Configurar catálogo" link

**Exit Points:**
- Save inline edit → stays on page
- Import CSV → stays on page
- Sidebar navigation to any other section

**User Story:**
> As a clinic_owner, I want to manage my procedure price catalog with CUPS codes so that my team can select standardized services when creating invoices without manually entering prices.

**Roles with access:** clinic_owner only (read: clinic_owner, receptionist for invoice creation typeahead)

---

## Layout Structure

```
+--------+--------------------------------------------------+
|        |  Header                                          |
|        +--------------------------------------------------+
|        |                                                  |
| Side-  |  "Catálogo de Servicios"   [Importar] [+ Nuevo] |
|  bar   |                                                  |
|        |  [Buscar por nombre o código CUPS...]            |
|        |  Filtros: [Todos ▼]  [Activos/Inactivos ▼]      |
|        |                                                  |
|        |  +--------------------------------------------+ |
|        |  | Código CUPS | Procedimiento | Precio | Act. | |
|        |  |------------|--------------|--------|------| |
|        |  | 890201     | Examen oral  | $45.000 | ●   | |
|        |  | 903001     | Extracción   | $80.000 | ●   | |
|        |  | 903201     | Endodoncia   |[_$350K_]| ●   | |
|        |  +--------------------------------------------+ |
|        |                                                  |
|        |  N procedimientos  [Exportar CSV]                |
|        |  Pagination < 1 2 3 >                            |
+--------+--------------------------------------------------+
```

**Sections:**
1. Page header — title, Import CSV button, "Nuevo servicio" button
2. Search bar — search by procedure name or CUPS code
3. Filter bar — category filter, active/inactive toggle
4. Catalog table — CUPS code, name, price (inline editable), active toggle
5. Footer — item count, export CSV link, pagination

---

## UI Components

### Component 1: CatalogTable

**Type:** Table with inline editing (TanStack Table)

**Columns:**

| Column | Header (es-419) | Width | Sortable | Content |
|--------|-----------------|-------|----------|---------|
| cups_code | Código CUPS | 120px | Yes | Monospace code |
| name | Procedimiento | flex-1 | Yes | Procedure name |
| category | Categoría | 140px | Yes | Badge (preventivo/restaurativo/quirúrgico/ortodoncia/etc.) |
| price | Precio | 130px | Yes | Currency; inline editable (click to edit) |
| is_active | Activo | 80px | No | Toggle switch |
| actions | Acciones | 80px | No | Edit (pencil), Delete (trash — with confirmation) |

**Inline price editing:**
- Default: price displayed as formatted currency text
- On click: text replaces with input field, focused
- Pressing Enter or clicking outside: saves (PATCH request)
- Pressing Escape: cancels edit, restores original value
- Input shows COP currency symbol, accepts numeric input only

**Active toggle:**
- Toggle switch (Radix Switch)
- On toggle: PATCH `is_active` immediately (optimistic update)
- If deactivated: row dims to `opacity-60`

### Component 2: NewServiceModal

**Type:** Dialog modal

**Trigger:** "Nuevo servicio" button

**Fields:**
- CUPS code (text, 6 digits, optional if procedure isn't CUPS-classified)
- Procedure name (required, max 200 chars)
- Category (select dropdown)
- Price (required, COP, > 0)
- IVA applicable (checkbox, default off — dental services generally exempt)
- Is active (checkbox, default on)

### Component 3: ImportCSVModal

**Type:** Dialog modal with drag-and-drop file zone

**Trigger:** "Importar" button

**Content:**
- Drag-and-drop zone or file picker
- "Descargar plantilla CSV" link
- Column mapping preview (if CSV headers don't match expected)
- Validation: shows row-level errors before importing
- "Importar N filas" button (disabled until validation passes)

**CSV expected columns:** `cups_code`, `name`, `category`, `price`, `is_active`

### Component 4: CatalogSearchBar

**Type:** Text input with icon

**Behavior:**
- Debounced 300ms
- Searches name (partial match) OR cups_code (prefix match)
- Clears on click of X icon

### Component 5: ExportButton

**Type:** Button (secondary)

**Label:** "Exportar CSV"

**Behavior:** GET request returns CSV file; triggers browser download. Applies current search/filter to exported results.

---

## Form Fields (New Service Modal)

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| cups_code | Text | No | 6 digits or empty | "Código CUPS debe tener 6 dígitos" | "890201" |
| name | Text | Yes | 1-200 chars, unique in clinic | "Nombre requerido" / "Ya existe un procedimiento con este nombre" | "Ej: Extracción dental simple" |
| category | Select | Yes | One of valid categories | "Selecciona una categoría" | — |
| price | Currency | Yes | > 0 | "Precio debe ser mayor a $0" | "$0" |
| iva_applicable | Checkbox | No | — | — | unchecked |
| is_active | Checkbox | No | — | — | checked |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List services | `/api/v1/billing/services` | GET | `specs/billing/B-14.md` | 5min |
| Create service | `/api/v1/billing/services` | POST | `specs/billing/B-14.md` | — |
| Update service | `/api/v1/billing/services/{id}` | PATCH | `specs/billing/B-14.md` | — |
| Delete service | `/api/v1/billing/services/{id}` | DELETE | `specs/billing/B-14.md` | — |
| Import CSV | `/api/v1/billing/services/import` | POST | `specs/billing/B-15.md` | — |
| Export CSV | `/api/v1/billing/services/export` | GET | `specs/billing/B-15.md` | — |

**Query Parameters:** `q` (search), `category`, `is_active`, `sort_by`, `sort_order`, `page`, `per_page`

### State Management

**Local State (useState):**
- `editingRowId: string | null` — which row is in inline edit mode
- `editingValue: string` — current inline edit input value
- `showNewModal: boolean`
- `showImportModal: boolean`

**Global State (Zustand):**
- None

**Server State (TanStack Query):**
- Query key: `['services', tenantId, filters]` — stale 5 minutes
- Mutations: `createService`, `updateService`, `deleteService`, `importServices`
- Optimistic update for `is_active` toggle (immediate UI, rollback on error)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click price cell | Single click | Cell becomes editable input | Border highlights, cursor in field |
| Press Enter on price | Keyboard | PATCH price → save | Cell reverts to formatted text, success inline indicator (green flash 1s) |
| Press Escape on price | Keyboard | Discard edit | Cell reverts to original value |
| Toggle active | Click switch | PATCH is_active (optimistic) | Row dims/brightens immediately |
| Click "+ Nuevo servicio" | Button | Opens NewServiceModal | Modal slides in |
| Submit new service | Modal submit | POST, close modal, refresh table | "Servicio creado" toast |
| Click "Importar" | Button | Opens ImportCSVModal | Modal |
| Drop/select CSV | Drag-drop / file picker | Validate CSV, show preview | Row counts + error rows shown |
| Click "Importar N filas" | Button in modal | POST import, close modal, refresh | "N servicios importados" toast |
| Click "Exportar CSV" | Button | GET export, download file | Browser download begins |
| Click delete icon | Trash icon | Confirmation dialog | Dialog: "¿Eliminar '{name}'?" |
| Confirm delete | Dialog button | DELETE, refresh table | "Servicio eliminado" toast |

### Animations/Transitions

- Inline edit open: border color transition (100ms)
- Active toggle: spring animation on switch thumb
- New row after create: highlight fade (yellow → transparent, 1s)
- Delete row: fade out (200ms)

---

## Loading & Error States

### Loading State
- Initial load: 8 skeleton table rows with variable-width cells
- Inline save: price cell shows small spinner icon (12px) to right of value
- Import: progress bar inside ImportCSVModal during upload

### Error State
- Inline save failure: cell border turns red, error tooltip "No se pudo guardar. Intenta de nuevo."
- Active toggle failure: rollback to original state + error toast "Error al actualizar el estado."
- Delete failure: toast "No se pudo eliminar el servicio."
- Import failure: row-level error messages in preview table

### Empty State
- No services at all: illustration + "Tu catálogo está vacío" + "Agregar primer servicio" + "Importar desde CSV" buttons
- No search results: "Sin resultados para '{query}'" + "Limpiar búsqueda"

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Service cards instead of table. Each card: name, cups code, price, active toggle. Price edit via tap → modal edit (not inline). Import/export in overflow menu. |
| Tablet (640-1024px) | Table with columns: name, price, active, actions. CUPS code and category hidden. Horizontal scroll. |
| Desktop (> 1024px) | Full table with all columns. Inline editing as described. |

---

## Accessibility

- **Focus order:** Search input → category filter → active filter → "Nuevo servicio" → table headers → table rows → pagination → "Exportar CSV"
- **Screen reader:** Inline editing state: `aria-label="Editar precio de {name}, valor actual {price}"` when input active. Active toggles: `aria-label="Servicio {name} activo"` with `aria-pressed`.
- **Keyboard navigation:** Tab through rows. Enter to activate inline edit. Escape to cancel. Space to toggle active switch.
- **Color contrast:** WCAG AA. Inactive rows at 60% opacity still meet contrast on white background.
- **Language:** All labels, column headers, modals in es-419.

---

## Design Tokens

**Colors:**
- Inactive row: `opacity-60`
- Inline edit cell: `bg-blue-50 ring-1 ring-blue-400 rounded`
- New row highlight: `bg-yellow-50 transition-colors duration-1000`
- Category badges: preventivo=green, restaurativo=blue, quirúrgico=red, ortodoncia=purple, otros=gray
- Active toggle on: `bg-primary-600`, off: `bg-gray-300`

**Typography:**
- CUPS code: `text-sm font-mono text-gray-500`
- Procedure name: `text-sm font-medium text-gray-900`
- Price: `text-sm font-semibold text-gray-900`
- Category badge: `text-xs font-medium rounded-full px-2 py-0.5`

**Spacing:**
- Page padding: `px-4 py-6 md:px-6 lg:px-8`
- Table cell: `py-3 px-4`
- Button group in header: `gap-3`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-table` — table with inline state
- `@tanstack/react-query` — queries + mutations
- `@radix-ui/react-switch` — active toggle
- `@radix-ui/react-dialog` — modals
- `react-dropzone` — CSV import drag-and-drop
- `papaparse` — client-side CSV parsing for preview/validation
- `lucide-react` — Pencil, Trash2, Upload, Download, Plus

**File Location:**
- Page: `src/app/(dashboard)/billing/catalog/page.tsx`
- Components: `src/components/billing/CatalogTable.tsx`, `src/components/billing/NewServiceModal.tsx`, `src/components/billing/ImportCSVModal.tsx`
- Hooks: `src/hooks/useServiceCatalog.ts`, `src/hooks/useImportCSV.ts`
- API: `src/lib/api/billing.ts`

**Hooks Used:**
- `useAuth()` — restrict to clinic_owner
- `useQuery(['services', ...])` — catalog list
- `useMutation(updateService)` — inline price edit + active toggle
- `useMutation(importServices)` — CSV import

---

## Test Cases

### Happy Path
1. Edit price inline
   - **Given:** "Extracción dental" shows $80.000
   - **When:** User clicks price cell, types 90000, presses Enter
   - **Then:** PATCH sent, cell shows $90.000, green flash confirms save

2. Import CSV
   - **Given:** Valid CSV with 50 procedures
   - **When:** User drops file, clicks "Importar 50 filas"
   - **Then:** 50 services added, toast "50 servicios importados"

### Edge Cases
1. Duplicate name on create
   - **Given:** "Extracción dental simple" already exists
   - **When:** User creates new service with same name
   - **Then:** API 409 → modal shows inline error "Ya existe un procedimiento con este nombre"

2. CSV with partial errors
   - **Given:** CSV with 10 rows, 2 have invalid price format
   - **When:** File dropped
   - **Then:** Preview shows 8 valid rows (green) + 2 error rows (red with message). Import button label "Importar 8 filas (2 con errores)".

### Error Cases
1. Inline save network failure
   - **Given:** Network drops while saving price
   - **When:** User presses Enter
   - **Then:** Cell border turns red, tooltip "No se pudo guardar", value reverts to original

---

## Acceptance Criteria

- [ ] Table: CUPS code, procedure name, category, price, active toggle, actions (edit, delete)
- [ ] Inline price editing (click cell → input → Enter to save / Escape to cancel)
- [ ] Active/inactive toggle with optimistic update
- [ ] Search by name or CUPS code (debounced)
- [ ] Category and active/inactive filters
- [ ] "Nuevo servicio" modal with all fields and Zod validation
- [ ] Import CSV: drag-and-drop, client-side validation preview, row-level errors, import button
- [ ] Export CSV: applies current filters to export
- [ ] Delete with confirmation dialog
- [ ] Loading skeletons (8 rows)
- [ ] Empty state with "Agregar primer servicio" and "Importar desde CSV" CTAs
- [ ] Restricted to clinic_owner (page-level guard + server-side enforcement)
- [ ] Responsive: cards mobile, simplified table tablet, full table desktop
- [ ] Accessibility: ARIA, keyboard, es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
