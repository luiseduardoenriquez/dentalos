# Skeleton Loader — Design System Component Spec

## Overview

**Spec ID:** FE-DS-17

**Component:** `Skeleton`, `SkeletonText`, `SkeletonCard`, `SkeletonTable`, `SkeletonForm`, `SkeletonChart`, `SkeletonAvatar`

**File:** `src/components/ui/skeleton.tsx`

**Description:** Placeholder loading components that mimic the layout of content before data arrives. Prevents layout shift and provides visual continuity during loading states. Uses CSS `animate-pulse` for the shimmer effect. Every data-driven component in DentalOS has a matching skeleton variant.

**Design System Ref:** `FE-DS-01` (§4.13)

---

## Base Props — `Skeleton`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `className` | `string` | — | No | Additional Tailwind classes for shape/size |
| `animate` | `boolean` | `true` | No | Enable/disable pulse animation |

## Higher-level Skeleton Props

### `SkeletonText`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `lines` | `number` | `1` | Number of text lines |
| `lastLineWidth` | `'full' \| 'partial'` | `'partial'` | Last line is full-width or 60% |
| `className` | `string` | — | Container classes |

### `SkeletonTable`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `rows` | `number` | `5` | Number of skeleton rows |
| `columns` | `number` | `4` | Number of column placeholders per row |
| `showHeader` | `boolean` | `true` | Show a header row skeleton |
| `density` | `'compact' \| 'default' \| 'relaxed'` | `'default'` | Row height matching table density |

### `SkeletonCard`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `lines` | `number` | `3` | Text lines in card body |
| `hasHeader` | `boolean` | `true` | Show header skeleton |
| `hasFooter` | `boolean` | `false` | Show footer skeleton |
| `hasAvatar` | `boolean` | `false` | Show avatar in header |

### `SkeletonForm`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `fields` | `number` | `4` | Number of label+input pairs |
| `columns` | `number` | `1` | Column layout (1 or 2) |
| `hasFooter` | `boolean` | `true` | Show save button placeholder |

### `SkeletonChart`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `type` | `'bar' \| 'line' \| 'donut'` | `'bar'` | Chart type visual |
| `height` | `number` | `200` | Height of chart area |

---

## Base Skeleton Element

The foundation of all skeleton components:

```tsx
// src/components/ui/skeleton.tsx
export function Skeleton({ className, animate = true }: SkeletonProps) {
  return (
    <div
      className={cn(
        'bg-gray-200 dark:bg-gray-700 rounded',
        animate && 'animate-pulse',
        className
      )}
      aria-hidden="true"
    />
  )
}
```

**Always `aria-hidden="true"`** — skeletons are purely visual and should not be read by screen readers. The loading state is communicated to screen readers via `aria-busy="true"` on the parent container.

---

## Animation

**CSS animation:** `animate-pulse` from Tailwind:
```css
@keyframes pulse {
  50% { opacity: 0.5; }
}
```

**Period:** 2 seconds, infinite.

**Reduced motion:** When `prefers-reduced-motion: reduce`, `animate-pulse` is disabled by Tailwind automatically (`@media (prefers-reduced-motion: reduce) { .animate-pulse { animation: none } }`).

---

## SkeletonText

Single or multi-line text placeholder. Last line is shorter to simulate paragraph endings.

```tsx
<SkeletonText lines={3} />
```

**Renders:**
```
[============================]  h-4 w-full
[============================]  h-4 w-full
[==================]            h-4 w-[60%]  ← last line partial
```

**Line height:** `h-4` (16px) with `rounded` (4px). Gap between lines: `space-y-2`.

**Width variations:**
- `lines=1`: `w-full` (or constrained by className)
- `lines>1`: all full width except last: `w-[65%]` (randomized variation optional)

---

## SkeletonAvatar

Circular placeholder matching avatar sizes.

```tsx
<SkeletonAvatar size="md" />
```

| Size | Classes |
|------|---------|
| `xs` | `w-6 h-6 rounded-full` |
| `sm` | `w-8 h-8 rounded-full` |
| `md` | `w-10 h-10 rounded-full` |
| `lg` | `w-12 h-12 rounded-full` |
| `xl` | `w-16 h-16 rounded-full` |

Often used alongside SkeletonText for user rows:

```tsx
<div className="flex items-center gap-3">
  <SkeletonAvatar size="sm" />
  <div className="flex-1">
    <Skeleton className="h-4 w-32 mb-1" />
    <Skeleton className="h-3 w-48" />
  </div>
</div>
```

---

## SkeletonTable

Full table skeleton with header and data rows.

```tsx
<SkeletonTable rows={5} columns={4} />
```

**Renders:**

```
[====] [========] [=======] [====]    ← header row (bg-gray-100)
[====] [========] [=======] [====]    ← data row 1
[====] [========] [=======] [====]    ← data row 2
[====] [========] [=======] [====]    ← data row 3
[====] [========] [=======] [====]    ← data row 4
[====] [========] [=======] [====]    ← data row 5
```

**Column width distribution:** First column narrower (checkbox/avatar: `w-12`), flex-1 for main column, fixed for badge and action columns.

**Density row heights:**
- `compact`: `h-10` rows
- `default`: `h-13` rows
- `relaxed`: `h-16` rows

**First column variant:** If table has avatar column:

```tsx
<SkeletonTable rows={5} firstColumnType="avatar" />
```

Row contains: `SkeletonAvatar sm` + `SkeletonText lines=2 w-40`.

---

## SkeletonCard

Card-shaped skeleton block.

```tsx
<SkeletonCard hasHeader hasFooter />
```

**Renders:**
```
+------------------------------------------+
| [====== Card title ======]  [action btn] |   ← hasHeader: h-6 w-48
+------------------------------------------+
| [================================]        |   ← body line 1
| [============================]            |   ← body line 2 (shorter)
| [======================]                  |   ← body line 3 (shorter)
+------------------------------------------+
| [=====] button skeleton                  |   ← hasFooter: h-9 w-24
+------------------------------------------+
```

**With avatar in header:**
```tsx
<SkeletonCard hasHeader hasAvatar />
```

Header: `SkeletonAvatar md` + `Skeleton h-5 w-32` (name).

---

## SkeletonForm

Multi-field form skeleton. Simulates label + input pairs.

```tsx
<SkeletonForm fields={4} columns={2} hasFooter />
```

**Single column (columns=1):**
```
[Label bar h-4 w-24]
[Input bar h-10 w-full]

[Label bar h-4 w-32]
[Input bar h-10 w-full]

...

[Button bar h-10 w-28]  ← hasFooter
```

**Two column (columns=2):**
```
[Label w-24]    [Label w-32]
[Input w-full]  [Input w-full]

[Label w-20]    [Label w-28]
[Input w-full]  [Input w-full]
```

Label: `h-4 rounded w-[30%]`
Input: `h-10 rounded-md w-full`

Gap between fields: `space-y-4`. Grid gap: `gap-4`.

---

## SkeletonChart

Visual placeholder for charts.

```tsx
<SkeletonChart type="bar" height={200} />
```

**Bar chart:**
```
+------------------------------------------+
| [Axis line left]                         |
|    |           [bar]                     |
|    |      [bar][bar]   [bar]             |
|    |  [bar][bar][bar]  [bar][bar]        |
|    +--------------------------------------+
|          [x-axis labels]                 |
+------------------------------------------+
```

Bar skeletons: variable width `h-full`, bottom-aligned, `space-x-2`.

**Line chart:**
- Rectangular area for chart `h-[height]` with inner wavy path (SVG wave as skeleton)

**Donut chart:**
- Circular `w-32 h-32 rounded-full` with ring: `ring-[16px] ring-gray-200`
- Legend items beside: 3 rows of `[circle dot][label bar]`

---

## Context-Specific Skeletons

### Dashboard Skeleton

```tsx
// 4 KPI cards + table + calendar side panel
<div className="grid grid-cols-4 gap-4 mb-6">
  {Array.from({length: 4}).map((_, i) => (
    <SkeletonCard key={i} />
  ))}
</div>
<div className="grid grid-cols-3 gap-6">
  <div className="col-span-2">
    <SkeletonTable rows={5} />
  </div>
  <div>
    <SkeletonCard lines={8} />
  </div>
</div>
```

### Patient List Skeleton

```tsx
<SkeletonTable rows={10} columns={5} firstColumnType="avatar" />
```

### Patient Detail Skeleton

```tsx
<div className="flex gap-6">
  <div className="w-80">
    <SkeletonCard hasAvatar lines={6} />
  </div>
  <div className="flex-1">
    <SkeletonForm fields={8} columns={2} />
  </div>
</div>
```

### Settings Page Skeleton

```tsx
<div className="space-y-6">
  <SkeletonCard hasHeader hasFooter lines={5} />
  <SkeletonCard hasHeader hasFooter lines={3} />
  <SkeletonCard hasHeader hasFooter lines={4} />
</div>
```

---

## Parent Container Aria Attributes

When a section is loading, the parent container should signal this:

```tsx
<section aria-busy={isLoading} aria-label="Lista de pacientes">
  {isLoading ? (
    <SkeletonTable rows={10} columns={5} />
  ) : (
    <DataTable data={patients} columns={columns} />
  )}
</section>
```

Screen reader announces: "Lista de pacientes. Cargando." when `aria-busy="true"`.

---

## Full-page Skeleton

For initial page load before any content renders:

```tsx
// src/components/shared/page-skeleton.tsx
<div className="min-h-screen bg-gray-50">
  {/* Header skeleton */}
  <div className="h-16 bg-white border-b flex items-center px-6 gap-4">
    <Skeleton className="w-8 h-8 rounded" />
    <Skeleton className="h-6 w-48 rounded" />
    <div className="ml-auto flex gap-3">
      <Skeleton className="w-8 h-8 rounded-full" />
      <Skeleton className="w-8 h-8 rounded-full" />
    </div>
  </div>
  <div className="flex">
    {/* Sidebar skeleton */}
    <div className="w-16 lg:w-64 h-screen bg-white border-r p-4 space-y-3">
      {Array.from({length: 6}).map((_, i) => (
        <Skeleton key={i} className="h-9 rounded-lg w-full" />
      ))}
    </div>
    {/* Content skeleton */}
    <main className="flex-1 p-6 space-y-6">
      <Skeleton className="h-8 w-64 rounded" />
      <SkeletonTable rows={8} />
    </main>
  </div>
</div>
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec — all skeleton variants |
