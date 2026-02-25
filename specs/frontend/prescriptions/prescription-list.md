# Lista de Recetas Medicas — Frontend Spec

## Overview

**Screen:** Lista paginada de recetas medicas de un paciente. Tab dentro del detalle del paciente que muestra todas las recetas en formato de tabla con fecha, resumen de medicamentos (primeros 2 + "y N mas"), doctor prescriptor y boton de descarga de PDF. Diseño simple y funcional orientado a consulta rapida del historial de prescripciones.

**Route:** `/patients/{id}/prescriptions` (tab dentro de `/patients/{id}`)

**Priority:** Medium

**Backend Specs:** `specs/prescriptions/RX-03-list-prescriptions.md`

**Dependencies:**
- `specs/frontend/patients/patient-detail.md` — tab container padre
- `specs/frontend/prescriptions/prescription-create.md` — modal de creacion (FE-RX-01)
- `specs/frontend/prescriptions/prescription-preview.md` — vista de detalle/print (FE-RX-03)

---

## User Flow

**Entry Points:**
- Tab "Recetas" dentro del detalle del paciente (`/patients/{id}`)
- Redireccion desde creacion exitosa en FE-RX-01

**Exit Points:**
- Click en icono de descarga PDF → descarga o abre PDF de la receta (FE-RX-03 en modo print)
- Click en fila de receta → abre modal de detalle (FE-RX-03 en modo preview)
- Boton "+ Nueva receta" → abre modal FE-RX-01

**User Story:**
> As a doctor | assistant, I want to see all prescriptions issued to a patient so that I can quickly review prescription history and download any previous prescription as a PDF.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`, `receptionist` (solo lectura)

---

## Layout Structure

```
+--------------------------------------------------+
|  Paciente: Juan Perez            [Tabs nav bar]  |
+--------------------------------------------------+
|  Recetas Medicas                                 |
|  +--------------------------------------------+ |
|  |                        [+ Nueva Receta]     | |
|  +--------------------------------------------+ |
|  | Fecha       | Medicamentos      | Dr.  | PDF| |
|  |-------------|-------------------|----- |----|  |
|  | 24 Feb 2026 | Amoxicilina 500mg | Dr.L | [↓]| |
|  |             | Ibuprofeno 400mg  |      |    | |
|  |             | y 1 mas           |      |    | |
|  | 10 Ene 2026 | Clindamicina 300mg| Dra.R| [↓]| |
|  | 05 Dic 2025 | Diclofenaco 50mg  | Dr.L | [↓]| |
|  +--------------------------------------------+ |
|  [< 1 2 >]                                      |
+--------------------------------------------------+
```

**Sections:**
1. Barra de acciones — boton "+ Nueva Receta" alineado a la derecha
2. Tabla de recetas — columnas: fecha, medicamentos (resumen), doctor, boton PDF
3. Paginacion — navegacion en el footer

---

## UI Components

### Component 1: TablaRecetas

**Type:** Table simple

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| recetas | Receta[] | [] | Array de recetas a mostrar |
| isLoading | boolean | false | Muestra skeleton rows |
| onRowClick | function | — | Abre modal de detalle de la receta |
| onDownload | function | — | Descarga PDF de la receta especifica |

**States:**
- Default — tabla con filas de recetas
- Loading — skeleton de 5 filas
- Empty — estado vacio con CTA

**Behavior:**
- Click en fila (excepto en el boton de descarga) abre el modal de previsualizacion FE-RX-03
- Fila completa es area clickeable con hover state `hover:bg-gray-50`
- Touch target de la fila: minimo 52px de altura (para que los 2 medicamentos sean confortables en tablet)

---

### Component 2: ResumenMedicamentos

**Type:** Text display inline

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| medicamentos | Medicamento[] | [] | Lista completa de medicamentos de la receta |
| maxVisible | number | 2 | Cuantos medicamentos mostrar antes del resumen |

**Behavior:**
- Muestra los primeros `maxVisible` medicamentos en lineas separadas (nombre + dosis)
- Si hay mas: "+ y {N} mas" en `text-xs text-blue-600` como texto clickeable
  - Click en "y N mas" hace tooltip/popover con la lista completa
- Formato de cada medicamento: `{nombre} {dosis_cantidad}{dosis_unidad}`
  - Ej: "Amoxicilina 500mg", "Ibuprofeno 400mg"
- Si hay solo 1 medicamento: solo se muestra ese, sin truncacion

---

### Component 3: BotonDescargaPDF

**Type:** Icon button

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| recetaId | string | — | ID de la receta para la descarga |
| onDownload | function | — | Handler de descarga |
| isLoading | boolean | false | Spinner durante descarga |

**States:**
- Default — icono `Download` en gris
- Hover — icono azul con tooltip "Descargar PDF"
- Loading — icono `Loader2` animado mientras genera/descarga

**Behavior:**
- Click dispara `GET /api/v1/prescriptions/{id}/pdf` que retorna el archivo PDF
- El PDF se descarga con nombre `receta_{fecha}_{paciente}.pdf`
- Boton tiene `stopPropagation` para no activar el click de la fila
- Area de toque: `p-2` con hit area minima de 44px via `min-w-[44px] min-h-[44px]`

---

### Component 4: BotonNuevaReceta

**Type:** Primary button

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onClick | function | — | Abre modal FE-RX-01 |
| disabled | boolean | false | Disabled para roles sin permiso de crear |

**States:**
- Default — boton azul "+ Nueva Receta" con icono `Plus`
- Disabled — para roles `assistant` y `receptionist` que solo pueden ver

**Behavior:**
- Si el usuario es `receptionist` o `assistant`, el boton no se muestra (la vista es de solo lectura para estos roles)
- Si el usuario es `doctor` o `clinic_owner`, el boton esta visible y activo

---

## Form Fields

No aplica — esta pantalla es solo listado sin formulario de entrada de datos. Los filtros no son necesarios en esta vista (la lista de recetas tipicamente es corta y la paginacion es suficiente).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Listar recetas del paciente | `/api/v1/patients/{id}/prescriptions` | GET | `specs/prescriptions/RX-03-list-prescriptions.md` | 3min |
| Descargar PDF de receta | `/api/v1/prescriptions/{id}/pdf` | GET | `specs/prescriptions/RX-04-generate-pdf.md` | 1hora |

### Query Params
```
GET /api/v1/patients/{id}/prescriptions
  ?page=1
  &per_page=15
  &sort=created_at_desc
```

### State Management

**Local State (useState):**
- `downloadingId: string | null` — ID de la receta cuyo PDF se esta descargando

**Global State (Zustand):**
- `patientStore.currentPatient` — paciente activo

**Server State (TanStack Query):**
- Query key: `['prescriptions', patientId, tenantId, page]`
- Stale time: 3 minutos
- Refetch on window focus: true

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `patient_not_found` | 404 | "Paciente no encontrado" |
| `forbidden` | 403 | "No tienes permisos para ver las recetas" |
| `pdf_generation_failed` | 500 | "Error al generar el PDF. Intenta de nuevo." |
| `server_error` | 500 | "Error al cargar las recetas. Intenta de nuevo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click en fila | Click en celda (no en boton PDF) | Abre modal de detalle FE-RX-03 | Modal slide-up |
| Descargar PDF | Click en boton descarga `[↓]` | GET PDF → descarga del archivo | Spinner en boton durante descarga |
| Click "+ y N mas" | Click en texto de medicamentos extras | Tooltip/popover con lista completa | Popover aparece |
| Nueva Receta | Click boton "+ Nueva Receta" | Abre modal FE-RX-01 | Modal slide-up |
| Cambiar pagina | Click paginacion | Fetch pagina nueva | Skeleton durante carga |

### Animations/Transitions

- Modal detalle: slide-up desde bottom en tablet/mobile
- Hover en fila: `bg-gray-50` transition 75ms
- Spinner en boton descarga: `animate-spin` en `Loader2`
- Popover de medicamentos extras: fade-in 100ms

---

## Loading & Error States

### Loading State
- Skeleton de 5 filas de tabla:
  - Columna fecha: `w-24 h-4 bg-gray-200 rounded animate-pulse`
  - Columna medicamentos: 2 lineas de placeholder `w-40 h-4` + `w-32 h-3`
  - Columna doctor: `w-20 h-4`
  - Columna PDF: icono placeholder `w-8 h-8 bg-gray-200 rounded`

### Error State
- Banner de error sobre la tabla con boton "Reintentar"
- Error de descarga de PDF: toast de error con el icono de la fila volviendo al estado normal

### Empty State
- Sin recetas emitidas para el paciente:
  - **Ilustracion:** icono `FileText` en `text-gray-300 w-14 h-14`
  - **Mensaje:** "Este paciente no tiene recetas medicas"
  - **Submensaje:** "Las recetas que prescribas apareceran aqui"
  - **CTA:** "Nueva receta" (solo si el rol lo permite) → abre FE-RX-01
- Sin CTA para roles de solo lectura

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Tabla colapsa a cards apiladas. Cada card muestra: fecha en header, lista completa de medicamentos, doctor, boton PDF full-width. Sin truncacion en mobile (espacio suficiente para mostrar todo). |
| Tablet (640-1024px) | Tabla completa con todas las columnas. Columna medicamentos muestra max 2 + "y N mas". Filas de 52px de altura. Touch target del boton PDF: 44px. Layout primario. |
| Desktop (> 1024px) | Tabla completa. Columna medicamentos puede mostrar max 2 (mismo comportamiento). Mayor padding. |

**Tablet priority:** Medium-High — la lista de recetas se consulta en tablet para referencia durante la consulta. Filas de 52px de altura para tocar con facilidad. Boton de descarga PDF con area de toque de 44x44px como minimo.

---

## Accessibility

- **Focus order:** Boton "+ Nueva Receta" → Filas de tabla (por orden, Tab navega entre filas) → Boton PDF por fila → Paginacion
- **Screen reader:** `aria-label="Lista de recetas medicas de {nombre paciente}"` en la tabla. Cada fila con `aria-label="Receta del {fecha}, medicamentos: {lista}, prescrita por {doctor}"`. Boton PDF: `aria-label="Descargar PDF de receta del {fecha}"` con `aria-busy="true"` durante descarga.
- **Keyboard navigation:** Tab navega entre filas y botones. Enter en fila abre el detalle. Enter en boton PDF descarga. Escape cierra modal de detalle.
- **Color contrast:** WCAG AA. Texto "y N mas" en `text-blue-600` sobre `bg-white` cumple 4.5:1.
- **Language:** es-419. Fechas formateadas con locale es (ej: "24 de febrero de 2026"). Nombres de medicamentos como los provee el sistema.

---

## Design Tokens

**Colors:**
- Fila hover: `hover:bg-gray-50 dark:hover:bg-gray-800/30`
- Fila click: `active:bg-gray-100`
- Boton PDF default: `text-gray-400`
- Boton PDF hover: `text-blue-600`
- "y N mas": `text-xs text-blue-600 hover:text-blue-700 hover:underline`
- Nombre medicamento: `text-sm text-gray-900`
- Dosis: `text-xs text-gray-500`
- Nombre doctor: `text-sm text-gray-600`
- Fecha: `text-sm text-gray-700 font-medium`

**Typography:**
- Header tabla: `text-xs font-medium text-gray-500 uppercase tracking-wider`
- Fecha en fila: `text-sm font-medium text-gray-700 whitespace-nowrap`
- Nombre medicamento en fila: `text-sm text-gray-900`
- Doctor en fila: `text-sm text-gray-600 whitespace-nowrap`

**Spacing:**
- Fila tabla: `py-3.5 px-4`
- Gap entre medicamentos en celda: `space-y-0.5`
- Boton PDF padding: `p-2`
- Paginacion: `mt-4`

**Border Radius:**
- Tabla container: `rounded-xl overflow-hidden border border-gray-200`
- Skeleton: `rounded`
- Popover "y N mas": `rounded-lg shadow-lg border border-gray-200`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — fetch paginado y query de PDF
- `lucide-react` — Plus, Download, Loader2, FileText, AlertCircle
- `date-fns` + `date-fns/locale/es` — formateo de fechas

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/prescriptions/page.tsx`
- Tabla: `src/components/prescriptions/PrescriptionTable.tsx`
- Fila: `src/components/prescriptions/PrescriptionRow.tsx`
- Resumen medicamentos: `src/components/prescriptions/MedicamentosSummary.tsx`
- Boton PDF: `src/components/prescriptions/DownloadPDFButton.tsx`
- Hook: `src/hooks/usePrescriptions.ts`
- API: `src/lib/api/prescriptions.ts`

**Hooks Used:**
- `useQuery(['prescriptions', patientId, page])` — lista paginada
- `useAuth()` — para verificar rol y mostrar/ocultar boton "Nueva Receta"
- `usePatientStore()` — paciente activo
- `useState` — `downloadingId` para estado de descarga individual
- `useRouter()` (si la descarga usa redireccion en lugar de fetch directo)

**Descarga de PDF:**
```typescript
const handleDownload = async (recetaId: string) => {
  setDownloadingId(recetaId);
  try {
    const response = await fetch(`/api/v1/prescriptions/${recetaId}/pdf`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `receta_${recetaId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    toast.error('Error al generar el PDF. Intenta de nuevo.');
  } finally {
    setDownloadingId(null);
  }
};
```

**Form Library:** No aplica en esta vista.

---

## Test Cases

### Happy Path
1. Lista de recetas carga correctamente
   - **Given:** Paciente con 3 recetas de distintas fechas y doctores
   - **When:** Usuario navega al tab "Recetas"
   - **Then:** 3 filas con fecha correcta, medicamentos resumidos (max 2 + "y N mas"), doctor y boton de descarga

2. Descargar PDF de una receta
   - **Given:** Fila de receta visible en la tabla
   - **When:** Usuario hace click en el boton de descarga `[↓]`
   - **Then:** Boton muestra spinner durante la generacion, luego el PDF se descarga con nombre apropiado

3. Ver detalle al hacer click en la fila
   - **Given:** Lista de recetas cargada
   - **When:** Click en cualquier parte de la fila (excepto el boton PDF)
   - **Then:** Modal de previsualizacion FE-RX-03 se abre con la receta formateada

4. "y N mas" muestra lista completa
   - **Given:** Receta con 4 medicamentos, solo se muestran 2 en la tabla
   - **When:** Usuario hace click en "y 2 mas"
   - **Then:** Popover aparece con la lista completa de los 4 medicamentos

### Edge Cases
1. Receta con 1 solo medicamento
   - **Given:** Receta con un unico medicamento
   - **When:** Se renderiza la fila
   - **Then:** Solo se muestra ese medicamento sin "y N mas"

2. Nombre de medicamento muy largo
   - **Given:** Medicamento con nombre de 60 caracteres
   - **When:** Se muestra en la celda de la tabla
   - **Then:** Nombre truncado con ellipsis en tablet; nombre completo en mobile (cards)

3. Descarga simultanea de dos recetas
   - **Given:** Usuario hace click rapido en PDF de receta A y luego receta B
   - **When:** Ambas descargas se inician
   - **Then:** Ambos botones muestran spinner independientemente; las descargas no se interfieren entre si

4. Rol receptionist no ve boton "Nueva Receta"
   - **Given:** Usuario con rol `receptionist` en el tab de recetas
   - **When:** Se renderiza la pantalla
   - **Then:** Boton "+ Nueva Receta" no aparece; la tabla es de solo lectura

### Error Cases
1. Error de red al cargar lista
   - **Given:** Sin conexion
   - **When:** El query falla
   - **Then:** Banner de error: "Error al cargar las recetas. Intenta de nuevo." con boton "Reintentar"

2. Error al descargar PDF
   - **Given:** Servidor retorna 500 al intentar generar el PDF
   - **When:** Usuario hace click en descarga
   - **Then:** Spinner desaparece, icono vuelve a normal, toast: "Error al generar el PDF. Intenta de nuevo."

---

## Acceptance Criteria

- [ ] Tabla con columnas: fecha (formateo es-419), resumen de medicamentos (max 2 + "y N mas"), nombre del doctor, boton de descarga PDF
- [ ] Boton "+ Nueva Receta" visible solo para roles `doctor` y `clinic_owner`
- [ ] Click en fila (excepto PDF) abre modal FE-RX-03
- [ ] "y N mas" clickeable muestra popover con lista completa de medicamentos
- [ ] Boton PDF con `stopPropagation` (no activa el click de la fila)
- [ ] Descarga de PDF con nombre de archivo apropiado
- [ ] Spinner individual en boton PDF durante descarga (no bloquea otros botones)
- [ ] Paginacion funcional (15 recetas por pagina)
- [ ] Estado de carga: 5 skeleton rows
- [ ] Estado de error: banner con "Reintentar"
- [ ] Estado vacio: ilustracion + mensaje + CTA solo para roles con permiso
- [ ] Responsive: cards en mobile, tabla en tablet+
- [ ] Filas de 52px de altura en tablet (doble linea de medicamentos)
- [ ] Touch target del boton PDF: minimo 44x44px
- [ ] Accesibilidad: aria-label descriptivo por fila, aria-busy en boton durante descarga
- [ ] Fechas en formato es-419 (locale es de date-fns)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
