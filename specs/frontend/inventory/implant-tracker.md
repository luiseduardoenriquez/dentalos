# Trazabilidad de Implantes (Implant Tracker) — Frontend Spec

## Overview

**Screen:** Implant traceability page with two sections. Section 1: form to link an implant inventory item to a patient procedure (with tooth number selector). Section 2: search/trace function by serial number or lot number to see the full traceability chain (implant → procedure → patient). Used for recall scenarios and compliance audits.

**Route:** `/inventory/implants`

**Priority:** Medium

**Backend Specs:** `specs/inventory/implant-tracker.md` (INV-07)

**Dependencies:** `specs/frontend/inventory/inventory-list.md`, `specs/frontend/patients/patient-search.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar "Inventario" → "Trazabilidad de Implantes" sub-link
- Inventory list → filter category=Implantes → row action "Ver trazabilidad"

**Exit Points:**
- Success link → navigate to `/patients/{id}` for linked patient
- "Ver inventario" → `/inventory`

**User Story:**
> As a clinic_owner | doctor, I want to link each implant to a specific patient procedure and be able to trace any implant by serial or lot number so that I can identify affected patients in case of a product recall.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | "Trazabilidad de Implantes"            |
|          | [Ver inventario link]                  |
|          +---------------------------------------+
|          |  === VINCULAR IMPLANTE ===            |
|          |  [Link Implant Form]                  |
|          |  [Guardar vinculacion btn]            |
|          +---------------------------------------+
|          |  === BUSCAR / TRAZABILIDAD ===        |
|          |  [Search: serial or lot number]       |
|          |  [Trace results — chain cards]        |
+------------------------------------------+-------+
```

---

## Section 1: Vincular Implante a Procedimiento

### Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Notes |
|-------|------|----------|------------|------------------------|-------|
| inventario_item | typeahead select | Yes | Must be inventory item with category=implant | "Selecciona un implante del inventario" | Search by name, lot, or serial |
| paciente | patient search | Yes | Must be existing patient | "Selecciona un paciente" | Reuses GlobalSearch mini variant |
| procedimiento | select (lazy) | Yes | Loaded after patient selected | "Selecciona el procedimiento" | Patient's recent procedures |
| numero_diente | tooth selector | Yes | Valid FDI number | "Selecciona el numero de diente" | Mini FDI selector |
| notas | textarea | No | Max 300 chars | — | Optional notes |

**Auto-filled from inventory item (read-only once item selected):**
- Serie: `text-sm font-mono text-gray-700`
- Lote: `text-sm font-mono text-gray-700`
- Fabricante: `text-sm text-gray-700`
- Vencimiento: `text-sm text-gray-700` (with semaphore color)

### Component: ImplantInventorySearch

**Type:** Combobox with typeahead

**Behavior:**
- Search by: product name, serial number, lot number
- Filtered to: `category = "Implantes"` inventory items
- Each option shows: name + serial + lot + remaining quantity badge
- After selection: auto-fills serial, lot, manufacturer, expiry in read-only fields below
- Quantity badge turns amber if stock = 1, red if stock = 0 (warn before linking last unit)

**Zero stock warning:** If selected implant has quantity = 0, show warning: `"Advertencia: este implante esta fuera de stock. Verifica el numero de serie antes de continuar."` `bg-amber-50 border-amber-200`

**After linking successfully:** Auto-decrements inventory quantity by 1 (PATCH to inventory).

### Component: PatientSearchInput

**Type:** Inline patient search (mini version of GlobalSearch)

**Behavior:**
- Text input with typeahead debounced 300ms
- Shows mini patient cards in dropdown
- After selection: shows patient name badge + "X" to clear
- Triggers loading of that patient's recent procedures in the next field

### Component: ProcedureSelect

**Type:** Select dropdown (lazy loaded)

**Enabled when:** Patient selected
**Options:** Patient's last 10 procedures from `/api/v1/patients/{id}/procedures?limit=10`
**Each option:** `"{CUPS code}: {procedure name} — {date}"` `text-sm`
**"Procedimiento no listado":** Last option — shows a note field to enter procedure manually

### Component: ToothFDISelector

**Type:** Mini interactive tooth grid

**Visual:** Compact 2-row FDI grid, same layout as classic odontogram but very small (each tooth `w-7 h-7`)
**Interaction:** Click tooth to select — tooth fills with `bg-teal-500 text-white`
**Only one tooth selectable at a time**
**Selected tooth shows FDI number below: `"Diente seleccionado: 16 (Primer molar superior derecho)"`**
**Keyboard:** Arrow keys navigate between teeth, Enter selects

---

## Section 2: Buscar Implante / Trazabilidad

### Search Component

**Type:** Text input with search button

**Input:** `placeholder="Busca por numero de serie o numero de lote..."` full-width `h-11`
**Search button:** `"Buscar"` `bg-teal-600 text-white px-6 h-11 rounded-r-lg`
**Min 3 chars required**

**Examples shown below input (first load):**
```
Ejemplos: "SIN-2024-001234"  "LOT-2025-A789"
```

### Trace Result: Chain Cards

When a match is found, display a vertical chain of 3 cards connected by arrows:

```
+------------------------+
| IMPLANTE               |
| Nombre del producto    |
| Serie: SIN-2024-001234 |
| Lote: LOT-2025-A789    |
| Fabricante: Straumann  |
| Vence: 15/03/2027      |
+------------------------+
        ↓ (arrow connector)
+------------------------+
| PROCEDIMIENTO          |
| Tipo: Colocacion de implante |
| Diente: 36 (FDI)       |
| CUPS: 89.25            |
| Doctor: Dr. Garcia     |
| Fecha: 15 feb 2026     |
+------------------------+
        ↓
+------------------------+
| PACIENTE               |
| [Avatar] Maria Gonzalez|
| CC: 32567890           |
| Tel: +57 300 123 4567  |
| [Ver perfil →]         |
+------------------------+
```

**Card styling per entity type:**

| Card | Icon | Header color |
|------|------|-------------|
| Implante | `Package` | `bg-teal-50 border-teal-200` |
| Procedimiento | `Wrench` | `bg-blue-50 border-blue-200` |
| Paciente | `User` | `bg-purple-50 border-purple-200` |

**Arrow connector:** `w-0.5 h-8 bg-gray-300 mx-auto` + `ChevronDown text-gray-300` centered between cards.

**Multiple results (lot search):** If lot number matches multiple implants → shows list of chains collapsed with "Ver trazabilidad completa" expand per result.

**"Ver perfil →" link:** Opens patient detail in new tab.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Link implant | `/api/v1/implants/link` | POST | `specs/inventory/implant-tracker.md` | None |
| Search implant | `/api/v1/implants/trace?q={serial_or_lot}` | GET | `specs/inventory/implant-tracker.md` | 1min |
| Get patient procedures | `/api/v1/patients/{id}/procedures?limit=10` | GET | — | 2min |
| Search inventory implants | `/api/v1/inventory?category=implants&q={query}` | GET | — | 2min |

### Link POST Request

```typescript
{
  inventory_item_id: string;
  patient_id: string;
  procedure_id: string | null;
  procedure_manual?: string;
  tooth_fdi: string;
  notes?: string;
}
```

### State Management

**Local State (useState):**
- `selectedItem: InventoryItem | null`
- `selectedPatient: PatientSummary | null`
- `selectedTooth: string | null`
- `traceQuery: string`
- `traceResults: TraceResult[]`
- `isSearching: boolean`

**Server State (TanStack Query):**
- `useQuery(['patient-procedures', patientId], { enabled: !!patientId })`
- `useMutation({ mutationFn: linkImplant, onSuccess: () => { resetForm(); toast.success("Vinculacion guardada"); } })`
- `useQuery(['implant-trace', traceQuery], { enabled: traceQuery.length >= 3 })` — on search click

---

## Interactions

### Form Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select implant from search | Click option | Auto-fills serial, lot, manufacturer, expiry | Fields populate with read-only data |
| Zero stock implant selected | Selection | Warning banner appears | Amber banner below |
| Select patient | Typeahead select | Enables procedure dropdown, loads patient's procedures | Dropdown loads |
| Select tooth | Click mini grid | Tooth highlighted, FDI shown below | Visual selection |
| Submit | Click "Guardar vinculacion" | POST link, decrement inventory qty | Loading → success toast → form reset |

### Trace Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Type in search | Keystroke | No action until search clicked | Input updates |
| Click "Buscar" | Click | Fetch trace results | Spinner → chain cards |
| Press Enter in search | Key | Same as click search | Same |
| Click "Ver perfil →" | Click | Patient detail opens in new tab | New tab |
| Expand lot result | Click | Full chain revealed | Height animation |

---

## Loading & Error States

### Loading State
- Form submit: button loading, fields disabled
- Procedure dropdown: skeleton while fetching patient procedures
- Trace search: spinner centered below search bar + skeleton chain cards (3 stacked gray boxes)

### Error State
- Implant already linked to different patient (409): `"Este implante ya fue vinculado a otro paciente. Verifica el numero de serie."` banner
- Trace: no results: `"Sin resultados para '{query}'"` with sad-tooth illustration + "Verifica el numero de serie o lote"
- Trace: API error: inline error below search bar

### Empty State
- Trace section before any search: `"Busca por numero de serie o lote para ver la trazabilidad completa"` `text-sm text-gray-400 text-center py-8` with `Search` icon

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Form fields single column. Tooth selector smaller `w-6 h-6` cells. Chain cards stack full-width with reduced padding. Search bar stacked (input + button stacked). |
| Tablet (640-1024px) | Two-column layout for short form fields. Full tooth selector. Chain cards full-width stacked. |
| Desktop (> 1024px) | `max-w-4xl` container. Two-column form layout. Chain cards `max-w-md` centered. |

---

## Accessibility

- **Focus order:** Form: implant search → patient search → procedure select → tooth grid → notes → submit. Trace: search input → search button → result chain cards (each focusable).
- **Screen reader:** Tooth grid: `role="grid" aria-label="Selector de diente FDI"`, each cell `role="gridcell" aria-label="Diente {FDI}: {tooth name}" aria-selected={bool}`. Read-only auto-filled fields: `aria-readonly="true"`. Trace chain: `role="list"` + each card `role="listitem" aria-label="{entity type}: {key info}"`.
- **Keyboard:** Arrow keys in tooth grid. Enter selects. Tab between chain cards.
- **Language:** All labels, tooth names, and results in es-419.

---

## Design Tokens

**Colors:**
- Implant card: `bg-teal-50 border-teal-200`
- Procedure card: `bg-blue-50 border-blue-200`
- Patient card: `bg-purple-50 border-purple-200`
- Arrow connector: `bg-gray-300`
- Selected tooth: `bg-teal-500 text-white`
- Auto-filled fields: `bg-gray-50 text-gray-600 border-gray-100`
- Zero stock warning: `bg-amber-50 border-amber-200 text-amber-800`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod`
- `lucide-react` — Package, Wrench, User, ChevronDown, Search, Loader2
- `framer-motion` — lot result expand

**File Location:**
- Page: `src/app/(dashboard)/inventory/implants/page.tsx`
- Components: `src/components/inventory/ImplantLinkForm.tsx`, `src/components/inventory/ImplantTraceSearch.tsx`, `src/components/inventory/TraceChainCards.tsx`, `src/components/inventory/ToothFDISelector.tsx`

---

## Acceptance Criteria

- [ ] Form: implant inventory search (category=implants) with auto-fill of serial/lot/manufacturer/expiry
- [ ] Zero stock warning when selecting out-of-stock implant
- [ ] Patient search (existing GlobalSearch pattern)
- [ ] Procedure select lazy-loaded after patient selection
- [ ] Mini FDI tooth selector (compact grid, single selection)
- [ ] Form submit links implant to patient/procedure, decrements inventory qty
- [ ] Trace search by serial or lot number
- [ ] Chain cards: Implante → Procedimiento → Paciente with entity-specific styling
- [ ] Multiple results for lot number (expanded list)
- [ ] "Ver perfil →" patient link opens in new tab
- [ ] Loading states for search, form submit, procedure dropdown
- [ ] Empty state before search, no-results state
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessibility: tooth grid ARIA, chain list ARIA, keyboard navigation
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
