# Card — Design System Component Spec

## Overview

**Spec ID:** FE-DS-10

**Component:** `Card`, `CardHeader`, `CardBody`, `CardFooter`

**File:** `src/components/ui/card.tsx`

**Description:** Container component providing visual grouping, elevation, and sectioned layout for content blocks. Used extensively across DentalOS for stat widgets, patient summaries, appointment blocks, settings sections, plan comparisons, and form containers. Extends shadcn/ui Card with clinical-specific variants.

**Design System Ref:** `FE-DS-01` (§4.4)

---

## Props Table — `Card`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `variant` | `'default' \| 'elevated' \| 'outlined' \| 'interactive' \| 'clinical'` | `'default'` | No | Visual style |
| `padding` | `'sm' \| 'md' \| 'none'` | `'md'` | No | Internal padding size |
| `onClick` | `() => void` | — | No | Makes card interactive (interactive variant) |
| `className` | `string` | — | No | Additional Tailwind classes |
| `children` | `ReactNode` | — | Yes | Card content |
| `asChild` | `boolean` | `false` | No | Render as child element |

## Props Table — `CardHeader`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | `string` | — | Card title text |
| `description` | `string` | — | Optional subtitle |
| `actions` | `ReactNode` | — | Right-aligned actions (buttons, menus) |
| `icon` | `ReactNode` | — | Optional icon before title |
| `className` | `string` | — | Additional classes |

## Props Table — `CardFooter`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `justify` | `'left' \| 'right' \| 'between'` | `'right'` | Button alignment |
| `divided` | `boolean` | `true` | Show top border separator |
| `className` | `string` | — | Additional classes |

---

## Variants

### Default

Standard content card. Used for settings sections, form containers, dashboard content.

```
bg-white shadow-sm rounded-xl border-0
```

```tsx
<Card variant="default">
  <CardHeader title="Información de la clínica" />
  <CardBody>...</CardBody>
  <CardFooter>
    <Button variant="primary">Guardar</Button>
  </CardFooter>
</Card>
```

### Elevated

Stronger shadow for prominent cards like stat widgets or modals-as-cards.

```
bg-white shadow-md rounded-xl border-0
```

Used for: Dashboard KPI widgets, current plan card, featured content.

```tsx
<Card variant="elevated">
  <CardBody>
    <p className="text-3xl font-bold">243</p>
    <p className="text-sm text-gray-500">Pacientes activos</p>
  </CardBody>
</Card>
```

### Outlined

Border only, no shadow. Use in dense layouts to reduce visual noise.

```
bg-white border border-gray-200 rounded-xl shadow-none
```

Used for: Plan comparison cards, list items inside other cards, secondary info boxes.

### Interactive

Clickable card. Hover elevates shadow, cursor pointer. Used for patient cards in search results, appointment blocks, navigation cards.

```
bg-white shadow-sm rounded-xl border-0
cursor-pointer
hover:shadow-md transition-shadow duration-200
focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2
active:scale-[0.99] transition-transform
```

```tsx
<Card variant="interactive" onClick={() => router.push(`/pacientes/${patient.id}`)}>
  <CardBody>
    <div className="flex items-center gap-3">
      <Avatar name={patient.nombre} />
      <div>
        <p className="font-medium">{patient.nombre}</p>
        <p className="text-sm text-gray-500">Última visita: hace 3 días</p>
      </div>
    </div>
  </CardBody>
</Card>
```

### Clinical

Card with a left border accent colored by clinical status. Used for treatment plan items, appointment cards, diagnosis items.

```
bg-white shadow-sm rounded-xl
border-l-4 border-[statusColor]
```

**Status colors for left border:**

| Status | Color |
|--------|-------|
| active / confirmed | `border-teal-500` |
| pending | `border-amber-500` |
| completed | `border-green-500` |
| cancelled | `border-red-500` |
| draft | `border-gray-300` |

```tsx
<Card variant="clinical" className="border-l-4 border-teal-500">
  <CardBody>
    <Badge status="en_progreso" />
    <p className="font-medium mt-1">Plan de tratamiento — Implante superior</p>
  </CardBody>
</Card>
```

---

## Padding Sizes

| Size | Padding | Use Case |
|------|---------|---------|
| `none` | `p-0` | Card wrapping image or full-bleed content |
| `sm` | `p-4` (16px) | Compact cards, mobile, secondary info |
| `md` | `p-6` (24px) | Default — settings sections, forms |

---

## Structural Subcomponents

### CardHeader

```
+------------------------------------------------+
| [Icon] [Title text]           [Actions area]  |
| [Description text]                            |
+------------------------------------------------+
```

**Classes:**
```
flex items-start justify-between
px-6 pt-6 pb-4 (if followed by CardBody)
or px-6 py-5 border-b border-gray-200 (if divided variant)
```

**Title:** `text-lg font-semibold text-gray-900`
**Description:** `text-sm text-gray-500 mt-0.5`
**Icon:** `w-5 h-5 text-gray-500` before title, `gap-2`
**Actions:** right-aligned slot, typically icon buttons or a secondary button

**Divided variant** (when `divided={true}`): Header has bottom border separating it from the body.

### CardBody

```
flex-1 px-6 py-4
```

Primary content area. Scrollable if combined with max-height on parent.

### CardFooter

```
+------------------------------------------------+
| border-t border-gray-200 (if divided)         |
| px-6 py-4                                     |
| flex items-center justify-[end|start|between] |
| gap-3                                         |
+------------------------------------------------+
```

Contains action buttons. `justify="between"` used when there's a secondary left action + primary right action.

---

## Compound Usage Examples

### Settings Section Card

```tsx
<Card variant="default">
  <CardHeader
    title="Información de la clínica"
    description="Nombre, dirección y datos de contacto"
    actions={
      isDirty && <span className="w-2 h-2 rounded-full bg-amber-500" />
    }
  />
  <CardBody>
    <div className="grid grid-cols-2 gap-4">
      <Input label="Nombre de la clínica" {...register('nombre')} />
      <Input label="NIT" {...register('nit')} />
      {/* more fields */}
    </div>
  </CardBody>
  <CardFooter>
    <Button variant="primary" isLoading={isSaving}>
      Guardar
    </Button>
  </CardFooter>
</Card>
```

### Dashboard KPI Card

```tsx
<Card variant="elevated">
  <CardBody>
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-gray-500">Pacientes este mes</p>
        <p className="text-3xl font-bold text-gray-900 mt-1">47</p>
        <p className="text-xs text-green-600 mt-1">↑ 12% vs. mes anterior</p>
      </div>
      <div className="p-2 bg-teal-50 rounded-lg">
        <Users className="w-6 h-6 text-teal-600" />
      </div>
    </div>
  </CardBody>
</Card>
```

### Plan Comparison Card (Outlined + Interactive)

```tsx
<Card
  variant={isCurrentPlan ? 'default' : 'outlined'}
  className={isCurrentPlan ? 'ring-2 ring-teal-600' : ''}
>
  <CardBody>
    <div className="text-center">
      <Badge>{plan.name}</Badge>
      <p className="text-3xl font-bold mt-2">${plan.price}</p>
      <p className="text-sm text-gray-500">/ doctor / mes</p>
    </div>
    <ul className="mt-4 space-y-2">
      {plan.features.map(f => (
        <li key={f.key} className="flex items-center gap-2 text-sm">
          {f.included ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <X className="w-4 h-4 text-gray-300" />
          )}
          <span className={f.included ? 'text-gray-700' : 'text-gray-400'}>{f.label}</span>
        </li>
      ))}
    </ul>
  </CardBody>
  <CardFooter>
    <Button variant={isCurrentPlan ? 'outline' : 'primary'} fullWidth disabled={isCurrentPlan}>
      {isCurrentPlan ? 'Plan actual' : `Actualizar a ${plan.name}`}
    </Button>
  </CardFooter>
</Card>
```

### Patient Summary Card (Interactive)

```tsx
<Card variant="interactive" onClick={() => router.push(`/pacientes/${patient.id}`)}>
  <CardBody padding="sm">
    <div className="flex items-center gap-3">
      <Avatar size="md" name={patient.nombre_completo} src={patient.foto_url} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate">{patient.nombre_completo}</p>
        <p className="text-xs text-gray-500">
          {patient.edad} años · {patient.numero_documento}
        </p>
      </div>
      <Badge status="active" size="sm" />
    </div>
  </CardBody>
</Card>
```

---

## Responsive Behavior

- Cards are full width on mobile
- On tablet/desktop, cards fit within their grid or flex container
- `CardHeader` actions stack below title on very small cards
- `CardFooter` buttons stack vertically on mobile when `fullWidth` is set on buttons

---

## Accessibility

- **Interactive cards:** `role="button"`, `tabIndex={0}`, `onKeyDown` handles Enter and Space
- **Focus:** `focus-visible:ring-2 ring-teal-600 ring-offset-2` on interactive cards
- **Screen reader:** Interactive card `aria-label` should describe the card destination or action: `aria-label="Ver perfil de María García Torres"`
- **Non-interactive:** No role override needed. Content is read naturally.

---

## Dark Mode

```
dark:bg-gray-800 (default/elevated/interactive)
dark:border-gray-700 (outlined)
dark:shadow-none dark:border dark:border-gray-700 (replaces shadow in dark mode)
dark:text-gray-100 (CardHeader title)
dark:text-gray-400 (CardHeader description)
dark:border-gray-700 (CardHeader/CardFooter dividers)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
