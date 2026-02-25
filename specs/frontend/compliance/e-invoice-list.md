# Lista de Facturas Electrónicas — Frontend Spec

## Overview

**Spec ID:** FE-CO-03

**Screen:** Electronic invoice list and status tracking. Full table view of all invoices submitted to the tax authority, with status tracking, per-row resend action, XML/PDF download, a submission history modal, and multi-country authority awareness (DIAN for Colombia, SAT for Mexico, SII for Chile).

**Route:** `/compliance/e-invoices`

**Priority:** High (DIAN compliance — Colombia deadline April 2026)

**Backend Specs:**
- `specs/compliance/CO-06.md` — electronic-invoice (submit, retry, download)
- `specs/compliance/CO-07.md` — electronic-invoice-status (get status, submission history)

**Dependencies:**
- `FE-DS-01` (design tokens)
- `FE-DS-02` (button)
- `FE-DS-05` (table)
- `FE-DS-10` (card)
- `FE-DS-11` (badge)
- `FE-DS-12` (modal)
- `FE-DS-14` (skeleton)
- `specs/frontend/billing/invoice-list.md` (FE-BI-01 — sibling screen; links from billing to this compliance view)

---

## User Flow

**Entry Points:**
- Sidebar: Cumplimiento → "Facturas Electrónicas {authority name}"
- Billing invoice list → "Ver en {authority}" link per invoice row
- Dashboard compliance widget → "Ver facturas electrónicas"
- Notification: "N facturas rechazadas por {authority}" → links here

**Exit Points:**
- Click invoice number → `/billing/invoices/{id}` (billing invoice detail)
- Click patient name → `/patients/{id}`
- Download XML → browser file download
- Download PDF → browser file download
- "Configurar facturación electrónica" link (shown when not configured) → `/settings/cumplimiento`
- Back → `/compliance`

**User Story:**
> As a clinic_owner, I want to see the submission status of all electronic invoices sent to the tax authority, quickly identify and resend rejected ones, and download the XML or PDF of any submitted invoice — so that my clinic maintains billing compliance and has a complete audit trail.

**Roles with access:** `clinic_owner` only. Other roles redirect to `/dashboard` with toast "Solo los propietarios pueden ver las facturas electrónicas."

---

## Layout Structure

```
+------------------------------------------+
|        Header (h-16)                     |
+--------+---------------------------------+
|        |  Cumplimiento > Facturas DIAN   |
|        |  "Facturas Electrónicas —       |
|        |   DIAN"  [Authority badge]      |
| Side-  +---------------------------------+
|        |  [Connection Status Banner]     |
|        +---------------------------------+
|        |  [Stats Row — 4 KPI cards]     |
|        +---------------------------------+
|        |  [Filter Bar]                  |
|        +---------------------------------+
|        |  [E-Invoice Table]             |
|        |  [Pagination]                  |
+--------+---------------------------------+
```

**Sections:**
1. Page header — title, country authority name, authority connection badge
2. Connection status banner — shown only when authority is disconnected or degraded
3. Stats row — 4 KPI cards: total, accepted, pending, rejected (clickable to filter)
4. Filter bar — status, date range, search
5. E-invoice table — 7 columns with per-row actions
6. Pagination
7. Submission history modal — opens on "Ver historial" action

---

## Country-Aware Authority Labels

The page adapts its labels based on `tenant.country`:

| Country | Tax Authority | Authority Short | Invoice ID Code | Abbreviation |
|---------|-------------|-----------------|----------------|--------------|
| `CO` | DIAN | DIAN | CUFE | Código Único de Factura Electrónica |
| `MX` | SAT | SAT | UUID | Folio Fiscal |
| `CL` | SII | SII | Folio | Folio Tributario |

**Label substitution examples:**
- Page title: `"Facturas Electrónicas — {authority}"` → `"Facturas Electrónicas — DIAN"`
- Column header: `"{CUFE/UUID/Folio}"` → `"CUFE"` (CO), `"Folio Fiscal"` (MX)
- Status tooltip prefix: `"DIAN Código: {N} —"` / `"SAT Error:"` / `"SII:"` per country

This is implemented via a `useCountryCompliance()` hook that returns `{ authority, invoiceIdCode, invoiceIdLabel }` based on `tenant.country`.

---

## UI Components

### Component 1: AuthorityConnectionBadge

**Type:** Pill badge — top right of page header area

**Position:** Inline with the page title (`flex justify-between items-start`)

**States:**

| State | Visual | Icon |
|-------|--------|------|
| Connected | `bg-green-100 text-green-700 border border-green-200` | `Wifi` |
| Degraded (slow) | `bg-amber-100 text-amber-700 border border-amber-200` | `WifiOff` |
| Disconnected | `bg-red-100 text-red-700 border border-red-200` | `WifiOff` |

**Labels:** `"{authority} Conectado"` / `"{authority} — Respuesta lenta"` / `"{authority} — Sin conexión"`

**Data source:** `GET /api/v1/integrations/{authority_code}/status` — polled every 60 seconds via `refetchInterval: 60000`

---

### Component 2: ConnectionStatusBanner

**Type:** Full-width alert — shown only when state is `disconnected` or `degraded`

**Disconnected:**
```
+----------------------------------------------+
| ⚠  Conexión con DIAN no disponible           |
|    Los envíos están en pausa hasta que       |
|    se restablezca la conexión.               |
|                          [Ver configuración] |
+----------------------------------------------+
```
`bg-red-50 border border-red-200 rounded-xl p-4`

**Degraded:**
```
+----------------------------------------------+
| ⚡  DIAN está respondiendo lentamente        |
|    Los envíos pueden demorar más de lo normal|
+----------------------------------------------+
```
`bg-amber-50 border border-amber-200 rounded-xl p-4`

**Hidden when `connected`.**

---

### Component 3: StatusStatsRow

**Type:** 4 compact KPI cards in a horizontal row

| # | Label (es-419) | Value | On Click |
|---|----------------|-------|----------|
| 1 | Total enviadas | `{N}` | No filter |
| 2 | Aceptadas | `{N}` | Filter table to `accepted` |
| 3 | Pendientes | `{N}` | Filter table to `pending` |
| 4 | Rechazadas | `{N}` | Filter table to `rejected` |

**Card style:**
- Default: `bg-white border border-gray-200 rounded-lg p-4 cursor-pointer hover:border-gray-300`
- Active (when matching filter applied): `border-2 border-blue-400 bg-blue-50`
- "Rechazadas" card default border: `border-red-200` if count > 0 (draws attention)

**Accessibility:** Each card is `role="button"` with `aria-label="Filtrar: {N} facturas {label}"` and `tabIndex={0}`

---

### Component 4: FilterBar

**Type:** Horizontal filter group

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| Estado | Multi-select dropdown | Todos / Pendiente / En proceso / Aceptada / Aceptada con observaciones / Rechazada / Error | All |
| Fecha desde | Date input | Calendar picker | 30 days ago |
| Fecha hasta | Date input | Calendar picker | Today |
| Buscar | Text input (debounced 300ms) | Searches by invoice #, patient name, {invoiceIdCode} | Empty |

**"Limpiar filtros" button:** Appears to the right when any filter is non-default. Resets all filters + URL state.

**URL sync:** All filter values are synced to URL: `?status=rejected&from=2026-01-01&to=2026-02-25&q=FE-001`

---

### Component 5: EInvoiceTable

**Type:** Data table (TanStack Table, no row selection on mobile)

#### Columns

| Column | Header (es-419) | Width | Sortable | Content |
|--------|-----------------|-------|----------|---------|
| invoice | Factura # | 110px | Yes | Link `text-sm font-mono text-teal-600` → `/billing/invoices/{id}` |
| patient | Paciente | flex-1 | Yes | Name `text-sm text-gray-800` — link → `/patients/{id}` |
| amount | Monto | 110px | Yes | COP/MXN/CLP formatted `text-sm font-medium text-gray-900` |
| date | Enviada el | 130px | Yes | `"15 feb 2026, 09:45"` `text-xs text-gray-500` |
| status | Estado | 160px | No | Status badge (see below) |
| invoice_id | CUFE / UUID / Folio | 160px | No | Truncated + copy button |
| actions | Acciones | 180px | No | Inline action buttons |

#### DIAN/SAT/SII Status Badges

| Status code | Label (es-419) | Badge classes | Extra |
|-------------|----------------|--------------|-------|
| `pending` | Pendiente de envío | `bg-gray-100 text-gray-600` | — |
| `in_process` | En proceso | `bg-blue-100 text-blue-700` | `● animate-pulse` dot |
| `accepted` | Aceptada | `bg-green-100 text-green-700` | — |
| `accepted_with_notes` | Aceptada con observaciones | `bg-amber-100 text-amber-700` | — |
| `rejected` | Rechazada | `bg-red-100 text-red-700 font-semibold` | — |
| `error` | Error de envío | `bg-red-100 text-red-600` | — |

**Pulsing dot for `in_process`:** `<span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse inline-block mr-1" />`

**Status badge tooltip (hover or tap on mobile):**
- Content: translated DIAN/SAT/SII error message in plain Spanish
- Example: `"DIAN Código: 89 — El NIT del emisor no coincide con el registrado en el RUT. Verifica el NIT de la clínica en Configuración."`
- Implementation: `@radix-ui/react-tooltip`, `max-w-xs text-xs`, side="bottom"
- Raw authority error codes never shown directly — always wrapped in Spanish explanation

#### Invoice ID Column (CUFE / UUID / Folio)

- Display: first 20 characters + `"..."` in `text-xs font-mono text-gray-500`
- Copy button: `<Copy className="w-3.5 h-3.5" />` icon — click copies full ID to clipboard
  - Success toast: `"CUFE copiado"` / `"UUID copiado"` / `"Folio copiado"` (authority-aware)
- When no ID yet (status = pending): `"—"` `text-gray-300`
- Full ID shown in submission history modal

#### Actions Column

Per-row actions depend on status:

| Status | Available actions |
|--------|-----------------|
| `pending` | "Enviar ahora" button |
| `in_process` | "Actualizar estado" link (polls CO-07) |
| `accepted` | "XML" download button + "PDF" download button + "Ver historial" |
| `accepted_with_notes` | "XML" + "PDF" + "Ver historial" + "Ver observaciones" (opens modal) |
| `rejected` | "Reintentar" button + "XML" (inspection) + "Ver historial" |
| `error` | "Reintentar" button + "Ver historial" |

**"Reintentar" button:**
- Style: `text-xs text-red-600 border border-red-200 px-3 py-1 rounded-md hover:bg-red-50`
- On click: `POST /api/v1/e-invoices/{id}/retry` (CO-06)
- Optimistic update: row status → `in_process`; button replaced by "En proceso..." `text-xs text-blue-600`
- If retry fails: row reverts to `rejected`; toast `"Error al reenviar la factura {#}. Código: {code}"`

**"Enviar ahora" button:**
- Same POST as retry; used for `pending` status invoices
- Style: `text-xs text-teal-600 border border-teal-300 px-3 py-1 rounded-md hover:bg-teal-50`

**Download XML:**
- `GET /api/v1/e-invoices/{id}/xml` (CO-06) → browser download
- Button: `FileCode icon` + `"XML"` `text-xs text-gray-600 border border-gray-200 px-2 py-1 rounded`

**Download PDF:**
- `GET /api/v1/billing/invoices/{id}/pdf` → browser download
- Button: `FileText icon` + `"PDF"` — same style as XML

**"Ver historial" link:**
- `text-xs text-gray-500 underline hover:text-gray-700`
- Opens `SubmissionHistoryModal` for the row's invoice

---

### Component 6: SubmissionHistoryModal

**Type:** Modal — `FE-DS-12` Modal component, max-w-lg

**Trigger:** "Ver historial" link in actions column

**Content:**
```
+----------------------------------------------+
| Historial de Envíos — Factura FAC-2026-001   |
| ─────────────────────────────────────────── |
| [Timeline of submission attempts]            |
|                                              |
| ● 15 feb 2026, 09:45   Enviada              |
|   → En proceso                               |
|                                              |
| ● 15 feb 2026, 09:47   Respuesta DIAN        |
|   → Rechazada                               |
|   Código 89: El NIT del emisor no coincide  |
|   con el RUT registrado en DIAN.            |
|                                              |
| ● 15 feb 2026, 10:03   Reintento             |
|   → Aceptada                               |
|   CUFE: 8a3f9c... (completo copiable)       |
| ─────────────────────────────────────────── |
| CUFE completo:                              |
| [8a3f9c21b4d7e0f1a2b3c4d5e6f7a8b9c0d1...]  |
| [Copiar CUFE completo]                      |
|                                            [X] Cerrar |
+----------------------------------------------+
```

**Timeline entries:** Vertical list, newest first. Each entry has:
- Timestamp `text-xs text-gray-500`
- Event label `text-sm font-medium`
- Status badge (same as table)
- Error message in `text-sm text-red-700 bg-red-50 rounded p-2` (for rejection entries)
- CUFE/UUID/Folio when finally accepted

**Full invoice ID section:** Below timeline. `font-mono text-xs break-all text-gray-700`. "Copiar" button beside it.

**Data source:** `GET /api/v1/e-invoices/{id}/history` (CO-07)

---

## Batch Actions

**Batch retry bar:** Appears at bottom of screen (sticky) when one or more rows are selected via checkbox.

**Checkbox column:** Visible on desktop. Hidden on mobile (no batch on mobile). Appears on hover over row on tablet.

**Batch bar content:**
```
+----------------------------------------------+
| N facturas seleccionadas    [Reintentar seleccionadas (N)] [Deseleccionar]
+----------------------------------------------+
```
`bg-blue-50 border-t border-blue-200 px-4 py-3 fixed bottom-0 left-0 right-0 z-30`

**"Reintentar seleccionadas" button:**
- Enabled only if ALL selected invoices have status `rejected` or `error`
- If mixed statuses: disabled + tooltip "Solo se pueden reintentar facturas rechazadas o con error"
- On click: confirmation dialog "¿Reintentar envío de {N} facturas rechazadas a {authority}?"
- On confirm: `POST /api/v1/e-invoices/bulk-retry` → progress indicator "Reenviando {current} de {total}..."
- On success: toast "{N} facturas reenviadas" + list invalidated

**Batch bar animation:** Slides up from bottom on selection (200ms ease-out, framer-motion).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List e-invoices | `GET /api/v1/e-invoices` | GET | `specs/compliance/CO-07.md` | 2min stale |
| Authority status | `GET /api/v1/integrations/{code}/status` | GET | — | 60s |
| Submit invoice | `POST /api/v1/e-invoices/{id}/submit` | POST | `specs/compliance/CO-06.md` | — |
| Retry invoice | `POST /api/v1/e-invoices/{id}/retry` | POST | `specs/compliance/CO-06.md` | — |
| Bulk retry | `POST /api/v1/e-invoices/bulk-retry` | POST | `specs/compliance/CO-06.md` | — |
| Poll single status | `GET /api/v1/e-invoices/{id}/status` | GET | `specs/compliance/CO-07.md` | None |
| Get submission history | `GET /api/v1/e-invoices/{id}/history` | GET | `specs/compliance/CO-07.md` | 30s |
| Download XML | `GET /api/v1/e-invoices/{id}/xml` | GET | `specs/compliance/CO-06.md` | None |
| Download PDF | `GET /api/v1/billing/invoices/{id}/pdf` | GET | — | None |

**Query Parameters (list endpoint):**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string[] | Filter by status (comma-separated) |
| `date_from` | ISO date | Submission date from |
| `date_to` | ISO date | Submission date to |
| `q` | string | Search invoice #, patient name, or invoice ID code |
| `sort_by` | string | `invoice_number`, `date`, `amount`, `status` |
| `sort_order` | string | `asc` / `desc` |
| `page` | number | 1-based |
| `per_page` | number | 10, 20, 50 |

### State Management

**Local State (useState):**
- `selectedIds: Set<string>` — selected rows for batch retry
- `historyModalInvoiceId: string | null` — which invoice's history modal is open
- `retryingIds: Set<string>` — IDs currently being retried (optimistic)

**Server State (TanStack Query):**
```typescript
// Main list — auto-refresh every 15s when any row is in_process
const hasInProcess = data?.invoices.some(i => i.status === 'in_process');
useQuery({
  queryKey: ['e-invoices', tenantId, filters, sort, page],
  staleTime: 2 * 60 * 1000,
  refetchInterval: hasInProcess ? 15_000 : false,
  keepPreviousData: true, // no flicker during pagination
});

// Authority status — always polled every 60s
useQuery({
  queryKey: ['authority-status', tenantId, authorityCode],
  refetchInterval: 60_000,
  staleTime: 60_000,
});

// Submission history — on-demand per modal open
useQuery({
  queryKey: ['e-invoice-history', invoiceId],
  enabled: historyModalInvoiceId !== null,
  staleTime: 30_000,
});
```

**URL State (useSearchParams):**
- `?status=rejected,error&from=2026-01-01&to=2026-02-25&q=FAC-001&sort_by=date&sort_order=desc&page=1`
- Filter state fully reflected in URL for shareable links and back-navigation

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Reintentar" | Click | POST retry; optimistic status → in_process | Button disabled → "En proceso..."; auto-refresh picks up result |
| Click "Enviar ahora" | Click | POST submit; same as retry | Same flow |
| Click invoice # | Click | Navigate to `/billing/invoices/{id}` | Standard navigation |
| Click patient name | Click | Navigate to `/patients/{id}` | Standard navigation |
| Click "Ver historial" | Click | Open SubmissionHistoryModal | Modal slides in from right (desktop) or bottom sheet (mobile) |
| Click "Ver observaciones" | Click | Open modal to accepted_with_notes detail | Modal with notes from authority |
| Click CUFE copy | Click | Copy full ID to clipboard | Toast "CUFE copiado" |
| Click Download XML | Click | GET → browser file download | "Descargando..." toast briefly |
| Click Download PDF | Click | GET → browser file download | Same |
| Click stat card | Click | Apply status filter | Table re-fetches; card border activates |
| Select row checkbox | Click | Row selected; batch bar appears | Batch bar slides up |
| Click "Reintentar seleccionadas" | Click | Confirmation dialog | Dialog with count; on confirm, bulk retry |
| Auto-refresh (15s) | Timer | Silent refetch when in_process | Status badges update silently |
| Close history modal | Escape or X | Modal closes | Smooth exit transition |

### Animations/Transitions

- Batch bar: `translateY` from 100% to 0 in 200ms ease-out (framer-motion)
- Pulsing blue dot: `animate-pulse` CSS on `in_process` badges
- Table row status badge: 150ms fade when status changes via auto-refresh
- History modal: slide-in from right on desktop (300ms), bottom sheet on mobile
- "Reintentar" optimistic: immediate status badge swap, no delay

---

## Loading & Error States

### Loading State

- Initial page load:
  - Stats row: 4 `h-20 w-36 rounded-lg bg-gray-100 animate-pulse` skeleton cards
  - Filter bar: shown but empty (not skeletonized — renders immediately)
  - Table: 10 `h-14 rounded-lg bg-gray-100 animate-pulse mb-2` skeleton rows
- Filter change / pagination: previous data stays visible at `opacity-60` while new data loads (keepPreviousData)
- History modal: single spinner `Loader2 animate-spin` in center of modal while data loads

### Error State

- List fetch fails: table area replaced by error card
  - Icon: `AlertOctagon` red
  - Message: "Error al cargar las facturas electrónicas. Intenta de nuevo."
  - Button: "Reintentar" — retriggers query

- Retry fails: per-row toast `"Error al reenviar la factura {#}. Código {authority}: {translated_error}"`. Row status reverts from optimistic in_process to rejected.

- Authority disconnected: `ConnectionStatusBanner` shown; "Reintentar" buttons remain functional but will fail with clear error

- History modal fetch fails: error message inside modal "No se pudo cargar el historial. Intenta de nuevo." + Retry button within modal

### Empty State

- **No invoices at all (e-invoicing not configured):**
  ```
  No hay facturas electrónicas configuradas.
  Activa la facturación electrónica DIAN en Configuración para empezar a emitir facturas válidas ante la DIAN.
  [Configurar facturación electrónica →]
  ```
  `text-gray-500` illustration + link to `/settings/cumplimiento`

- **No results for current filters:**
  - "Sin facturas con estos filtros"
  - "Limpiar filtros" button → resets all filters

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table shows only: Factura # + Estado + Acciones. Invoice ID column hidden. Tap row → bottom sheet with full invoice detail (all fields + action buttons). Batch checkboxes hidden. Filters in slide-out panel accessible via "Filtros" button. Stats row scrollable horizontally. |
| Tablet (640–1024px) | Table shows all columns except Invoice ID (shown in submission history modal). Horizontal scroll on table if needed. Batch checkbox column visible on hover. History modal as full-height right panel. |
| Desktop (> 1024px) | All 7 columns visible. Invoice ID truncated with copy button. Batch checkboxes always visible. Batch bar fixed at bottom. History modal as centered dialog. Max-w-7xl content area. |

**Tablet priority:** High — clinic owners track billing compliance on tablets. All action buttons min 44px height. Status badges have tap target padding min 44px.

---

## Accessibility

- **Focus order:** Page heading → Authority badge → Stats cards → Filter inputs → Table (per row: invoice link → patient link → status badge → actions) → Pagination
- **Screen reader:**
  - Status badges: `aria-label="Estado {authority}: {full label}"` (e.g., `"Estado DIAN: Rechazada"`)
  - Invoice ID copy button: `aria-label="Copiar CUFE completo para factura {invoice_number}"`
  - Retry button: `aria-label="Reintentar envío de factura {invoice_number} a DIAN"` — not just "Reintentar"
  - Pulsing dot for in_process: `aria-hidden="true"` (decorative; status label text is the indicator)
  - Table: `<table>` with proper `<th scope="col">` headers, `<caption>` hidden ("Lista de facturas electrónicas")
  - Batch bar: `role="status"` + `aria-live="polite"` + `aria-label="{N} facturas seleccionadas"`
  - History modal: `role="dialog"` + `aria-labelledby` pointing to modal title, focus trapped while open
  - Stats cards: `role="button"` + `aria-label="Filtrar: {N} facturas {label}"`
- **Keyboard:** Table rows Tab-navigable. Copy buttons reachable with Tab. Escape closes modal. All dropdowns keyboard operable. Batch bar keyboard accessible.
- **Color:** Status badges always use both color and text. Retry button labeled, not icon-only. No information conveyed through color alone.
- **Language:** All authority error messages translated to actionable Spanish before display. No raw DIAN/SAT/SII error codes exposed to users without Spanish explanation.

---

## Design Tokens

**Colors:**
- Authority connected: `bg-green-100 text-green-700 border-green-200`
- Authority degraded: `bg-amber-100 text-amber-700 border-amber-200`
- Authority disconnected: `bg-red-100 text-red-700 border-red-200`
- Status pending: `bg-gray-100 text-gray-600`
- Status in_process: `bg-blue-100 text-blue-700` + `bg-blue-500` pulse dot
- Status accepted: `bg-green-100 text-green-700`
- Status accepted_with_notes: `bg-amber-100 text-amber-700`
- Status rejected: `bg-red-100 text-red-700 font-semibold`
- Status error: `bg-red-100 text-red-600`
- "Reintentar" button: `border-red-200 text-red-600 hover:bg-red-50`
- "Enviar ahora" button: `border-teal-300 text-teal-600 hover:bg-teal-50`
- Invoice link: `text-teal-600 hover:text-teal-800`
- Invoice ID: `font-mono text-gray-500`
- Stats card active: `border-2 border-blue-400 bg-blue-50`
- Batch bar: `bg-blue-50 border-t border-blue-200`

**Typography:**
- Invoice number: `text-sm font-mono text-teal-600`
- Patient name: `text-sm text-gray-800`
- Amount: `text-sm font-medium text-gray-900`
- Invoice ID: `text-xs font-mono text-gray-500`
- Submission date: `text-xs text-gray-500`
- Status badge: `text-xs font-medium px-2.5 py-1 rounded-full`
- Stats value: `text-2xl font-bold text-gray-900`
- Stats label: `text-xs text-gray-500`

**Spacing:**
- Page padding: `px-4 py-6 md:px-6 lg:px-8`
- Stats row gap: `gap-4`
- Filter bar gap: `gap-3`
- Table cell: `py-3 px-4`
- Actions gap: `gap-2`
- Modal padding: `p-6`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — server state, `refetchInterval` for auto-refresh, `keepPreviousData`
- `@tanstack/react-table` — table with sorting and row selection
- `@radix-ui/react-tooltip` — status badge tooltips with authority error messages
- `@radix-ui/react-dialog` — submission history modal
- `@radix-ui/react-select` — status multi-select filter dropdown
- `lucide-react` — Wifi, WifiOff, FileCode, FileText, Copy, Loader2, RefreshCw, AlertTriangle, AlertOctagon, X, CheckCircle2
- `framer-motion` — batch bar slide-up animation, modal transitions
- `date-fns` — date formatting with `es` locale for submission timestamps

**File Location:**
- Page: `src/app/(dashboard)/compliance/e-invoices/page.tsx`
- Components:
  - `src/components/compliance/EInvoiceTable.tsx`
  - `src/components/compliance/EInvoiceStatusBadge.tsx`
  - `src/components/compliance/AuthorityConnectionBadge.tsx`
  - `src/components/compliance/ConnectionStatusBanner.tsx`
  - `src/components/compliance/EInvoiceStatsRow.tsx`
  - `src/components/compliance/EInvoiceFilterBar.tsx`
  - `src/components/compliance/SubmissionHistoryModal.tsx`
  - `src/components/compliance/BatchRetryBar.tsx`
- Hook: `src/hooks/useEInvoices.ts`, `src/hooks/useCountryCompliance.ts`
- API: `src/lib/api/compliance.ts`
- Types: `src/types/einvoice.ts`

**Country-aware hook:**

```typescript
// src/hooks/useCountryCompliance.ts
export function useCountryCompliance() {
  const { tenant } = useAuth();
  const map = {
    CO: { authority: 'DIAN', authorityCode: 'dian', invoiceIdCode: 'CUFE', invoiceIdLabel: 'Código Único de Factura Electrónica' },
    MX: { authority: 'SAT',  authorityCode: 'sat',  invoiceIdCode: 'UUID', invoiceIdLabel: 'Folio Fiscal' },
    CL: { authority: 'SII',  authorityCode: 'sii',  invoiceIdCode: 'Folio', invoiceIdLabel: 'Folio Tributario' },
  };
  return map[tenant.country] ?? map['CO']; // CO default
}
```

**Auto-refresh logic:**

```typescript
const { data } = useQuery({
  queryKey: ['e-invoices', tenantId, filters, page],
  queryFn: fetchEInvoices,
  staleTime: 2 * 60 * 1000,
  refetchInterval: () => {
    const hasInProcess = data?.invoices.some(i => i.status === 'in_process');
    return hasInProcess ? 15_000 : false;
  },
  keepPreviousData: true,
});
```

**Optimistic retry update:**

```typescript
const retryMutation = useMutation({
  mutationFn: (id: string) => api.post(`/e-invoices/${id}/retry`),
  onMutate: async (invoiceId) => {
    await queryClient.cancelQueries(['e-invoices']);
    const prev = queryClient.getQueryData(['e-invoices', ...]);
    queryClient.setQueryData(['e-invoices', ...], (old) => ({
      ...old,
      invoices: old.invoices.map(i =>
        i.id === invoiceId ? { ...i, status: 'in_process' } : i
      ),
    }));
    return { prev };
  },
  onError: (err, invoiceId, ctx) => {
    queryClient.setQueryData(['e-invoices', ...], ctx.prev);
    toast.error(`Error al reenviar. ${translateAuthorityError(err)}`);
  },
  onSettled: () => queryClient.invalidateQueries(['e-invoices']),
});
```

---

## Test Cases

### Happy Path

1. View invoice list with mixed statuses
   - **Given:** 30 invoices: 20 accepted, 5 rejected, 3 in_process, 2 pending
   - **When:** clinic_owner navigates to `/compliance/e-invoices`
   - **Then:** Stats row shows 30/20/5/5(pending+in_process). Table shows 20 rows (per_page default). Status badges render correctly. Blue pulse dot on 3 in_process rows.

2. Retry rejected invoice
   - **Given:** Invoice FAC-001 has status `rejected` with DIAN error code 89
   - **When:** User clicks "Reintentar"
   - **Then:** Status badge optimistically changes to "En proceso" with pulse dot; "Reintentar" button replaced by "En proceso..."; 15 seconds later auto-refresh picks up accepted/rejected response from DIAN; badge updates accordingly

3. Open submission history modal
   - **Given:** Invoice FAC-005 was rejected then accepted on retry
   - **When:** User clicks "Ver historial"
   - **Then:** Modal opens with 3-entry timeline: sent → rejected (DIAN code + translated message) → accepted with full CUFE

4. Copy CUFE
   - **Given:** Accepted invoice with 96-char CUFE
   - **When:** User clicks Copy icon in CUFE column
   - **Then:** Full CUFE copied to clipboard; toast "CUFE copiado" appears

5. Filter by "Rechazadas" stat card
   - **Given:** 5 rejected invoices in dataset
   - **When:** User clicks "Rechazadas" KPI card
   - **Then:** Table immediately shows only 5 rejected rows; stat card border highlights; URL updates to `?status=rejected`

6. Download XML + PDF for accepted invoice
   - **Given:** Invoice accepted by DIAN; XML and PDF available
   - **When:** User clicks "XML" then "PDF"
   - **Then:** Two file downloads begin in browser; toast "Descargando..." briefly

7. Batch retry 3 rejected invoices
   - **Given:** 3 rejected invoices selected via checkboxes
   - **When:** User clicks "Reintentar seleccionadas (3)"
   - **Then:** Confirmation dialog shows count; on confirm, progress "Reenviando 1 de 3..." updates; success toast "3 facturas reenviadas"; all 3 rows update to in_process optimistically

8. Auto-refresh updates in_process status
   - **Given:** 2 invoices have status `in_process`; DIAN processes them during viewing
   - **When:** 15 seconds elapse
   - **Then:** List silently re-fetches; status badges update to `accepted` or `rejected` without user action; if accepted, badges turn green; if rejected, retry button reappears

### Edge Cases

1. Mixed status batch selection blocked
   - **Given:** User selects 2 rejected and 1 accepted invoice
   - **When:** "Reintentar seleccionadas" button renders
   - **Then:** Button is disabled; tooltip "Solo se pueden reintentar facturas rechazadas o con error"

2. DIAN disconnected during retry
   - **Given:** Authority badge shows "DIAN — Sin conexión"; user clicks "Reintentar"
   - **When:** POST /retry returns 503
   - **Then:** Optimistic status reverts to `rejected`; toast "Error al reenviar. DIAN no está disponible en este momento."

3. Status filter from URL on direct link
   - **Given:** User follows link `/compliance/e-invoices?status=rejected`
   - **When:** Page loads
   - **Then:** Status filter pre-selected to "Rechazada"; table shows only rejected; "Rechazadas" stat card shows active border

4. Invoice ID longer than truncation limit
   - **Given:** CUFE is 96 characters (standard)
   - **When:** Column renders
   - **Then:** First 20 chars + "..." shown; Copy button copies all 96 characters; modal shows full string in `break-all` font-mono

5. No e-invoicing configured (new clinic)
   - **Given:** Tenant has no electronic invoicing enabled; list returns 0 records
   - **When:** Page loads
   - **Then:** Empty state with illustration + "Activa la facturación electrónica DIAN en Configuración" + link button; stats row shows all zeros

6. Mexico tenant — SAT labels
   - **Given:** `tenant.country = "MX"`
   - **When:** Page renders
   - **Then:** Page title "Facturas Electrónicas — SAT"; authority badge "SAT Conectado"; column header "Folio Fiscal"; copy toast "UUID copiado"; error messages prefixed "SAT Error:"

### Error Cases

1. List API returns 500
   - **Given:** Server error on CO-07 fetch
   - **When:** Page loads
   - **Then:** Stats row and filter bar visible; table area shows error card with "Reintentar" button; authority badge still shows (separate query)

2. Retry POST returns 422 (validation error from DIAN)
   - **Given:** Invoice has an unfixable DIAN validation issue
   - **When:** User clicks "Reintentar"; API returns 422 with error detail
   - **Then:** Optimistic in_process status reverts; toast shows translated DIAN error "El NIT no coincide. Actualiza el NIT en Configuración."

3. Bulk retry partial failure
   - **Given:** 3 invoices batch retried; 2 accepted, 1 still rejected
   - **When:** Bulk retry completes
   - **Then:** Toast "2 facturas reenviadas, 1 requiere atención"; rejected row still shows retry button; table re-fetches to show accurate statuses

---

## Acceptance Criteria

- [ ] Page accessible to clinic_owner only; other roles redirected
- [ ] Page title and authority labels adapt to tenant country (DIAN/SAT/SII)
- [ ] Authority connection badge shows connected/degraded/disconnected states; polls every 60s
- [ ] Disconnected/degraded banner shown when applicable
- [ ] Stats row: 4 KPI cards with correct counts; clicking filters table
- [ ] Filter bar: status multi-select, date range, search (invoice #, patient, invoice ID)
- [ ] All filter state synced to URL
- [ ] Table with 7 columns: invoice #, patient, amount, date, status, invoice ID, actions
- [ ] Status badges for all 6 states with correct colors and labels (es-419)
- [ ] Pulsing blue dot on `in_process` status rows
- [ ] Status badge tooltip with translated authority error message
- [ ] Invoice ID column: truncated display + full copy button + toast on copy
- [ ] "Reintentar" / "Enviar ahora" actions with optimistic status update
- [ ] Retry failure reverts optimistic update + shows translated error toast
- [ ] Download XML button for applicable statuses
- [ ] Download PDF button for applicable statuses
- [ ] "Ver historial" opens SubmissionHistoryModal with full submission timeline
- [ ] History modal: all submissions in chronological order, error messages, full invoice ID
- [ ] Batch retry bar: appears on selection, shows count, respects status eligibility
- [ ] Batch retry confirmation dialog + progress indicator
- [ ] Auto-refresh every 15s when any invoice is `in_process`; stops when none
- [ ] `keepPreviousData` prevents table flicker during pagination/filter changes
- [ ] Pagination (10/20/50 per page)
- [ ] Loading skeletons for stats and table on initial load
- [ ] Error state with retry for list fetch failure
- [ ] Empty state with setup link for unconfigured clinics
- [ ] No-results state with "Limpiar filtros" CTA
- [ ] Responsive: mobile condensed table + bottom sheet, tablet/desktop full columns
- [ ] All ARIA labels, table markup, and live regions correct
- [ ] All text in es-419; raw authority error codes never exposed to users

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — multi-country (DIAN/SAT/SII), status tracking, submission history modal, batch retry |
