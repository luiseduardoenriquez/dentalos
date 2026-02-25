# Lista de Inventario (Inventory List) — Frontend Spec

## Overview

**Screen:** Inventory list with traffic-light semaphore status system. Alert banner at top shows expired and expiring items. Table displays inventory items with inline quantity adjustment (+/- controls), semaphore status circles (green/yellow/orange/red), and filters. Clicking a row opens a detail slide-in panel.

**Route:** `/inventory`

**Priority:** Medium

**Backend Specs:** `specs/inventory/inventory-list.md` (INV-01), `specs/inventory/inventory-update.md` (INV-02), `specs/inventory/inventory-alerts.md` (INV-03)

**Dependencies:** `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar "Inventario" link
- Notifications panel → "Productos por vencer" alert

**Exit Points:**
- "Agregar producto" → `/inventory/new`
- Click row → detail slide-in panel (no route change)
- Sterilization log link → `/inventory/sterilization`

**User Story:**
> As a clinic_owner | assistant, I want to see all inventory items with their expiry status at a glance so that I can reorder items before they expire and avoid using expired materials.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | "Inventario"                          |
|          | [Agregar producto btn]  [Exportar btn] |
|          +---------------------------------------+
|          |  [Alert banner: X vencidos, Y por vencer] |
|          +---------------------------------------+
|          |  [Filter bar: categoria | estado | bajo_stock | search] |
|          |  [Active filter chips]                |
|          +---------------------------------------+
|          |  [Inventory Table]                    |
|          |  (sortable, with +/- quantity)        |
|          +---------------------------------------+
|          |  [Pagination]                         |
|          +-----------------------------+   +-----+
|                                       | [Slide-in Detail Panel] |
+---------------------------------------+---------+
```

---

## UI Components

### Component 1: AlertBanner

**Type:** Warning banner — shown only when alerts exist

**Conditions for display:**
- `expired_count > 0`: `"X producto(s) vencido(s)"` — red
- `expiring_soon_count > 0`: `"Y producto(s) vencen en menos de 30 dias"` — amber

**Layout:**
```
[AlertOctagon icon]  "X productos vencidos y Y por vencer"   [Ver solo alertas →]
```

**Styling:**
- Expired only: `bg-red-50 border border-red-200 text-red-800`
- Expiring only: `bg-amber-50 border border-amber-200 text-amber-800`
- Both: `bg-red-50 border-red-200` with combined message

**"Ver solo alertas →":** Applies filter to show only `status = expired OR expiring_soon` rows.

### Component 2: FilterBar

**Filters:**

| Filter | Type | Options |
|--------|------|---------|
| Categoria | Select dropdown | Todos / Material descartable / Medicamentos / Instrumental / Equipos / Implantes |
| Estado | Select dropdown | Todos / En stock / Bajo stock / Por vencer / Vencido |
| Bajo stock | Toggle switch | Only items with quantity ≤ min_quantity |
| Buscar | Text input | Debounced 300ms search by name, lot number |

**Active filter chips:** Same pattern as analytics — `bg-teal-100 text-teal-800 rounded-full` with X.

### Component 3: InventoryTable

**Type:** Sortable data table

**Columns:**

| Column | Sortable | Notes |
|--------|---------|-------|
| Nombre | Yes | Product name, max 40 chars displayed |
| Categoria | No | Badge chip |
| Cantidad | Yes | Inline +/- controls |
| Unidad | No | "unidades", "cajas", "ml", etc. |
| Lote # | No | Lot number, monospace font |
| Vencimiento | Yes | Formatted date + days remaining |
| Estado | Yes | Color circle semaphore |
| Acciones | No | `...` overflow menu |

**Sort:** Click column header toggles asc/desc. Active sort shows `ChevronUp/Down` icon.

**Semaphore Status Circle:**

| Status | Color | Condition | Label |
|--------|-------|-----------|-------|
| Verde | `bg-green-500` | > 90 days to expiry AND qty > min | "En stock" |
| Amarillo | `bg-yellow-400` | 30-90 days to expiry OR qty approaching min | "Por vencer pronto" |
| Naranja | `bg-orange-500` | 0-30 days to expiry OR qty at min | "Critico" |
| Rojo | `bg-red-500` | Expired OR qty = 0 | "Vencido / Sin stock" |

**Circle size:** `w-4 h-4 rounded-full` with tooltip on hover showing full status text.

**Categoria badge:** `text-xs rounded-full px-2 py-0.5` per category:
- Material descartable: `bg-blue-100 text-blue-700`
- Medicamentos: `bg-purple-100 text-purple-700`
- Instrumental: `bg-gray-100 text-gray-700`
- Implantes: `bg-teal-100 text-teal-700`
- Equipos: `bg-amber-100 text-amber-700`

**Vencimiento column:**
- Date: `"15 mar 2026"`
- Days remaining: `"(en 18 dias)"` — color matches semaphore: green/yellow/orange/red text
- Expired: `"Vencido"` in red, `text-red-600 font-medium`

**Row click:** Opens slide-in detail panel from the right (row remains highlighted).

**Row hover:** `bg-gray-50 cursor-pointer`

**Expired rows:** Full row `bg-red-50/50` background.

### Component 4: QuantityAdjuster

**Type:** Inline +/- stepper

**Design:**
```
[-]  [24]  [+]
```

- `-` button: `w-7 h-7 rounded border border-gray-200 text-gray-600 hover:bg-gray-50`
- Quantity: `w-12 text-center text-sm font-medium text-gray-800 border-0 outline-none`
- `+` button: same as `-`

**Behavior:**
- Click `+`: PATCH quantity +1, optimistic update, debounced save (500ms after last click)
- Click `-`: PATCH quantity -1, minimum 0
- Quantity = 0: shows `bg-red-50` background on number, `-` disabled
- Direct input: click number field → editable text input, blur saves
- Saving indicator: small `Loader2 animate-spin` beside stepper while PATCH in flight

### Component 5: DetailSlidePanel

**Type:** Side panel (right slide-in)

**Animation:** `motion.div initial={{ x: '100%' }} animate={{ x: 0 }}` 300ms ease-out
**Width:** `w-80 md:w-96`
**Overlay:** `fixed inset-0 bg-black/20` behind panel on mobile only

**Panel content:**
- Header: product name + close X button + "Editar" link
- Status circle + label (large)
- Section: stock info (current qty, min qty, unit, location)
- Section: product details (category, lot #, manufacturer, supplier)
- Section: expiry (date, days remaining, manufacturing date if available)
- Section: usage history (last 5 quantity changes with date + user)
- Section: linked procedures (if category = implant, shows linked patient procedures)
- Actions: "Ajustar cantidad", "Marcar como vencido", "Archivar producto"

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List inventory | `/api/v1/inventory?page={n}&category={cat}&status={s}&q={search}` | GET | `specs/inventory/inventory-list.md` | 2min |
| Adjust quantity | `/api/v1/inventory/{id}/quantity` | PATCH | `specs/inventory/inventory-update.md` | None |
| Get alerts | `/api/v1/inventory/alerts` | GET | `specs/inventory/inventory-alerts.md` | 5min |
| Get item detail | `/api/v1/inventory/{id}` | GET | `specs/inventory/inventory-list.md` | 2min |

### State Management

**Local State (useState):**
- `filters: { category, status, lowStock, search }`
- `sortBy: string`, `sortOrder: 'asc' | 'desc'`
- `selectedItemId: string | null` — for slide panel
- `quantityEdits: Record<string, number>` — pending quantity changes

**Server State (TanStack Query):**
- `useQuery(['inventory', filters, sort, page])` — list
- `useQuery(['inventory-alerts'])` — alert counts
- `useMutation` for quantity PATCH — optimistic update

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click `+` on quantity | Click | Optimistic +1, PATCH after 500ms debounce | Quantity updates immediately |
| Click `-` on quantity | Click | Same as above | Immediate |
| Click table row | Click | Open slide panel for that item | Panel slides in |
| Click X on slide panel | Click / Escape | Close panel | Slides out |
| Sort column | Click header | Sort applied | ChevronUp/Down icon + data re-sorted |
| Apply filter | Select/toggle | Refetch | Table updates, filter chip appears |
| Click "Ver solo alertas →" | Click (banner) | Apply status filter | Banner highlights matching rows |

---

## Loading & Error States

### Loading State
- Table: 10 skeleton rows `h-14 animate-pulse bg-gray-100 rounded mb-2`
- Alert banner: skeleton `h-12 animate-pulse bg-gray-100 rounded`
- Slide panel: skeleton content while item detail loads

### Error State
- Table load error: `"Error al cargar inventario"` + retry button
- Quantity PATCH error: optimistic update reverted + toast `"Error al actualizar cantidad"`
- Slide panel error: inline error within panel

### Empty State
- No items matching filters: inventory illustration + "Sin productos para estos filtros" + "Limpiar filtros" CTA
- Inventory completely empty: "Agrega tus primeros productos al inventario" + "Agregar producto" CTA button

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table shows only: Nombre + Status circle + Cantidad stepper. Other columns hidden. Click row → slide panel with full details. Slide panel full-screen on mobile. |
| Tablet (640-1024px) | Table shows: Nombre, Categoria, Cantidad, Vencimiento, Estado. Slide panel `w-80`. |
| Desktop (> 1024px) | All columns visible. Slide panel `w-96`. |

**Touch targets:** `+/-` buttons min 44px touch area (even though visual size is smaller).

---

## Accessibility

- **Focus order:** Alert banner → Filter bar → Table header (sortable buttons) → Table rows → Pagination → Slide panel (when open)
- **Screen reader:** Table: proper `<table><thead><th scope="col">` markup. Status circle: `aria-label="Estado: {label}"` — color not sole indicator (tooltip + aria-label). Quantity stepper: `aria-label="Cantidad de {product name}: {N}. Haz clic en mas o menos para ajustar"`. Slide panel: `role="dialog" aria-label="Detalle de {product name}"`.
- **Keyboard:** Slide panel opened with Enter on row. Closed with Escape. `+/-` buttons Tab-navigable within row.
- **Language:** All labels, statuses, filter options in es-419.

---

## Design Tokens

**Colors:**
- Status verde: `bg-green-500`
- Status amarillo: `bg-yellow-400`
- Status naranja: `bg-orange-500`
- Status rojo: `bg-red-500`
- Expired row: `bg-red-50/50`
- Alert banner expired: `bg-red-50 border-red-200`
- Alert banner expiring: `bg-amber-50 border-amber-200`
- Slide panel: `bg-white border-l border-gray-100 shadow-2xl`

**Typography:**
- Product name: `text-sm font-medium text-gray-900`
- Category badge: `text-xs`
- Lot number: `text-xs font-mono text-gray-500`
- Days remaining: same color as semaphore
- Table header: `text-xs font-semibold uppercase text-gray-500`

---

## Implementation Notes

**Dependencies (npm):**
- `framer-motion` — slide panel animation
- `lucide-react` — AlertOctagon, Plus, Minus, ChevronUp, ChevronDown, X, Loader2

**File Location:**
- Page: `src/app/(dashboard)/inventory/page.tsx`
- Components: `src/components/inventory/InventoryTable.tsx`, `src/components/inventory/QuantityAdjuster.tsx`, `src/components/inventory/InventoryDetailPanel.tsx`, `src/components/inventory/InventoryAlertBanner.tsx`

---

## Acceptance Criteria

- [ ] Alert banner shows expired and expiring counts with appropriate color
- [ ] "Ver solo alertas" filter shortcut
- [ ] Table with all 7 columns, sortable on name, quantity, expiry, status
- [ ] Semaphore circles: green/yellow/orange/red with tooltip labels
- [ ] Inline +/- quantity stepper with optimistic update
- [ ] Filters: category, status, low-stock toggle, search with debounce
- [ ] Row click opens detail slide-in panel
- [ ] Slide panel shows full product info, usage history, actions
- [ ] Expired rows with red background
- [ ] Pagination
- [ ] Mobile: condensed table columns, full-screen slide panel
- [ ] Accessibility: table markup, status aria-labels, keyboard navigation
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
