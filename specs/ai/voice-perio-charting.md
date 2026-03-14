# AI Voice Perio Charting — Spec (AI-07)

> **Spec ID:** AI-07
> **Status:** Draft
> **Last Updated:** 2026-03-14
> **Feature Flag:** `ai_voice_perio` (requires `voice_enabled`)
> **Add-on:** AI Voice ($10/doc/mo) — bundled with Voice-to-Odontogram
> **Sprint:** S37-38 (Tier 3 — Leapfrog)
> **Priority:** High

---

## 1. Overview

**Feature:** During a periodontal examination, the doctor dictates probing depth measurements per tooth and site using natural speech. The AI Voice pipeline captures audio, transcribes it in real-time, extracts numeric measurements, and auto-fills the corresponding sites in the periodontal charting UI — eliminating the need for a second person to manually record values.

**Example dictation:**
> "Diente 16, vestibular: 3, 2, 3. Palatino: 4, 5, 3."

This auto-fills all 6 sites (3 buccal + 3 palatal) for tooth 16 in the active `PeriodontalRecord`.

**Domain:** voice / periodontal

**Regulatory disclaimer (always shown in UI):**
> "Los valores son sugerencias de IA. Verifique antes de guardar."

### Dependencies

- `specs/voice/voice-capture.md` (V-01) — Voice session creation
- `specs/voice/voice-transcription.md` (V-02) — Whisper transcription
- `specs/periodontal/periodontal-charting.md` — PeriodontalRecord, PeriodontalMeasurement models
- `backend/app/services/ai_claude_client.py` — Claude extraction
- `backend/app/models/tenant/periodontal_record.py`
- `backend/app/models/tenant/periodontal_measurement.py`

### Architecture Diagram

```
Doctor speaks ──→ V-01 (capture) ──→ V-02 (Whisper transcribe)
                                              │
                                              ▼
                                    AI-07: Claude extraction
                                    (tooth, surface, depths[6])
                                              │
                                    ┌─────────▼─────────┐
                                    │  FastAPI handler   │
                                    │  validates FDI +   │
                                    │  depth ranges      │
                                    └─────────┬─────────┘
                                              │ WebSocket / SSE
                                              ▼
                                    Frontend perio chart
                                    (sites auto-filled,
                                     highlighted yellow)
```

---

## 2. Database Schema

### Reuses Existing Tables

AI-07 writes directly into the existing periodontal schema — no new tables required.

**`periodontal_records`** (existing) — one record per perio exam session.
**`periodontal_measurements`** (existing) — one row per tooth per record, stores `probing_depths INTEGER[6]`, `bleeding_points BOOLEAN[6]`, `mobility INTEGER`, etc.

### New Column: `periodontal_measurements.voice_filled`

```sql
ALTER TABLE periodontal_measurements
    ADD COLUMN voice_filled BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN voice_filled_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN voice_session_id UUID REFERENCES voice_sessions(id) DEFAULT NULL;
```

This tracks which measurements were captured via voice vs. keyboard, useful for quality audits.

### New Table: `voice_perio_extractions` (audit trail)

```sql
CREATE TABLE voice_perio_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Context
    session_id      UUID NOT NULL REFERENCES voice_sessions(id),
    perio_record_id UUID NOT NULL REFERENCES periodontal_records(id),
    patient_id      UUID NOT NULL REFERENCES patients(id),
    doctor_id       UUID NOT NULL REFERENCES users(id),

    -- Raw transcription
    raw_text        TEXT NOT NULL,

    -- Parsed result (array of extraction objects)
    extracted_data  JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Model tracking
    model_used      VARCHAR(50) DEFAULT NULL,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    processing_ms   INTEGER DEFAULT NULL,

    -- Status
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'completed', 'failed', 'partial')),
    error_message   TEXT DEFAULT NULL,

    -- Soft delete
    is_active       BOOLEAN NOT NULL DEFAULT true,
    deleted_at      TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX idx_voice_perio_extractions_session ON voice_perio_extractions(session_id);
CREATE INDEX idx_voice_perio_extractions_record  ON voice_perio_extractions(perio_record_id);
```

**`extracted_data` element structure:**

```json
{
  "tooth_fdi": 16,
  "surface": "buccal",
  "depths": [3, 2, 3],
  "confidence": 0.97,
  "applied": true,
  "measurement_id": "uuid-of-periodontal_measurement-row"
}
```

`surface` values: `"buccal"` | `"lingual"` | `"palatal"` | `"mesial"` | `"distal"`

---

## 3. API Endpoints

### POST `/api/v1/voice/perio-extractions`

Triggered after Whisper produces a transcript segment. Runs Claude extraction synchronously (target < 800 ms).

**Auth:** `doctor`, `assistant`
**Feature gate:** `ai_voice_perio`

**Request body:**

```json
{
  "session_id": "uuid",
  "perio_record_id": "uuid",
  "text": "Diente 16 vestibular 3, 2, 3. Palatino 4, 5, 3.",
  "auto_apply": true
}
```

**Response `201`:**

```json
{
  "extraction_id": "uuid",
  "extractions": [
    {
      "tooth_fdi": 16,
      "surface": "buccal",
      "depths": [3, 2, 3],
      "confidence": 0.97,
      "applied": true,
      "measurement_id": "uuid"
    },
    {
      "tooth_fdi": 16,
      "surface": "palatal",
      "depths": [4, 5, 3],
      "confidence": 0.95,
      "applied": true,
      "measurement_id": "uuid"
    }
  ],
  "unrecognized_segments": []
}
```

If `auto_apply = true`, the service immediately updates `periodontal_measurements` rows and sets `voice_filled = true`.

**Error `422`:** Tooth FDI out of range, depth value > 15 mm.
**Error `409`:** Site already manually entered by keyboard (requires `force_overwrite: true` to proceed).

---

### GET `/api/v1/voice/perio-extractions/{extraction_id}`

Returns full extraction record with status and applied flag per site.

**Auth:** `doctor`, `assistant`

---

### POST `/api/v1/voice/perio-extractions/{extraction_id}/apply`

Manually applies a pending extraction (when `auto_apply = false`).

**Auth:** `doctor`

---

## 4. Claude Prompt Design

**Model:** `claude-haiku-4-20250514` (low latency, numeric extraction)
**Temperature:** 0 (deterministic)
**Max tokens:** 400

**System prompt:**

```
You are a dental assistant parsing periodontal probing dictation into structured data.
Extract tooth number (FDI notation, 11-48), surface (buccal/lingual/palatal/mesial/distal),
and exactly 3 probing depth integers per surface (in millimeters).

Output ONLY a JSON array. No explanation. No markdown.

Rules:
- FDI tooth numbers: 11-18, 21-28, 31-38, 41-48
- Depth values: 1-15 mm. If a value seems implausible, flag it.
- Map Spanish surface names: vestibular→buccal, palatino→palatal, lingual→lingual,
  mesial→mesial, distal→distal
- If a surface has fewer than 3 values, set missing values to null.
- confidence: 0.0-1.0 based on clarity of dictation.

Output schema:
[{"tooth_fdi": 16, "surface": "buccal", "depths": [3, 2, 3], "confidence": 0.97}]
```

**User message template:**

```
Transcription: "{raw_text}"
Patient's active quadrant context (optional): "{quadrant_hint}"
```

**Validation after extraction:**
- `tooth_fdi` must match FDI regex `^[1-4][1-8]$`
- Each depth: integer 1–15 (values > 12 flagged with `requires_confirmation: true`)
- Array length must be exactly 3; nulls allowed for partial dictations

---

## 5. Frontend

**Component:** `PerioChartVoiceMode` (extends existing `PeriodontalChart`)

**Location:** `frontend/components/periodontal/perio-chart-voice-mode.tsx`

### UX Flow

1. Doctor opens existing periodontal charting view for a patient.
2. Presses **"Iniciar dictado"** button (only visible if `ai_voice_perio` flag active).
3. Recording indicator appears — same waveform component as Voice-to-Odontogram.
4. As each tooth segment is dictated, UI highlights that tooth in the chart and fills values in **yellow** (pending confirmation color).
5. Doctor reviews — can edit any value inline. Confirmed values turn **green**.
6. Pressing **"Finalizar"** saves all voice-filled measurements to the record.

### State Management

```typescript
interface VoicePerioCaptureState {
  isRecording: boolean;
  activeToothFdi: number | null;
  pendingExtractions: PerioExtraction[];
  appliedCount: number;
  errorSegments: string[];
}
```

### Error Display

- Unrecognized segments shown in a warning list below the chart: "No se pudo interpretar: '{segment}'"
- Implausible values (> 12 mm) flagged with orange border — doctor must confirm before save.

---

## 6. Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `VOICE_PERIO_feature_disabled` | 403 | `ai_voice_perio` flag not active for tenant |
| `VOICE_PERIO_session_not_found` | 404 | Voice session ID not found |
| `VOICE_PERIO_record_not_found` | 404 | PeriodontalRecord not found |
| `VOICE_PERIO_invalid_fdi` | 422 | Tooth FDI out of valid range |
| `VOICE_PERIO_depth_out_of_range` | 422 | Depth value < 1 or > 15 mm |
| `VOICE_PERIO_site_conflict` | 409 | Site already has manually entered data |
| `VOICE_PERIO_extraction_failed` | 500 | Claude API error during extraction |

---

## 7. Test Plan

| # | Scenario | Expected |
|---|----------|----------|
| T1 | Dictate "Diente 11 vestibular 2 2 3" | Fills buccal sites [2,2,3] for tooth 11 |
| T2 | Dictate "16 palatino 4, 5, 3" | Fills palatal sites [4,5,3] for tooth 16 |
| T3 | Mixed quadrant in one segment | Extracts both teeth independently |
| T4 | Depth value of 14 mm | Marks site with `requires_confirmation: true` |
| T5 | Gibberish audio segment | `unrecognized_segments` populated, no writes |
| T6 | Auto-apply false, manual apply | Sites only filled after explicit apply call |
| T7 | Overwrite existing manual entry without flag | Returns 409 |
| T8 | Feature flag disabled | Returns 403 |
| T9 | Invalid FDI (e.g., tooth 19) | Returns 422 |
| T10 | Audit trail | `voice_perio_extractions` row created for every call |
