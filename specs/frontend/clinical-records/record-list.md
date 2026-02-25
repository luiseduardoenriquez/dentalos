# Lista de Registros Clinicos — Frontend Spec

## Overview

**Screen:** Lista paginada de registros clinicos de un paciente. Tab dentro del detalle del paciente que muestra todos los registros ordenados por fecha con filtros por tipo, rango de fechas y doctor. Soporta expansion rapida (expandable rows) para previsualizar el contenido sin abrir el registro completo.

**Route:** `/patients/{id}/records` (tab dentro de `/patients/{id}`)

**Priority:** High

**Backend Specs:** `specs/clinical-records/CR-03-list-records.md`

**Dependencies:**
- `specs/frontend/patients/patient-detail.md` — tab container padre
- `specs/frontend/clinical-records/record-create.md` — modal de creacion (FE-CR-02)

---

## User Flow

**Entry Points:**
- Tab "Registros Clinicos" dentro del detalle del paciente (`/patients/{id}`)
- Redireccion desde creacion exitosa de registro

**Exit Points:**
- Click en fila abre modal de detalle del registro
- Boton "Nuevo Registro" abre modal FE-CR-02 (record-create)
- Tab de navegacion lleva a otros tabs del paciente (odontograma, plan de tratamiento, etc.)

**User Story:**
> As a doctor | assistant, I want to see all clinical records for a patient in one list so that I can quickly review the clinical history and find specific entries by type, date, or doctor.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  Paciente: Juan Perez            [Tabs nav bar]  |
+--------------------------------------------------+
|  Registros Clinicos                              |
|  +--------------------------------------------+ |
|  | [Tipo v] [Fecha inicio] [Fecha fin] [Dr. v]  | |
|  |                           [+ Nuevo Registro] | |
|  +--------------------------------------------+ |
|  | Tipo | Fecha     | Doctor    | Preview  | 📎 | |
|  |----- |-----------|-----------|----------|----|  |
|  | [>]  | 24 Feb 26 | Dra. Ruiz | Paciente | 2  | |
|  |      |  (expanded preview row)              | |
|  | [>]  | 20 Feb 26 | Dr. Lopez | Control  | 0  | |
|  +--------------------------------------------+ |
|  [Paginacion: < 1 2 3 >]                        |
+--------------------------------------------------+
```

**Sections:**
1. Barra de filtros — dropdowns tipo, rango de fechas, doctor + boton de nuevo registro alineado a la derecha
2. Tabla de registros — columnas: icono tipo, fecha, doctor, preview de texto, contador de adjuntos; filas expandibles
3. Fila expandida — muestra los primeros 200 caracteres del contenido + boton "Ver completo"
4. Paginacion — navegacion de paginas en el footer de la tabla

---

## UI Components

### Component 1: FiltrosRegistros

**Type:** Filter bar (row de inputs/selects)

**Design System Ref:** `frontend/design-system/design-system.md` Section 5.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| tipoValue | string | "todos" | Tipo seleccionado actualmente |
| fechaInicio | Date \| null | null | Inicio del rango de fechas |
| fechaFin | Date \| null | null | Fin del rango de fechas |
| doctorId | string \| null | null | ID del doctor seleccionado |
| onChange | function | — | Callback al cambiar cualquier filtro |

**States:**
- Default — todos los filtros en valor inicial
- Filtrado activo — badge de conteo en el boton "Filtros" en mobile
- Limpiando — boton "Limpiar filtros" visible cuando hay filtros activos

**Behavior:**
- Cambio en cualquier filtro dispara re-fetch inmediato (sin boton "Aplicar")
- En mobile los filtros colapsan en un bottom sheet activado por boton "Filtrar"
- "Limpiar filtros" reinicia todos los valores y re-fetcha

---

### Component 2: TablaRegistros

**Type:** Table con expandable rows

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| registros | RegistroClinico[] | [] | Array de registros a mostrar |
| isLoading | boolean | false | Muestra skeleton rows |
| expandedRowId | string \| null | null | ID de la fila actualmente expandida |
| onRowExpand | function | — | Toggle expansion de fila |
| onRowClick | function | — | Abre modal de detalle |

**States:**
- Default — filas colapsadas
- Expanded — una fila abierta mostrando preview (solo una a la vez)
- Loading — skeleton de 5 filas
- Empty — estado vacio con CTA

**Behavior:**
- Click en icono chevron expande/colapsa la fila (solo una abierta a la vez)
- Click en el resto de la fila abre el modal de detalle completo
- Fila expandida anima con `height` transition 200ms ease-out
- Touch target de toda la fila: min 44px de altura

---

### Component 3: IconoTipoRegistro

**Type:** Badge + icon

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| tipo | "anamnesis" \| "examen" \| "evolucion" \| "procedimiento" | — | Tipo de registro |
| size | "sm" \| "md" | "md" | Tamano del icono |

**States:**
- Default — icono + label de tipo

**Behavior:** Solo visual, sin interaccion. Mapa de colores:
- `anamnesis` → icono `ClipboardList`, badge `bg-purple-100 text-purple-700`
- `examen` → icono `Stethoscope`, badge `bg-blue-100 text-blue-700`
- `evolucion` → icono `FileText`, badge `bg-green-100 text-green-700`
- `procedimiento` → icono `Wrench`, badge `bg-orange-100 text-orange-700`

---

### Component 4: SelectorNuevoRegistro

**Type:** Button con dropdown de tipo

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onSelect | function | — | Callback con el tipo elegido |
| disabled | boolean | false | Deshabilita el boton |

**States:**
- Default — boton "+ Nuevo Registro" con chevron
- Open — dropdown visible con las 4 opciones de tipo
- Disabled — opacidad reducida si el paciente no tiene historia clinica abierta

**Behavior:**
- Click abre dropdown con opciones: Anamnesis, Examen, Nota de evolucion, Procedimiento
- Seleccionar tipo abre modal FE-CR-02 con el tipo pre-seleccionado
- Dropdown cierra al hacer click fuera o al seleccionar opcion

---

## Form Fields

No aplica — esta pantalla es solo listado con filtros, no tiene formulario de entrada de datos propio. Los filtros se manejan como controlled state sin validacion Zod.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Listar registros | `/api/v1/patients/{id}/clinical-records` | GET | `specs/clinical-records/CR-03-list-records.md` | 2min |
| Obtener doctores del tenant | `/api/v1/tenant/doctors` | GET | `specs/users/users.md` | 10min |

### Query Params
```
GET /api/v1/patients/{id}/clinical-records
  ?type=anamnesis|examen|evolucion|procedimiento
  &date_from=2026-01-01
  &date_to=2026-02-28
  &doctor_id=uuid
  &page=1
  &per_page=20
  &sort=date_desc
```

### State Management

**Local State (useState):**
- `expandedRowId: string | null` — ID de la fila expandida actualmente
- `filtros: FiltrosState` — valores actuales de tipo, fechas y doctor

**Global State (Zustand):**
- `patientStore.currentPatient` — datos del paciente activo (nombre, id)

**Server State (TanStack Query):**
- Query key: `['clinical-records', patientId, tenantId, filtros, page]`
- Stale time: 2 minutos
- Refetch on window focus: true
- Mutation: N/A en este componente

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `patient_not_found` | 404 | "Paciente no encontrado" |
| `forbidden` | 403 | "No tienes permisos para ver estos registros" |
| `server_error` | 500 | "Error al cargar registros. Intenta de nuevo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Cambiar filtro tipo | Select dropdown | Re-fetch con nuevo filtro | Skeleton durante carga |
| Cambiar rango de fechas | Date picker | Re-fetch con fechas | Skeleton durante carga |
| Seleccionar doctor | Dropdown | Re-fetch filtrado | Skeleton durante carga |
| Limpiar filtros | Click "Limpiar" | Reset filtros + re-fetch | Filtros vuelven a default |
| Expandir fila | Click chevron | Muestra preview 200 chars | Animacion height 200ms |
| Colapsar fila | Click chevron activo | Oculta preview | Animacion height 200ms |
| Ver completo | Click "Ver completo" en expanded | Abre modal detalle | Modal slide-in |
| Nuevo Registro | Click dropdown opcion | Abre modal FE-CR-02 | Modal slide-up |
| Cambiar pagina | Click paginacion | Fetch pagina nueva | Skeleton durante carga |

### Animations/Transitions

- Expansion de fila: `max-height` transition `200ms ease-out`, parte de `0` hasta la altura del contenido
- Modal de detalle: slide-up desde bottom en tablet/mobile; fade-in centrado en desktop
- Skeleton rows: `animate-pulse` en `bg-gray-200` placeholders
- Dropdown de tipo nuevo: fade + scale desde el boton, `100ms ease-out`

---

## Loading & Error States

### Loading State
- 5 filas skeleton con columnas simulando la estructura: icono circular `w-8 h-4`, texto `w-24 h-4`, texto `w-32 h-4`, texto `w-48 h-4`, badge `w-6 h-4`
- Filtros siguen interactivos durante carga de lista
- Spinner de pagina completa NO — solo skeleton de filas

### Error State
- Banner de error sobre la tabla: `bg-red-50 border border-red-200 rounded-lg p-4`
- Icono `AlertCircle` rojo + mensaje de error + boton "Reintentar" que dispara re-fetch
- Persiste hasta que el usuario reintenta o cambia filtros

### Empty State
- Cuando no hay registros con los filtros actuales:
  - **Ilustracion:** icono `FileX` en `text-gray-300 w-16 h-16`
  - **Mensaje:** "No hay registros clinicos"
  - **Submensaje:** "No se encontraron registros con los filtros seleccionados" (si hay filtros activos) o "Este paciente aun no tiene registros clinicos" (sin filtros)
  - **CTA:** "Crear primer registro" → abre dropdown de tipo de registro (mismo que boton "Nuevo Registro")

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Tabla colapsa a cards apiladas. Filtros en bottom sheet. Solo columnas: tipo, fecha, preview. Adjuntos y doctor en la fila expandida. |
| Tablet (640-1024px) | Tabla completa con todas las columnas. Filtros en fila horizontal. Layout primario. Touch targets 44px min en toda la fila. |
| Desktop (> 1024px) | Tabla completa. Filtros en fila. Columnas con mas espacio. Hover states en filas. |

**Tablet priority:** High — dispositivo primario clinico. Toda la fila es touch target. Chevron de expansion tiene area de toque minima de 44x44px. Dropdown del tipo de nuevo registro con opciones de minimo 44px de altura.

---

## Accessibility

- **Focus order:** Filtro tipo → Fecha inicio → Fecha fin → Doctor → Boton "Nuevo Registro" → Filas de tabla (por orden) → Paginacion
- **Screen reader:** `aria-label="Lista de registros clinicos de {nombre paciente}"` en tabla. `aria-expanded={true|false}` en boton chevron de cada fila. `aria-live="polite"` en region de resultados para anunciar cambios de conteo.
- **Keyboard navigation:** `Tab` navega filtros y tabla. `Enter`/`Space` expande/colapsa fila. `Enter` en fila abre modal. `Arrow` keys en dropdowns de filtros.
- **Color contrast:** WCAG AA en todos los badges de tipo. Texto de preview `text-gray-600` sobre `bg-white` cumple 4.5:1.
- **Language:** Todos los labels, placeholders y mensajes en es-419.

---

## Design Tokens

**Colors:**
- Fila hover: `hover:bg-gray-50 dark:hover:bg-gray-800/50`
- Fila expandida fondo: `bg-blue-50/50 dark:bg-blue-900/10`
- Badge anamnesis: `bg-purple-100 text-purple-700`
- Badge examen: `bg-blue-100 text-blue-700`
- Badge evolucion: `bg-green-100 text-green-700`
- Badge procedimiento: `bg-orange-100 text-orange-700`
- Adjuntos count: `bg-gray-100 text-gray-600 rounded-full`

**Typography:**
- Fecha: `text-sm text-gray-700 font-medium`
- Doctor: `text-sm text-gray-600`
- Preview text: `text-sm text-gray-500 truncate max-w-xs`
- Count adjuntos: `text-xs font-medium`

**Spacing:**
- Fila tabla: `py-3 px-4`
- Fila expandida: `px-4 pb-4 pt-2`
- Gap filtros: `gap-3`
- Container: `px-4 md:px-6`

**Border Radius:**
- Tabla: `rounded-xl overflow-hidden`
- Badges: `rounded-full px-2 py-0.5`
- Filter inputs: `rounded-md`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — data fetching y cache
- `react-hook-form` + `zod` — no en esta pantalla (solo filtros)
- `lucide-react` — ClipboardList, Stethoscope, FileText, Wrench, ChevronRight, Paperclip, AlertCircle, FileX, Plus
- `date-fns` — formateo de fechas en es-419
- `framer-motion` — animacion de expansion de fila

**File Location:**
- Tab page: `src/app/(dashboard)/patients/[id]/records/page.tsx`
- Tabla: `src/components/clinical-records/ClinicalRecordTable.tsx`
- Fila expandible: `src/components/clinical-records/ClinicalRecordRow.tsx`
- Filtros: `src/components/clinical-records/ClinicalRecordFilters.tsx`
- Badge tipo: `src/components/clinical-records/RecordTypeBadge.tsx`
- Hook: `src/hooks/useClinicalRecords.ts`

**Hooks Used:**
- `useAuth()` — usuario y tenant actuales
- `useQuery(['clinical-records', ...])` — TanStack Query para fetch paginado
- `useState` — expandedRowId, filtros locales
- `useDebounce()` — si se agrega busqueda de texto libre en el futuro

**Form Library:**
- No aplica en esta vista. Filtros como controlled state directo con `useState`.

---

## Test Cases

### Happy Path
1. Lista de registros carga correctamente
   - **Given:** Paciente con 5 registros clinicos de distintos tipos
   - **When:** Usuario navega al tab "Registros Clinicos"
   - **Then:** Se muestran 5 filas con tipo, fecha, doctor, preview y adjuntos correctos

2. Filtro por tipo funciona
   - **Given:** Lista con registros de tipo mixto
   - **When:** Usuario selecciona "Procedimiento" en dropdown de tipo
   - **Then:** Solo se muestran registros de tipo procedimiento; contador actualiza

3. Expansion de fila muestra preview
   - **Given:** Lista cargada con al menos un registro
   - **When:** Usuario toca el chevron de una fila
   - **Then:** Fila se expande con animacion mostrando los primeros 200 caracteres y boton "Ver completo"

### Edge Cases
1. Fila con texto muy largo
   - **Given:** Registro con contenido de mas de 500 caracteres
   - **When:** Se expande la fila
   - **Then:** Solo muestra 200 caracteres con "..." y boton "Ver completo"

2. Registro sin adjuntos
   - **Given:** Registro que no tiene archivos adjuntos
   - **When:** Se renderiza la fila
   - **Then:** La columna de adjuntos muestra "—" en lugar de badge con 0

3. Filtros combinados sin resultados
   - **Given:** Filtros por tipo "Anamnesis" + doctor especifico
   - **When:** No hay registros que cumplan ambos criterios
   - **Then:** Estado vacio con mensaje "No se encontraron registros con los filtros seleccionados" y CTA

4. Solo una fila expandida a la vez
   - **Given:** Fila A expandida
   - **When:** Usuario expande fila B
   - **Then:** Fila A se colapsa automaticamente, fila B se expande

### Error Cases
1. Error de red al cargar
   - **Given:** Sin conexion o servidor no disponible
   - **When:** Se monta el componente
   - **Then:** Banner de error con boton "Reintentar"; skeleton no se muestra

2. Permiso denegado
   - **Given:** Usuario sin rol para ver registros del paciente
   - **When:** Se carga la vista
   - **Then:** Error 403 muestra mensaje "No tienes permisos para ver estos registros"

---

## Acceptance Criteria

- [ ] Tabla muestra todas las columnas: tipo (con icono y badge de color), fecha formateada en es-419, nombre del doctor, preview de texto, count de adjuntos
- [ ] Filtros: tipo (todos/anamnesis/examen/evolucion/procedimiento), fecha inicio, fecha fin, doctor — funcionan individualmente y combinados
- [ ] Boton "Nuevo Registro" abre dropdown con 4 tipos y redirige a FE-CR-02 con tipo pre-seleccionado
- [ ] Expansion de fila muestra preview (max 200 chars) con animacion; solo una fila expandida a la vez
- [ ] Estado vacio con mensaje diferenciado (sin registros vs. sin resultados con filtros)
- [ ] Estado de carga con 5 skeleton rows
- [ ] Estado de error con boton "Reintentar"
- [ ] Paginacion funciona correctamente
- [ ] Responsive: cards en mobile, tabla completa en tablet+
- [ ] Touch targets minimo 44px en tablet
- [ ] Accesibilidad: aria-expanded en chevrons, aria-live en region de resultados, navegacion teclado
- [ ] Todos los textos en es-419 (fechas formateadas en locale es)
- [ ] Cache TanStack Query de 2 minutos con refetch on focus

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
