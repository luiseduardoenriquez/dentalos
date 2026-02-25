# Lista de Planes de Tratamiento — Frontend Spec

## Overview

**Screen:** Lista de planes de tratamiento de un paciente en layout de tarjetas (cards), con informacion resumida de cada plan: titulo, estado con badge de color, barra de progreso, conteo de items y costo total. Tab dentro del detalle del paciente. Soporta ordenamiento y creacion rapida con opcion de auto-generacion desde el odontograma.

**Route:** `/patients/{id}/treatment-plans` (tab dentro de `/patients/{id}`)

**Priority:** High

**Backend Specs:** `specs/treatment-plans/TP-03-list-plans.md`

**Dependencies:**
- `specs/frontend/patients/patient-detail.md` — tab container padre
- `specs/frontend/treatment-plans/plan-create.md` — modal de creacion (FE-TP-02)
- `specs/frontend/treatment-plans/plan-detail.md` — ruta de detalle al hacer click en card (FE-TP-03)

---

## User Flow

**Entry Points:**
- Tab "Planes de Tratamiento" en el detalle del paciente
- Redireccion desde creacion exitosa de un plan

**Exit Points:**
- Click en card de plan → `/patients/{id}/treatment-plans/{plan_id}` (FE-TP-03)
- Boton "Nuevo Plan" → abre modal FE-TP-02
- Opcion "Auto-generar desde odontograma" → inicia flujo de auto-generacion en FE-TP-02

**User Story:**
> As a doctor | clinic_owner, I want to see all treatment plans for a patient at a glance so that I can quickly understand their treatment progress, costs, and history.

**Roles with access:** `clinic_owner`, `doctor`, `assistant` (solo lectura), `receptionist` (solo lectura)

---

## Layout Structure

```
+--------------------------------------------------+
|  Paciente: Juan Perez            [Tabs nav bar]  |
+--------------------------------------------------+
|  Planes de Tratamiento                           |
|  +--------------------------------------------+ |
|  | [Ordenar por: Fecha v]  [Nuevo Plan v]      | |
|  +--------------------------------------------+ |
|                                                  |
|  +------------------+ +------------------+      |
|  | Plan de ortodoncia| | Tratamiento peri.|      |
|  | [Activo] ●       | | [Borrador] ○    |      |
|  |                  | |                  |      |
|  | Progreso: ██░░ 2/5| | Progreso: ░░░░ 0/3|  |
|  |                  | |                  |      |
|  | 5 procedimientos | | 3 procedimientos  |      |
|  | Total: $1.250.000 | | Total: $450.000   |      |
|  |                  | |                  |      |
|  | Dr. Lopez        | | Dra. Ruiz        |      |
|  | 15 Ene 2026     | | 22 Feb 2026      |      |
|  +------------------+ +------------------+      |
|                                                  |
|  +------------------+ +------------------+      |
|  | Blanqueamiento   | |                  |      |
|  | [Completado] ✓   | |                  |      |
|  | ...              | |                  |      |
|  +------------------+ +------------------+      |
+--------------------------------------------------+
```

**Sections:**
1. Barra de acciones — selector de orden y boton "Nuevo Plan" con dropdown (crear / auto-generar)
2. Grid de cards — 2 columnas en tablet, 1 en mobile, 3 en desktop
3. Estado vacio — si no hay planes, ilustracion + CTA

---

## UI Components

### Component 1: PlanCard

**Type:** Card interactivo

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| plan | TratamientoPlan | — | Datos del plan |
| onClick | function | — | Navega al detalle del plan |

**States:**
- Default — card con sombra sutil
- Hover — sombra elevada `shadow-md`, cursor pointer
- Active (click) — escala ligera `scale-[0.99]` durante 100ms

**Behavior:**
- Toda el area del card es clickeable (navega al detalle)
- NO hay acciones secundarias dentro del card (sin menú contextual en esta vista)
- La barra de progreso es solo visual (no interactiva)

**Contenido del card:**
1. Header: titulo del plan (truncate si > 40 chars) + badge de estado
2. Progreso: barra de progreso + texto "N de M completados"
3. Stats: "N procedimientos" + "Total: $X"
4. Footer: nombre del doctor + fecha de creacion

---

### Component 2: EstadoBadge

**Type:** Badge de estado del plan

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| estado | "borrador" \| "activo" \| "completado" \| "cancelado" | — | Estado del plan |
| size | "sm" \| "md" | "sm" | Tamano del badge |

**Behavior:** Mapa de colores y labels:
- `borrador` → `bg-gray-100 text-gray-600` + label "Borrador" + icono `Circle` gris
- `activo` → `bg-blue-100 text-blue-700` + label "Activo" + indicador puntito azul animado
- `completado` → `bg-green-100 text-green-700` + label "Completado" + icono `CheckCircle`
- `cancelado` → `bg-red-100 text-red-700` + label "Cancelado" + icono `XCircle`

---

### Component 3: BarraProgreso

**Type:** Progress bar

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| completados | number | 0 | Items completados |
| total | number | 0 | Total de items |
| colorScheme | "blue" \| "green" | "blue" | Color de la barra activa |

**Behavior:**
- Si `total === 0`: barra vacia con texto "Sin procedimientos"
- Si `completados === total && total > 0`: barra verde completa
- Texto: "{completados} de {total} completados"
- Barra: `rounded-full`, `h-2`, transicion de anchura cuando cambia

---

### Component 4: SelectorNuevoPlan

**Type:** Button con dropdown

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onNuevo | function | — | Abre modal de creacion manual |
| onAutoGenerar | function | — | Inicia flujo de auto-generacion |
| hasOdontogram | boolean | true | Si el paciente tiene odontograma para auto-generar |

**States:**
- Default — boton "Nuevo Plan" con chevron
- Open — dropdown visible con 2 opciones
- Auto-generar disabled — si `!hasOdontogram`, la opcion tiene tooltip "El paciente no tiene odontograma"

**Behavior:**
- Click en boton abre dropdown con 2 opciones:
  1. "Crear plan manualmente" → abre modal FE-TP-02
  2. "Auto-generar desde odontograma" → abre FE-TP-02 con modo auto-generacion activo

---

## Form Fields

No aplica — esta pantalla es solo listado con filtros de ordenamiento, sin formulario de entrada de datos propio.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Listar planes del paciente | `/api/v1/patients/{id}/treatment-plans` | GET | `specs/treatment-plans/TP-03-list-plans.md` | 3min |

### Query Params
```
GET /api/v1/patients/{id}/treatment-plans
  ?sort=created_at_desc|created_at_asc|status
  &page=1
  &per_page=20
```

### State Management

**Local State (useState):**
- `sortBy: "fecha_desc" | "fecha_asc" | "estado"` — criterio de ordenamiento actual

**Global State (Zustand):**
- `patientStore.currentPatient` — datos del paciente activo

**Server State (TanStack Query):**
- Query key: `['treatment-plans', patientId, tenantId, sortBy]`
- Stale time: 3 minutos
- Refetch on window focus: true

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `patient_not_found` | 404 | "Paciente no encontrado" |
| `forbidden` | 403 | "No tienes permisos para ver los planes de tratamiento" |
| `server_error` | 500 | "Error al cargar los planes. Intenta de nuevo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click en card | Click en cualquier parte del card | Navega a `/patients/{id}/treatment-plans/{id}` | Transicion de pagina |
| Cambiar orden | Dropdown de ordenamiento | Re-fetch con nuevo orden | Skeleton durante carga |
| Nuevo Plan | Click opcion "Crear manualmente" | Abre modal FE-TP-02 | Modal slide-up |
| Auto-generar | Click opcion "Auto-generar" | Abre FE-TP-02 con modo auto | Modal slide-up con estado auto-generando |

### Animations/Transitions

- Cards: fade-in con stagger 50ms de delay entre cards al cargar la lista
- Hover en card: `shadow-md` con transition `150ms ease-out`
- Click en card: `scale-[0.99]` 100ms → navega
- Dropdown nuevo plan: fade + scale 100ms ease-out

---

## Loading & Error States

### Loading State
- Grid de 4 cards skeleton (2x2 en tablet):
  - Cada skeleton: `rounded-xl bg-gray-100 animate-pulse`
  - Lineas de placeholder: ancho variable simulando titulo, barra, stats
  - Altura de skeleton card: 180px (mismo que card real aproximado)

### Error State
- Banner de error sobre el grid: `bg-red-50 border border-red-200 rounded-lg p-4`
- Icono `AlertCircle` + mensaje + boton "Reintentar"

### Empty State
- Sin planes en el paciente:
  - **Ilustracion:** icono `ClipboardList` en `text-gray-300 w-16 h-16`
  - **Mensaje:** "Este paciente no tiene planes de tratamiento"
  - **Submensaje:** "Crea un plan para documentar y organizar los procedimientos a realizar"
  - **CTA primario:** "Crear plan" → abre FE-TP-02
  - **CTA secundario:** "Auto-generar desde odontograma" (si el paciente tiene odontograma)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | 1 columna de cards apiladas. Barra de acciones vertical (orden arriba, boton abajo). Cards full-width. |
| Tablet (640-1024px) | 2 columnas de cards. Barra de acciones horizontal. Layout primario clinico. Cards con min 44px touch target en boton nuevo. |
| Desktop (> 1024px) | 3 columnas de cards. Barra de acciones con mas espacio. Cards mas anchas. |

**Tablet priority:** High — planes de tratamiento se revisan en tablet en sala de espera. Cards con padding generoso. Todo el area del card es touch target. Boton "Nuevo Plan" con altura minima de 44px.

---

## Accessibility

- **Focus order:** Selector de orden → Boton "Nuevo Plan" → Cards en orden del grid (izquierda a derecha, fila por fila)
- **Screen reader:** `aria-label="Lista de planes de tratamiento de {nombre paciente}"` en la region. Cada card tiene `role="article"` con `aria-label="{titulo del plan}, estado {estado}, {N} de {M} completados, total ${costo}"`.
- **Keyboard navigation:** Tab navega entre cards. Enter/Space en card navega al detalle. Enter/Space en boton abre dropdown.
- **Color contrast:** WCAG AA en todos los badges de estado. Texto del card en `text-gray-900` / `text-gray-600` cumple 4.5:1.
- **Language:** es-419. Fechas formateadas con `date-fns/locale/es`. Valores monetarios en formato COP.

---

## Design Tokens

**Colors:**
- Card fondo: `bg-white`
- Card borde: `border border-gray-200`
- Card hover: `hover:shadow-md hover:border-gray-300`
- Barra progreso inactiva: `bg-gray-200`
- Barra progreso activa (en progreso): `bg-blue-500`
- Barra progreso completo: `bg-green-500`
- Texto stats: `text-gray-600`
- Texto footer (doctor, fecha): `text-xs text-gray-400`
- Precio: `text-gray-900 font-semibold`

**Typography:**
- Titulo plan: `text-base font-semibold text-gray-900 truncate`
- Stats: `text-sm text-gray-600`
- Total cost: `text-base font-bold text-gray-900`
- Doctor/fecha: `text-xs text-gray-400`

**Spacing:**
- Grid gap: `gap-4`
- Card padding: `p-5`
- Barra progreso: `mt-3 mb-3`
- Stats gap: `gap-3`

**Border Radius:**
- Card: `rounded-xl`
- Barra progreso: `rounded-full`
- Badge: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — fetch y cache de planes
- `lucide-react` — ClipboardList, Plus, ChevronDown, CheckCircle, XCircle, Circle, AlertCircle
- `date-fns` + `date-fns/locale/es` — formateo de fechas
- `framer-motion` — stagger animation de cards y fade-in

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/treatment-plans/page.tsx`
- Grid: `src/components/treatment-plans/TreatmentPlanGrid.tsx`
- Card: `src/components/treatment-plans/TreatmentPlanCard.tsx`
- Badge: `src/components/treatment-plans/PlanStatusBadge.tsx`
- Progreso: `src/components/treatment-plans/PlanProgressBar.tsx`
- Hook: `src/hooks/useTreatmentPlans.ts`

**Hooks Used:**
- `useQuery(['treatment-plans', patientId, sortBy])` — fetch de planes
- `useAuth()` — contexto de usuario y tenant
- `usePatientStore()` — paciente activo
- `useState` — sortBy local
- `useRouter()` — navegacion al detalle

**Form Library:** No aplica en esta vista.

---

## Test Cases

### Happy Path
1. Lista de planes carga correctamente
   - **Given:** Paciente con 3 planes (activo, completado, borrador)
   - **When:** Usuario navega al tab "Planes de Tratamiento"
   - **Then:** 3 cards en grid con estado, progreso y costo correctos; animacion stagger

2. Ordenar por estado
   - **Given:** Lista con planes de distintos estados
   - **When:** Usuario selecciona "Estado" en el dropdown de ordenamiento
   - **Then:** Cards se reordenan: activos primero, luego borrador, completados, cancelados

3. Navegar al detalle
   - **Given:** Card de plan visible en el grid
   - **When:** Usuario hace click en el card
   - **Then:** Navega a `/patients/{id}/treatment-plans/{plan_id}`

### Edge Cases
1. Plan con titulo muy largo
   - **Given:** Plan con titulo de 80 caracteres
   - **When:** Card se renderiza
   - **Then:** Titulo truncado con ellipsis (`truncate`) sin romper el layout del card

2. Plan sin procedimientos (total = 0)
   - **Given:** Plan recien creado sin items agregados
   - **When:** Card se muestra
   - **Then:** Barra de progreso vacia con texto "Sin procedimientos"

3. Auto-generar cuando no hay odontograma
   - **Given:** Paciente sin odontograma registrado (`hasOdontogram=false`)
   - **When:** Usuario abre dropdown de "Nuevo Plan"
   - **Then:** Opcion "Auto-generar" aparece deshabilitada con tooltip "El paciente no tiene odontograma"

### Error Cases
1. Error de red al cargar lista
   - **Given:** Sin conexion
   - **When:** Tab se monta
   - **Then:** Banner de error con boton "Reintentar"

---

## Acceptance Criteria

- [ ] Grid de cards: 1 columna mobile, 2 tablet, 3 desktop
- [ ] Card muestra: titulo (truncado), badge de estado con color correcto, barra de progreso, conteo de items, costo total formateado en COP, nombre del doctor, fecha
- [ ] 4 estados con colores distintos: Borrador (gris), Activo (azul), Completado (verde), Cancelado (rojo)
- [ ] Barra de progreso proporcional a items completados/total
- [ ] Animacion puntito azul parpadeando en estado "Activo"
- [ ] Dropdown "Nuevo Plan" con 2 opciones: crear manual y auto-generar
- [ ] Auto-generar disabled con tooltip si el paciente no tiene odontograma
- [ ] Click en card navega al detalle del plan
- [ ] Selector de orden: fecha desc (default), fecha asc, estado
- [ ] Estado de carga: 4 skeleton cards con animate-pulse
- [ ] Estado de error: banner con "Reintentar"
- [ ] Estado vacio: mensaje + CTA "Crear plan" + CTA secundario "Auto-generar"
- [ ] Stagger animation al cargar los cards
- [ ] Responsive: 1/2/3 columnas segun breakpoint
- [ ] Touch target completo de cada card (toda la superficie)
- [ ] Accesibilidad: role="article" por card, aria-label descriptivo con datos del plan
- [ ] Fechas y precios en formato es-419 / COP

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
