# Mensajes — Portal del Paciente (Portal Messages) — Frontend Spec

## Overview

**Screen:** Messaging interface between patient and clinic in the patient portal. Thread list sidebar, message view area, text input with file attachment. WhatsApp-like UX. Unread indicators. Simple, non-clinical.

**Route:** `/portal/[clinicSlug]/messages`

**Priority:** Medium

**Backend Specs:** `specs/portal/PP-10.md`, `specs/portal/PP-11.md`

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`

---

## User Flow

**Entry Points:**
- "Ver mensajes" from portal dashboard messages card
- "Mensajes" in portal navigation

**Exit Points:**
- "← Inicio" → dashboard

**User Story:**
> As a patient, I want to message my clinic directly from the portal so that I can ask questions about my treatment, reschedule, or request information without calling.

**Roles with access:** patient (portal session)

---

## Layout Structure

```
+------------------------------------------+
|  [Navbar]                                 |
+------------------------------------------+
|  ← Inicio     Mensajes                   |
|                                           |
| MOBILE: Thread list → tap → message view |
|                                           |
| DESKTOP (2-column):                       |
| +------------------+ +------------------+|
| | CONVERSACIONES   | | CONVERSACIÓN     ||
| |                  | |                  ||
| | ● Clínica Dental | | 14 Feb 10:30 AM  ||
| |   Tu cita est... | | Dr. López:       ||
| |   10:30 AM    (3)| | "Tu próxima cita ||
| |                  | |  es el 3 de mar  ||
| +------------------+ |  zo a las 10am"  ||
|                      |                  ||
|                      | 14 Feb 10:35 AM  ||
|                      | Tú:              ||
|                      | "Gracias, anotado||
|                      |  !"              ||
|                      |                  ||
|                      | +------------+   ||
|                      | | Escribe... |📎| ||
|                      | +----[Enviar]--+ ||
+------------------------------------------+
```

**Sections:**
1. Page header — back link, title
2. Thread list (left panel desktop / full screen mobile) — clinic conversation threads
3. Message view (right panel desktop / full screen after tap mobile) — chronological messages
4. Message input bar — text area + attach file + send button

---

## UI Components

### Component 1: ThreadList

**Type:** Scrollable list

**Per thread item:**
- Clinic/sender avatar (clinic logo, small 40px)
- Sender name: "Clínica {clinicName}" or specific doctor name
- Last message preview (1 line, 30 chars, truncated)
- Timestamp (relative: "hace 5 min", "ayer", "14 Feb")
- Unread count badge (red pill): hidden if 0

**Selected state:** `bg-primary-50 border-l-2 border-l-primary-500`

**Note:** For patient portal, there is typically only 1 clinic thread, but the component supports multiple (for multi-clinic patients).

### Component 2: MessageBubble

**Type:** Chat bubble

**Variants:**
- Clinic message (received): left-aligned, `bg-gray-100 text-gray-900`, sender label above first consecutive message
- Patient message (sent): right-aligned, `bg-primary-500 text-white`
- System/automated message: centered, `text-xs text-gray-400 italic`

**Content:**
- Text content
- File attachment (if any): file name with download icon or image thumbnail
- Timestamp (small, below bubble)
- Read status for sent messages: single tick (sent) or double tick (read)

**Date separator:** Date pill between messages from different days ("Hoy", "Ayer", "14 de febrero")

### Component 3: MessageInputBar

**Type:** Input area with actions

**Content:**
- Multiline text input: "Escribe un mensaje..." (min 1 line, max 4 lines before scroll)
- Attach file button (paperclip icon): opens file picker; accepted: images + PDF, max 5MB
- Send button (arrow icon): enabled when text or attachment is present

**Behavior:**
- Enter sends message (on desktop)
- Shift+Enter inserts newline
- On mobile: Enter inserts newline; send via button only

### Component 4: FileAttachmentPreview

**Type:** Inline attachment preview in message input (before send)

**Content:** File name + size + remove button (×)

**Image preview:** Shows thumbnail if image type.

---

## Form Fields

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| message_text | Textarea | Yes (or attachment) | Max 2000 chars |
| attachment | File | No | Images (jpg/png/webp) or PDF. Max 5MB. |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List threads | `/api/v1/portal/messages/threads` | GET | `specs/portal/PP-10.md` | 1min |
| Get thread messages | `/api/v1/portal/messages/threads/{id}` | GET | `specs/portal/PP-10.md` | None |
| Send message | `/api/v1/portal/messages/threads/{id}/send` | POST | `specs/portal/PP-11.md` | — |
| Upload attachment | `/api/v1/portal/messages/attachments` | POST | `specs/portal/PP-11.md` | — |
| Mark as read | `/api/v1/portal/messages/threads/{id}/read` | PATCH | `specs/portal/PP-10.md` | — |

**Real-time:** Polling every 10 seconds for new messages (no WebSocket for MVP; add polling refetch interval).

### State Management

**Local State (useState):**
- `activeThreadId: string | null`
- `messageText: string`
- `attachmentFile: File | null`
- `isSending: boolean`

**Server State (TanStack Query):**
- Query key: `['portal-message-threads', patientId]` — stale 1min
- Query key: `['portal-messages', threadId]` — stale: none (always fresh); refetch interval 10s
- Mutation: `sendMessage` — on success: optimistically add message to list, mark as sent

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select thread | Tap in thread list | Thread messages load in right panel | Thread highlighted, mobile: full-screen message view |
| Type message | Input | Character count updates | Placeholder disappears |
| Attach file | Tap paperclip | File picker opens | Selected file shown in preview |
| Send message | Tap send or Enter | POST message; optimistic add to chat | New bubble appears, spinner on send button |
| Receive new message | Polling | New bubble appears at bottom | Unread badge in thread list if not focused |
| Mark as read | Open thread | PATCH mark as read | Unread count clears in thread list + dashboard |
| Remove attachment | Tap × on preview | File removed | Preview disappears |

### Animations/Transitions

- New message bubble: slide in from bottom (150ms)
- Send button: spring scale on click
- Thread select: background color transition (100ms)
- Auto-scroll to bottom on new message (if already at bottom)

---

## Loading & Error States

### Loading State
- Thread list: skeleton items
- Message view on first load: skeleton bubbles
- Send: send button shows spinner

### Error State
- Send failure: toast "No se pudo enviar el mensaje. Intenta de nuevo." Message removed from optimistic list.
- Upload failure: toast "No se pudo adjuntar el archivo."
- Load failure: error card with retry

### Empty State
- No messages in thread: "Inicia la conversación con tu clínica. Escríbenos para cualquier consulta."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Two screens: thread list full screen, tap thread → message view full screen (back button visible). Input bar sticky at bottom (above keyboard). |
| Tablet (640-1024px) | Two-panel layout (30/70 split). Thread list left, messages right. |
| Desktop (> 1024px) | Two-panel (25/75). Same layout. |

---

## Accessibility

- **Focus order:** Thread list items → message input → attach → send
- **Screen reader:** New messages announced via `aria-live="polite"`. Unread count in thread item: `aria-label="3 mensajes sin leer"`. Message time: `aria-label="Enviado el {date} a las {time}"`.
- **Keyboard navigation:** Tab through thread list. Arrow keys between threads. Enter to open. Tab to input, attach, send.
- **Language:** es-419. Time in 12h format for patient-friendly reading.

---

## Design Tokens

**Colors:**
- Received bubble: `bg-gray-100 text-gray-900`
- Sent bubble: `bg-primary-500 text-white`
- System message: `text-gray-400`
- Active thread: `bg-primary-50 border-l-2 border-primary-500`
- Unread badge: `bg-red-500 text-white`
- Date separator: `text-gray-400 bg-white border border-gray-200`
- Input bar: `bg-white border-t border-gray-200`

**Spacing:**
- Bubble padding: `px-3 py-2`
- Between same-sender bubbles: `mb-1`
- Between different-sender bubbles: `mb-3`
- Input bar height: `min-h-[56px]` (comfortable touch target)

---

## Implementation Notes

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/messages/page.tsx`
- Components: `src/components/portal/ThreadList.tsx`, `src/components/portal/MessageView.tsx`, `src/components/portal/MessageBubble.tsx`, `src/components/portal/MessageInputBar.tsx`
- Hooks: `src/hooks/usePortalMessages.ts`

**Polling:**
```typescript
useQuery(['portal-messages', threadId], fetchMessages, {
  refetchInterval: 10000, // 10 seconds
  refetchIntervalInBackground: false, // only when tab active
});
```

---

## Test Cases

### Happy Path
1. Send a text message
   - **Given:** Patient has 1 thread with clinic
   - **When:** Types "¿A qué hora debo llegar mañana?" and taps send
   - **Then:** Message bubble appears (sent style), marked as sent with tick

2. Receive new message
   - **Given:** Clinic staff replies "Favor llegar 10 minutos antes"
   - **When:** Polling fires (10s)
   - **Then:** New bubble appears in message view; thread list shows updated preview

### Edge Cases
1. File too large
   - **Given:** Patient tries to attach 10MB PDF
   - **When:** File selected
   - **Then:** Error toast "El archivo es demasiado grande. Máximo 5 MB."

---

## Acceptance Criteria

- [ ] Thread list: clinic conversations with unread count badge and last message preview
- [ ] Message view: chronological bubbles with sent/received styling
- [ ] Date separators between days
- [ ] Read/sent status indicators on sent messages (tick icons)
- [ ] Text input with multiline support
- [ ] File attachment: images + PDF, max 5MB, preview before send
- [ ] Send via button (always) and Enter key (desktop only)
- [ ] Auto-scroll to latest message
- [ ] Polling every 10 seconds for new messages (when tab active)
- [ ] Mark as read on thread open
- [ ] Loading skeletons
- [ ] Empty state (no messages yet)
- [ ] Error handling with toasts
- [ ] Responsive: two-screen mobile, two-panel tablet/desktop
- [ ] Non-clinical language, es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
