# Dictado por Voz para Evolucion Clinica (Voice Evolution) — Frontend Spec

## Overview

**Screen:** Voice dictation component embedded within the clinical evolution note form. A round microphone button allows the doctor to record dictation that is transcribed and used to fill the evolution note text area. If an evolution template is active, the system auto-detects and fills template variables from the transcription. The doctor can manually edit after transcription. A re-record button appends additional dictation to existing text.

**Route:** Embedded in `/patients/{id}/records/new` and `/patients/{id}/records/{recordId}/edit` — no dedicated route.

**Priority:** High

**Backend Specs:** `specs/voice/voice-transcription.md` (V-02), `specs/voice/voice-parse.md` (V-03)

**Dependencies:** `specs/frontend/clinical-records/record-create.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Within the evolution note form on clinical record creation/edit page
- Triggered by clicking the microphone button in the note text area

**Exit Points:**
- Transcription fills the note textarea (user continues form)
- User manually edits transcribed text and saves the record normally
- "Descartar grabacion" — clears transcribed text, returns to empty/previous note state

**User Story:**
> As a doctor, I want to dictate clinical notes by voice instead of typing so that I can complete evolution notes faster while keeping my focus on the patient.

**Roles with access:** `doctor`, `assistant`

---

## Layout Structure

```
Evolution Note Form Section:
+--------------------------------------------------+
|  "Evolucion Clinica"                             |
|  [Template selector — optional active template]  |
+--------------------------------------------------+
|  Note textarea area:                             |
|  +--------------------------------------------+ |
|  |                                            | |
|  |  [Transcribed text appears here]           | |
|  |                                            | |
|  |                                            | |
|  +--------------------------------------------+ |
|  |  [Mic button]  [Re-record btn]  Char count | |
+--------------------------------------------------+
|  [Template variables auto-fill status]           |
+--------------------------------------------------+
```

**Sections:**
1. Form section header — "Evolucion Clinica", optional template name
2. Textarea — receives transcription, manually editable
3. Voice control bar — microphone button, state-specific UI, re-record, character count
4. Template variable fill status — shown when active template has variables

---

## UI Components

### Component 1: VoiceMicButton

**Type:** Primary action button (round)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**States and visual:**

| State | Visual | Label (aria) |
|-------|--------|-------------|
| `idle` | `w-12 h-12 rounded-full bg-white border-2 border-gray-300 hover:border-teal-400 text-gray-400 hover:text-teal-600 shadow-sm` | "Iniciar grabacion de voz" |
| `recording` | `bg-red-500 border-red-500 text-white animate-pulse shadow-lg shadow-red-300/50` | "Detener grabacion" |
| `processing` | `bg-teal-100 border-teal-300 text-teal-600` + `Loader2 animate-spin` inside | "Procesando grabacion" |
| `complete` | `bg-green-100 border-green-400 text-green-600` + `CheckCircle2` inside | "Grabacion completada" |
| `error` | `bg-red-100 border-red-300 text-red-600` + `XCircle` inside | "Error en grabacion. Haz clic para reintentar" |

**Recording animation:**
- Outer ring `w-14 h-14 rounded-full bg-red-400/30 absolute animate-ping` around the button while recording
- Sound wave animation: 3 vertical bars beside the button `w-1 h-{2|4|3} bg-red-400 rounded animate-bounce` with staggered delays

**Click behavior:**
- `idle` → `recording`: request microphone permission, start MediaRecorder
- `recording` → `processing`: stop recording, send audio blob to API
- `error` → `recording`: retry

### Component 2: RecordingStateDisplay

**Type:** Status area beside mic button

**States:**

| State | Display |
|-------|---------|
| `idle` | `"Haz clic en el microfono para dictar"` `text-xs text-gray-400` |
| `recording` | Duration counter `"0:00"` counting up in `text-sm font-mono text-red-600` + `"Grabando... (haz clic para detener)"` `text-xs text-gray-500` |
| `processing` | `"Transcribiendo..."` `text-xs text-gray-500` |
| `complete` | `"Transcripcion lista"` `text-xs text-green-600` |
| `error` | Error message `text-xs text-red-600` (see error types below) |

**Max recording duration:** 5 minutes. At 4:30, show warning `"Grabacion se detendra en 30 segundos"`. Auto-stop at 5:00.

### Component 3: ReRecordButton

**Type:** Secondary text button

**Visible only when:** state is `complete` (transcription present in textarea)

**Label:** `"Agregar mas por voz"` with `Plus + Mic` icon

**Behavior:** Starts a new recording session. Transcribed text will be APPENDED to existing textarea content (not replaced), separated by a newline. User can also just start a second full dictation.

### Component 4: TranscriptionTextArea

**Type:** Controlled textarea

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Behavior:**
- `min-h-[160px]` resizable vertically
- During `processing` state: `bg-gray-50 text-gray-400 italic` with `"Transcribiendo audio..."` placeholder text
- After transcription: textarea pre-filled with transcription, fully editable
- Character counter: `{n}/2000` `text-xs text-gray-400` bottom-right of textarea

**Visual cue when transcription arrives:**
- Text fades in word-by-word: simulate streaming with 30ms word delay (cosmetic, full text available immediately from API)
- Brief highlight flash: `bg-teal-50` on textarea for 500ms after fill

---

## Template Variable Auto-Fill

### Active Template Context

When an evolution template is selected (e.g., "Revision Periodontal"), the template defines variables like:
```
Paciente con {{profundidad_sondaje}} mm de profundidad de sondaje en {{cuadrante}}.
Hallazgos: {{hallazgos}}. Indicaciones: {{indicaciones}}.
```

### Auto-Fill Logic (Client-Side)

After transcription arrives:
1. Check if an evolution template is active
2. Send transcription + template variable names to V-03 endpoint for variable extraction
3. Receive: `{ "profundidad_sondaje": "3", "cuadrante": "superior derecho", "hallazgos": "...", "indicaciones": "..." }`
4. Replace `{{variable_name}}` placeholders in template text with extracted values
5. Show fill status per variable (see TemplateVariableFillStatus component)

### Component 5: TemplateVariableFillStatus

**Type:** Compact status panel below textarea

**Visible only when:** active template with variables exists AND transcription has been processed

**Layout:** Row of small status chips per variable:

| Status | Chip style | Label |
|--------|-----------|-------|
| Filled | `bg-green-100 text-green-700` with check | `{variable_name}` |
| Not detected | `bg-amber-100 text-amber-700` with `!` | `{variable_name}` |
| Empty (no template) | — | Hidden |

**If variables not detected:**
- Amber chip with variable name
- Tooltip: "No se detecto en la grabacion. Edita manualmente."
- Corresponding `{{variable}}` placeholder remains in textarea for manual fill

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Transcribe audio | `/api/v1/voice/transcribe` | POST (multipart) | `specs/voice/voice-transcription.md` | None |
| Extract template variables | `/api/v1/voice/parse-template` | POST | `specs/voice/voice-parse.md` | None |

### Transcription Request

```typescript
// multipart/form-data
{
  audio: Blob;        // WebM/Opus from MediaRecorder API
  language: "es";     // force Spanish
  context: "clinical_evolution"; // hint for Whisper model
}
```

### Transcription Response

```typescript
{
  transcript: string;
  confidence: number;   // 0-1
  duration_seconds: number;
}
```

### Template Variables Request (if template active)

```typescript
{
  transcript: string;
  variables: string[];  // ["profundidad_sondaje", "cuadrante", "hallazgos"]
  context: "periodontal_review";
}
```

### State Management

**Local State (useState):**
- `recordingState: 'idle' | 'recording' | 'processing' | 'complete' | 'error'`
- `recordingDuration: number` — seconds elapsed
- `audioBlob: Blob | null`
- `transcription: string | null`
- `variableFillResults: Record<string, string | null>`
- `errorMessage: string | null`
- `mediaRecorder: MediaRecorder | null`

**Integration with Parent Form:**
- Component calls `onTranscriptionComplete(text: string)` callback
- Parent form updates the `evolucion_nota` field via React Hook Form's `setValue`

**Server State (TanStack Query):**
- Transcription: `useMutation({ mutationFn: transcribeAudio })`
- Template parse: `useMutation({ mutationFn: parseTemplateVariables })`, called after transcription if template active

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click mic (idle) | Click | Request mic permission → start recording | State → recording, pulse animation |
| Mic permission denied | Browser dialog denied | Show permission error | Error state with instructions |
| Click mic (recording) | Click | Stop recording → send to API | State → processing |
| Recording auto-stops (5min) | Timer | Send to API | Brief toast "Grabacion completada automaticamente" |
| Transcription ready | API response | Fill textarea, extract template vars if active | Text fades in, template status chips update |
| Edit textarea | Keyboard | User manually edits transcription | Character counter updates |
| Click "Agregar mas por voz" | Click | Start new recording, will append | State → recording again |
| Append recording complete | API | New text appended to textarea with `\n` | Same fade-in effect on appended text |
| Click "Descartar grabacion" | Click (when text present) | Confirm dialog → clear textarea | "Seguro que deseas descartar el texto transcrito?" |

### Permission Handling

- Browser prompts for microphone permission on first click
- If denied: error state with instruction card: `"Permite el acceso al microfono en la configuracion de tu navegador"` with browser-specific icon

### Animations/Transitions

- Idle → recording: pulse ring `animate-ping` 200ms to appear, sound wave bars bounce with stagger
- Processing: mic button icon swaps to `Loader2 animate-spin` 200ms transition
- Transcription text fill: word-by-word appearance `opacity 0 → 1` with 30ms inter-word delay
- Textarea highlight: `bg-teal-50` flash 500ms ease-in-out
- Template chips: scale in `0.8 → 1` staggered 50ms each

---

## Loading & Error States

### Loading State
- `processing` state: mic button shows spinner, textarea disabled and shows italic placeholder
- Template variable extraction: template status chips show skeleton pulse `h-5 w-16 animate-pulse bg-gray-100 rounded-full`

### Error State

| Error | Message |
|-------|---------|
| Microphone permission denied | `"Acceso al microfono denegado. Habilita el microfono en los ajustes del navegador."` |
| No audio detected | `"No se detecto audio en la grabacion. Intenta de nuevo."` |
| Transcription failed | `"Error al transcribir. Verifica tu conexion e intenta de nuevo."` |
| Audio too short (< 1s) | `"La grabacion es muy corta. Habla por al menos 2 segundos."` |
| Audio too large | `"La grabacion supera el limite. Divide en fragmentos mas cortos."` |

Error messages shown below the mic button in `text-xs text-red-600`. Mic button enters `error` state with `XCircle` icon.

### Empty State
- Textarea empty before recording: standard placeholder `"Escribe o dicta las notas de evolucion clinica..."` in `text-gray-300`

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Mic button `w-14 h-14` larger touch target. Recording duration prominent `text-base`. Template status chips scroll horizontally. "Agregar mas" button text shortens to "Agregar". |
| Tablet (640-1024px) | Standard layout. Mic button `w-12 h-12`. All elements on same row. |
| Desktop (> 1024px) | Same as tablet. Textarea wider. |

**Tablet priority:** Critical — doctors dictate on tablets at chairside. Mic button must be large, clearly visible, and fingertip-tappable. Minimum touch target `w-12 h-12` = 48px.

---

## Accessibility

- **Focus order:** Mic button → Re-record button (when visible) → Textarea → Character count (non-interactive)
- **Screen reader:** Mic button `aria-label` changes per state (see Component 1 table). `aria-live="polite"` on recording state display for real-time announcements. `aria-live="assertive"` when transcription arrives: "Transcripcion lista. Texto agregado al campo de notas." Textarea `aria-describedby` pointing to character counter.
- **Keyboard navigation:** Space/Enter activates mic button. F key not reserved — standard key navigation applies.
- **Color contrast:** Red recording state `bg-red-500` with white icon — white on red-500 is 4.94:1 (passes AA). Processing teal-100 with teal-600 text — meets 4.5:1.
- **Motion:** Pulse and bounce animations respect `prefers-reduced-motion: reduce` — replace with static indicators.
- **Language:** All state labels, error messages, and template chip labels in es-419.

---

## Design Tokens

**Colors:**
- Mic idle: `border-gray-300 text-gray-400`
- Mic recording: `bg-red-500 border-red-500 text-white`
- Mic processing: `bg-teal-100 border-teal-300 text-teal-600`
- Mic complete: `bg-green-100 border-green-400 text-green-600`
- Mic error: `bg-red-100 border-red-300 text-red-600`
- Recording pulse ring: `bg-red-400/30`
- Sound wave bars: `bg-red-400`
- Textarea transcription highlight: `bg-teal-50`
- Template chip filled: `bg-green-100 text-green-700`
- Template chip missing: `bg-amber-100 text-amber-700`

**Typography:**
- Recording duration: `text-sm font-mono text-red-600`
- State label: `text-xs text-gray-500`
- Error: `text-xs text-red-600`
- Template chip: `text-xs font-medium px-2 py-0.5 rounded-full`
- Character counter: `text-xs text-gray-400`

**Spacing:**
- Voice control bar: `flex items-center gap-3 mt-2`
- Mic button: `w-12 h-12` with `relative` parent for pulse ring
- Template status bar: `flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100`

---

## Implementation Notes

**Dependencies (npm):**
- Browser native `MediaRecorder API` — no library needed for recording
- `lucide-react` — Mic, MicOff, Loader2, CheckCircle2, XCircle, Plus
- `framer-motion` — animations

**File Location:**
- Component: `src/components/clinical/VoiceEvolution.tsx`
- Sub-components: `src/components/clinical/VoiceMicButton.tsx`, `src/components/clinical/TemplateVariableFillStatus.tsx`
- Hook: `src/hooks/useVoiceRecorder.ts`
- API: `src/lib/api/voice.ts`

**Custom Hook: `useVoiceRecorder`**

```typescript
export function useVoiceRecorder() {
  const [state, setState] = useState<RecordingState>('idle');
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    // ... chunk collection, auto-stop at 300s
  };

  const stopRecording = () => { /* ... */ };
  return { state, audioBlob, duration, startRecording, stopRecording };
}
```

**Integration with Form:**

```typescript
// In RecordCreate or RecordEdit form component
const { setValue } = useForm();

<VoiceEvolution
  activeTemplate={selectedTemplate}
  onTranscriptionComplete={(text) => {
    const current = getValues('evolucion_nota');
    setValue('evolucion_nota', current ? `${current}\n${text}` : text);
  }}
/>
```

---

## Test Cases

### Happy Path
1. Doctor dictates evolution note
   - **Given:** Clinical record create form open, no template active
   - **When:** Doctor clicks mic, speaks "Paciente refiere dolor leve en zona posterior inferior derecha, examen clinico sin hallazgos relevantes", clicks stop
   - **Then:** Text transcribed, textarea filled with Spanish text, doctor edits slightly and saves record

2. Doctor dictates with active template
   - **Given:** "Revision Periodontal" template active with 4 variables
   - **When:** Doctor dictates note including variable values
   - **Then:** Transcription fills textarea, 3/4 template variables filled (green chips), 1 missing (amber chip), doctor fills missing manually

### Edge Cases
1. Microphone permission denied
   - **Given:** User has not granted mic permission
   - **When:** Mic button clicked
   - **Then:** Browser permission dialog appears; if denied: error state with instructions to enable in browser settings

2. Re-record appends text
   - **Given:** First transcription in textarea "Examen clinico normal."
   - **When:** Doctor clicks "Agregar mas por voz", dictates more
   - **Then:** Second transcription appended with newline: "Examen clinico normal.\nSe prescribio ibuprofeno 400mg cada 8 horas."

### Error Cases
1. Transcription API timeout
   - **Given:** Slow connection
   - **When:** Audio sent but no response in 15s
   - **Then:** Error state "Error al transcribir..." mic button shows X icon, user can click to retry

2. Empty recording (user clicks stop immediately)
   - **Given:** Recording started, stopped after 0.5s
   - **When:** Blob sent to API
   - **Then:** API returns "audio too short" error → message "La grabacion es muy corta. Habla por al menos 2 segundos."

---

## Acceptance Criteria

- [ ] Microphone button with 5 distinct visual states (idle/recording/processing/complete/error)
- [ ] Recording pulse ring animation during active recording
- [ ] Duration counter during recording (MM:SS)
- [ ] Auto-stop at 5 minutes with user warning at 4:30
- [ ] Transcribed text fills textarea with word-by-word fade-in effect
- [ ] If active template: template variables auto-extracted from transcription
- [ ] Template variable status chips (green filled / amber missing)
- [ ] "Agregar mas por voz" re-record button appends to existing text
- [ ] Manual editing of textarea always possible after transcription
- [ ] All error types handled with Spanish messages
- [ ] Mic permission denied: actionable error message
- [ ] Mobile: larger touch target, prominent duration counter
- [ ] Accessibility: ARIA live regions, state-based aria-labels, reduced motion support
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
