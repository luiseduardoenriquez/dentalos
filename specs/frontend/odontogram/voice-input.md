# Entrada de Voz para Odontograma — Frontend Spec

## Overview

**Screen:** Voice recording button and real-time transcription display integrated into the odontogram view. A microphone button with recording animation triggers audio capture. Live transcription text appears below the odontogram as the user speaks. Visual feedback tracks the pipeline states: listening → processing → parsed. Feature is gated behind the AI Voice add-on subscription ($10/doctor/month). Disabled and replaced with an upsell prompt for tenants without the add-on.

**Route:** Embedded component within `/patients/{id}/odontogram` (FE-OD-01 classic-grid or FE-OD-02 anatomic-arch)

**Priority:** High

**Backend Specs:**
- `specs/voice/V-01` — Voice capture session initiation
- `specs/voice/V-02` — Audio streaming and Whisper transcription

**Dependencies:**
- `specs/frontend/odontogram/classic-grid.md` (FE-OD-01) — host view for classic mode
- `specs/frontend/odontogram/voice-review.md` (FE-OD-VR, FE-V-02) — next step after parsing
- `specs/frontend/odontogram/toolbar.md` (FE-OD-07) — microphone button lives in toolbar
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Click microphone button in odontogram toolbar (FE-OD-07)
- Doctor starts dictation during clinical examination

**Exit Points:**
- Stop recording → transitions automatically to voice review (FE-V-02) when parsing completes
- Cancel recording → discard audio → return to odontogram normal state
- Plan gate (no add-on) → upsell modal shown → plan upgrade page

**User Story:**
> As a doctor with the AI Voice add-on, I want to dictate odontogram findings by speaking naturally ("caries en el 16 oclusal, fractura en el 21") so that I can annotate the odontogram hands-free while examining the patient, without touching the screen.

**Roles with access:** doctor (with AI Voice add-on), clinic_owner (with AI Voice add-on)
**Plan gate:** Starter+ with AI Voice add-on OR Pro + AI Voice add-on

---

## Layout Structure

```
--- Odontogram view with voice active ---
+----------------------------------------------------------+
|  [Toolbar: ... [🎤 Voz] ...]                            |
+----------------------------------------------------------+
|  [Odontogram Grid — dimmed during recording]            |
|                                                          |
|  +----------------------------------------------------+  |
|  |  🔴 GRABANDO...   [■ Detener]        00:15        |  |
|  |  ─────────────────────────────────────────────────  |  |
|  |  "caries en el diente dieciséis oclusal..."        |  |
|  |  (live transcription scrolls here)                 |  |
|  |  ▊ (cursor blinks while transcribing)              |  |
|  +----------------------------------------------------+  |
|                                                          |
|  [Procesando IA... ████░░░░░░]  (shown after stop)    |
+----------------------------------------------------------+
```

**Sections:**
1. Microphone button in toolbar (always visible when add-on active)
2. Recording panel — slides up from bottom when recording starts
3. Live transcription display — real-time text from Whisper
4. Timer and stop button
5. Processing indicator — shown between stop and FE-V-02 review

---

## UI Components

### Component 1: VoiceMicrophoneButton

**Type:** Toggle icon button in odontogram toolbar

**States:**

| State | Visual | Label |
|-------|--------|-------|
| Idle (add-on active) | `Mic` icon, `text-gray-500 hover:text-primary-600` | "Voz" |
| Recording | `MicOff` icon, pulsing red `animate-pulse text-red-600` | "Detener" |
| Processing | `Loader2` icon, spinning `text-amber-500` | "Procesando..." |
| No add-on | `Mic` icon, `text-gray-300 cursor-not-allowed` | "Voz (requiere add-on)" |

**Size:** 44px minimum touch target, `w-10 h-10 rounded-lg`
**No add-on behavior:** Click opens `VoiceAddOnUpsellModal` (see Component 6)

**Recording pulse animation:**
```css
@keyframes pulse-ring {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 12px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}
.recording-pulse { animation: pulse-ring 1.5s ease-out infinite; }
```

### Component 2: RecordingPanel

**Type:** Bottom panel slide-up

**Layout:** Full-width panel, 160px height, slides up from bottom of odontogram area
**Background:** `bg-gray-900 text-white rounded-t-2xl shadow-2xl`

**Content:**
- Recording indicator: `🔴` animated dot + "GRABANDO" label in `text-xs font-bold tracking-widest`
- Timer: `00:00` counting up, monospace font `text-xl font-mono text-white`
- "Detener" button: `bg-red-600 text-white h-10 px-4 rounded-lg` with `Square` icon
- "Cancelar" text button: `text-gray-400 text-sm underline`
- Max recording: 120 seconds — auto-stops at limit with warning at 90s ("Grabación terminará en 30 segundos")

**Audio level waveform:**
- 20 thin vertical bars `h-6 bg-red-400 rounded-full mx-0.5`
- Heights vary in real-time based on microphone input amplitude (Web Audio API `AnalyserNode`)
- Bars animate at 60fps using `requestAnimationFrame`

### Component 3: LiveTranscriptionDisplay

**Type:** Scrollable text area with live streaming text

**Content:**
- Live text: Whisper transcription streamed via WebSocket / SSE as audio is processed
- Cursor blink: `▊` character with `animate-pulse` appended to current end of text
- Auto-scroll: scrolls to bottom as new text arrives
- Font: `text-base font-mono text-white` on dark panel background, or `text-gray-800` in light mode variant
- Max height: `max-h-20 overflow-y-auto` (approximately 3 lines visible)
- Placeholder before first words: `text-gray-500 italic` "Empieza a hablar..."

**Streaming behavior:**
- Backend streams partial transcription via SSE (`/api/v1/voice/stream/{sessionId}`)
- Each SSE `data:` event appends words to the displayed text
- Full sentences confirmed with punctuation when Whisper confidence is high

### Component 4: ProcessingIndicator

**Type:** Progress bar with status label — shown after recording stops, before FE-V-02 loads

**States:**
1. "Finalizando grabación..." — brief (< 1s)
2. "Transcribiendo audio..." — `text-amber-600`, progress bar fills to 40%
3. "Analizando con IA..." — `text-blue-600`, progress bar fills to 80%
4. "Preparando revisión..." — `text-primary-600`, progress bar fills to 100%
5. → Automatically transitions to FE-V-02 when API returns

**Progress bar:** Indeterminate (animated left-to-right shimmer) since actual duration varies, but percentages are simulated for UX reassurance.

### Component 5: VoicePermissionPrompt

**Type:** Modal (shown once on first use)

**Trigger:** Before first recording, browser microphone permission not yet granted
**Content:** "DentalOS necesita acceso al micrófono para la entrada de voz." + explanation + "Permitir acceso" button
**Browser API:** `navigator.mediaDevices.getUserMedia({ audio: true })`
**Permission denied:** Toast "Acceso al micrófono denegado. Ve a la configuración del navegador para habilitarlo."

### Component 6: VoiceAddOnUpsellModal

**Type:** Modal — shown when doctor without add-on clicks mic button

**Content:**
- Icon: `Sparkles` in `text-primary-600 w-12 h-12`
- Title: "Voz con IA — Add-on Profesional"
- Description: "Dicta hallazgos odontológicos en voz natural. Claude AI los convierte en anotaciones del odontograma automáticamente. Ahorra 3–5 minutos por paciente."
- Price: "$10/doctor/mes"
- Features list: 3 bullet points (dictado libre, transcripción Whisper, revisión antes de aplicar)
- CTA: "Activar add-on" → `/settings/billing?addon=ai_voice`
- Secondary: "Quizás después" → close modal

---

## Form Fields

Not applicable — voice input is audio capture, no typed form fields.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Initiate voice session | `/api/v1/voice/sessions` | POST | `specs/voice/V-01` | none |
| Stream audio (WebSocket) | `wss://api/v1/voice/sessions/{id}/stream` | WS | `specs/voice/V-02` | none |
| Get transcription SSE | `/api/v1/voice/sessions/{id}/transcription` | GET (SSE) | `specs/voice/V-02` | none |
| Stop session | `/api/v1/voice/sessions/{id}/stop` | POST | `specs/voice/V-01` | none |
| Cancel session | `/api/v1/voice/sessions/{id}/cancel` | DELETE | `specs/voice/V-01` | none |
| Check add-on status | (from auth/tenant context) | — | `specs/auth/me.md` | 10min |

### State Management

**Local State (useState):**
- `isRecording: boolean`
- `isParsing: boolean`
- `sessionId: string | null`
- `transcriptionText: string`
- `recordingSeconds: number`
- `hasPermission: boolean | null` — microphone permission state

**Global State (Zustand):**
- `voiceStore.isVoiceActive: boolean` — prevents concurrent recordings
- `voiceStore.sessionId: string | null`
- `authStore.tenant.addons` — includes `ai_voice` flag

**Server State (TanStack Query):**
- No TanStack Query — voice uses WebSocket + SSE (real-time, not REST polling)
- After session completes: navigate to FE-V-02 and pass `sessionId` as URL param

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click mic button (add-on active) | Click | Requests mic permission, starts session | Permission prompt if needed, then recording panel slides up |
| Grant mic permission | Browser prompt | Recording starts | Panel animates in, pulse begins |
| Click "Detener" | Click | Stop recording, begin processing | Button spinner, progress indicator |
| Click "Cancelar" | Click | Cancel session, return to normal | Panel slides down, DELETE session |
| Auto-stop at 120s | Timer | Recording stops | Warning at 90s: "Grabación termina en 30s" |
| Click mic button (no add-on) | Click | Upsell modal | Modal fades in |
| Processing completes | API response | Navigate to FE-V-02 | Progress bar fills → transition |

### Animations/Transitions

- Recording panel: slides up from bottom 250ms spring
- Mic button pulse: continuous red glow ring while recording
- Waveform bars: 60fps amplitude animation via requestAnimationFrame
- Transcription text: words appear left-to-right, streaming
- Processing indicator: shimmer left-to-right progress bar
- Panel close (cancel): slides down 200ms

---

## Loading & Error States

### Loading State
- Initiating session: mic button shows `Loader2` spinner for 1–2s before recording starts

### Error State
- Microphone permission denied: toast "Acceso al micrófono denegado. Actívalo en la configuración del navegador."
- Session init failure: toast "Error al iniciar la sesión de voz. Intenta de nuevo."
- WebSocket disconnect during recording: toast "Conexión interrumpida. La grabación se perdió. Intenta de nuevo." — panel closes
- Transcription service error (Whisper unavailable): toast "El servicio de transcripción no está disponible temporalmente."
- Parsing error (Claude API fail): toast "Error al analizar el texto. Puedes ingresar los hallazgos manualmente."

### Empty State
- No audio detected (silence for 10s): gentle prompt "¿Empezaste a hablar? No detectamos audio. Verifica tu micrófono." with "Cancelar" button

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Recording panel full-width, 200px height. Transcription text 2 lines. Waveform simplified (10 bars). |
| Tablet (640-1024px) | Recording panel full-width. Primary use case — doctor dictates while examining patient. 44px mic button. Waveform 20 bars. |
| Desktop (> 1024px) | Recording panel full-width at bottom of odontogram section. All features as designed. |

**Tablet priority:** Critical — the voice feature exists specifically for tablet-based clinical examination. Must work reliably on iPad/Android tablets.

---

## Accessibility

- **Focus order:** Mic button in toolbar → stop button (when recording) → cancel button
- **Screen reader:** Mic button `aria-label="Activar entrada de voz"` (idle) / `aria-label="Detener grabación de voz"` (recording). Recording panel `role="status"` `aria-live="polite"` announces "Grabación iniciada". Transcription `aria-live="polite"` streams transcribed text to screen reader. Processing states announced via `aria-live="assertive"`. Timer `aria-label="Tiempo de grabación: {mm:ss}"`.
- **Keyboard navigation:** Tab to mic button, Enter/Space to start/stop recording. ESC cancels active recording.
- **Non-audio alternative:** If microphone unavailable, the standard odontogram condition entry (click tooth → condition panel) remains fully functional — voice is an enhancement, not a replacement.
- **Language:** All labels, prompts, error messages in es-419.

---

## Design Tokens

**Colors:**
- Recording panel: `bg-gray-900 text-white`
- Recording dot: `bg-red-500 animate-pulse`
- Waveform bars: `bg-red-400`
- Transcription text: `text-white` (on dark panel) / `text-gray-800` (light mode)
- Processing bar: `bg-primary-500`
- Stop button: `bg-red-600 hover:bg-red-700`
- Timer: `text-white font-mono`
- Upsell modal accent: `text-primary-600`

**Typography:**
- Recording label: `text-xs font-bold tracking-widest text-red-400`
- Timer: `text-xl font-mono text-white`
- Transcription: `text-base font-mono text-white`
- Placeholder: `text-gray-500 italic text-sm`

**Spacing:**
- Recording panel padding: `px-4 py-4`
- Panel height: `h-40` (recording) `h-20` (processing)
- Mic button size: `w-10 h-10`
- Waveform bar width: `w-1 mx-0.5`

**Border Radius:**
- Recording panel: `rounded-t-2xl`
- Mic button: `rounded-lg`
- Stop button: `rounded-lg`
- Processing bar: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- Web Audio API (`AudioContext`, `AnalyserNode`) — waveform visualization (browser built-in)
- `navigator.mediaDevices.getUserMedia` — microphone access (browser built-in)
- `EventSource` API — SSE for transcription streaming (browser built-in)
- WebSocket API — audio streaming to backend (browser built-in)
- `lucide-react` — Mic, MicOff, Square, Loader2, Sparkles, X
- `framer-motion` — recording panel slide animation

**File Location:**
- Component: `src/components/voice/VoiceInputButton.tsx`
- Sub-components: `src/components/voice/RecordingPanel.tsx`, `src/components/voice/LiveTranscription.tsx`, `src/components/voice/AudioWaveform.tsx`, `src/components/voice/VoiceAddOnUpsellModal.tsx`
- Hook: `src/hooks/useVoiceRecording.ts`
- Store: `src/stores/voiceStore.ts`

**Hooks Used:**
- `useAuth()` — user role + tenant add-on flags
- `useVoiceRecording()` — custom hook managing WebSocket, MediaRecorder, SSE
- `useAudioAnalyser(streamRef)` — custom hook for waveform visualization
- `useVoiceStore()` — global voice state

**Plan gate check:**
```typescript
const hasVoiceAddon = authStore.tenant?.addons?.includes('ai_voice') ?? false;
```

**Audio streaming approach (V1):**
- `MediaRecorder` with `timeslice: 250ms` (send audio chunks every 250ms via WebSocket)
- Backend feeds chunks to Whisper streaming API
- SSE endpoint returns partial transcriptions as Whisper processes them

---

## Test Cases

### Happy Path
1. Doctor activates voice, dictates findings
   - **Given:** Doctor has AI Voice add-on, on odontogram view
   - **When:** Click mic → grant permission → say "caries en el 16 oclusal, extracción indicada en 38" → click Detener
   - **Then:** Transcription displays live, processing indicator runs, navigates to FE-V-02 with parsed findings

2. First use — permission prompt
   - **Given:** First time using voice on this browser
   - **When:** Click mic button
   - **Then:** Browser permission prompt appears → on grant → recording starts

### Edge Cases
1. Doctor clicks mic on slow connection
   - **Given:** WebSocket connection takes 3s to establish
   - **When:** Mic button clicked
   - **Then:** Button shows spinner for up to 3s, then recording starts — NOT double-started if clicked again

2. Auto-stop at 120 seconds
   - **Given:** Doctor recording for 90 seconds
   - **When:** Timer reaches 90s
   - **Then:** Warning overlay "Grabación termina en 30 segundos" appears. At 120s, auto-stops and transitions to processing.

### Error Cases
1. Browser microphone permission denied
   - **Given:** Browser previously denied microphone
   - **When:** Click mic button
   - **Then:** Toast "Acceso al micrófono denegado. Ve a Configuración > Privacidad > Micrófono para habilitar."

2. No add-on
   - **Given:** Tenant has no AI Voice add-on
   - **When:** Click mic button (grayed out)
   - **Then:** Upsell modal opens, recording does NOT start

---

## Acceptance Criteria

- [ ] Mic button visible in odontogram toolbar when add-on active
- [ ] Mic button grayed out and triggers upsell modal when no add-on
- [ ] Upsell modal with description, price, CTA to billing
- [ ] Browser microphone permission requested on first click
- [ ] Permission denied handled gracefully with toast
- [ ] Recording panel slides up on recording start
- [ ] Pulsing red dot animation during recording
- [ ] Recording timer counting up (mm:ss)
- [ ] Audio waveform visualization (amplitude bars)
- [ ] Live transcription text streams during recording
- [ ] "Detener" button stops recording
- [ ] "Cancelar" discards recording and closes panel
- [ ] Auto-stop at 120 seconds with 30s warning
- [ ] Processing indicator states (transcribing → analyzing → ready)
- [ ] Transition to FE-V-02 on successful parse
- [ ] Error handling for WebSocket disconnect
- [ ] Error handling for Whisper service unavailable
- [ ] Odontogram remains accessible (normal mode) when voice not active
- [ ] Tablet-optimized: touch targets 44px, waveform visible on small screens
- [ ] ESC key cancels active recording
- [ ] ARIA: live region for transcription, button labels
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
