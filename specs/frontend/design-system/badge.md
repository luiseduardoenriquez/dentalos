# Badge / Pill — Design System Component Spec

## Overview

**Spec ID:** FE-DS-11

**Component:** `Badge`, `StatusDot`

**File:** `src/components/ui/badge.tsx`

**Description:** Compact label component for displaying status, category, role, or condition information. Covers three visual variants: solid-background status pills, outline badges, and dot-only indicators. Includes domain-specific mappings for appointment statuses, clinical conditions, user roles, and billing states.

**Design System Ref:** `FE-DS-01` (§4.8, §1.2)

---

## Props Table — `Badge`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `variant` | `'status' \| 'outline' \| 'dot'` | `'status'` | No | Visual style |
| `color` | `BadgeColor` | — | No | Color override (bypasses status mapping) |
| `status` | `AppointmentStatus \| BillingStatus \| UserStatus \| ConditionCode` | — | No | Semantic status (auto-maps to color) |
| `size` | `'sm' \| 'md'` | `'md'` | No | Badge size |
| `dot` | `boolean` | `false` | No | Show dot indicator on status variant |
| `children` | `ReactNode` | — | Yes | Badge label text |
| `className` | `string` | — | No | Additional Tailwind classes |

## Props Table — `StatusDot`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `status` | `string` | — | Status key for color mapping |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Dot size |

---

## BadgeColor Type

```typescript
type BadgeColor =
  | 'green' | 'teal' | 'blue' | 'purple' | 'amber' | 'orange'
  | 'red' | 'gray' | 'indigo' | 'pink' | 'cyan' | 'lime'
```

---

## Sizes

| Size | Height | Padding | Font | Use Case |
|------|--------|---------|------|---------|
| `sm` | `h-5` (20px) | `px-2` | `text-xs` | Table cells, compact lists, condition icons |
| `md` | `h-6` (24px) | `px-2.5` | `text-sm` | Standard use, role badges, status pills |

**Border radius:** `rounded-sm` (4px) — this is the DentalOS badge radius, not full pill.

Exception: Role badges and some status badges use `rounded-full` for pill shape.

---

## Variant: Status (default)

Solid background with matching text color. The most common badge type.

**Base classes:**
```
inline-flex items-center gap-1.5
font-medium whitespace-nowrap
rounded-sm
```

**Color mapping table (Status variant):**

| Color | Background | Text | Dot |
|-------|-----------|------|-----|
| green | `bg-green-100` | `text-green-700` | `bg-green-500` |
| teal | `bg-teal-100` | `text-teal-700` | `bg-teal-500` |
| blue | `bg-blue-100` | `text-blue-700` | `bg-blue-500` |
| purple | `bg-purple-100` | `text-purple-700` | `bg-purple-500` |
| amber | `bg-amber-100` | `text-amber-700` | `bg-amber-500` |
| orange | `bg-orange-100` | `text-orange-700` | `bg-orange-500` |
| red | `bg-red-100` | `text-red-700` | `bg-red-500` |
| gray | `bg-gray-100` | `text-gray-600` | `bg-gray-400` |
| indigo | `bg-indigo-100` | `text-indigo-700` | `bg-indigo-500` |
| pink | `bg-pink-100` | `text-pink-700` | `bg-pink-500` |
| cyan | `bg-cyan-100` | `text-cyan-700` | `bg-cyan-500` |
| lime | `bg-lime-100` | `text-lime-700` | `bg-lime-500` |

---

## Variant: Outline

Border only, transparent background. Used for secondary categorization.

```
border border-current bg-transparent
```

```tsx
<Badge variant="outline" color="blue">Incorporada</Badge>
<Badge variant="outline" color="purple">Personalizada</Badge>
```

---

## Variant: Dot

Small circle only, no text label. Used as inline status indicator (e.g., online status, connection indicator).

```
w-2 h-2 rounded-full bg-[color]
```

```tsx
<StatusDot status="connected" size="md" />
```

---

## Domain Status Mappings

### Appointment Status

| Status | Label | Color |
|--------|-------|-------|
| `programada` | Programada | blue |
| `confirmada` | Confirmada | teal |
| `en_progreso` | En progreso | amber |
| `completada` | Completada | green |
| `cancelada` | Cancelada | gray |
| `no_asistio` | No asistió | orange |
| `reagendada` | Reagendada | purple |

```tsx
<Badge status="confirmada">Confirmada</Badge>
// → bg-teal-100 text-teal-700 with dot
```

### Billing / Invoice Status

| Status | Label | Color |
|--------|-------|-------|
| `borrador` | Borrador | gray |
| `pendiente` | Pendiente | amber |
| `pagada` | Pagada | green |
| `vencida` | Vencida | red |
| `anulada` | Anulada | gray |
| `parcial` | Pago parcial | orange |

### User / Team Member Status

| Status | Label | Color |
|--------|-------|-------|
| `active` | Activo | green |
| `pending` | Pendiente | amber |
| `inactive` | Inactivo | gray |

### User Roles

| Role | Label | Color | Shape |
|------|-------|-------|-------|
| `clinic_owner` | Propietario | purple | `rounded-full` |
| `doctor` | Doctor | blue | `rounded-full` |
| `assistant` | Asistente | teal | `rounded-full` |
| `receptionist` | Recepcionista | amber | `rounded-full` |

### Clinical Condition Badges (Odontogram)

Maps dental conditions to their design system colors (from FE-DS-01 §1.2):

| Condition | Label | Color |
|-----------|-------|-------|
| healthy | Sano | green |
| caries | Caries | red |
| restoration | Restauración | blue |
| extraction | Extracción | gray |
| crown | Corona | amber (custom `bg-yellow-100 text-yellow-700`) |
| endodontic | Endodoncia | purple |
| implant | Implante | cyan |
| fracture | Fractura | orange |
| sealant | Sellante | lime |
| fluorosis | Fluorosis | pink |
| temporary | Temporal | amber |
| prosthesis | Prótesis | indigo |

```tsx
<Badge status="caries" size="sm">Caries</Badge>
// → bg-red-100 text-red-700

<Badge status="endodontic" size="sm">Endodoncia</Badge>
// → bg-purple-100 text-purple-700
```

### Integration Status

| Status | Label | Color |
|--------|-------|-------|
| `connected` | Conectado | green |
| `disconnected` | Desconectado | gray |
| `error` | Error | red |
| `partial` | Parcial | amber |

### Template Type

| Type | Label | Color | Variant |
|------|-------|-------|---------|
| `built_in` | Incorporada | blue | outline |
| `custom` | Personalizada | purple | outline |

---

## Dot Indicator on Status Badge

When `dot={true}`:

```
● [Label text]
```

Dot: `w-1.5 h-1.5 rounded-full` colored by the badge color mapping.

Used for badges where the dot adds visual scannability (appointment status in calendar sidebars).

---

## Usage Examples

```tsx
// Simple appointment status
<Badge status="confirmada" dot>Confirmada</Badge>

// Role badge (pill shape)
<Badge color="blue" className="rounded-full">Doctor</Badge>

// Billing status
<Badge status="vencida">Vencida</Badge>

// Clinical condition
<Badge status="caries" size="sm">Caries</Badge>

// Integration status (outline)
<Badge variant="outline" color="green">Conectado</Badge>

// Template type (outline)
<Badge variant="outline" color="blue">Incorporada</Badge>

// Status dot only (sidebar notification)
<StatusDot status="connected" size="sm" />

// Custom color
<Badge color="indigo" size="sm">RIPS</Badge>
```

---

## StatusDot Component

Standalone dot indicator for use inline or as overlay on other elements (e.g., avatar online indicator, integration card connection dot):

```typescript
interface StatusDotProps {
  status: 'online' | 'offline' | 'busy' | 'connected' | 'disconnected' | string
  size: 'sm' | 'md' | 'lg'
}
```

| Size | Dimensions | Use Case |
|------|-----------|---------|
| `sm` | `w-2 h-2` (8px) | Inline text, compact indicators |
| `md` | `w-2.5 h-2.5` (10px) | Integration cards, sidebar |
| `lg` | `w-3 h-3` (12px) | Prominent status indicators |

**Status mapping:**

| Status | Color |
|--------|-------|
| online | `bg-green-500` |
| offline | `bg-gray-400` |
| busy | `bg-red-500` |
| connected | `bg-green-500` |
| disconnected | `bg-gray-400` |

---

## Accessibility

- **Role:** No special role needed; badges are presentational
- **Screen reader:** When badge conveys meaningful status, parent element should have `aria-label` including the status. E.g., `<tr aria-label="Cita de María García — Estado: Confirmada">`
- **Color alone:** Badge text must not rely solely on color to convey meaning. The text label is always required (except `StatusDot` which is supplementary).
- **Contrast:** All color combinations meet WCAG AA: 4.5:1 for text-sm, 3:1 for larger or bolded text.

---

## Implementation

```tsx
// src/components/ui/badge.tsx

const badgeColors = {
  green: 'bg-green-100 text-green-700',
  teal: 'bg-teal-100 text-teal-700',
  blue: 'bg-blue-100 text-blue-700',
  // ...
}

const statusMap: Record<string, BadgeColor> = {
  confirmada: 'teal',
  programada: 'blue',
  completada: 'green',
  cancelada: 'gray',
  vencida: 'red',
  caries: 'red',
  endodontic: 'purple',
  // ...
}

export function Badge({ variant = 'status', color, status, size = 'md', dot, children, className }) {
  const resolvedColor = color ?? (status ? statusMap[status] : 'gray')
  const colorClasses = variant === 'outline'
    ? `border border-current bg-transparent text-${resolvedColor}-700`
    : badgeColors[resolvedColor]

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 font-medium whitespace-nowrap rounded-sm',
      size === 'sm' ? 'h-5 px-2 text-xs' : 'h-6 px-2.5 text-sm',
      colorClasses,
      className
    )}>
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full', `bg-${resolvedColor}-500`)} />}
      {children}
    </span>
  )
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec — full domain status mappings |
