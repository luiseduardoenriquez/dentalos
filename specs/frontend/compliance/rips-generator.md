# Generador RIPS (RIPS Generator) — Frontend Spec

## Overview

**Screen:** RIPS (Registro Individual de Prestacion de Servicios) generation page for Colombia. Allows selecting a period (month/year), generating the RIPS files, tracking generation/validation status in a real-time status timeline, viewing a validation error table with clickable links to source records, and downloading individual files or a ZIP. Includes a history table of past generations.

**Route:** `/compliance/rips`

**Priority:** High (Regulatory — deadline April 2026)

**Backend Specs:** `specs/compliance/rips-generate.md` (CO-01), `specs/compliance/rips-validate.md` (CO-02), `specs/compliance/rips-download.md` (CO-03), `specs/compliance/rips-history.md` (CO-04)

**Dependencies:** `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar "Cumplimiento" → "RIPS" link
- Dashboard compliance alert → "Generar RIPS"
- Admin notification: "RIPS pendiente para {month}"

**Exit Points:**
- Click error record link → patient record or clinical record detail in new tab
- Download individual file or ZIP → browser download
- "Volver al inicio" → `/dashboard`

**User Story:**
> As a clinic_owner | admin, I want to generate and validate RIPS files for monthly submission to health authorities so that my clinic remains compliant with Colombia Resolución 2175 before the April 2026 deadline.

**Roles with access:** `clinic_owner`, `superadmin`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Cumplimiento > RIPS       |
|          | "Generador de RIPS"                    |
|          | [Deadline badge: "Plazo: 30 abril 2026"] |
|          +---------------------------------------+
|          |  [Period selector: month + year]      |
|          |  [Generar RIPS btn]                   |
|          +---------------------------------------+
|          |  (if active job)                      |
|          |  [Status Timeline: 3 steps]           |
|          |  [Validation Error Table]             |
|          |  [Download buttons]                   |
|          +---------------------------------------+
|          |  === HISTORIAL ===                    |
|          |  [Past generations table]             |
+------------------------------------------+-------+
```

---

## UI Components

### Component 1: DeadlineBanner

**Type:** Regulatory deadline indicator — always visible on this page

**Design:**
- `bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-3`
- Icon: `Clock text-amber-600`
- Text: `"Plazo reglamentario: 30 de abril de 2026"` `text-sm font-medium text-amber-800`
- Days remaining: `"Quedan X dias"` computed client-side from today
- If < 30 days: color escalates to `bg-red-50 border-red-200 text-red-800`

### Component 2: PeriodSelector

**Type:** Month + Year selector pair

**Design:**
- Month: `<select>` with options enero–diciembre in Spanish
- Year: `<select>` with years from 2024 to current year
- Default: previous completed month
- Layout: `flex gap-3 items-center`

**Validation:** Cannot select future months. If selected month = current month, show warning `"El mes aun no ha terminado. Los datos pueden estar incompletos."` `bg-amber-50 text-amber-700 text-xs mt-1`

### Component 3: GenerateButton

**Type:** Primary action button

**Label:** `"Generar RIPS"` with `FileCode2` icon
**Style:** `bg-teal-600 hover:bg-teal-700 text-white h-11 px-6 rounded-lg font-medium`
**Disabled when:** Another job is running for this tenant

**On click:**
- POST to start generation job
- Receive `{ job_id: string }`
- Begin polling job status

---

## Status Timeline Component

**Type:** Vertical 3-step timeline with real-time state

**Steps:**

| Step | # | States |
|------|---|--------|
| Generando archivos RIPS | 1 | pending / active / complete / error |
| Validando datos | 2 | pending / active / complete / error |
| Listo para descarga | 3 | pending / active / complete / error |

**Step visual per state:**

| State | Dot | Text color |
|-------|-----|-----------|
| `pending` | `border-2 border-gray-300 bg-white` circle | `text-gray-400` |
| `active` | `bg-teal-500 animate-pulse` circle + `Loader2 animate-spin` icon | `text-teal-700 font-medium` |
| `complete` | `bg-green-500` circle with `Check` icon | `text-green-700` |
| `error` | `bg-red-500` circle with `X` icon | `text-red-700 font-semibold` |

**Connecting lines:** `w-px h-8 bg-gray-200` between steps. Completed segment: `bg-green-400`.

**Status messages per active step:**
- Generating: `"Procesando {N} registros de consultas, procedimientos y urgencias..."`
- Validating: `"Verificando {N} registros contra esquema RIPS..."`
- Ready: `"X archivos generados. {E} errores de validacion."` or `"Generacion completada sin errores."`

**Polling:** Every 2 seconds while job status is `running` / `validating`.

---

## Validation Error Table

**Shown when:** Step 2 completes with `error_count > 0`

**Title:** `"Errores de Validacion"` + count badge `bg-red-100 text-red-700 text-xs rounded-full px-2`

**Columns:**

| Column | Description |
|--------|-------------|
| Archivo RIPS | CT, AF, US, AN, AC, AU — file type |
| Registro # | Row reference in the RIPS file |
| Campo | Field name that failed |
| Error | Human-readable description in Spanish |
| Referencia | Clickable link to source record |

**Error table styling:**
- `bg-white border border-gray-100 rounded-xl overflow-hidden`
- Alternating `bg-white` / `bg-gray-50` rows
- Error column: `text-sm text-red-600`
- "Referencia" column: `text-teal-600 underline cursor-pointer text-sm` — `"Paciente #{ID}"` or `"Consulta #{ID}"`

**Reference link behavior:** Opens source record in new tab — `/patients/{id}` or `/patients/{id}/records/{record_id}`.

**Filter above table:** Text search by field name or error type. `"Exportar errores CSV"` button.

**Severity column (optional):** `"Critico"` (blocks submission) `bg-red-100 text-red-700` vs `"Advertencia"` (can submit) `bg-amber-100 text-amber-700`.

---

## Download Buttons Section

**Shown when:** Step 3 is `complete`

**Layout:**
```
[Descargar ZIP (todos los archivos)]

Archivos individuales:
[CT.json]  [AF.json]  [US.json]  [AN.json]  [AC.json]  [AU.json]
```

**ZIP button:** `bg-teal-600 text-white h-11 px-6 rounded-lg w-full md:w-auto` with `Archive` icon

**Individual file buttons:** `variant="outline" text-sm h-9 px-3` row, one per RIPS file type
Each labeled with file type abbreviation + file size in KB/MB

**Note below buttons:** `"Los archivos RIPS generados cumplen con la especificacion tecnica de la Resolucion 2175 de 2015."` `text-xs text-gray-400`

---

## History Table

**Title:** `"Historial de Generaciones"` `text-base font-semibold text-gray-700`

**Columns:**

| Column | Notes |
|--------|-------|
| Periodo | "Enero 2026" |
| Generado el | "15 feb 2026 09:45 AM" |
| Registros | "{N} registros procesados" |
| Errores | `{N}` — `text-red-600` if > 0, `text-green-600 "0"` if clean |
| Estado | Complete / Error badge |
| Acciones | Download ZIP + Re-generar |

**"Re-generar" action:** Starts new generation for same period, with confirmation: `"¿Regenerar RIPS para Enero 2026? El archivo anterior sera reemplazado."`.

**Pagination:** 10 records per page.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Start RIPS generation | `/api/v1/rips/generate` | POST | `specs/compliance/rips-generate.md` | None |
| Poll job status | `/api/v1/rips/jobs/{job_id}` | GET | `specs/compliance/rips-generate.md` | None |
| Get validation errors | `/api/v1/rips/jobs/{job_id}/errors` | GET | `specs/compliance/rips-validate.md` | 5min |
| Download ZIP | `/api/v1/rips/jobs/{job_id}/download.zip` | GET | `specs/compliance/rips-download.md` | None |
| Download file | `/api/v1/rips/jobs/{job_id}/files/{type}` | GET | `specs/compliance/rips-download.md` | None |
| Get history | `/api/v1/rips/history` | GET | `specs/compliance/rips-history.md` | 2min |

### State Management

**Local State (useState):**
- `selectedMonth: number`
- `selectedYear: number`
- `jobId: string | null`
- `jobStatus: 'idle' | 'generating' | 'validating' | 'complete' | 'error'`
- `activeStep: 1 | 2 | 3`
- `errorCount: number`
- `errorFilter: string`

**Server State (TanStack Query):**
- Status poll: `useQuery(['rips-job', jobId], { refetchInterval: jobStatus === 'complete' || jobStatus === 'error' ? false : 2000, enabled: !!jobId })`
- Errors: `useQuery(['rips-errors', jobId], { enabled: jobStatus === 'complete' })`
- History: `useQuery(['rips-history', page])`
- Generation: `useMutation({ mutationFn: startGeneration, onSuccess: ({ job_id }) => setJobId(job_id) })`

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select month/year | Select change | Period updates | Generate button remains enabled |
| Click "Generar RIPS" | Click | POST job → start polling | Status timeline appears with step 1 active |
| Polling updates | Every 2s | Timeline steps advance | Steps animate through states |
| Generation complete | Poll returns complete | Download buttons appear | Step 3 shows green check |
| Click error reference link | Click | Open record in new tab | New tab opens |
| Click "Descargar ZIP" | Click | Download all files | Browser download |
| Click individual file | Click | Download that file | Browser download |
| Click "Re-generar" in history | Click | Confirmation → new job | Confirmation dialog → timeline restarts |

---

## Loading & Error States

### Loading State
- While generating: status timeline shows active step with spinner + progress messages
- "Generar RIPS" button disabled: `"Generando..."` + spinner, `cursor-not-allowed`
- Error table loading: skeleton rows

### Error State
- Generation failed: step with error state + `"Error durante la generacion: {message}"` below timeline + "Reintentar" button
- Download error: toast `"Error al descargar el archivo. Intenta de nuevo."`
- Validation errors > 0: error table shown — user can still download (if no critical errors)

### Empty State
- No history: `"No hay generaciones previas"` with document icon

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Period selector stacked (month then year). Status timeline simplified (steps condensed). Error table scrolls horizontally. Download buttons stacked. |
| Tablet (640-1024px) | Standard layout. Error table all columns. |
| Desktop (> 1024px) | `max-w-4xl` centered. Side-by-side layout possible for period selector + button. |

---

## Accessibility

- **Screen reader:** Status timeline: `role="list"` + each step `role="listitem" aria-label="Paso {N}: {name}, estado: {state}"`. Active step: `aria-live="polite"` for status updates. Error table: proper `<table>` markup with `<th scope="col">`. Download buttons each `aria-label="Descargar archivo {type}"`.
- **Deadline banner:** `role="alert"` if within 30 days of deadline.
- **Keyboard:** Form Tab. Error table rows keyboard navigable with Enter on reference links.
- **Language:** All RIPS file type labels, error descriptions, and status messages in es-419.

---

## Design Tokens

**Colors:**
- Deadline banner: `bg-amber-50 border-amber-200` → `bg-red-50 border-red-200` when < 30 days
- Timeline active: `bg-teal-500 animate-pulse`
- Timeline complete: `bg-green-500`
- Timeline error: `bg-red-500`
- Error severity critical: `bg-red-100 text-red-700`
- Error severity warning: `bg-amber-100 text-amber-700`
- Download ZIP: `bg-teal-600 text-white`
- Download individual: `border border-gray-300 text-gray-600`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — FileCode2, Clock, Check, X, Archive, Download, Loader2, ExternalLink
- `@tanstack/react-query` — polling with `refetchInterval`

**File Location:**
- Page: `src/app/(dashboard)/compliance/rips/page.tsx`
- Components: `src/components/compliance/RIPSGenerator.tsx`, `src/components/compliance/RIPSStatusTimeline.tsx`, `src/components/compliance/RIPSValidationErrorTable.tsx`, `src/components/compliance/RIPSHistoryTable.tsx`

---

## Acceptance Criteria

- [ ] Month/year period selector with future-month warning
- [ ] Regulatory deadline banner with dynamic days remaining counter
- [ ] "Generar RIPS" triggers backend job and shows status timeline
- [ ] Status timeline: 3 steps with pending/active/complete/error states
- [ ] Real-time polling every 2 seconds while job is running
- [ ] Validation error table with reference links to source records
- [ ] Error severity badges (critico/advertencia)
- [ ] Download ZIP button (all files) + individual file buttons per RIPS type
- [ ] File size shown on individual download buttons
- [ ] History table with previous generations and re-generate action
- [ ] Responsive layout on mobile, tablet, desktop
- [ ] Accessibility: timeline ARIA, error table markup, deadline alert role
- [ ] Spanish (es-419) throughout with proper Colombian regulatory terminology

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
