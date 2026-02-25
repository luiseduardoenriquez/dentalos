# [Screen/Component Name] — Frontend Spec

## Overview

**Screen:** [Brief description of the screen/component]

**Route:** `/[path]`

**Priority:** [Critical | High | Medium | Low]

**Backend Specs:** [List backend spec references, e.g., `specs/auth/login.md`]

**Dependencies:** [List other frontend specs this depends on, or "None"]

---

## User Flow

**Entry Points:**
- [How user gets to this screen]

**Exit Points:**
- [Where user can go from here]

**User Story:**
> As a [role: clinic_owner | doctor | assistant | receptionist | patient], I want to [action] so that [benefit].

**Roles with access:** [List roles that can see this screen]

---

## Layout Structure

```
+------------------------------------------+
|              Header / Navbar              |
+--------+---------------------------------+
|        |                                 |
| Side-  |         Main Content            |
|  bar   |                                 |
|        |                                 |
|        +---------------------------------+
|        |           Footer                |
+--------+---------------------------------+
```

**Sections:**
1. [Section 1 description]
2. [Section 2 description]

---

## UI Components

### Component 1: [Name]

**Type:** [Button | Input | Card | Table | Modal | etc.]

**Design System Ref:** `frontend/design-system/[component].md`

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | string | "primary" | Style variant |

**States:**
- Default
- Hover
- Active
- Disabled
- Loading

**Behavior:**
- [Click action]
- [Validation rules]

---

## Form Fields (if applicable)

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| email | email | Yes | Valid email format | "Email invalido" | "correo@ejemplo.com" |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load data | `/api/v1/endpoint` | GET | `specs/domain/spec.md` | 5min |

### State Management

**Local State (useState):**
- `isLoading: boolean`
- `error: string | null`

**Global State (Zustand):**
- [Store name]: `[state description]`

**Server State (TanStack Query):**
- Query key: `['entity', tenantId, params]`
- Stale time: [duration]
- Mutation: `useMutation()` for [action]

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Submit form | Click button | API call, redirect | Toast success/error |
| Input change | Typing | Validate field | Inline error |

### Animations/Transitions

- [Describe any animations — e.g., "Modal slides in from bottom on mobile"]

---

## Loading & Error States

### Loading State
- [Skeleton loader matching content layout — ref: `frontend/design-system/skeleton.md`]

### Error State
- [Error display approach — toast, inline, or full-page error]

### Empty State
- [What to show when no data — ref: `frontend/design-system/empty-state.md`]
- **Illustration:** [description]
- **Message:** "[message text]"
- **CTA:** "[button text]" -> [action]

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | [Layout changes — e.g., "Stack columns vertically"] |
| Tablet (640-1024px) | [Layout changes — e.g., "Sidebar collapses, 2-column grid"] |
| Desktop (> 1024px) | [Default layout] |

**Tablet priority:** [High — primary clinical device. Touch targets min 44px.]

---

## Accessibility

- **Focus order:** [Describe tab order]
- **Screen reader:** [ARIA labels, live regions, announcements]
- **Keyboard navigation:** [Supported keys — Enter, Escape, Arrow keys]
- **Color contrast:** [WCAG AA compliance for all text]
- **Language:** [es-419 (Latin American Spanish) default]

---

## Design Tokens

**Colors:**
- Primary: `--color-primary` / `bg-primary-600`
- Background: `--color-bg` / `bg-white dark:bg-gray-900`
- Clinical status colors: see `frontend/design-system/tokens.md`

**Typography:**
- Heading: `text-2xl font-bold font-inter`
- Body: `text-base font-normal`

**Spacing:**
- Container: `px-4 md:px-6 lg:px-8`
- Card gap: `gap-4`

**Border Radius:**
- Cards: `rounded-xl`
- Buttons: `rounded-lg`
- Inputs: `rounded-md`

---

## Implementation Notes

**Dependencies (npm):**
- [Required packages/components]

**File Location:**
- Page: `src/app/(dashboard)/[path]/page.tsx`
- Components: `src/components/[domain]/[ComponentName].tsx`

**Hooks Used:**
- `useAuth()` — current user + tenant context
- `useQuery()` / `useMutation()` — data fetching
- [Custom hooks]

**Form Library:**
- React Hook Form + Zod schema validation

---

## Test Cases

### Happy Path
1. [Test scenario]
   - **Given:** [preconditions]
   - **When:** [action]
   - **Then:** [expected result]

### Edge Cases
1. [Edge case scenario]

### Error Cases
1. [Error scenario]

---

## Acceptance Criteria

- [ ] Matches design spec / mockup
- [ ] All interactions working
- [ ] Form validation complete (client + server errors)
- [ ] API integration complete
- [ ] Loading states implemented (skeleton)
- [ ] Error handling implemented (toast + inline)
- [ ] Empty states implemented
- [ ] Responsive on all breakpoints (mobile, tablet, desktop)
- [ ] Accessibility requirements met (focus, ARIA, keyboard)
- [ ] Spanish (es-419) labels and messages

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | [date] | Initial spec |
