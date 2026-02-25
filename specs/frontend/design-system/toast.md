# Toast / Notification — Design System Component Spec

## Overview

**Spec ID:** FE-DS-07

**Component:** `Toast`, `useToast`

**File:** `src/components/ui/toast.tsx`, `src/lib/toast.ts`

**Description:** Non-blocking notification component for feedback on user actions. Implemented using the `sonner` library (shadcn/ui recommended). Toasts appear in the top-right corner, auto-dismiss after configurable duration, support action buttons, and stack up to 3 visible at a time.

**Design System Ref:** `FE-DS-01` (§4.7)

---

## Toast Types

| Type | Icon | Accent Color | Auto-Dismiss | Use Case |
|------|------|-------------|--------------|---------|
| `success` | `CheckCircle2` | `green-500` | 5 seconds | Saved, created, sent, confirmed |
| `error` | `XCircle` | `red-500` | Persistent | Failed API call, validation error, access denied |
| `warning` | `AlertTriangle` | `amber-500` | 8 seconds | Plan limit approaching, missing config |
| `info` | `Info` | `blue-500` | 5 seconds | Informational notices, tips |
| `loading` | `Loader2 animate-spin` | `gray-400` | Persistent (update to resolve) | Long-running operations |
| `default` | — | `gray-800` | 5 seconds | Generic messages without semantic type |

---

## Props — `toast()` function

The primary API is a function call, not a component directly:

```typescript
toast.success(message: string, options?: ToastOptions)
toast.error(message: string, options?: ToastOptions)
toast.warning(message: string, options?: ToastOptions)
toast.info(message: string, options?: ToastOptions)
toast.loading(message: string, options?: ToastOptions)
```

### ToastOptions

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `description` | `string` | — | Secondary text below the title |
| `duration` | `number` | Type default | Duration in ms (0 = persistent) |
| `action` | `{ label: string, onClick: () => void }` | — | Action button inside toast |
| `id` | `string` | Auto-generated | Unique ID (used to update or dismiss programmatically) |
| `onDismiss` | `() => void` | — | Callback when toast is dismissed |
| `position` | `ToastPosition` | `'top-right'` | Override global position |
| `important` | `boolean` | `false` | Error-level toasts are always important |

---

## Visual Structure

```
+-----------------------------------------------+
| [Icon]  Title text                        [X] |
|         Description text (optional)           |
|                           [Action button]     |
+-----------------------------------------------+
```

**Dimensions:**
- Width: 356px fixed on desktop. Full width minus 16px margin on mobile.
- Min-height: 64px
- Padding: `p-4`

**Background:** `bg-white border border-gray-200 shadow-lg rounded-xl`

**Left accent:** 4px left border colored by type (e.g., `border-l-4 border-green-500`).

---

## Component Structure Detail

### Icon

| Type | Icon | Color |
|------|------|-------|
| success | `CheckCircle2` | `text-green-500` |
| error | `XCircle` | `text-red-500` |
| warning | `AlertTriangle` | `text-amber-500` |
| info | `Info` | `text-blue-500` |
| loading | `Loader2 animate-spin` | `text-gray-400` |

Icon size: `w-5 h-5` (20px).

### Title Text

`text-sm font-semibold text-gray-900`

### Description Text (optional)

`text-xs text-gray-500 mt-0.5`

Appears below title. Useful for adding context or error codes.

### Dismiss Button (X)

- Top-right corner of toast
- `X` icon, 14px, `text-gray-400 hover:text-gray-600`
- `aria-label="Cerrar notificación"`
- Error toasts always show dismiss button (they are persistent)
- Success/info/warning show it on hover only

### Action Button (optional)

When `action` option is provided:

```
+------- toast -------+
| ✓ Paciente guardado |
|   [Ver perfil →]    |
+---------------------+
```

- `action.label`: `text-xs font-medium text-teal-700 hover:text-teal-900`
- Rendered as `<button>` (not `<a>`) to prevent navigation side effects
- Clicking action calls `action.onClick()` AND dismisses the toast

**Undo action pattern (common):**
```typescript
const id = toast.success('Recordatorio eliminado', {
  action: {
    label: 'Deshacer',
    onClick: () => { restoreReminder(); toast.dismiss(id) },
  },
  duration: 8000, // longer to allow time for undo
})
```

---

## Position

**Default:** `top-right` — `fixed top-4 right-4 z-[100]`

All toasts stack in a vertical column from the position. Gap between toasts: `8px`.

On mobile (< 640px): `top-4 left-4 right-4` (full width, centered).

---

## Stacking Behavior

- **Maximum visible:** 3 toasts at once
- When a 4th toast arrives, the oldest visible one is removed (or queued)
- Newer toasts appear at the top, pushing older ones down
- `sonner` handles stacking with a collapse effect (older toasts appear smaller behind the top one)

**sonner stack visual:**
```
Toast 3 (newest, full size)
  Toast 2 (slightly scaled down, partially visible behind Toast 3)
    Toast 1 (oldest, smallest, mostly hidden)
```

Hover over the stack → all expand to full size.

---

## Auto-dismiss

| Type | Duration |
|------|---------|
| success | 5000ms |
| info | 5000ms |
| warning | 8000ms |
| error | 0 (persistent) |
| loading | 0 (persistent, update manually) |

**Progress bar** (optional): thin bar at bottom of toast that depletes over duration. Enable via `sonner` `progressBar` option.

---

## Loading Toast Pattern

For long-running operations, use loading toast updated to success/error:

```typescript
const id = toast.loading('Generando RIPS...')

try {
  await generateRips()
  toast.success('RIPS generado. Descarga disponible.', {
    id, // replaces the loading toast
    action: { label: 'Descargar', onClick: downloadRips },
  })
} catch (e) {
  toast.error('Error al generar RIPS. Intenta de nuevo.', { id })
}
```

---

## Animation

**Enter (slide in from right):**
```css
@keyframes slide-in {
  from { transform: translateX(calc(100% + 1rem)); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}
animation: slide-in 0.25s ease-out;
```

**Exit (fade and slide out):**
```css
@keyframes slide-out {
  from { transform: translateX(0); opacity: 1; }
  to   { transform: translateX(calc(100% + 1rem)); opacity: 0; }
}
animation: slide-out 0.2s ease-in;
```

**Mobile (slide down from top):**
```css
from { transform: translateY(-100%); opacity: 0; }
to   { transform: translateY(0); opacity: 1; }
```

**Reduced motion:** When `prefers-reduced-motion: reduce`, skip translate animations. Use only opacity transitions.

---

## Global Configuration (Toaster)

Place `<Toaster />` in the root layout:

```tsx
// src/app/layout.tsx
import { Toaster } from 'sonner'

export default function RootLayout({ children }) {
  return (
    <html lang="es-419">
      <body>
        {children}
        <Toaster
          position="top-right"
          richColors
          expand
          visibleToasts={3}
          duration={5000}
          closeButton
          toastOptions={{
            classNames: {
              toast: 'bg-white border border-gray-200 shadow-lg rounded-xl font-sans',
              title: 'text-sm font-semibold text-gray-900',
              description: 'text-xs text-gray-500',
            },
          }}
        />
      </body>
    </html>
  )
}
```

---

## Common Toast Messages (es-419)

**Success:**
- "Configuración guardada"
- "Paciente registrado exitosamente"
- "Invitación enviada a [email]"
- "Cita agendada para el [fecha]"
- "Registro clínico guardado"
- "Factura generada"

**Error:**
- "No se pudo guardar. Intenta de nuevo."
- "Sin conexión. Verifica tu red."
- "Sesión expirada. Inicia sesión nuevamente."
- "No tienes permiso para realizar esta acción."
- "Error del servidor (500). Contacta soporte."

**Warning:**
- "Estás cerca del límite de [X] pacientes"
- "WhatsApp no está configurado. [Configurar]"
- "Cambios sin guardar. Guarda antes de salir."

**Info:**
- "La exportación está siendo preparada."
- "Invitación pendiente de aceptación."

---

## Accessibility

- **Role:** `role="status"` (success, info, warning). `role="alert"` (error — more urgent announcement).
- **aria-live:** `aria-live="polite"` for success/info. `aria-live="assertive"` for error.
- **Dismiss button:** `aria-label="Cerrar notificación"`.
- **Screen reader:** Title + description are announced on appearance.
- **Keyboard:** Dismiss button is focusable. Action button is focusable. Tab moves to toast content when visible. Escape does not close toasts (they're non-modal).
- **Language:** All messages in Spanish es-419.

---

## Usage Examples

```typescript
import { toast } from 'sonner'

// Simple success
toast.success('Paciente guardado exitosamente')

// Error with description
toast.error('No se pudo enviar la invitación', {
  description: 'El correo electrónico ya existe en el sistema',
})

// Warning with action
toast.warning('Estás cerca de tu límite de pacientes (48/50)', {
  action: { label: 'Ver planes', onClick: () => router.push('/settings/plan') },
  duration: 10000,
})

// Loading → success pattern
const id = toast.loading('Guardando registro clínico...')
await saveRecord()
toast.success('Registro guardado', { id })

// Info with undo
const id = toast.success('Recordatorio eliminado', {
  duration: 8000,
  action: { label: 'Deshacer', onClick: () => undoDelete(id) },
})
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
