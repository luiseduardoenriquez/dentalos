# Data Table — Design System Component Spec

## Overview

**Spec ID:** FE-DS-05

**Component:** `DataTable`

**File:** `src/components/shared/data-table.tsx`

**Description:** Headless-powered data table component built on TanStack Table v8 with shadcn/ui rendering primitives. Handles sorting, cursor-based pagination, row selection, expandable rows, and bulk actions. Used for patient lists, team members, billing history, audit logs, treatment plans, and all tabular data in DentalOS.

**Design System Ref:** `FE-DS-01` (§4.5)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `data` | `T[]` | `[]` | Yes | Array of row data |
| `columns` | `ColumnDef<T>[]` | — | Yes | TanStack column definitions |
| `isLoading` | `boolean` | `false` | No | Shows skeleton rows |
| `error` | `string \| null` | `null` | No | Shows error state |
| `emptyState` | `ReactNode` | Default empty | No | Custom empty state content |
| `pagination` | `PaginationConfig` | — | No | Pagination configuration |
| `selectable` | `boolean` | `false` | No | Enables checkbox row selection |
| `onSelectionChange` | `(rows: T[]) => void` | — | No | Callback when selection changes |
| `expandable` | `boolean` | `false` | No | Enables expandable rows |
| `renderExpanded` | `(row: T) => ReactNode` | — | No | Content for expanded row |
| `density` | `'compact' \| 'default' \| 'relaxed'` | `'default'` | No | Row height/padding |
| `stickyHeader` | `boolean` | `false` | No | Makes header sticky on scroll |
| `className` | `string` | — | No | Additional classes on table wrapper |
| `onRowClick` | `(row: T) => void` | — | No | Row click handler (makes rows hoverable) |
| `getRowId` | `(row: T) => string` | `row.id` | No | Row key resolver |

## PaginationConfig Type

```typescript
interface PaginationConfig {
  type: 'cursor' | 'offset'
  pageSize: number
  totalCount?: number       // for offset pagination
  hasNextPage?: boolean     // for cursor pagination
  hasPrevPage?: boolean
  onNextPage: () => void
  onPrevPage: () => void
  currentPage?: number      // for offset pagination
}
```

---

## Row Density

| Density | Row Height | Cell Padding | Use Case |
|---------|-----------|--------------|----------|
| `compact` | 40px | `py-2 px-3` | Audit logs, clinical records |
| `default` | 52px | `py-3 px-4` | Patient list, team, appointments |
| `relaxed` | 64px | `py-4 px-4` | Dashboard summary tables |

---

## Column Types

TanStack `ColumnDef` with DentalOS-specific cell renderers:

### Text Column

```typescript
{
  accessorKey: 'nombre',
  header: 'Nombre',
  cell: ({ getValue }) => (
    <span className="text-sm text-gray-900">{getValue()}</span>
  ),
}
```

### Number Column

Right-aligned, formatted with locale:

```typescript
{
  accessorKey: 'monto',
  header: () => <span className="block text-right">Monto</span>,
  cell: ({ getValue }) => (
    <span className="block text-right text-sm font-mono">
      {formatCurrency(getValue(), 'COP')}
    </span>
  ),
}
```

### Date Column

Relative time for recent dates, absolute for old ones:

```typescript
{
  accessorKey: 'created_at',
  header: 'Fecha',
  cell: ({ getValue }) => (
    <span className="text-sm text-gray-500">
      {formatRelativeDate(getValue())} {/* "hace 3 días" */}
    </span>
  ),
}
```

### Badge Column

```typescript
{
  accessorKey: 'status',
  header: 'Estado',
  cell: ({ getValue }) => <Badge status={getValue()} />,
}
```

### Avatar Column

```typescript
{
  accessorKey: 'user',
  header: 'Usuario',
  cell: ({ getValue }) => {
    const user = getValue()
    return (
      <div className="flex items-center gap-2">
        <Avatar size="sm" name={user.nombre} src={user.foto_url} />
        <div>
          <p className="text-sm font-medium text-gray-900">{user.nombre}</p>
          <p className="text-xs text-gray-500">{user.email}</p>
        </div>
      </div>
    )
  },
}
```

### Actions Column

```typescript
{
  id: 'actions',
  header: '',
  cell: ({ row }) => (
    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <Button variant="ghost" size="sm" className="w-8 h-8 p-0" aria-label="Editar">
        <Pencil className="w-4 h-4" />
      </Button>
      <Button variant="ghost" size="sm" className="w-8 h-8 p-0 text-red-500" aria-label="Eliminar">
        <Trash2 className="w-4 h-4" />
      </Button>
    </div>
  ),
}
```

---

## Sortable Columns

Columns with `enableSorting: true` show sort indicator in header:

**Unsorted:** `ChevronsUpDown` icon, 14px, `text-gray-400`
**Sorted ASC:** `ChevronUp` icon, 14px, `text-gray-600`
**Sorted DESC:** `ChevronDown` icon, 14px, `text-gray-600`

Click header → cycles through: unsorted → ASC → DESC → unsorted.

Only one column can be sorted at a time (single-sort). Header cell classes:
```
cursor-pointer select-none hover:bg-gray-100 transition-colors
```

---

## Row Selection

When `selectable={true}`:
- First column is a checkbox column (`w-12`, non-sortable)
- Header checkbox: selects/deselects all visible rows
- Header checkbox shows indeterminate state when some (not all) rows are selected

**Checkbox style:** shadcn/ui Checkbox, 16px, `accent-teal-600`.

**Selected row:** `bg-teal-50` background on the row.

**Bulk Action Bar:**

Appears above the table (slides down) when at least 1 row is selected:

```
+----------------------------------------------+
| [X] 3 pacientes seleccionados               |
|     [Exportar] [Enviar recordatorio] [Archivar] |
+----------------------------------------------+
```

- `bg-teal-700 text-white` bar, `h-12`
- Left: X button (clear selection) + count label
- Right: bulk action buttons passed via `bulkActions` prop

---

## Expandable Rows

When `expandable={true}`:
- Last column (or first) shows `ChevronRight` icon button
- Click → row expands, `ChevronRight` rotates `90deg`
- Expanded content renders in a row spanning all columns below the parent row
- `renderExpanded(row)` prop provides the expanded content

**Expanded row styling:**
```
bg-gray-50 border-t border-b border-gray-200
```

Only one row can be expanded at a time (accordion behavior) unless `multiExpand` prop is set.

---

## Sticky Header

When `stickyHeader={true}`:
```
thead > tr > th: sticky top-0 z-10 bg-white border-b border-gray-200
```

Header maintains its position while the table body scrolls inside a fixed-height container.

---

## Table Header Styling

```
<th>: text-xs font-medium text-gray-500 uppercase tracking-wider
bg-gray-50 border-b border-gray-200
```

---

## Responsive Behavior

### Horizontal Scroll (Mobile)

Default on mobile: table container gets `overflow-x-auto`. All columns remain visible via horizontal scroll. No column hiding.

### Card View Option

When `cardView={true}` prop is set, on screens < 640px the table switches to a stacked card layout:

```
+---------------------------+
| [Column1 label]: value    |
| [Column2 label]: value    |
| [Actions]                 |
+---------------------------+
```

This is used for team member list (FE-S-02) and patient list (FE-PAT-01).

---

## Pagination

**Rendered below the table:**

```
+------------------------------------------+
| Mostrando 1-50 de 243 resultados         |
|        [← Anterior]  [1] [2] ... [Siguiente →]  |
+------------------------------------------+
```

**Cursor-based pagination** (clinical data, audit logs): Only shows "Anterior" / "Siguiente" buttons + "Mostrando X resultados".

**Offset pagination** (simple lists): Shows page numbers + total count.

**Page size selector:** Dropdown `10 / 20 / 50` per page. Optional, enabled via `showPageSizeSelector` prop.

---

## Loading State — Skeleton Rows

When `isLoading={true}`, renders `skeletonRows` (default: 5) skeleton rows:

```
Each skeleton row:
+--[checkbox]--[avatar circle + bar]--[bar]--[badge]--[bar]--+
```

Bars use: `bg-gray-200 animate-pulse rounded h-4`

---

## Error State

When `error` is non-null:

```
+-------------------------------------------+
| [AlertCircle icon]                        |
| No se pudo cargar los datos               |
| [error message]                           |
| [Reintentar] button                       |
+-------------------------------------------+
```

Centered within the table body area.

---

## Empty State

When `data.length === 0` and not loading:

Default or custom `emptyState` ReactNode rendered centered in the table body.

Default: "Sin datos para mostrar" in `text-sm text-gray-500`.

---

## Accessibility

- **Role:** `role="table"` on `<table>`, `role="rowgroup"` on `<thead>`/`<tbody>`, `role="row"` on `<tr>`, `role="columnheader"` on `<th>`, `role="cell"` on `<td>`
- **Sortable columns:** `aria-sort="ascending" / "descending" / "none"` on `<th>` elements
- **Row selection:** Checkboxes have `aria-label="Seleccionar [row identifier]"`. Header checkbox: `aria-label="Seleccionar todas las filas"`.
- **Expandable rows:** Toggle button has `aria-expanded="true/false"` and `aria-controls="expanded-row-[id]"`. Expanded content has `id="expanded-row-[id]"`.
- **Keyboard:** Tab navigates to rows. Enter activates row click or expand. Space selects checkbox.

---

## Usage Example

```tsx
const columns: ColumnDef<Patient>[] = [
  {
    accessorKey: 'nombre_completo',
    header: 'Paciente',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <Avatar size="sm" name={row.original.nombre_completo} />
        <div>
          <p className="text-sm font-medium">{row.original.nombre_completo}</p>
          <p className="text-xs text-gray-500">{row.original.numero_documento}</p>
        </div>
      </div>
    ),
  },
  { accessorKey: 'edad', header: 'Edad', enableSorting: true },
  { accessorKey: 'ultima_visita', header: 'Última visita', enableSorting: true,
    cell: ({ getValue }) => formatRelativeDate(getValue()) },
  { id: 'actions', header: '', cell: ({ row }) => <PatientRowActions patient={row.original} /> },
]

<DataTable
  data={patients}
  columns={columns}
  isLoading={isLoading}
  density="default"
  selectable
  onSelectionChange={setSelectedPatients}
  pagination={{ type: 'cursor', pageSize: 20, hasNextPage, onNextPage, onPrevPage }}
  emptyState={<PatientEmptyState />}
  onRowClick={(patient) => router.push(`/pacientes/${patient.id}`)}
/>
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
