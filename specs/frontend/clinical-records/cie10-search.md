# Busqueda CIE-10 — Frontend Spec

## Overview

**Screen:** Componente reutilizable de busqueda y seleccion de codigos CIE-10 (Clasificacion Internacional de Enfermedades, 10ma revision). Implementado como combobox con autocompletado: busqueda debounced de 300ms, minimo 2 caracteres para activar, muestra codigo en negrita con descripcion, navegacion completa por teclado. Se usa embebido en FE-CR-04 (diagnostico) y otras pantallas que requieran codigos diagnosticos.

**Route:** Componente reutilizable — sin ruta propia. Se monta en `/patients/{id}/records` y rutas relacionadas.

**Priority:** High

**Backend Specs:** `specs/clinical-records/CR-10-cie10-search.md`

**Dependencies:**
- `specs/frontend/clinical-records/diagnosis-form.md` — contexto primario de uso (FE-CR-04)
- `specs/frontend/clinical-records/record-create.md` — contexto secundario (FE-CR-02)

---

## User Flow

**Entry Points:**
- Renderizado como campo de formulario en FE-CR-04 (DiagnosisFormModal)
- Renderizado como campo en cualquier formulario que requiera seleccion de diagnostico CIE-10

**Exit Points:**
- Seleccion de item: llama a `onChange(item)` con el objeto CIE-10 seleccionado
- Escape / blur sin seleccion: mantiene el valor anterior o vacio

**User Story:**
> As a doctor, I want to search for ICD-10 diagnosis codes by typing a description or code so that I can quickly find and assign the correct standardized diagnosis without having to memorize codes.

**Roles with access:** `clinic_owner`, `doctor` (contexto de formularios clinicos)

---

## Layout Structure

```
+--------------------------------------------+
|  [Buscar diagnostico CIE-10...         ] [x]|
+--------------------------------------------+
| K02   Caries dental                         |
| K02.1 Caries de la dentina         (hover) |
| K02.2 Caries del cemento                   |
| K02.3 Caries detenida                      |
| K02.5 Caries con exposicion pulpar         |
| [Sin resultados | Buscando... | Min 2 chars]|
+--------------------------------------------+
```

**Sections:**
1. Input de busqueda — campo de texto con placeholder, icono de busqueda, boton de limpiar (X)
2. Dropdown de resultados — lista de hasta 10 items: codigo en negrita + descripcion
3. Estado interno del dropdown — loading, sin resultados, hint minimo caracteres

---

## UI Components

### Component 1: CIE10ComboboxInput

**Type:** Combobox / Autocomplete input

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | CIE10Item \| null | null | Item actualmente seleccionado |
| onChange | (item: CIE10Item \| null) => void | — | Callback al seleccionar o limpiar |
| placeholder | string | "Buscar diagnostico CIE-10..." | Texto del placeholder |
| disabled | boolean | false | Deshabilita el input y el dropdown |
| error | string \| undefined | undefined | Mensaje de error para mostrar bajo el input |
| autoFocus | boolean | false | Hace foco al montar el componente |
| name | string | — | Nombre del campo para formularios |

**States:**
- Idle (sin valor) — input vacio con placeholder gris + icono `Search`
- Typing (menos de 2 chars) — hint "Escribe al menos 2 caracteres" en dropdown
- Searching — dropdown con spinner inline `Loader2` animado
- Results — lista de hasta 10 codigos con hover y keyboard navigation
- Selected — input muestra `{codigo} — {descripcion}` en texto; boton X visible para limpiar
- Error — borde rojo en input, mensaje de error en `text-xs text-red-600` debajo
- Disabled — opacidad 50%, cursor not-allowed, sin interaccion

---

### Component 2: CIE10DropdownItem

**Type:** List item dentro del dropdown

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| item | CIE10Item | — | Datos del codigo: { codigo, descripcion, capitulo? } |
| isHighlighted | boolean | false | Item bajo el cursor o navegacion de teclado |
| onSelect | function | — | Callback al hacer click |
| query | string | "" | Texto de busqueda para highlighting |

**States:**
- Default — fondo blanco, texto normal
- Highlighted (hover o arrow key) — fondo `bg-blue-50`
- Selected (ya seleccionado) — checkmark a la derecha, texto `text-blue-700`

**Behavior:**
- Codigo: `font-mono font-bold text-gray-900` — siempre en primer lugar
- Separador visual: `—` en `text-gray-400`
- Descripcion: `text-sm text-gray-700` — puede hacer truncate si es muy larga
- Highlighting: los caracteres que coinciden con el query se resaltan en `font-semibold` o `text-blue-600`
- Altura minima: 44px para touch targets en tablet

---

## Form Fields

Este componente es un campo de formulario reutilizable, no tiene campos propios adicionales. Los valores de busqueda son manejados como estado local interno. El valor seleccionado se expone via `onChange`.

**Tipos TypeScript:**
```typescript
interface CIE10Item {
  codigo: string;        // Ej: "K02.1"
  descripcion: string;   // Ej: "Caries de la dentina"
  capitulo?: string;     // Ej: "Enfermedades del sistema digestivo"
}

interface CIE10SearchProps {
  value: CIE10Item | null;
  onChange: (item: CIE10Item | null) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  autoFocus?: boolean;
  name?: string;
}
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Buscar codigos CIE-10 | `/api/v1/cie10/search?q={query}&limit=10` | GET | `specs/clinical-records/CR-10-cie10-search.md` | 30min |

### Query Params
```
GET /api/v1/cie10/search
  ?q=caries          # query de busqueda (min 2 chars)
  &limit=10          # max resultados (default 10)
```

### Response esperada:
```json
{
  "data": [
    { "codigo": "K02", "descripcion": "Caries dental" },
    { "codigo": "K02.1", "descripcion": "Caries de la dentina" }
  ],
  "total": 2
}
```

### State Management

**Local State (useState):**
- `inputValue: string` — texto actual en el input (puede diferir del valor seleccionado)
- `isOpen: boolean` — dropdown abierto o cerrado
- `highlightedIndex: number` — indice del item actualmente resaltado por teclado (-1 = ninguno)
- `searchQuery: string` — valor debounced del input (300ms) que dispara el query

**Global State (Zustand):**
- No requiere estado global — es un componente completamente controlado via props

**Server State (TanStack Query):**
- Query key: `['cie10-search', searchQuery]`
- Enabled: solo cuando `searchQuery.length >= 2`
- Stale time: 30 minutos (datos CIE-10 son muy estables)
- Cache time: 60 minutos
- Retry: 1 vez en caso de error de red

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `search_failed` | 500 | "Error al buscar. Intenta de nuevo." (inline en dropdown) |
| `rate_limited` | 429 | "Demasiadas busquedas. Espera un momento." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Escribir en input | Keypress | Actualiza `inputValue`; 300ms despues dispara query | Loading spinner durante fetch |
| Escribir menos de 2 chars | Keypress | Dropdown muestra hint | "Escribe al menos 2 caracteres para buscar" |
| Arrow Down | Keydown ArrowDown | Mueve `highlightedIndex` al siguiente | Item resaltado visualmente |
| Arrow Up | Keydown ArrowUp | Mueve `highlightedIndex` al anterior | Item resaltado visualmente |
| Enter | Keydown Enter (con item resaltado) | Selecciona el item resaltado | Dropdown cierra, input muestra codigo+descripcion |
| Enter (sin resaltado) | Keydown Enter | No hace nada (o selecciona el primer resultado) | — |
| Click en item | MouseDown en CIE10DropdownItem | Selecciona el item | Dropdown cierra, input muestra codigo+descripcion |
| Click fuera | Blur / click fuera del componente | Cierra dropdown | Si hay valor seleccionado, input vuelve a mostrarlo; si no, se limpia |
| Escape | Keydown Escape | Cierra dropdown sin seleccionar | Dropdown cierra, input mantiene estado anterior |
| Click X (limpiar) | Click en boton X | Limpia seleccion y input | Input vuelve a vacio + placeholder, onChange(null) |
| Tab | Keydown Tab | Cierra dropdown y pasa foco al siguiente campo | Comportamiento de teclado estandar |

### Animations/Transitions

- Dropdown aparece: fade-in + scale-y desde 0.95 a 1, `100ms ease-out`
- Dropdown desaparece: fade-out `80ms ease-in`
- Item highlight: transicion de fondo `75ms ease-out`
- Loading spinner: `animate-spin` en icono `Loader2`

---

## Loading & Error States

### Loading State
- El icono `Search` del input se reemplaza temporalmente por `Loader2` animado durante el fetch
- Dropdown permanece abierto mostrando spinner central mientras carga
- Si hay resultados anteriores (cache), se muestran mientras se actualiza (stale-while-revalidate)

### Error State
- Error de API: mensaje inline dentro del dropdown (no toast, para mantener contexto)
- Formato: icono `AlertCircle` pequeno + texto "Error al buscar. Intenta de nuevo." centrado en el dropdown
- El input permanece editable para que el usuario pueda reintentar escribiendo

### Empty State
- 0 resultados con query >= 2 chars: mensaje "Sin resultados para '{query}'" centrado en dropdown
- Icono `SearchX` en gris + texto `text-sm text-gray-500`
- No hay CTA — el usuario puede modificar el texto de busqueda

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Input full-width. Dropdown full-width alineado al input. Items con 48px minimo de altura para touch. |
| Tablet (640-1024px) | Input full-width dentro de su contenedor. Dropdown max-w del contenedor padre. Items 44px altura. Layout primario. |
| Desktop (> 1024px) | Igual al tablet. Dropdown puede extenderse hasta 400px de ancho si el contenedor lo permite. |

**Tablet priority:** High — el input se usa durante consultas en tablet. Touch target de cada item: minimo 44px de altura. Boton X de limpiar: minimo 32x32px con area de toque expandida a 44px via padding.

---

## Accessibility

- **Focus order:** El input recibe foco con Tab. Cuando el dropdown esta abierto, Arrow Up/Down navegan entre items sin mover el foco del DOM fuera del input.
- **Screen reader:**
  - Input: `role="combobox"` con `aria-expanded={isOpen}`, `aria-haspopup="listbox"`, `aria-controls="cie10-listbox"`, `aria-autocomplete="list"`
  - Dropdown: `role="listbox"` con `id="cie10-listbox"`
  - Cada item: `role="option"` con `aria-selected={isSelected}`, `id="cie10-option-{index}"`
  - Input tiene `aria-activedescendant="cie10-option-{highlightedIndex}"` cuando hay item resaltado
  - Al seleccionar: `aria-live="polite"` anuncia "{codigo} — {descripcion} seleccionado"
- **Keyboard navigation:** Arrow Down/Up para navegar. Enter para seleccionar. Escape para cerrar. Tab cierra dropdown y avanza foco.
- **Color contrast:** WCAG AA. Codigo en `font-mono font-bold` agrega enfasis visual adicional al color. Item resaltado `bg-blue-50` con texto `text-gray-900` cumple 4.5:1.
- **Language:** es-419. Placeholder en español. Mensajes de error y estados en español. Los codigos CIE-10 y sus descripciones estan en español latinoamericano en el backend.

---

## Design Tokens

**Colors:**
- Input borde: `border-gray-300 focus:border-blue-500 focus:ring-blue-500`
- Input con error: `border-red-400 focus:border-red-500`
- Input disabled: `bg-gray-50 border-gray-200 text-gray-400`
- Dropdown: `bg-white border border-gray-200 shadow-lg`
- Item default: `bg-white text-gray-900`
- Item highlighted: `bg-blue-50`
- Item selected checkmark: `text-blue-600`
- Codigo: `text-gray-900 font-mono font-bold`
- Descripcion: `text-gray-600`
- Separador: `text-gray-400`

**Typography:**
- Codigo CIE-10: `text-sm font-mono font-bold text-gray-900`
- Descripcion: `text-sm text-gray-600`
- Placeholder: `text-sm text-gray-400`
- Hint/Error en dropdown: `text-sm text-gray-500`
- Error bajo input: `text-xs text-red-600`

**Spacing:**
- Input padding: `px-3 py-2.5 pl-10` (espacio para el icono Search)
- Item padding: `px-3 py-2.5`
- Dropdown: `mt-1 rounded-md` sobre el input
- Gap icono-texto en item: `gap-2`

**Border Radius:**
- Input: `rounded-md`
- Dropdown: `rounded-md`
- Item hover: sin borde extra

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — query de busqueda con cache de 30 min
- `use-debounce` — debounce de 300ms en el input
- `lucide-react` — Search, X, Loader2, AlertCircle, SearchX, Check
- `framer-motion` — animacion de entrada/salida del dropdown (opcional, puede ser CSS puro)

**File Location:**
- Component: `src/components/clinical-records/CIE10SearchInput.tsx`
- Hook: `src/hooks/useCIE10Search.ts`
- API: `src/lib/api/cie10.ts`
- Types: `src/types/clinical-records.ts` — `CIE10Item` interface

**Hooks Used:**
- `useDebounce(inputValue, 300)` — para disparar el query
- `useQuery(['cie10-search', debouncedQuery], { enabled: debouncedQuery.length >= 2 })` — fetch de resultados
- `useRef` — referencia al input y al dropdown para manejo de click-fuera
- `useEffect` — listener de click fuera para cerrar dropdown

**Form Library:**
- Compatible con React Hook Form via `Controller` o registro manual:
```typescript
// Uso con React Hook Form:
<Controller
  name="cie10_codigo"
  control={control}
  render={({ field, fieldState }) => (
    <CIE10SearchInput
      value={field.value}
      onChange={field.onChange}
      error={fieldState.error?.message}
    />
  )}
/>
```

**Manejo de foco y click-outside:**
```typescript
// Pattern recomendado con useRef:
const containerRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  const handleClickOutside = (e: MouseEvent) => {
    if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
      setIsOpen(false);
    }
  };
  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
}, []);
```

---

## Test Cases

### Happy Path
1. Busqueda exitosa y seleccion con click
   - **Given:** Componente montado y sin valor seleccionado
   - **When:** Usuario escribe "caries" → espera 300ms → hace click en "K02.1 — Caries de la dentina"
   - **Then:** Input muestra "K02.1 — Caries de la dentina", dropdown cierra, `onChange({ codigo: "K02.1", descripcion: "Caries de la dentina" })` se llama

2. Busqueda y seleccion con teclado
   - **Given:** Dropdown abierto con 5 resultados, primer item highlighteado
   - **When:** Usuario presiona Arrow Down 2 veces → Enter
   - **Then:** El 3er item es seleccionado, dropdown cierra, foco permanece en el input

3. Limpiar seleccion con boton X
   - **Given:** Item "K02.1" seleccionado, input muestra el valor
   - **When:** Usuario hace click en el boton X
   - **Then:** Input vuelve a vacio, `onChange(null)` se llama, placeholder reaparece

4. Busqueda por codigo directamente
   - **Given:** Componente vacio
   - **When:** Usuario escribe "K02" (codigo exacto)
   - **Then:** Dropdown muestra codigos K02.x con K02 primero (match exacto al tope)

### Edge Cases
1. Menos de 2 caracteres
   - **Given:** Usuario escribe solo "k"
   - **When:** Dropdown se abre
   - **Then:** Mensaje "Escribe al menos 2 caracteres para buscar" — no se hace fetch al API

2. Sin resultados
   - **Given:** Usuario escribe "xyzxyz123"
   - **When:** Fetch retorna array vacio
   - **Then:** Dropdown muestra "Sin resultados para 'xyzxyz123'"

3. Escape cierra sin cambiar valor
   - **Given:** Item K02.1 seleccionado, usuario empieza a escribir "K05" y el dropdown se abre
   - **When:** Presiona Escape
   - **Then:** Dropdown cierra, input vuelve a mostrar "K02.1 — Caries de la dentina" (valor previo restaurado)

4. Debounce — no spamea el API
   - **Given:** Usuario escribe "ca", "car", "cari", "carie", "caries" en rapida sucesion
   - **When:** Pasan 300ms tras el ultimo caracter
   - **Then:** Solo se hace 1 llamada al API con query "caries"

### Error Cases
1. Error de red durante busqueda
   - **Given:** Sin conexion
   - **When:** Usuario escribe 2+ caracteres y el fetch falla
   - **Then:** Dropdown muestra icono AlertCircle + "Error al buscar. Intenta de nuevo."

2. Componente disabled
   - **Given:** `disabled={true}` en las props
   - **When:** Usuario intenta hacer click en el input
   - **Then:** Input no recibe foco, cursor `not-allowed`, sin dropdown

---

## Acceptance Criteria

- [ ] Input con placeholder "Buscar diagnostico CIE-10..."
- [ ] Icono `Search` a la izquierda del input
- [ ] Busqueda NO se activa con menos de 2 caracteres (hint visible en dropdown)
- [ ] Debounce de exactamente 300ms antes de llamar al API
- [ ] Spinner de carga reemplaza el icono Search durante fetch
- [ ] Dropdown muestra hasta 10 resultados: codigo en `font-mono font-bold` + descripcion
- [ ] Highlighting de texto que coincide con el query
- [ ] Navegacion completa con Arrow Up/Down + Enter para seleccionar
- [ ] Escape cierra dropdown sin cambiar seleccion
- [ ] Click fuera del componente cierra dropdown
- [ ] Tab cierra dropdown y mueve foco al siguiente elemento
- [ ] Boton X visible cuando hay valor seleccionado; limpia con `onChange(null)`
- [ ] Cache de TanStack Query de 30 minutos para resultados identicos
- [ ] Estado de error inline en el dropdown (no toast)
- [ ] Estado "Sin resultados" cuando fetch retorna vacio
- [ ] ARIA completo: role="combobox", role="listbox", role="option", aria-expanded, aria-activedescendant
- [ ] Touch targets minimo 44px por item en tablet
- [ ] Funciona integrado con React Hook Form via Controller
- [ ] Textos en es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
