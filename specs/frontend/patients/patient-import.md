# Importar Pacientes (Patient Import) — Frontend Spec

## Overview

**Screen:** Multi-step patient import flow. Four sequential steps: (1) upload CSV/Excel file via drag-and-drop, (2) column mapping with auto-detect and manual override, (3) validation preview table showing valid/error/duplicate rows, (4) import progress with real-time feedback and downloadable error report.

**Route:** `/patients/import`

**Priority:** Medium

**Backend Specs:** `specs/patients/patient-import.md` (P-08)

**Dependencies:** `specs/frontend/patients/patient-list.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- "Importar pacientes" button in `/patients` list (overflow menu or top actions)
- Step 4 of onboarding wizard (patient import step)

**Exit Points:**
- Success (all imported) → `/patients` with toast "X pacientes importados exitosamente"
- Partial success → stay on step 4, download error report, option to retry errors or proceed
- "Cancelar" button on any step → confirm dialog → `/patients`

**User Story:**
> As a clinic_owner | receptionist, I want to bulk import patient records from a spreadsheet so that I can migrate data from a previous system without manual entry.

**Roles with access:** `clinic_owner`, `receptionist`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Pacientes > Importar      |
|          +---------------------------------------+
|          |  "Importar Pacientes"                 |
|          |  [Step progress: 1 2 3 4]             |
|          +---------------------------------------+
|          |                                       |
|          |  [Step Content Area]                  |
|          |                                       |
|          +---------------------------------------+
|          |  [Cancelar]  [Atras]  [Siguiente/     |
|          |                        Iniciar Importacion] |
+------------------------------------------+-------+
```

**Sections:**
1. Page header — breadcrumb, title
2. Step progress indicator — 4-step horizontal tracker
3. Step content area — varies per step
4. Navigation row — cancel, back, next/finish

---

## UI Components

### Component 1: StepProgressIndicator

**Type:** Horizontal step tracker (same pattern as onboarding wizard)

**Labels:**

| Step | Label |
|------|-------|
| 1 | Subir Archivo |
| 2 | Mapear Columnas |
| 3 | Vista Previa |
| 4 | Importacion |

---

## Step Specifications

### Step 1: Subir Archivo

**Drop zone:**
- Large: `min-h-[240px] border-2 border-dashed border-gray-300 rounded-2xl flex flex-col items-center justify-center`
- Icon: `UploadCloud` size 48px `text-gray-300`
- Primary text: `"Arrastra tu archivo aqui"` `text-base font-medium text-gray-600`
- Secondary: `"o haz clic para seleccionar"` link-style `text-teal-600 underline cursor-pointer`
- Accepted formats badge: `".CSV, .XLSX, .XLS — Maximo 10MB"` `text-xs text-gray-400`
- Hover state: `border-teal-400 bg-teal-50/40`
- Drag-over state: `border-teal-500 bg-teal-50 scale-[1.01]`

**After file selection:**
- Drop zone shrinks to `h-24`
- File info row: `FileSpreadsheetIcon` + filename + file size + row count preview + `X` remove button
- Row count: "X filas detectadas (incluyendo encabezado)" — from client-side CSV parse
- "Descargar plantilla" link: provides a pre-formatted CSV template with correct column headers
- Format instructions callout: collapsible `details/summary` with column requirements

**Template download:**
- CSV with headers: Nombres, Apellidos, Tipo_Documento, Numero_Documento, Fecha_Nacimiento, Genero, Telefono, Correo, Direccion, Alergias, Condiciones
- Download as `plantilla-importacion-dentalos.csv`

**Validation on "Siguiente":**
- File required
- Max 10MB: inline error below drop zone "El archivo no puede superar 10MB"
- Supported format: inline error "Formato no compatible. Usa CSV, XLSX o XLS"
- Max rows: 5000 — if exceeded, error "El archivo contiene mas de 5.000 filas. Divide el archivo."

---

### Step 2: Mapear Columnas

**Layout:**
- Title: "Relaciona las columnas de tu archivo con los campos de DentalOS"
- Two-column table: left = "Tu columna" (detected header), right = "Campo DentalOS" (dropdown)
- Auto-detect: backend or client-side heuristic maps common header names automatically

**Column mapping table:**

| Column in file | Maps to DentalOS field | Required |
|---------------|------------------------|----------|
| Detected column name | `<select>` dropdown | Required fields marked with `*` |

**Dropdown options (DentalOS fields):**
- Primer Nombre *
- Segundo Nombre
- Primer Apellido *
- Segundo Apellido
- Tipo de Documento *
- Numero de Documento *
- Fecha de Nacimiento
- Genero
- Telefono Principal
- Telefono Alternativo
- Correo Electronico
- Direccion
- Ciudad
- Alergias (separadas por coma)
- Condiciones Medicas
- Seguro / Aseguradora
- Numero de Poliza
- No importar esta columna (ignore option)

**Auto-detect confidence:**
- High confidence (> 90%): dropdown pre-selected, `bg-green-50` row background, `CheckCircle` icon
- Medium confidence (60-90%): dropdown pre-selected with amber `AlertCircle` icon, tooltip "Verifica esta asociacion"
- Low / no match: dropdown shows "Seleccionar campo..." with red `AlertTriangle` icon

**Validation on "Siguiente":**
- All required fields (`*`) must be assigned exactly once
- Duplicate assignments: inline warning "Este campo ya esta asignado a otra columna"
- Unassigned required: error banner "Asigna los campos obligatorios: {list}"

---

### Step 3: Vista Previa de Validacion

**Title:** "Vista previa — {N} filas" + "X validas, Y con errores, Z duplicadas"

**Summary row (color-coded chips):**
- Green: `{X} listas para importar` `bg-green-100 text-green-800`
- Red: `{Y} con errores` `bg-red-100 text-red-800`
- Yellow: `{Z} duplicadas` `bg-amber-100 text-amber-700`

**Preview table:**

| # | Nombre | Documento | Telefono | Estado | Detalle |
|---|--------|-----------|----------|--------|---------|
| 1 | Juan Garcia | CC 12345678 | +57 300... | (green dot) Valida | — |
| 2 | Ana (missing) | CC 87654321 | — | (red dot) Error | "Apellido requerido" |
| 3 | Carlos Lopez | CC 11223344 | +57 310... | (yellow dot) Duplicado | "Paciente existente [Ver →]" |

**Row color coding:**
- Valid row: `bg-white` default, green status dot `w-3 h-3 rounded-full bg-green-500`
- Error row: `bg-red-50` background, red status dot `bg-red-500`
- Duplicate row: `bg-amber-50` background, yellow status dot `bg-amber-400`

**Table features:**
- Virtualized (react-virtual) for large imports (> 100 rows)
- Fixed columns: #, Status, Detalle — scrollable middle columns
- Paginated: 50 rows per page
- Filter tabs: "Todas" | "Validas" | "Errores" | "Duplicadas"
- Duplicate row: link "Ver paciente existente →" opens patient in new tab

**Error details:** hover/click the status cell to see tooltip with full error message(s) per row

**Duplicate handling option:** radio group above table:
- "Omitir duplicados (recomendado)" — skip rows where document number already exists
- "Actualizar pacientes existentes" — PATCH existing patient with imported data

---

### Step 4: Importacion en Progreso

**Layout:**
- Large circular progress indicator (SVG): `{n}%` in center
- Below: `"{X} de {N} pacientes importados"` progress text
- Progress bar (linear, secondary): fills left to right
- Status log: scrollable list of last 5 events `text-xs text-gray-500` — e.g., "Juan Garcia — importado", "Error: Ana (apellido requerido)"

**States:**
- `running` — progress indicator animates, cancel button disabled
- `complete_success` — progress 100%, large green checkmark, "X pacientes importados exitosamente" message
- `complete_partial` — progress 100%, mixed icon, "X importados, Y con errores" + download error report button
- `complete_error` — red X icon, "Importacion fallida. Descarga el reporte de errores."

**Error report download:**
- Button: `"Descargar reporte de errores"` `variant="outline"` with `DownloadIcon`
- File: CSV with same columns as original + "Error" column describing the issue per rejected row
- Filename: `errores-importacion-{YYYY-MM-DD}.csv`

**Post-completion actions:**
- Success: `"Ver pacientes importados"` → `/patients` (filtered)
- Partial: `"Ver pacientes importados"` + `"Reintentar errores"` (loads error rows back to Step 1)

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Parse + validate file | `/api/v1/patients/import/validate` | POST (multipart) | `specs/patients/patient-import.md` | None |
| Execute import | `/api/v1/patients/import` | POST | `specs/patients/patient-import.md` | None |
| Poll import status | `/api/v1/patients/import/{job_id}/status` | GET | `specs/patients/patient-import.md` | None |
| Download error report | `/api/v1/patients/import/{job_id}/errors.csv` | GET | `specs/patients/patient-import.md` | None |

### Step 2 API Call

After column mapping is confirmed, send to validate endpoint:
```typescript
// multipart/form-data
{
  file: File;
  column_mapping: Record<string, string>; // { "Col A": "primer_nombre", "Col B": "numero_documento" }
  duplicate_strategy: "skip" | "update";
}
```

### Step 4 Polling

- After import job starts, receive `{ job_id: string }`
- Poll `GET /api/v1/patients/import/{job_id}/status` every 2 seconds
- Response: `{ status: "running" | "complete", processed: number, total: number, errors: number }`
- Stop polling when `status === "complete"`

### State Management

**Local State (useState):**
- `currentStep: 1 | 2 | 3 | 4`
- `file: File | null`
- `detectedColumns: string[]`
- `columnMapping: Record<string, string>`
- `validationResult: { valid, errors, duplicates, rows }[]`
- `importJobId: string | null`
- `importProgress: { processed, total, errors }`
- `duplicateStrategy: 'skip' | 'update'`

**Server State (TanStack Query):**
- Step 2 mutation: `useMutation` for validate endpoint
- Step 4 mutation: `useMutation` to start import
- Step 4 polling: `useQuery(['import-status', jobId], { refetchInterval: 2000, enabled: !!jobId && isRunning })`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Drop file | Drag-and-drop onto zone | File parsed client-side for row count | Zone shows file info |
| Remove file | Click X | File cleared, zone returns to initial state | Immediate |
| Click "Siguiente" Step 1 | Button | Validate file format/size | Spinner → Step 2 |
| Change column mapping | Select dropdown | Updates mapping state | Auto-detect confidence icon may clear |
| Click "Siguiente" Step 2 | Button | Send to validate endpoint | Spinner → Step 3 with results |
| Change duplicate strategy | Radio | Updates strategy | Immediate state update |
| Click "Iniciar Importacion" | Button | POST import job | Step 4 progress |
| Click "Descargar reporte" | Button | Download CSV | Browser file download |
| Click "Ver pacientes" | Button (post-success) | Navigate to `/patients` | Full navigation |

---

## Loading & Error States

### Loading State
- Step 1→2 transition: spinner on "Siguiente" button while file uploads and parses
- Step 2→3 transition: spinner + "Validando {N} filas..." inline below button
- Step 4: live progress indicator

### Error State
- File format error: inline below drop zone
- Missing required column mapping: banner above navigation row
- API failure during validation: toast "Error al procesar el archivo. Intenta de nuevo."
- Import job failure: step 4 error state with download report button

### Empty State
- Step 3 with 0 valid rows (all errors): "Ninguna fila esta lista para importar. Revisa tu archivo."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Column mapping table scrolls horizontally. Preview table shows only Name + Status columns; expand row for details. Progress screen is centered. |
| Tablet (640-1024px) | Full table layout. Drop zone full-width. |
| Desktop (> 1024px) | `max-w-4xl` container. Column mapping in two-column grid. |

**Tablet priority:** Medium — import typically done by clinic admin on desktop, but tablet support required.

---

## Accessibility

- **Focus order:** Drop zone → "Siguiente" button. Step 2: Column mapping selects top-to-bottom → "Siguiente". Step 3: Filter tabs → Table rows → "Iniciar Importacion". Step 4: Progress (read-only) → action buttons.
- **Screen reader:** `role="status"` on progress percentage with `aria-live="polite"` for updates. `role="table"` on preview table with proper `th` headers. File drop zone: `role="button"` with `aria-label="Zona de carga. Haz clic o arrastra un archivo CSV o Excel"`. Status column: `aria-label` per row describing validity.
- **Keyboard navigation:** Drop zone activates with Enter/Space. Column dropdowns keyboard-navigable. Table filter tabs use arrow keys.
- **Color contrast:** Status dot supplemented by text label (not color alone). Error rows use both red background AND "Error" text in status column.
- **Language:** All labels, instructions, error messages in es-419.

---

## Design Tokens

**Colors:**
- Drop zone border: `border-gray-300` → hover `border-teal-400`
- Drop zone bg hover: `bg-teal-50/40`
- Valid row: default white
- Error row: `bg-red-50`
- Duplicate row: `bg-amber-50`
- Status dots: `bg-green-500`, `bg-red-500`, `bg-amber-400`
- Progress bar: `bg-teal-600`
- Summary chips: green/red/amber per status

**Typography:**
- Page title: `text-2xl font-bold text-gray-900`
- Drop zone primary: `text-base font-medium text-gray-600`
- Table headers: `text-xs font-semibold uppercase text-gray-500`
- Table rows: `text-sm text-gray-800`
- Error detail: `text-xs text-red-600`

**Spacing:**
- Page: `max-w-4xl mx-auto px-4 py-6`
- Drop zone: `min-h-[240px] p-8`
- Table: `w-full mt-6`
- Navigation row: `mt-8 pt-4 border-t border-gray-100 flex justify-between`

---

## Implementation Notes

**Dependencies (npm):**
- `react-dropzone` — file upload
- `react-virtual` / `@tanstack/react-virtual` — virtualized preview table
- `papaparse` — client-side CSV parsing for row count and column detection
- `xlsx` — client-side Excel parsing
- `lucide-react` — UploadCloud, FileSpreadsheet, CheckCircle, AlertCircle, AlertTriangle, Download, Loader2

**File Location:**
- Page: `src/app/(dashboard)/patients/import/page.tsx`
- Components: `src/components/patients/import/FileUploadStep.tsx`, `src/components/patients/import/ColumnMappingStep.tsx`, `src/components/patients/import/ValidationPreviewStep.tsx`, `src/components/patients/import/ImportProgressStep.tsx`

**Hooks Used:**
- `useMutation()` — validate and start import
- `useQuery(['import-status', jobId], { refetchInterval: 2000 })` — polling
- `useDropzone()` from react-dropzone

---

## Test Cases

### Happy Path
1. Clean CSV import
   - **Given:** 50-row CSV with correct columns
   - **When:** Upload → auto-map columns → all 50 valid → start import
   - **Then:** 50 patients imported, navigate to patient list with success toast

### Edge Cases
1. File with partial errors
   - **Given:** 100-row file, 10 rows have missing apellido
   - **When:** Step 3 preview shows 10 red rows
   - **Then:** User can still import 90 valid rows, download error report for 10

2. Large file (4000 rows)
   - **Given:** 4000-row Excel file
   - **When:** Upload and validate
   - **Then:** Step 3 preview virtualized, import progress shows real-time updates

### Error Cases
1. Wrong file format
   - **Given:** User drops a .DOCX file
   - **When:** File added to drop zone
   - **Then:** Inline error "Formato no compatible. Usa CSV, XLSX o XLS"

2. All duplicate rows
   - **Given:** File with 20 patients who all exist
   - **When:** Step 3 shows 0 valid, 20 duplicates, strategy = skip
   - **Then:** "Ninguna fila nueva para importar" message, no import button

---

## Acceptance Criteria

- [ ] 4-step progress indicator with correct labels
- [ ] Step 1: drag-and-drop and click-to-select for CSV/XLSX/XLS up to 10MB
- [ ] Step 1: client-side row count preview and format validation
- [ ] Step 1: downloadable CSV template
- [ ] Step 2: auto-detect column mapping with confidence indicators
- [ ] Step 2: manual override dropdowns for all columns
- [ ] Step 2: validation of required field assignments
- [ ] Step 3: color-coded preview table (green/red/yellow rows)
- [ ] Step 3: filter tabs (Todas/Validas/Errores/Duplicadas)
- [ ] Step 3: duplicate strategy selection (skip/update)
- [ ] Step 4: real-time progress with polling
- [ ] Step 4: downloadable error report CSV
- [ ] Post-import: navigate to patients or retry errors
- [ ] Responsive on tablet and desktop
- [ ] Accessibility: drop zone keyboard, table ARIA, live progress announcements
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
