# Modal / Dialog — Design System Component Spec

## Overview

**Spec ID:** FE-DS-06

**Component:** `Modal`, `ConfirmModal`

**File:** `src/components/ui/modal.tsx`, `src/components/shared/confirm-dialog.tsx`

**Description:** Dialog overlay component for focused interactions, confirmations, and complex forms that require a dedicated UI surface without leaving the current page. Built on Radix UI Dialog primitive with DentalOS styling. Implements focus trap, scroll lock, and accessibility standards.

**Design System Ref:** `FE-DS-01` (§4.6)

---

## Props Table — `Modal`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `open` | `boolean` | — | Yes | Controls open/close state |
| `onClose` | `() => void` | — | Yes | Called when modal requests to close |
| `title` | `string` | — | Yes | Modal header title |
| `description` | `string` | — | No | Optional subtitle below title |
| `size` | `'sm' \| 'md' \| 'lg' \| 'full'` | `'md'` | No | Modal width |
| `footer` | `ReactNode` | — | No | Footer content (buttons) |
| `closeOnOverlay` | `boolean` | `true` | No | Close when overlay clicked |
| `closeOnEscape` | `boolean` | `true` | No | Close on Escape key |
| `showCloseButton` | `boolean` | `true` | No | Shows X button in header |
| `scrollBehavior` | `'inside' \| 'outside'` | `'inside'` | No | Whether body or overlay scrolls |
| `children` | `ReactNode` | — | Yes | Modal body content |
| `className` | `string` | — | No | Additional classes on modal panel |
| `isLoading` | `boolean` | `false` | No | Disables close and shows loading state |

## Props Table — `ConfirmModal`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `open` | `boolean` | — | Yes | Controls open/close state |
| `onClose` | `() => void` | — | Yes | Called on cancel or overlay click |
| `onConfirm` | `() => void` | — | Yes | Called when confirm button clicked |
| `title` | `string` | — | Yes | Dialog title |
| `message` | `string \| ReactNode` | — | Yes | Dialog body message |
| `confirmLabel` | `string` | `"Confirmar"` | No | Confirm button label |
| `cancelLabel` | `string` | `"Cancelar"` | No | Cancel button label |
| `variant` | `'default' \| 'danger'` | `'default'` | No | Confirm button color |
| `icon` | `ReactNode` | — | No | Icon above title |
| `isConfirming` | `boolean` | `false` | No | Loading state on confirm button |

---

## Sizes

| Size | Max Width | Use Case |
|------|-----------|---------|
| `sm` | `max-w-md` (448px) | Confirmations, simple alerts |
| `md` | `max-w-lg` (576px) | Standard forms (invite, add note) |
| `lg` | `max-w-2xl` (672px) | Complex forms, template editors, previews |
| `full` | `max-w-5xl` (90vw on smaller screens) | Document viewer, odontogram, image viewer |

---

## Visual Structure

```
+------ Overlay (bg-black/50 backdrop-blur-sm) ------+
|                                                     |
|   +------ Modal Panel (bg-white rounded-xl) ------+ |
|   | [Title]                                [X]     | |
|   | [Description] (optional)                       | |
|   +-------------------------------------------------+ |
|   | [Body content — scrollable]                    | |
|   |                                                 | |
|   +-------------------------------------------------+ |
|   | [Footer — buttons]                    border-t  | |
|   +-------- shadow-xl ---- z-50 --------------------+ |
|                                                     |
+-----------------------------------------------------+
```

---

## Overlay

```
fixed inset-0 bg-black/50 backdrop-blur-sm z-40
flex items-center justify-center p-4
```

**Mobile:** `p-0` (modal goes full-screen below 640px — see responsive section).

---

## Modal Panel

**Base classes:**
```
relative bg-white rounded-xl shadow-xl
w-full flex flex-col
max-h-[90vh]
```

**Width:** controlled by `size` prop (max-w-md, max-w-lg, max-w-2xl, max-w-5xl).

---

## Modal Header

**Structure:**
```
flex items-start justify-between p-6 border-b border-gray-200
```

- Title: `text-lg font-semibold text-gray-900`
- Description: `text-sm text-gray-500 mt-1`
- Close button (X): `Button` ghost sm, `w-8 h-8 p-0`, top-right corner, `aria-label="Cerrar diálogo"`

---

## Modal Body

```
flex-1 overflow-y-auto p-6
```

When `scrollBehavior="inside"`: body scrolls, header and footer stay fixed.

When `scrollBehavior="outside"`: entire modal scrolls within the overlay.

**Form modals:** Body contains the form. Footer has submit + cancel buttons. Body padding gives visual breathing room from header/footer borders.

---

## Modal Footer

```
flex items-center justify-end gap-3 p-4 border-t border-gray-200
```

**Convention:**
- Left-align: destructive action (rare)
- Right-align: Cancel (secondary) + Primary action

```tsx
<Modal
  title="Invitar miembro"
  footer={
    <div className="flex items-center justify-end gap-3">
      <Button variant="secondary" onClick={onClose}>Cancelar</Button>
      <Button variant="primary" type="submit" isLoading={isSubmitting}>
        Enviar invitación
      </Button>
    </div>
  }
>
  {/* form content */}
</Modal>
```

---

## Modal Types

### Default (content modal)

Free-form body content. Header + optional footer.

### Confirmation Modal (`ConfirmModal`)

Standardized layout for confirmation dialogs:

```
+------------------------------------------+
|              [X]                          |
|                                           |
|  [Icon — AlertTriangle, 24px, amber/red] |
|                                           |
|  Title (text-lg font-semibold)           |
|                                           |
|  Message (text-sm text-gray-600,         |
|  max-w-sm, centered or left)             |
|                                           |
+------------------------------------------+
|  [Cancelar]      [Confirmar / Eliminar]  |
+------------------------------------------+
```

**variant="default":** Confirm button is primary teal.
**variant="danger":** Confirm button is danger red.

```tsx
<ConfirmModal
  open={isOpen}
  onClose={onClose}
  onConfirm={handleDelete}
  title="Eliminar paciente"
  message="¿Estás seguro? Esta acción no se puede deshacer."
  confirmLabel="Eliminar"
  cancelLabel="Cancelar"
  variant="danger"
  icon={<AlertTriangle className="w-8 h-8 text-red-500" />}
  isConfirming={isDeleting}
/>
```

### Form Modal

Modal with a `<form>` tag wrapping the body + footer. Submit via footer button (type="submit"):

```tsx
<Modal
  title="Agregar cita"
  size="md"
  footer={
    <div className="flex gap-3 justify-end">
      <Button variant="secondary" onClick={onClose} type="button">Cancelar</Button>
      <Button variant="primary" type="submit" form="appointment-form" isLoading={isSubmitting}>
        Guardar cita
      </Button>
    </div>
  }
>
  <form id="appointment-form" onSubmit={handleSubmit(onSubmit)}>
    {/* fields */}
  </form>
</Modal>
```

---

## Animation

**Open:**
1. Overlay: `opacity 0 → 1`, 150ms ease-out
2. Panel: `opacity 0 → 1` + `scale 0.95 → 1`, 200ms ease-out, delayed 50ms

**Close:**
1. Panel: `opacity 1 → 0` + `scale 1 → 0.95`, 150ms ease-in
2. Overlay: `opacity 1 → 0`, 150ms ease-in

**Framer Motion variant:**
```tsx
const panelVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, scale: 0.95, transition: { duration: 0.15 } },
}
```

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal becomes full-screen: `fixed inset-0 rounded-none`. Overlay not shown (modal IS the full screen). Close button always visible. |
| Tablet (640-1024px) | Standard modal with overlay. All sizes apply. |
| Desktop (> 1024px) | Standard modal. `full` size uses 90vw. |

**Mobile full-screen detail:**
- Header: fixed at top
- Body: scrollable, fills remaining height
- Footer: fixed at bottom (`fixed bottom-0 left-0 right-0`)

---

## Focus Trap

Radix Dialog handles focus trap automatically. On open:
1. Focus moves to first focusable element inside modal (or `autoFocus` element)
2. Tab cycles only through focusable elements inside the modal
3. On close, focus returns to the trigger element that opened the modal

---

## Scroll Lock

When a modal is open, `overflow: hidden` is applied to `<body>` to prevent background scroll. Radix Dialog handles this via `DialogContent`.

**Scrollbar compensation:** `padding-right: [scrollbar-width]` added to body to prevent layout shift when scroll is removed.

---

## Accessibility

- **Role:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby="[title-id]"`, `aria-describedby="[desc-id]"` (if description present)
- **Focus trap:** Radix Dialog primitive
- **Close button:** `aria-label="Cerrar diálogo"`
- **Keyboard:** Escape key closes (when `closeOnEscape={true}`)
- **Screen reader:** Title announced on open. `aria-live="polite"` for dynamic content changes inside modal.
- **Language:** All labels es-419

---

## Stacking

When multiple modals are needed (rare), each subsequent modal increments z-index by 10:
- Modal 1: `z-50`
- Modal 2: `z-60`
- Modal 3: `z-70`

Avoid more than 2 stacked modals. Prefer step-based single modals.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
