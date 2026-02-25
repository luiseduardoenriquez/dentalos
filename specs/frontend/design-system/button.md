# Button — Design System Component Spec

## Overview

**Spec ID:** FE-DS-02

**Component:** `Button`

**File:** `src/components/ui/button.tsx`

**Description:** Primary interactive element for triggering actions. Extends shadcn/ui Button with DentalOS variants and a clinical loading state. Used across every page in the application.

**Design System Ref:** `FE-DS-01` (§4.1)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `variant` | `'primary' \| 'secondary' \| 'outline' \| 'ghost' \| 'danger'` | `'primary'` | No | Visual style variant |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | No | Button height and padding |
| `isLoading` | `boolean` | `false` | No | Shows spinner, disables interaction |
| `disabled` | `boolean` | `false` | No | Disables button without loading state |
| `iconLeft` | `ReactNode` | — | No | Icon rendered before label text |
| `iconRight` | `ReactNode` | — | No | Icon rendered after label text |
| `fullWidth` | `boolean` | `false` | No | Sets `w-full` on the button |
| `type` | `'button' \| 'submit' \| 'reset'` | `'button'` | No | HTML button type |
| `onClick` | `(e: MouseEvent) => void` | — | No | Click handler |
| `className` | `string` | — | No | Additional Tailwind classes |
| `children` | `ReactNode` | — | Yes | Button label content |
| `asChild` | `boolean` | `false` | No | Renders as child element (Radix slot) |

---

## Variants

### Primary

Used for main CTAs: Save, Create, Confirm, Submit.

```tsx
<Button variant="primary">Guardar paciente</Button>
```

| State | Classes |
|-------|---------|
| Default | `bg-teal-700 text-white hover:bg-teal-800` |
| Active | `active:bg-teal-900` |
| Focus | `focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2` |
| Disabled | `disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed` |
| Loading | `bg-teal-700 cursor-wait` + spinner |

### Secondary

Used for Cancel, Back, and secondary actions.

```tsx
<Button variant="secondary">Cancelar</Button>
```

| State | Classes |
|-------|---------|
| Default | `bg-gray-100 text-gray-700 hover:bg-gray-200` |
| Active | `active:bg-gray-300` |
| Disabled | `disabled:bg-gray-50 disabled:text-gray-300` |

### Outline

Used for tertiary actions, filter toggles, and less prominent CTAs.

```tsx
<Button variant="outline">Ver detalles</Button>
```

| State | Classes |
|-------|---------|
| Default | `border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50` |
| Active | `active:bg-gray-100` |

### Ghost

Used for icon-adjacent text buttons, toolbar buttons, minimal-emphasis actions.

```tsx
<Button variant="ghost" iconLeft={<Pencil className="w-4 h-4" />}>
  Editar
</Button>
```

| State | Classes |
|-------|---------|
| Default | `bg-transparent text-gray-600 hover:bg-gray-100 hover:text-gray-900` |
| Active | `active:bg-gray-200` |

### Danger

Used for destructive actions: Delete, Deactivate, Remove.

```tsx
<Button variant="danger">Eliminar paciente</Button>
```

| State | Classes |
|-------|---------|
| Default | `bg-red-600 text-white hover:bg-red-700` |
| Active | `active:bg-red-800` |
| Disabled | `disabled:bg-red-200` |

---

## Sizes

| Size | Height | Horizontal Padding | Font Size | Icon Size | Min Touch |
|------|--------|--------------------|-----------|-----------|-----------|
| `sm` | `h-8` (32px) | `px-3` | `text-sm` | `w-4 h-4` | 44px wrapper |
| `md` | `h-10` (40px) | `px-4` | `text-sm` | `w-4 h-4` | Natural |
| `lg` | `h-12` (48px) | `px-6` | `text-base` | `w-5 h-5` | Natural |

**Touch target note:** `sm` buttons on mobile receive an invisible 44px touch target via `::after` pseudo-element or padding wrapper. This ensures WCAG 2.5.5 compliance on tablet/mobile.

---

## States

### Loading State

When `isLoading={true}`:
- Button text is replaced by: `<Loader2 className="w-4 h-4 animate-spin" />` + optional loading text
- Button is `disabled` and `aria-busy="true"`
- Width is preserved (no layout shift) via min-width matching original text width

```tsx
<Button variant="primary" isLoading={isSaving}>
  {isSaving ? "Guardando..." : "Guardar"}
</Button>
```

### Disabled State

When `disabled={true}`:
- Opacity reduced
- `cursor-not-allowed`
- `pointer-events-none` equivalent
- `aria-disabled="true"` on the button element

### Icon-Only Button

Use `variant="ghost"` or `variant="outline"` with a single icon child and `aria-label`:

```tsx
<Button
  variant="ghost"
  size="sm"
  aria-label="Eliminar registro"
  className="w-8 h-8 p-0"
>
  <Trash2 className="w-4 h-4" />
</Button>
```

Icon-only buttons always need an `aria-label`.

---

## Full-Width

```tsx
<Button variant="primary" fullWidth>
  Iniciar sesión
</Button>
```

Renders with `w-full` class. Used in login forms, mobile CTAs, modal footers.

---

## Button Groups

Adjacent buttons use `gap-2` or `gap-3`:

```tsx
<div className="flex items-center gap-2">
  <Button variant="secondary">Cancelar</Button>
  <Button variant="primary">Guardar cambios</Button>
</div>
```

**Convention:** In modal footers and form actions, Secondary always on the left, Primary on the right.

---

## Accessibility

- **Role:** `role="button"` (native `<button>` element, no override needed)
- **Focus visible:** `focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2` on all variants
- **Keyboard:** Enter and Space both activate the button
- **Screen reader:** Use `aria-label` for icon-only buttons. Loading state adds `aria-busy="true"` and `aria-label="Guardando..."` (or passed `loadingLabel` prop)
- **Disabled ARIA:** `aria-disabled="true"` rather than `disabled` when button must remain focusable (e.g., with a tooltip explaining why it's disabled)
- **Language:** All button text in Spanish (es-419)

---

## Responsive Behavior

- Buttons maintain their defined sizes across breakpoints unless `fullWidth` is set
- On mobile (`< 640px`), primary CTAs in page headers become full-width
- Touch target minimum: 44x44px enforced via CSS on all sizes
- `sm` size uses padding wrapper on mobile: `py-2 px-3` minimum

---

## Design Tokens

```css
/* Primary */
--btn-primary-bg: theme('colors.teal.700');
--btn-primary-hover: theme('colors.teal.800');
--btn-primary-text: white;

/* Secondary */
--btn-secondary-bg: theme('colors.gray.100');
--btn-secondary-hover: theme('colors.gray.200');
--btn-secondary-text: theme('colors.gray.700');

/* Danger */
--btn-danger-bg: theme('colors.red.600');
--btn-danger-hover: theme('colors.red.700');
```

**Border radius:** `rounded-lg` (8px) on all sizes.

**Transition:** `transition-colors duration-150 ease-in-out`

---

## Implementation

```tsx
// src/components/ui/button.tsx
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  // Base classes
  'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-teal-700 text-white hover:bg-teal-800 focus-visible:ring-teal-600',
        secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 focus-visible:ring-gray-400',
        outline: 'border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50 focus-visible:ring-gray-400',
        ghost: 'bg-transparent text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus-visible:ring-gray-400',
        danger: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
  iconLeft?: React.ReactNode
  iconRight?: React.ReactNode
  fullWidth?: boolean
}

export function Button({
  variant,
  size,
  isLoading,
  iconLeft,
  iconRight,
  fullWidth,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        buttonVariants({ variant, size }),
        fullWidth && 'w-full',
        className
      )}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        iconLeft
      )}
      {children}
      {!isLoading && iconRight}
    </button>
  )
}
```

---

## Usage Examples

```tsx
// Primary save action
<Button variant="primary" onClick={handleSave} isLoading={isSaving}>
  {isSaving ? "Guardando..." : "Guardar paciente"}
</Button>

// Cancel button in modal footer
<Button variant="secondary" onClick={onClose}>
  Cancelar
</Button>

// Danger delete
<Button variant="danger" iconLeft={<Trash2 className="w-4 h-4" />}>
  Eliminar registro
</Button>

// Full-width in form
<Button variant="primary" fullWidth type="submit">
  Iniciar sesión
</Button>

// Outline with right icon
<Button variant="outline" iconRight={<ChevronRight className="w-4 h-4" />}>
  Ver más detalles
</Button>

// Ghost icon-only
<Button variant="ghost" size="sm" aria-label="Editar" className="w-8 h-8 p-0">
  <Pencil className="w-4 h-4" />
</Button>
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
