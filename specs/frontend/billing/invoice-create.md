# Crear Factura (Invoice Create) — Frontend Spec

## Overview

**Screen:** Multi-section form to create a new invoice. Select patient via typeahead, add line items (from procedure catalog or manual entry), auto-calculate IVA 19%, preview running total, and save as draft or send immediately. Optional auto-populate from existing treatment plan.

**Route:** `/billing/invoices/new`

**Priority:** High

**Backend Specs:** `specs/billing/B-01.md`

**Dependencies:** `specs/frontend/billing/invoice-list.md`, `specs/frontend/billing/service-catalog.md`

---

## User Flow

**Entry Points:**
- "Nueva Factura" button on `/billing/invoices`
- "Crear Factura" from patient detail billing tab
- "Convertir a Factura" from treatment plan detail

**Exit Points:**
- Save as draft → `/billing/invoices/{newId}` (detail, draft status)
- Send immediately → `/billing/invoices/{newId}` (detail, sent status) + send confirmation toast
- Cancel → `/billing/invoices` (with discard confirmation if form has data)

**User Story:**
> As a receptionist or clinic_owner, I want to create and send an invoice from a patient's procedures so that I can bill accurately without manually re-entering prices.

**Roles with access:** clinic_owner, receptionist

---

## Layout Structure

```
+--------+-------------------------------------------------+
|        |  Header                                         |
|        +-------------------------------------------------+
|        |                                                 |
| Side-  |  ← Volver    "Nueva Factura"                   |
|  bar   |                                                 |
|        |  +-------------------------------------------+ |
|        |  | Sección 1: Paciente & Encabezado          | |
|        |  | [Buscar paciente...] [Fecha] [Vence]      | |
|        |  +-------------------------------------------+ |
|        |                                                 |
|        |  [Importar desde plan de tratamiento ▼]         |
|        |                                                 |
|        |  +-------------------------------------------+ |
|        |  | Sección 2: Ítems de Factura               | |
|        |  | Descripción | Cant | P.Unit | Descuento | Total |
|        |  | [+ Agregar ítem]                          | |
|        |  +-------------------------------------------+ |
|        |                                                 |
|        |  +-------------------------------------------+ |
|        |  | Sección 3: Totales                        | |
|        |  | Subtotal: $XXX | IVA 19%: $XXX | Total: $ | |
|        |  +-------------------------------------------+ |
|        |                                                 |
|        |  [Notas para el paciente (opcional)]            |
|        |                                                 |
|        |  [Guardar como borrador]  [Enviar factura]      |
|        |                                                 |
+--------+-------------------------------------------------+
```

**Sections:**
1. Page header — breadcrumb + title
2. Patient & header section — patient typeahead, invoice date, due date
3. Import from treatment plan — optional quick-populate button
4. Line items section — table with add/remove rows
5. Totals section — subtotal, IVA, grand total (calculated)
6. Notes field — optional notes visible on printed/sent invoice
7. Action buttons — save as draft, send immediately

---

## UI Components

### Component 1: PatientTypeahead

**Type:** Async combobox (Radix UI Combobox or react-select)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| placeholder | string | "Buscar paciente por nombre o documento..." | Input placeholder |
| debounceMs | number | 300 | Debounce before API call |
| required | boolean | true | Validation required |

**Behavior:**
- Minimum 2 characters before search
- Shows patient avatar + name + document in dropdown results
- Selecting patient auto-fills header with patient info
- If arriving from patient context (URL param `?patient_id=...`), pre-selects patient

### Component 2: LineItemsTable

**Type:** Dynamic editable table (react-hook-form useFieldArray)

**Columns:**

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| description | Combobox (catalog) + free text | Yes | Select from service catalog or type manually |
| quantity | Number input | Yes | Min 1, max 999 |
| unit_price | Currency input | Yes | Auto-filled from catalog, editable |
| discount_pct | Number input (%) | No | 0-100, applied per line |
| subtotal | Computed display | — | quantity × unit_price × (1 - discount/100) |
| remove | Icon button | — | Remove row (trash icon) |

**Line item behavior:**
- "Agregar ítem" button appends new empty row
- Selecting from service catalog auto-fills description + unit price
- Manual entry allowed (free text description + custom price)
- At least 1 line item required to save/send
- Subtotal per row updates in real time as user types

### Component 3: TreatmentPlanImportButton

**Type:** Button + Dropdown (conditional)

**Behavior:**
- Appears after patient is selected
- Dropdown lists patient's active treatment plans (GET `/api/v1/treatment-plans?patient_id=...&status=approved`)
- Selecting a plan populates line items with plan procedures and approved prices
- Existing line items are replaced (with confirmation dialog if items already present)

### Component 4: TotalsPanel

**Type:** Summary card (read-only computed display)

**Content:**

| Row | Calculation |
|-----|-------------|
| Subtotal | Sum of all line item subtotals |
| Descuento total | Sum of discounts |
| Base gravable | Subtotal − Descuento total |
| IVA (19%) | Base gravable × 0.19 (if applicable; dental services may be IVA-exempt — toggle) |
| Total | Base gravable + IVA |

**IVA toggle:** "Aplicar IVA (19%)" checkbox. Default state per clinic settings.

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| patient_id | Combobox | Yes | Must select existing patient | "Selecciona un paciente" | "Buscar paciente..." |
| invoice_date | Date | Yes | Valid date, not in future | "Fecha inválida" | "dd/mm/aaaa" |
| due_date | Date | No | Must be ≥ invoice_date | "La fecha de vencimiento debe ser posterior a la fecha de factura" | "dd/mm/aaaa" |
| items[].description | Text / Combobox | Yes | Non-empty, max 200 chars | "Descripción requerida" | "Procedimiento o servicio..." |
| items[].quantity | Number | Yes | Integer, min 1 | "Cantidad mínima: 1" | "1" |
| items[].unit_price | Currency | Yes | Positive number | "Precio requerido" | "$0" |
| items[].discount_pct | Number | No | 0-100 | "Descuento entre 0 y 100%" | "0" |
| notes | Textarea | No | Max 500 chars | — | "Notas para el paciente (opcional)..." |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Search patients | `/api/v1/patients?q={query}` | GET | `specs/patients/P-01.md` | None |
| Fetch service catalog | `/api/v1/billing/services?q={query}` | GET | `specs/billing/B-14.md` | 10min |
| Fetch treatment plans | `/api/v1/treatment-plans?patient_id={id}&status=approved` | GET | `specs/treatment-plans/TP-01.md` | 2min |
| Create invoice (draft) | `/api/v1/billing/invoices` | POST | `specs/billing/B-01.md` | — |
| Create + send invoice | `/api/v1/billing/invoices` + send | POST | `specs/billing/B-01.md` | — |

### State Management

**Local State (useState):**
- `isSubmitting: boolean`
- `sendMode: 'draft' | 'send'` — tracks which button was clicked

**Global State (Zustand):**
- None

**Server State (TanStack Query):**
- Query key: `['services-catalog', tenantId, query]` (stale 10min)
- Query key: `['treatment-plans', patientId, 'approved']` (stale 2min)
- Mutation: `useMutation(createInvoice)` — on success redirect to detail page

**Form State (React Hook Form):**
- Schema: Zod with `z.object({ patient_id, invoice_date, due_date, items: z.array(...), apply_iva, notes })`
- `useFieldArray` for dynamic line items
- `watch()` on items to compute running totals

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select patient | Click typeahead result | Patient set, treatment plan button appears | Patient name shown in field |
| Import from plan | Select plan in dropdown | Line items populated from plan procedures | Confirmation if items exist; then populated |
| Add line item | Click "Agregar ítem" | New empty row appended to table | New row focused on description field |
| Select catalog item | Type/select in description combobox | Description + price auto-filled | Fields populated |
| Edit quantity/price | Type in cell | Row subtotal + grand total update in real time | Totals panel updates live |
| Remove line item | Click trash icon on row | Row removed, totals recalculate | Row fades out (150ms) |
| Toggle IVA | Click checkbox | Total recalculates with/without 19% IVA | IVA row in totals panel shows/hides |
| Save as draft | Click "Guardar como borrador" | POST invoice with status=draft | Loading spinner on button → redirect to detail |
| Send invoice | Click "Enviar factura" | POST invoice + trigger send | Loading spinner → redirect to detail with "Factura enviada" toast |
| Cancel | Click "← Volver" with data | Confirmation dialog | Dialog: "¿Descartar cambios?" |

### Animations/Transitions

- Line item row added: slide down + fade in (150ms)
- Line item row removed: fade out + collapse (200ms)
- Totals panel: number changes animate with `transition-all` (100ms)

---

## Loading & Error States

### Loading State
- Catalog search: spinner in description combobox input while fetching suggestions
- Patient search: spinner in patient typeahead
- Form submit: button shows spinner + disabled state; prevent double-submit

### Error State
- Inline validation errors below each field (React Hook Form)
- API error (400/500): error toast "No se pudo guardar la factura. Verifica los datos e intenta de nuevo."
- Network error: toast "Error de conexión. Intenta de nuevo."

### Empty State
- No line items: placeholder row "Agrega al menos un ítem para continuar" with "Agregar ítem" button highlighted
- No catalog results: "Sin resultados. Puedes ingresar el ítem manualmente." in dropdown

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Line items table stacks vertically per item (card layout). Each item: description full-width, then qty/price/discount in a row. Totals panel sticky at bottom. Action buttons stack vertically (full width). |
| Tablet (640-1024px) | Line items table with horizontal scroll. Patient + date fields in 2-column grid. Totals panel right-aligned. |
| Desktop (> 1024px) | Full table layout. Patient field and date fields in same row. Totals panel floats right of notes field. |

**Tablet priority:** High — receptionists create invoices on tablets at front desk.

---

## Accessibility

- **Focus order:** Patient typeahead → invoice date → due date → import button → line items (description → qty → price → discount) → IVA toggle → notes → save/send buttons
- **Screen reader:** `aria-label="Ítems de factura"` on table. Each row has `aria-label="Ítem {n}"`. Totals panel has `aria-live="polite"` so total updates are announced. Required fields have `aria-required="true"`.
- **Keyboard navigation:** Tab through all inputs. Enter selects catalog item. Delete key on focused row removes it (with confirmation). Escape closes catalog dropdown.
- **Color contrast:** WCAG AA. Error states use red text + icon, not color alone.
- **Language:** All labels, errors, placeholders in es-419.

---

## Design Tokens

**Colors:**
- Section card: `bg-white rounded-xl border border-gray-100 p-6`
- Totals panel: `bg-gray-50 rounded-xl p-4`
- Grand total row: `text-xl font-bold text-gray-900`
- IVA row: `text-sm text-gray-500`
- Remove button: `text-gray-400 hover:text-red-500`
- Line item input: `border-gray-200 focus:ring-primary-500`

**Typography:**
- Section title: `text-base font-semibold text-gray-700`
- Table header: `text-xs font-medium text-gray-500 uppercase tracking-wider`
- Currency cells: `text-sm font-mono text-gray-900`
- Total label: `text-sm text-gray-500`
- Grand total: `text-xl font-bold text-gray-900`

**Spacing:**
- Between sections: `space-y-6`
- Table row: `py-2 px-3`
- Button group: `gap-3 mt-8`

**Border Radius:**
- Section cards: `rounded-xl`
- Inputs: `rounded-md`
- Action buttons: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` — form validation
- `@tanstack/react-query` — async data fetching
- `@radix-ui/react-combobox` — patient + catalog typeaheads
- `lucide-react` — Trash2, Plus, ChevronDown, AlertCircle
- `date-fns` — date validation, formatting

**File Location:**
- Page: `src/app/(dashboard)/billing/invoices/new/page.tsx`
- Components: `src/components/billing/InvoiceForm.tsx`, `src/components/billing/LineItemsTable.tsx`, `src/components/billing/TotalsPanel.tsx`, `src/components/billing/TreatmentPlanImport.tsx`
- Hooks: `src/hooks/useCreateInvoice.ts`, `src/hooks/useServiceCatalog.ts`
- API: `src/lib/api/billing.ts`
- Schema: `src/lib/schemas/invoice.schema.ts`

**Hooks Used:**
- `useAuth()` — tenant context
- `useFieldArray()` — dynamic line items
- `useWatch()` — real-time totals calculation
- `useMutation(createInvoice)` — form submission
- `useQuery(serviceCatalog)` — catalog typeahead

**Total Calculation Logic:**
```typescript
const totals = useMemo(() => {
  const subtotal = items.reduce((acc, item) =>
    acc + item.quantity * item.unit_price * (1 - (item.discount_pct || 0) / 100), 0);
  const iva = applyIva ? subtotal * 0.19 : 0;
  return { subtotal, iva, total: subtotal + iva };
}, [items, applyIva]);
```

---

## Test Cases

### Happy Path
1. Create invoice from treatment plan
   - **Given:** Patient "Ana López" has an approved treatment plan with 3 procedures
   - **When:** User selects patient → clicks "Importar desde plan de tratamiento" → selects the plan → clicks "Enviar factura"
   - **Then:** Invoice created and sent; redirect to detail with "Factura enviada" toast

2. Manual line item entry
   - **Given:** Empty form
   - **When:** User adds patient, adds 2 manual line items, checks IVA, clicks "Guardar como borrador"
   - **Then:** Invoice created as draft; totals correct including 19% IVA

### Edge Cases
1. Zero-quantity validation
   - **Given:** User enters quantity 0
   - **When:** Submits form
   - **Then:** Inline error "Cantidad mínima: 1"

2. Discount > 100%
   - **Given:** User enters 150 in discount field
   - **When:** Submits form
   - **Then:** Inline error "Descuento entre 0 y 100%"

### Error Cases
1. Patient not found
   - **Given:** Clinic has no matching patient
   - **When:** User types name with no results
   - **Then:** Dropdown shows "Sin resultados. Verifica el nombre o documento."

---

## Acceptance Criteria

- [ ] Patient typeahead search (debounced, min 2 chars)
- [ ] Invoice date field (required) and due date field (optional, must be ≥ invoice date)
- [ ] Import from treatment plan: populates line items from approved plan
- [ ] Dynamic line items table with add/remove rows
- [ ] Description combobox: service catalog search + free-text fallback
- [ ] Quantity, unit price, discount % fields with real-time subtotal per row
- [ ] IVA (19%) toggle with automatic grand total recalculation
- [ ] Notes textarea (optional)
- [ ] "Guardar como borrador" and "Enviar factura" actions
- [ ] Zod validation with inline errors (all fields)
- [ ] Loading state on submit buttons (no double-submit)
- [ ] Success redirect to invoice detail with toast
- [ ] Discard confirmation when navigating away with unsaved data
- [ ] Responsive on mobile (stacked), tablet (scrollable table), desktop (full layout)
- [ ] Accessibility: focus order, ARIA labels, keyboard navigation
- [ ] Spanish (es-419) labels and messages

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
