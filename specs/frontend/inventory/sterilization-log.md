# Registro de Esterilizacion (Sterilization Log) — Frontend Spec

## Overview

**Screen:** Sterilization cycle registration form (top section) and historical log table (bottom section). The form captures autoclave details, biological and chemical indicators, instrument list, and requires a digital signature. The history table is sortable, filterable, and each row is expandable for full details. PDF export available.

**Route:** `/inventory/sterilization`

**Priority:** Medium

**Backend Specs:** `specs/inventory/sterilization-create.md` (INV-05), `specs/inventory/sterilization-list.md` (INV-06)

**Dependencies:** `specs/frontend/inventory/inventory-list.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar "Inventario" → "Esterilizacion" sub-link
- Inventory list page → "Registro de Esterilizacion" button

**Exit Points:**
- Success form submit → cycle added to history table below, form resets
- PDF export → download file
- "Ver inventario" link → `/inventory`

**User Story:**
> As a doctor | assistant, I want to register each sterilization cycle with indicators and instrument lists so that I can maintain required compliance records per Colombian biosafety regulations.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | "Registro de Esterilizacion"           |
|          | [Ver inventario link]                  |
|          +---------------------------------------+
|          |  === NUEVO CICLO ===                  |
|          |  [Sterilization Form]                 |
|          |  [Registrar Ciclo btn]                |
|          +---------------------------------------+
|          |  === HISTORIAL ===                    |
|          |  [Filter row + Exportar PDF btn]      |
|          |  [History Table - sortable]           |
|          |  [Pagination]                         |
+------------------------------------------+-------+
```

---

## Form Section: Nuevo Ciclo de Esterilizacion

### Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Notes |
|-------|------|----------|------------|------------------------|-------|
| autoclave_id | select | Yes | From registered autoclaves | "Selecciona un autoclave" | Preloaded list |
| numero_carga | text | Yes | Alphanumeric, max 20 | "Numero de carga requerido" | Auto-suggested: "C-{date}-{n}" |
| fecha_hora | datetime-local | Yes | Past or current datetime | "Fecha y hora requeridas" | Default: now |
| temperatura | number | Yes | 121-134°C | "Temperatura debe ser entre 121 y 134°C" | `°C` unit label |
| tiempo_exposicion | number | Yes | 3-60 min | "Duracion entre 3 y 60 minutos" | `min` unit label |
| indicador_biologico | radio | Yes | pass / fail / no_aplica | "Selecciona el resultado del indicador" | Pass/Fail/No aplica |
| indicador_quimico | radio | Yes | pass / fail | "Selecciona el resultado del indicador" | Pass/Fail |
| instrumentos | multi-select | Yes | Min 1 instrument | "Selecciona al menos un instrumento" | Search from inventory |
| observaciones | textarea | No | Max 500 chars | — | Optional notes |
| firma | canvas | Yes | Non-empty signature | "La firma del responsable es requerida" | Who performed sterilization |

### Component: AutoclaveSelect

**Type:** Select with registered autoclave list

**Options loaded from:** `GET /api/v1/inventory/autoclaves`
**Each option:** `{model_name} — Serial {serial} (Sala {room})`
**"Agregar autoclave" option at bottom:** Opens a small modal to register a new autoclave inline.

### Component: BiologicalIndicatorRadio

**Type:** Radio group with visual indicators

**Options as large radio cards:**
- "Aprobado (Negativo)" — `CheckCircle text-green-500` — sterility confirmed
- "Rechazado (Positivo)" — `XCircle text-red-500` — cycle failed, instruments not sterile
- "No aplica / No disponible" — `Minus text-gray-400`

**When "Rechazado":** Warning banner appears below radio: `"ATENCIÓN: Ciclo fallido. Los instrumentos de esta carga NO deben usarse. Notifica al responsable."` `bg-red-50 border-red-300 text-red-700 font-medium`

### Component: InstrumentMultiSelect

**Type:** Searchable multi-select with chips

**Behavior:**
- Search input with typeahead (debounced 300ms) against inventory items filtered to category = "Instrumental"
- Selected instruments shown as chips below input
- Each chip: instrument name + lot # + X remove
- Quick add "Carga completa (todos los instrumentos disponibles)" option at top of dropdown

### Component: SignaturePad

**Type:** Embedded signature canvas (same implementation as consent-sign.md)

**Label:** `"Firma del responsable del ciclo"` `text-sm font-medium text-gray-700`
**Under signature:** Name field auto-filled with current user's name (editable)
**"Limpiar" and "Deshacer" buttons** (same as consent-sign)

---

## Zod Schema

```typescript
const sterilizationCycleSchema = z.object({
  autoclave_id: z.string().uuid("Selecciona un autoclave"),
  numero_carga: z.string().min(1).max(20),
  fecha_hora: z.string().datetime(),
  temperatura: z.number().min(121).max(134, "Temperatura debe ser entre 121 y 134°C"),
  tiempo_exposicion: z.number().min(3).max(60),
  indicador_biologico: z.enum(["pass", "fail", "no_aplica"]),
  indicador_quimico: z.enum(["pass", "fail"]),
  instrumentos: z.array(z.string().uuid()).min(1, "Selecciona al menos un instrumento"),
  observaciones: z.string().max(500).optional(),
  firma: z.string().min(10, "La firma es requerida"),  // base64 data URL
  responsable_nombre: z.string().min(2),
});
```

---

## History Table Section

### Filter Row

| Filter | Type | Options |
|--------|------|---------|
| Autoclave | Select | All autoclaves |
| Resultado | Select | Todos / Aprobado / Rechazado |
| Fecha desde | Date | — |
| Fecha hasta | Date | — |

**"Exportar PDF" button:** Right-aligned. Downloads sterilization log as official PDF report. Button: `variant="outline"` with `FileDown` icon.

### History Table

**Columns:**

| Column | Sortable | Notes |
|--------|---------|-------|
| Fecha/Hora | Yes | "15 feb 2026 10:30 AM" |
| Autoclave | No | Model + serial abbreviated |
| Carga # | No | `font-mono text-xs` |
| Temperatura | Yes | `{n}°C` |
| Duracion | No | `{n} min` |
| Indicador Bio | No | Icon: CheckCircle green / XCircle red / Minus gray |
| Indicador Quim | No | Same icon pattern |
| Instrumentos | No | `{N} instrumentos` — click to see list |
| Responsable | No | Name + signature thumbnail |
| Detalles | No | `ChevronDown` expand button |

**Failed cycle rows:** Full row `bg-red-50 border-l-4 border-red-500`.

**Expandable row:**
- Click `ChevronDown` in Detalles column
- Expands to show: full instrument list (each with inventory ID link), observations, full signature image, PDF download for this cycle
- `motion.div` height animation 250ms

### Pagination

Standard pagination: 20 records per page, page numbers + prev/next arrows.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Create cycle | `/api/v1/sterilization` | POST | `specs/inventory/sterilization-create.md` | None |
| List cycles | `/api/v1/sterilization?page={n}&autoclave={id}&result={r}&from={d}&to={d}` | GET | `specs/inventory/sterilization-list.md` | 2min |
| Get autoclaves | `/api/v1/inventory/autoclaves` | GET | — | 10min |
| Get instruments | `/api/v1/inventory?category=instrumental&q={search}` | GET | — | 2min |
| Export PDF | `/api/v1/sterilization/report.pdf?from={d}&to={d}` | GET | — | None |

### State Management

**Local State (useState):**
- `expandedRowId: string | null`
- `isSubmitting: boolean`
- `serverError: string | null`

**Server State (TanStack Query):**
- `useQuery(['sterilization-history', filters, page], { staleTime: 2 * 60 * 1000 })`
- `useMutation({ onSuccess: () => { queryClient.invalidateQueries(['sterilization-history']); resetForm(); } })`

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select "Rechazado" for bio indicator | Radio click | Red warning banner appears below | Immediate |
| Add instrument | Typeahead select | Chip added below search | Chip animation |
| Remove instrument chip | Click X | Chip removed | Immediate |
| Submit form | Click "Registrar Ciclo" | POST → success | Loading state → form resets → history table refreshes → success toast |
| Expand history row | Click ChevronDown | Row expands | Height animation 250ms |
| Collapse history row | Click ChevronUp | Row collapses | Height animation |
| Click "Exportar PDF" | Click | Download PDF | "Generando PDF..." toast → download |

---

## Loading & Error States

### Loading State
- Form submit: `"Registrando ciclo..."` spinner on button, all fields disabled
- History table load: 10 skeleton rows
- Instruments search: spinner in input while fetching

### Error State
- Form submit error: `bg-red-50` banner above submit button
- Field errors: inline per field
- History load error: inline error + retry

### Empty State
- No cycles in history: "Sin ciclos de esterilizacion registrados" + thermometer illustration + "Registra tu primer ciclo arriba" note

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Form fields single column. Indicator radios stacked. History table shows only: Fecha, Autoclave, Bio Indicator, Expand button. Horizontal scroll for full table or detail panel. |
| Tablet (640-1024px) | Form two columns for short fields (temp + duration side by side). History table all columns. |
| Desktop (> 1024px) | Same as tablet. Max width `max-w-5xl`. |

---

## Accessibility

- **Focus order:** Form fields top-to-bottom → Submit → History filters → History table rows → Pagination
- **Screen reader:** Indicator radio cards: `role="radiogroup" aria-label="Resultado indicador biologico"`. Failed cycle warning: `role="alert"`. History table: proper `<table>` markup with `th scope="col"`. Expandable rows: `aria-expanded` on expand button.
- **Keyboard:** Form Tab navigation. History row expand with Enter/Space on expand button.
- **Language:** All labels, indicator options, status text in es-419. Temperature and duration units labeled clearly.

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod`
- `framer-motion` — row expand, warning banner
- `lucide-react` — CheckCircle, XCircle, Minus, ChevronDown, ChevronUp, FileDown, Loader2
- Custom `SignaturePad` component (shared with consent-sign)

**File Location:**
- Page: `src/app/(dashboard)/inventory/sterilization/page.tsx`
- Components: `src/components/inventory/SterilizationForm.tsx`, `src/components/inventory/SterilizationHistoryTable.tsx`

---

## Acceptance Criteria

- [ ] Form: autoclave select, load number, date/time, temperature, duration
- [ ] Biological indicator radio with pass/fail/no-aplica options and failed warning banner
- [ ] Chemical indicator radio with pass/fail options
- [ ] Instruments multi-select with typeahead against inventory
- [ ] Signature pad with clear/undo buttons
- [ ] Zod validation on all required fields
- [ ] Submit creates cycle, refreshes history, resets form
- [ ] History table with expand-row detail view
- [ ] Failed cycle rows visually distinct (red row + left border)
- [ ] Filters: autoclave, result, date range
- [ ] Export PDF button downloads report
- [ ] Pagination: 20 records per page
- [ ] Responsive: condensed mobile table, full tablet/desktop
- [ ] Accessibility: table markup, radiogroup ARIA, alert on failed indicator
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
