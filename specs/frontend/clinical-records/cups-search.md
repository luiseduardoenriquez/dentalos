# Busqueda CUPS — Frontend Spec

## Overview

**Screen:** Componente reutilizable de busqueda y seleccion de codigos CUPS (Clasificacion Unica de Procedimientos en Salud) para Colombia. Mismo patron que el componente CIE-10 (FE-CR-06): combobox con autocompletado, debounce 300ms, minimo 2 caracteres, navegacion por teclado. Diferencia clave: muestra codigo + descripcion + badge de categoria (ej: "Odontologia General", "Cirugia Oral"). Se usa en FE-CR-05 (ProcedureForm) y FE-TP-02 (PlanCreate).

**Route:** Componente reutilizable — sin ruta propia. Montado en formularios de procedimientos y planes de tratamiento.

**Priority:** High

**Backend Specs:** `specs/clinical-records/CR-11-cups-search.md`

**Dependencies:**
- `specs/frontend/clinical-records/procedure-form.md` — contexto primario de uso (FE-CR-05)
- `specs/frontend/treatment-plans/plan-create.md` — contexto secundario (FE-TP-02)
- `specs/frontend/clinical-records/cie10-search.md` — patron de diseno identico (FE-CR-06)

---

## User Flow

**Entry Points:**
- Renderizado como campo de formulario en FE-CR-05 (ProcedureFormModal)
- Renderizado como campo en FE-TP-02 (PlanCreateModal) al agregar items
- Cualquier formulario futuro que requiera seleccion de procedimiento CUPS

**Exit Points:**
- Seleccion de item: llama a `onChange(item)` con el objeto CUPS completo
- Escape / blur sin seleccion: mantiene valor anterior o vacio

**User Story:**
> As a doctor | assistant, I want to search for CUPS procedure codes by typing a description or code so that I can quickly find and assign the correct standardized procedure code to a clinical record or treatment plan.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+---------------------------------------------------+
|  [Buscar procedimiento CUPS...              ] [X]  |
+---------------------------------------------------+
| 89.07  Examen dental completo                     |
|        [badge: Odontología General]       (hover) |
|                                                   |
| 23.09  Extraccion de diente permanente            |
|        [badge: Cirugia Oral]                      |
|                                                   |
| 97.22  Restauracion con composite posterior       |
|        [badge: Operatoria]                        |
|                                                   |
| [Sin resultados | Buscando... | Min 2 chars]      |
+---------------------------------------------------+
```

**Sections:**
1. Input de busqueda — texto con icono `Search`, boton X para limpiar
2. Dropdown de resultados — lista de hasta 10 items: codigo + descripcion + badge de categoria
3. Estado interno del dropdown — loading, sin resultados, hint de minimo caracteres

---

## UI Components

### Component 1: CUPSComboboxInput

**Type:** Combobox / Autocomplete input

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | CUPSItem \| null | null | Item actualmente seleccionado |
| onChange | (item: CUPSItem \| null) => void | — | Callback al seleccionar o limpiar |
| placeholder | string | "Buscar procedimiento CUPS..." | Texto del placeholder |
| disabled | boolean | false | Deshabilita el input y el dropdown |
| error | string \| undefined | undefined | Mensaje de error bajo el input |
| autoFocus | boolean | false | Autofocus al montar |
| name | string | — | Nombre del campo para integracion con formularios |
| showPrice | boolean | false | Muestra precio del catalogo junto al resultado (para FE-TP-02) |

**States:**
- Idle (sin valor) — input vacio con placeholder e icono `Search`
- Typing (menos de 2 chars) — hint "Escribe al menos 2 caracteres" en dropdown
- Searching — icono `Loader2` animado, spinner inline en input
- Results — lista de hasta 10 codigos con badge de categoria
- Selected — input muestra `{codigo} — {descripcion}` + boton X
- Error — borde rojo, mensaje `text-xs text-red-600`
- Disabled — opacidad 50%, cursor not-allowed

---

### Component 2: CUPSDropdownItem

**Type:** List item con badge de categoria

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| item | CUPSItem | — | Datos del codigo: { codigo, descripcion, categoria, precio? } |
| isHighlighted | boolean | false | Item bajo cursor o navegacion teclado |
| onSelect | function | — | Callback al hacer click |
| showPrice | boolean | false | Muestra el precio del catalogo (solo en contexto de plan) |
| query | string | "" | Para highlighting del texto que coincide |

**States:**
- Default — fondo blanco
- Highlighted — `bg-blue-50`
- Selected — checkmark azul a la derecha

**Behavior:**
- Layout del item:
  ```
  [codigo bold] — [descripcion]
  [badge categoria]    [precio? $xx,xxx]
  ```
- Codigo: `font-mono font-bold text-gray-900` en la primera linea
- Descripcion: en la misma linea que el codigo, `text-gray-700`
- Badge categoria: segunda linea, mas pequeno
- Precio (opcional): alineado a la derecha de la segunda linea, `text-gray-600 font-medium`
- Altura minima del item: 52px (mayor que CIE-10 por tener 2 lineas)

---

### Component 3: CategoriaBadge

**Type:** Badge de categoria CUPS

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| categoria | string | — | Nombre de la categoria del procedimiento |
| size | "sm" \| "xs" | "xs" | Tamano del badge |

**Behavior:** Badge de color fijo segun categoria (mapa de colores predefinido):
- "Odontologia General" → `bg-blue-100 text-blue-700`
- "Cirugia Oral" → `bg-red-100 text-red-700`
- "Operatoria" → `bg-green-100 text-green-700`
- "Periodoncia" → `bg-purple-100 text-purple-700`
- "Endodoncia" → `bg-yellow-100 text-yellow-700`
- "Ortodoncia" → `bg-pink-100 text-pink-700`
- "Radiologia" → `bg-gray-100 text-gray-700`
- "Protesis" → `bg-orange-100 text-orange-700`
- Otras categorias → `bg-gray-100 text-gray-600`

---

## Form Fields

Igual que CIE-10 Search (FE-CR-06), este componente es un campo de formulario reutilizable sin campos propios adicionales.

**Tipos TypeScript:**
```typescript
interface CUPSItem {
  codigo: string;         // Ej: "89.07"
  descripcion: string;    // Ej: "Examen dental completo"
  categoria: string;      // Ej: "Odontologia General"
  precio?: number;        // Precio del catalogo del tenant (opcional)
}

interface CUPSSearchProps {
  value: CUPSItem | null;
  onChange: (item: CUPSItem | null) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  autoFocus?: boolean;
  name?: string;
  showPrice?: boolean;    // true en contexto de plan de tratamiento
}
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Buscar codigos CUPS | `/api/v1/cups/search?q={query}&limit=10` | GET | `specs/clinical-records/CR-11-cups-search.md` | 30min |
| Buscar con precio | `/api/v1/cups/search?q={query}&include_price=true&limit=10` | GET | `specs/clinical-records/CR-11-cups-search.md` | 30min |

### Query Params
```
GET /api/v1/cups/search
  ?q=extraccion          # query de busqueda (min 2 chars)
  &limit=10              # max resultados
  &include_price=true    # solo cuando showPrice=true (para planes de tratamiento)
  &categoria=cirugia     # filtro opcional por categoria (futuro)
```

### Response esperada:
```json
{
  "data": [
    {
      "codigo": "23.09",
      "descripcion": "Extraccion de diente permanente",
      "categoria": "Cirugia Oral",
      "precio": 85000
    }
  ],
  "total": 1
}
```

### State Management

**Local State (useState):**
- `inputValue: string` — texto actual en el input
- `isOpen: boolean` — dropdown abierto o cerrado
- `highlightedIndex: number` — indice del item resaltado (-1 = ninguno)
- `searchQuery: string` — valor debounced (300ms) para el query

**Global State (Zustand):**
- No requiere estado global — componente completamente controlado via props

**Server State (TanStack Query):**
- Query key: `['cups-search', searchQuery, showPrice]`
- Enabled: `searchQuery.length >= 2`
- Stale time: 30 minutos
- Cache time: 60 minutos
- Retry: 1 vez

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `search_failed` | 500 | "Error al buscar. Intenta de nuevo." |
| `rate_limited` | 429 | "Demasiadas busquedas. Espera un momento." |

---

## Interactions

### User Actions

Identicos a FE-CR-06 (CIE-10 Search). Referencia completa en `specs/frontend/clinical-records/cie10-search.md`:

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Escribir en input | Keypress | Actualiza `inputValue`; 300ms → query | Spinner durante fetch |
| Escribir < 2 chars | Keypress | Hint en dropdown | "Escribe al menos 2 caracteres para buscar" |
| Arrow Down | Keydown | Mueve highlight al siguiente | Item visualmente resaltado |
| Arrow Up | Keydown | Mueve highlight al anterior | Item visualmente resaltado |
| Enter (con highlight) | Keydown | Selecciona el item resaltado | Input actualizado, dropdown cierra |
| Click en item | MouseDown | Selecciona el item | Input actualizado, dropdown cierra |
| Click fuera | Blur/click fuera | Cierra dropdown | Input restaura valor o queda vacio |
| Escape | Keydown | Cierra dropdown | Sin cambio de valor |
| Click X | Click boton X | Limpia seleccion | Input vacio, `onChange(null)` |

### Diferencias respecto a CIE-10 Search:

- El dropdown tiene altura minima mayor por la segunda linea (badge + precio)
- Al seleccionar en contexto de plan (`showPrice=true`), el badge de precio se muestra junto al codigo en el input tras seleccion: `{codigo} — {descripcion} ($85,000)`
- Badge de categoria en el dropdown es un elemento visual adicional sin comportamiento

### Animations/Transitions

- Identicas a FE-CR-06: fade-in + scale-y del dropdown 100ms, fade-out 80ms
- Badge de categoria: sin animacion propia, aparece con el item

---

## Loading & Error States

### Loading State
- Icono `Search` reemplazado por `Loader2` animado en el input durante fetch
- Dropdown permanece abierto con spinner central
- Resultados previos en cache se muestran con opacidad reducida mientras actualiza

### Error State
- Error inline en el dropdown: icono `AlertCircle` + "Error al buscar. Intenta de nuevo."
- No se usa toast — el error es contextual al campo
- Input permanece editable para reintentar

### Empty State
- 0 resultados: icono `SearchX` + "Sin resultados para '{query}'"
- Si la categoria filtrada no tiene resultados: "Sin procedimientos de {categoria} para '{query}'"

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Input full-width. Dropdown full-width. Items con 52px minimo de altura. Badge en segunda linea. |
| Tablet (640-1024px) | Input full-width en su contenedor. Items 52px minimo. Badge categoria visible. Precio visible si `showPrice`. Touch targets 44px. |
| Desktop (> 1024px) | Dropdown hasta 480px de ancho si el contenedor lo permite. Layout de 2 lineas por item intacto. |

**Tablet priority:** High — busqueda de CUPS se usa durante el registro de procedimientos en tablet. Items del dropdown con area de toque de minimo 52px por tener 2 lineas de contenido (garantiza que la segunda linea es facilmente tocable).

---

## Accessibility

- **Focus order:** Igual que CIE-10 Search. El input recibe foco con Tab. Arrow Up/Down navegan entre items sin mover el foco del DOM.
- **Screen reader:**
  - Input: `role="combobox"` con `aria-expanded`, `aria-haspopup="listbox"`, `aria-controls="cups-listbox"`, `aria-autocomplete="list"`
  - Dropdown: `role="listbox"` con `id="cups-listbox"`
  - Cada item: `role="option"` con `aria-selected`, `aria-label="{codigo} — {descripcion}, categoria: {categoria}"`
  - Badge de categoria: `aria-hidden="true"` (ya incluido en el aria-label del item)
  - Input: `aria-activedescendant` apunta al item resaltado
  - Al seleccionar: `aria-live="polite"` anuncia "{codigo} — {descripcion} seleccionado"
- **Keyboard navigation:** Identico a FE-CR-06. Arrow keys, Enter, Escape, Tab.
- **Color contrast:** WCAG AA. Badges con suficiente contraste. Colores seleccionados para cumplir 4.5:1 texto sobre fondo del badge.
- **Language:** es-419. Nombres de categorias en español. Mensajes de error y estados en español.

---

## Design Tokens

**Colors:**
- Input: `border-gray-300 focus:border-blue-500`
- Input error: `border-red-400 focus:border-red-500`
- Item highlighted: `bg-blue-50`
- Codigo: `text-gray-900 font-mono font-bold`
- Descripcion: `text-gray-700`
- Precio: `text-gray-600 font-medium`

**Typography:**
- Codigo CUPS: `text-sm font-mono font-bold text-gray-900`
- Descripcion: `text-sm text-gray-700`
- Badge categoria: `text-xs font-medium`
- Precio: `text-sm font-medium text-gray-600`
- Placeholder: `text-sm text-gray-400`

**Spacing:**
- Input padding: `px-3 py-2.5 pl-10`
- Item padding: `px-3 py-3` (mayor que CIE-10 por 2 lineas)
- Gap codigo-descripcion: inline con espacio normal
- Gap entre linea 1 y linea 2: `mt-1`

**Border Radius:**
- Input: `rounded-md`
- Dropdown: `rounded-md shadow-lg`
- Badge categoria: `rounded-full px-2 py-0.5`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — query de busqueda
- `use-debounce` — 300ms debounce
- `lucide-react` — Search, X, Loader2, AlertCircle, SearchX, Check

**File Location:**
- Component: `src/components/clinical-records/CUPSSearchInput.tsx`
- Badge categoria: `src/components/clinical-records/CategoriasBadge.tsx`
- Hook: `src/hooks/useCUPSSearch.ts`
- API: `src/lib/api/cups.ts`
- Types: `src/types/clinical-records.ts` — `CUPSItem` interface

**Relacion con CIE-10 Search:**
Ambos componentes siguen el mismo patron de combobox. Se recomienda extraer la logica compartida en:
- `src/hooks/useComboboxSearch.ts` — hook generico de combobox con debounce y navegacion de teclado
- `src/components/ui/ComboboxInput.tsx` — componente base sin estilos especificos de dominio

Los componentes `CIE10SearchInput` y `CUPSSearchInput` serían wrappers que usan el hook y componente base pero con endpoints, tipos y estilos de item especificos.

**Hooks Used:**
- `useDebounce(inputValue, 300)`
- `useQuery(['cups-search', debouncedQuery, showPrice], { enabled: debouncedQuery.length >= 2 })`
- `useRef` para click-outside
- `useEffect` para listener click-outside

**Form Library:**
- Compatible con React Hook Form via `Controller`:
```typescript
<Controller
  name="cups_codigo"
  control={control}
  render={({ field, fieldState }) => (
    <CUPSSearchInput
      value={field.value}
      onChange={field.onChange}
      error={fieldState.error?.message}
      showPrice={isInTreatmentPlanContext}
    />
  )}
/>
```

---

## Test Cases

### Happy Path
1. Busqueda por descripcion y seleccion con click
   - **Given:** Componente montado en FE-CR-05
   - **When:** Usuario escribe "extraccion", espera 300ms, hace click en "23.09 — Extraccion de diente permanente"
   - **Then:** Input muestra "23.09 — Extraccion de diente permanente", dropdown cierra, `onChange` llamado con el objeto completo

2. Busqueda por codigo exacto
   - **Given:** Usuario escribe "89.07"
   - **When:** Fetch retorna resultado
   - **Then:** "89.07 — Examen dental completo" aparece primero con badge "Odontologia General"

3. Seleccion con precio (en contexto de plan)
   - **Given:** `showPrice={true}`, usuario selecciona extraccion ($85,000)
   - **When:** Item seleccionado
   - **Then:** Input muestra "23.09 — Extraccion de diente permanente ($85,000)"

4. Navegacion de teclado completa
   - **Given:** Dropdown abierto con 5 resultados
   - **When:** Arrow Down 3 veces → Enter
   - **Then:** 4to item seleccionado, dropdown cierra

### Edge Cases
1. Mismo patron de minimo 2 chars que CIE-10
   - **Given:** Usuario escribe "e" (1 char)
   - **When:** Dropdown aparece
   - **Then:** "Escribe al menos 2 caracteres para buscar" — sin fetch al API

2. Badge de categoria correcto
   - **Given:** Resultado "23.09 Extraccion..."
   - **When:** Item aparece en dropdown
   - **Then:** Badge muestra "Cirugia Oral" con fondo rojo claro

3. Componente en plan (showPrice=false)
   - **Given:** `showPrice={false}` (default)
   - **When:** Dropdown muestra resultados
   - **Then:** No se muestra precio; query al API sin `include_price=true`

### Error Cases
1. Error de red
   - **Given:** Sin conexion
   - **When:** Usuario escribe y el fetch falla
   - **Then:** Mensaje inline en dropdown: "Error al buscar. Intenta de nuevo."

2. Resultado seleccionado sin precio cuando showPrice es true
   - **Given:** `showPrice={true}` pero el CUPS no tiene precio en el catalogo
   - **When:** Item aparece en dropdown
   - **Then:** Precio muestra "Sin precio" en lugar de "$0" o nada

---

## Acceptance Criteria

- [ ] Input con placeholder "Buscar procedimiento CUPS..."
- [ ] Icono `Search` a la izquierda del input
- [ ] Busqueda NO se activa con menos de 2 caracteres (hint visible en dropdown)
- [ ] Debounce de exactamente 300ms
- [ ] Spinner de carga reemplaza el icono Search durante fetch
- [ ] Dropdown muestra hasta 10 resultados: codigo `font-mono font-bold` + descripcion + badge de categoria
- [ ] Badge de categoria con colores por dominio clinico (8 categorias con colores distintos)
- [ ] Precio visible en dropdown cuando `showPrice={true}`
- [ ] Navegacion completa con Arrow Up/Down + Enter
- [ ] Escape cierra dropdown sin cambiar seleccion
- [ ] Click fuera cierra dropdown
- [ ] Boton X limpia seleccion con `onChange(null)`
- [ ] Cache de TanStack Query 30 minutos
- [ ] Estado de error inline (no toast)
- [ ] Estado "Sin resultados" con icono
- [ ] ARIA completo: role="combobox", listbox, option, aria-expanded, aria-activedescendant
- [ ] Badge con `aria-hidden="true"` (info en aria-label del item)
- [ ] Touch targets minimo 52px por item (2 lineas de contenido)
- [ ] Funciona con React Hook Form via Controller
- [ ] Patron compartido con CIE-10 Search (hook base reutilizable)
- [ ] Textos en es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
