# Avatar — Design System Component Spec

## Overview

**Spec ID:** FE-DS-12

**Component:** `Avatar`, `AvatarGroup`

**File:** `src/components/ui/avatar.tsx`

**Description:** Visual representation of a user or entity, supporting photo URLs with initials fallback. The initials fallback derives a deterministic background color from the person's name, ensuring consistent color assignment across the application. Includes group variant for displaying team overlaps.

**Design System Ref:** `FE-DS-01` (§4.9)

---

## Props Table — `Avatar`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `size` | `'xs' \| 'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | No | Avatar size |
| `src` | `string` | — | No | Image URL |
| `name` | `string` | — | No | Full name for initials fallback and alt text |
| `status` | `'online' \| 'offline' \| 'busy' \| null` | `null` | No | Presence status indicator dot |
| `className` | `string` | — | No | Additional classes on outer wrapper |
| `onClick` | `() => void` | — | No | Makes avatar clickable |
| `fallbackColor` | `string` | Auto | No | Override deterministic background color |

## Props Table — `AvatarGroup`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `avatars` | `AvatarProps[]` | `[]` | Yes | Array of avatar data |
| `max` | `number` | `5` | No | Max visible avatars before "+N" overflow |
| `size` | `'xs' \| 'sm' \| 'md'` | `'sm'` | No | Size applied to all avatars in group |
| `spacing` | `'tight' \| 'normal'` | `'tight'` | No | Overlap amount between avatars |
| `className` | `string` | — | No | Additional classes on group wrapper |

---

## Sizes

| Size | Dimensions | Font Size | Border Width | Icon Size |
|------|-----------|-----------|--------------|-----------|
| `xs` | `w-6 h-6` (24px) | `text-[10px]` | `ring-1` | 12px |
| `sm` | `w-8 h-8` (32px) | `text-xs` | `ring-1` | 14px |
| `md` | `w-10 h-10` (40px) | `text-sm` | `ring-2` | 16px |
| `lg` | `w-12 h-12` (48px) | `text-base` | `ring-2` | 20px |
| `xl` | `w-16 h-16` (64px) | `text-xl` | `ring-2` | 24px |

---

## Visual Structure

```
+----------------+
|   [Photo or]   |
|  [Initials AB] |
|              ● |  ← status dot
+----------------+
```

**Wrapper classes:**
```
relative inline-flex flex-shrink-0
rounded-full overflow-hidden
```

**Image:** `object-cover w-full h-full`

**Initials fallback:** Centered text on colored background.

**Status dot position:** `absolute bottom-0 right-0`

---

## Initials Fallback

When `src` is undefined or image fails to load.

### Initials Derivation

```typescript
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

// Examples:
// "María García Torres" → "MT"
// "Dr. Alejandro Gómez" → "DG"
// "Carlos" → "C"
```

### Deterministic Background Color

Background color is derived from the name string via a simple hash:

```typescript
const AVATAR_COLORS = [
  'bg-blue-500',    // 0
  'bg-teal-500',    // 1
  'bg-purple-500',  // 2
  'bg-amber-500',   // 3
  'bg-pink-500',    // 4
  'bg-indigo-500',  // 5
  'bg-green-600',   // 6
  'bg-red-500',     // 7
]

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

// "María García" always → bg-teal-500 (deterministic)
// "Carlos López" always → bg-purple-500
```

All background colors use `text-white` for the initials text. WCAG AA contrast is guaranteed for all 8 colors (white text on these Tailwind 500+ colors).

---

## Status Indicator

Small dot in bottom-right corner of avatar:

**Dot classes:**
```
absolute bottom-0 right-0
rounded-full ring-2 ring-white
```

**Dot sizes by avatar size:**

| Avatar | Dot Size |
|--------|---------|
| xs | `w-1.5 h-1.5` |
| sm | `w-2 h-2` |
| md | `w-2.5 h-2.5` |
| lg | `w-3 h-3` |
| xl | `w-3.5 h-3.5` |

**Status colors:**

| Status | Color | Classes |
|--------|-------|---------|
| online | Green | `bg-green-500` |
| offline | Gray | `bg-gray-400` |
| busy | Red | `bg-red-500` |

`aria-label` on the wrapper includes status: `aria-label="María García — En línea"`.

---

## Image Loading

1. Image renders with `loading="lazy"` by default
2. On load error: falls back to initials automatically via `onError` handler
3. During load: initials visible underneath image (no flicker on fast networks)
4. Blurred placeholder optional for large sizes (`blur-up` technique)

---

## AvatarGroup

Displays multiple avatars overlapping, with a "+N" counter for overflow.

```
[A] [B] [C] [D] +3
```

Each avatar (except the first) has negative margin: `spacing="tight"` → `-ml-3`, `spacing="normal"` → `-ml-2`.

**Stack order:** `z-index` increases left to right (`z-[4]` for 1st, `z-[3]` for 2nd, etc.) so the leftmost avatar is on top visually (or reverse as configured).

**Border:** Each avatar has `ring-2 ring-white` to create separation between overlapping circles.

### Overflow Badge ("+N")

When avatars exceed `max`:

```tsx
<div className={cn(
  'relative inline-flex items-center justify-center',
  'rounded-full bg-gray-100 text-gray-600 font-medium',
  sizeClasses[size], // same dimensions as other avatars
  'ring-2 ring-white -ml-3 z-[0]'
)}>
  +{overflow}
</div>
```

Text: `text-xs` for sm, `text-sm` for md.

Tooltip on the "+N" badge: shows names of hidden avatars as a comma-separated list.

---

## Clickable Avatar

When `onClick` is provided:

```tsx
<Avatar
  size="md"
  name={user.nombre}
  src={user.foto_url}
  onClick={() => openProfile(user.id)}
  className="cursor-pointer hover:ring-2 hover:ring-teal-500 hover:ring-offset-1 transition-all"
/>
```

Also requires `tabIndex={0}` and `onKeyDown` for Enter/Space activation.

---

## Usage Examples

```tsx
// Basic avatar with photo
<Avatar
  size="md"
  src="https://cdn.dentalos.io/users/abc123/photo.jpg"
  name="María García Torres"
/>

// Initials fallback (no photo)
<Avatar
  size="lg"
  name="Dr. Alejandro Gómez"
/>
// → Renders "AG" on deterministic color background

// With online status
<Avatar
  size="md"
  name="Carlos López"
  status="online"
/>

// Extra small in table row
<Avatar
  size="xs"
  name="Dra. Sofía Martínez"
  src={user.foto_url}
/>

// Patient header avatar
<Avatar
  size="xl"
  name={patient.nombre_completo}
  src={patient.foto_url}
/>

// Group (team display)
<AvatarGroup
  size="sm"
  max={4}
  avatars={[
    { name: 'Dr. Gómez', src: null },
    { name: 'Dra. García', src: '/photos/garcia.jpg' },
    { name: 'Carlos López', src: null },
    { name: 'Andrea Ruiz', src: null },
    { name: 'Pedro Silva', src: null },
  ]}
/>
// → Shows 4 avatars + "+1" overflow badge
```

---

## Accessibility

- **Role:** `role="img"` on the avatar wrapper
- **Alt text:** `aria-label="[name]"` or if no name, `aria-label="Usuario"`. When status present: `aria-label="[name] — [status label]"`.
- **Initials:** Pure CSS content, not meaningful text for screen readers. Aria-label on wrapper provides the name.
- **Clickable:** `role="button"`, `tabIndex={0}`, `aria-label="Ver perfil de [name]"`, keyboard: Enter/Space activates.
- **Group:** Group wrapper has `role="list"`, each avatar has `role="listitem"`. `+N` badge has `aria-label="y [N] más"` + `title` with the hidden names.

---

## Dark Mode

Initials avatars maintain their colored backgrounds in dark mode (no change needed — they're always bright colors).

Ring borders on AvatarGroup: `dark:ring-gray-800` instead of `ring-white` to blend with dark surfaces.

---

## Implementation Notes

**File Location:** `src/components/ui/avatar.tsx`

**Dependencies:** No external library needed — pure Tailwind + React.

**Memoization:** `getAvatarColor(name)` should be memoized or computed at render time since it's pure.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
