# AI Voice Clinical Notes Spec

> **Spec ID:** AI-03
> **Status:** Draft
> **Last Updated:** 2026-03-13
> **Feature Flag:** `ai_voice_notes` (requires `voice_enabled`)
> **Add-on:** AI Voice ($10/doc/mo) — bundled with Voice-to-Odontogram

---

## 1. Overview

**Feature:** Doctor dictates during or after a consultation. The existing Voice pipeline (V-01 capture, V-02 Whisper transcription) produces raw text. A new Claude structuring step converts that text into a **SOAP evolution note** (Subjective, Objective, Assessment, Plan) and auto-links FDI tooth numbers, CIE-10 diagnosis codes, and CUPS procedure codes mentioned in the dictation. The structured note is presented for doctor review before being persisted as a `clinical_records` row of type `evolution_note`.

**Domain:** voice / clinical

**Priority:** Critical (Tier 1 parity with Dentalink "Notas Clinicas")

**Dependencies:**
- V-01 (`specs/voice/voice-capture.md`) — Voice session creation
- V-02 (`specs/voice/voice-transcription.md`) — Whisper transcription
- V-03 (`specs/voice/voice-parse.md`) — Claude parse (odontogram findings)
- Clinical records (`backend/app/models/tenant/clinical_record.py`)
- Evolution templates (`backend/app/models/tenant/evolution_template.py`)
- AI Claude client (`backend/app/services/ai_claude_client.py`)
- CIE-10 catalog (`specs/catalogs/cie10.md`)
- CUPS catalog (`specs/catalogs/cups.md`)

### How It Extends the Existing Voice Pipeline

The existing pipeline is: **capture session (V-01) -> upload audio (V-02) -> Whisper transcribe -> Claude parse to odontogram findings (V-03) -> apply to odontogram (V-04)**.

AI Voice Clinical Notes adds a **parallel structuring path** branching after transcription:

```
                                   ┌─── V-03: Parse (odontogram findings) ─── V-04: Apply
Audio → V-01 → V-02 → Whisper ───┤
                                   └─── AI-03: Structure (SOAP note) ─── Doctor review ─── Save as evolution_note
```

The session context determines which path is taken:
- `context = "odontogram"` → V-03/V-04 path (existing)
- `context = "evolution"` → AI-03 path (this spec)
- Both paths share the same VoiceSession and VoiceTranscription models.

---

## 2. Database Schema

### New Table: `voice_clinical_notes` (tenant schema)

Stores the structured SOAP note output from Claude, linked to the voice session. Separate from `voice_parses` (which stores odontogram findings) because the output schema and downstream consumers are different.

```sql
CREATE TABLE voice_clinical_notes (
    -- Standard columns
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Foreign keys
    session_id UUID NOT NULL REFERENCES voice_sessions(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    doctor_id UUID NOT NULL REFERENCES users(id),

    -- Input
    input_text TEXT NOT NULL,

    -- SOAP structured output (JSONB)
    structured_note JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Auto-linked codes
    linked_teeth INTEGER[] DEFAULT '{}',
    linked_cie10_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    linked_cups_codes JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Template integration
    template_id UUID REFERENCES evolution_templates(id),
    template_mapping JSONB DEFAULT NULL,

    -- Processing state
    status VARCHAR(20) NOT NULL DEFAULT 'processing'
        CHECK (status IN ('processing', 'structured', 'reviewed', 'saved', 'failed')),

    -- Output destination (clinical_records.id after save)
    clinical_record_id UUID REFERENCES clinical_records(id),

    -- LLM metadata
    llm_model VARCHAR(50) NOT NULL,
    llm_cost_usd NUMERIC(10, 6),
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    prompt_version VARCHAR(50) NOT NULL,

    -- Doctor review metadata
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES users(id),
    review_edits JSONB DEFAULT NULL,

    -- Soft delete
    is_active BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_voice_clinical_notes_session ON voice_clinical_notes(session_id);
CREATE INDEX idx_voice_clinical_notes_patient ON voice_clinical_notes(patient_id);
CREATE INDEX idx_voice_clinical_notes_doctor ON voice_clinical_notes(doctor_id);
CREATE INDEX idx_voice_clinical_notes_status ON voice_clinical_notes(status);
CREATE INDEX idx_voice_clinical_notes_created ON voice_clinical_notes(created_at);
```

### `structured_note` JSONB Schema

```json
{
  "subjective": "Paciente refiere dolor en zona molar inferior derecha desde hace 3 dias, peor al masticar. Niega antecedentes de trauma.",
  "objective": "Se observa caries extensa en diente 46 cara oclusal con compromiso de dentina. Tejido gingival eritematoso alrededor de 46. Movilidad grado 0. Percusion positiva en 46.",
  "assessment": "Caries profunda en 46 con posible compromiso pulpar. Diagnostico diferencial: pulpitis irreversible vs. reversible.",
  "plan": "Radiografia periapical de 46. Si no hay compromiso periapical, restauracion con resina. Si hay compromiso, considerar tratamiento de conducto.",
  "additional_notes": "Paciente refiere alergia a la penicilina. Programar cita de control en 2 semanas."
}
```

### `linked_cie10_codes` JSONB Schema

```json
[
  {
    "code": "K02.1",
    "description": "Caries de la dentina",
    "tooth": 46,
    "confidence": 0.92,
    "raw_phrase": "caries extensa en diente cuarenta y seis con compromiso de dentina"
  }
]
```

### `linked_cups_codes` JSONB Schema

```json
[
  {
    "code": "232101",
    "description": "Obturacion dental con resina de foton",
    "tooth": 46,
    "confidence": 0.85,
    "raw_phrase": "restauracion con resina"
  }
]
```

### `template_mapping` JSONB Schema

When a template is selected, maps SOAP sections to template steps:

```json
{
  "template_id": "uuid",
  "template_name": "Nota de Evolucion - Operatoria",
  "step_mappings": [
    { "step_order": 1, "step_content_key": "motivo_consulta", "soap_source": "subjective" },
    { "step_order": 2, "step_content_key": "hallazgos", "soap_source": "objective" },
    { "step_order": 3, "step_content_key": "diagnostico", "soap_source": "assessment" },
    { "step_order": 4, "step_content_key": "plan_tratamiento", "soap_source": "plan" }
  ],
  "variable_values": {
    "diente_tratado": "46",
    "material": "resina compuesta"
  }
}
```

### VoiceSession Context Extension

The existing `voice_sessions.context` CHECK constraint already includes `'evolution'`. No schema change needed for the session model itself.

---

## 3. API Endpoints

### 3.1 Start Voice Clinical Note Session

Uses the existing V-01 endpoint with `context = "evolution"`:

```
POST /api/v1/patients/{patient_id}/voice/sessions
```

```json
{
  "context": "evolution",
  "notes": "Consulta control post operatorio extraccion 48"
}
```

No changes to V-01. The `context = "evolution"` value triggers the AI-03 structuring path downstream.

---

### 3.2 Submit Audio for Transcription

Uses the existing V-02 endpoint. No changes needed.

```
POST /api/v1/voice/sessions/{session_id}/audio
```

---

### 3.3 Structure Transcription into SOAP Note

```
POST /api/v1/patients/{patient_id}/voice/clinical-note
```

**Rate Limiting:**
- 30 requests per hour per user
- Rate limit key: `voice:clinical_note:{user_id}`
- LLM cost approximately $0.002-$0.01 per call (Claude Sonnet pricing)

#### Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant (assistant requires doctor supervision)
- **Tenant context:** Required — resolved from JWT
- **Feature flags:** `voice_enabled` AND `ai_voice_notes` must both be active

#### Request

**Headers:**

| Header | Required | Type | Description |
|--------|----------|------|-------------|
| Authorization | Yes | string | Bearer JWT token |
| Content-Type | Yes | string | application/json |

**URL Parameters:**

| Parameter | Required | Type | Constraints | Description |
|-----------|----------|------|-------------|-------------|
| patient_id | Yes | UUID v4 | Must exist in tenant, active | The patient |

**Request Body:**

```json
{
  "session_id": "uuid (required) — active voice session with context='evolution'",
  "template_id": "uuid (optional) — evolution template to map SOAP sections to",
  "override_text": "string (optional) — max 15000 chars, manually corrected transcription",
  "include_codes": "boolean (optional, default true) — whether to extract CIE-10 and CUPS codes",
  "patient_context": {
    "dentition_type": "string (optional) — enum: adult | pediatric | mixed",
    "age_years": "integer (optional)",
    "chief_complaint": "string (optional) — pre-fill for subjective section context"
  }
}
```

**Example Request:**

```json
{
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "template_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ef",
  "include_codes": true,
  "patient_context": {
    "dentition_type": "adult",
    "chief_complaint": "Dolor en molar inferior derecho"
  }
}
```

#### Response

**Status:** 200 OK

**Schema:**

```json
{
  "clinical_note_id": "uuid",
  "session_id": "uuid",
  "patient_id": "uuid",
  "status": "string",
  "structured_note": {
    "subjective": "string",
    "objective": "string",
    "assessment": "string",
    "plan": "string",
    "additional_notes": "string | null"
  },
  "linked_teeth": [46, 47],
  "linked_cie10_codes": [
    {
      "code": "string",
      "description": "string",
      "tooth": "integer | null",
      "confidence": "number (0.0-1.0)",
      "raw_phrase": "string"
    }
  ],
  "linked_cups_codes": [
    {
      "code": "string",
      "description": "string",
      "tooth": "integer | null",
      "confidence": "number (0.0-1.0)",
      "raw_phrase": "string"
    }
  ],
  "template_mapping": "object | null",
  "input_text": "string",
  "warnings": ["string"],
  "llm_model": "string",
  "llm_cost_usd": "number",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example Response:**

```json
{
  "clinical_note_id": "e5f6a7b8-c9d0-1234-ef56-789012345678",
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "structured",
  "structured_note": {
    "subjective": "Paciente refiere dolor en zona molar inferior derecha desde hace 3 dias, aumenta al masticar alimentos duros. Niega antecedentes de trauma reciente. Refiere alergia a penicilina.",
    "objective": "Se observa caries extensa en diente 46 cara oclusal con compromiso de dentina profunda. Tejido gingival eritematoso perimarginal en 46. Movilidad grado 0. Percusion vertical positiva. Prueba de vitalidad positiva con respuesta exagerada y prolongada.",
    "assessment": "Pulpitis irreversible sintomatica en diente 46 secundaria a caries profunda. CIE-10: K04.0.",
    "plan": "1. Radiografia periapical de 46 para evaluar compromiso periapical. 2. Tratamiento de conducto en 46 (CUPS 232301). 3. Restauracion definitiva posterior con corona. 4. Prescribir analgesico (ibuprofeno 400mg c/8h por 3 dias). 5. Control en 1 semana.",
    "additional_notes": "Paciente alergico a penicilina - usar clindamicina si se requiere antibiotico. Consentimiento informado firmado para endodoncia."
  },
  "linked_teeth": [46],
  "linked_cie10_codes": [
    {
      "code": "K04.0",
      "description": "Pulpitis",
      "tooth": 46,
      "confidence": 0.95,
      "raw_phrase": "pulpitis irreversible sintomatica en diente cuarenta y seis"
    },
    {
      "code": "K02.1",
      "description": "Caries de la dentina",
      "tooth": 46,
      "confidence": 0.90,
      "raw_phrase": "caries extensa con compromiso de dentina profunda"
    }
  ],
  "linked_cups_codes": [
    {
      "code": "232301",
      "description": "Tratamiento de conducto diente uniradicular",
      "tooth": 46,
      "confidence": 0.88,
      "raw_phrase": "tratamiento de conducto en cuarenta y seis"
    }
  ],
  "template_mapping": {
    "template_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ef",
    "template_name": "Nota de Evolucion - Endodoncia",
    "step_mappings": [
      { "step_order": 1, "step_content_key": "motivo_consulta", "soap_source": "subjective" },
      { "step_order": 2, "step_content_key": "hallazgos_clinicos", "soap_source": "objective" },
      { "step_order": 3, "step_content_key": "diagnostico", "soap_source": "assessment" },
      { "step_order": 4, "step_content_key": "plan_tratamiento", "soap_source": "plan" }
    ],
    "variable_values": {
      "diente_tratado": "46",
      "tipo_conducto": "uniradicular"
    }
  },
  "input_text": "El paciente viene por dolor en la zona molar inferior derecha...",
  "warnings": [],
  "llm_model": "claude-sonnet-4-20250514",
  "llm_cost_usd": 0.0045,
  "created_at": "2026-03-13T10:30:00Z"
}
```

#### Error Responses

##### 400 Bad Request
**When:** Invalid JSON, missing session_id, or session context is not `evolution`.

```json
{
  "error": "VOICE_invalid_session_context",
  "message": "La sesion de voz no tiene contexto 'evolution'. Use una sesion con contexto de evolucion para notas clinicas.",
  "details": {
    "session_context": "odontogram",
    "expected_context": "evolution"
  }
}
```

##### 402 Payment Required
**When:** Voice add-on or `ai_voice_notes` feature flag not active.

```json
{
  "error": "VOICE_addon_required",
  "message": "Las notas clinicas por voz requieren el complemento de Voz con IA activo.",
  "details": {
    "addon": "voice",
    "feature_flag": "ai_voice_notes",
    "upgrade_url": "/settings/billing/addons"
  }
}
```

##### 404 Not Found
**When:** Patient or session not found within the tenant.

##### 409 Conflict
**When:** No completed transcriptions in the session.

```json
{
  "error": "VOICE_no_completed_transcriptions",
  "message": "No hay transcripciones completadas en esta sesion. Espere a que el procesamiento de audio finalice.",
  "details": {
    "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
    "transcription_statuses": {
      "processing": 1,
      "completed": 0,
      "failed": 0
    }
  }
}
```

##### 422 Unprocessable Entity
**When:** Template not found, or override_text exceeds 15000 characters.

##### 429 Too Many Requests
**When:** Rate limit of 30/hour per user exceeded.

##### 502 Bad Gateway
**When:** Claude API unreachable or returns malformed output after retry.

```json
{
  "error": "VOICE_llm_unavailable",
  "message": "El servicio de estructuracion de notas clinicas no esta disponible. Intente nuevamente en unos momentos.",
  "details": {
    "retry_after_seconds": 30
  }
}
```

---

### 3.4 Get Structured Note

```
GET /api/v1/patients/{patient_id}/voice/clinical-note/{clinical_note_id}
```

**Status:** 200 OK

Returns the full `VoiceClinicalNoteResponse` schema (same as 3.3 response). Used for retrieving a previously structured note that the doctor wants to review or edit before saving.

**Error Responses:** 401, 403, 404 (standard).

---

### 3.5 Confirm and Save as Evolution Note

```
POST /api/v1/patients/{patient_id}/voice/clinical-note/{clinical_note_id}/save
```

**Rate Limiting:** Inherits global (100/min per user).

#### Request Body

```json
{
  "edited_note": {
    "subjective": "string (optional) — doctor-edited version",
    "objective": "string (optional)",
    "assessment": "string (optional)",
    "plan": "string (optional)",
    "additional_notes": "string (optional)"
  },
  "accepted_cie10_codes": ["K04.0"],
  "accepted_cups_codes": ["232301"],
  "accepted_teeth": [46],
  "appointment_id": "uuid (optional) — link to appointment"
}
```

If `edited_note` fields are omitted, the original AI-generated values are used. If provided, the doctor's edits override the AI output.

#### Response

**Status:** 201 Created

```json
{
  "clinical_record_id": "uuid",
  "clinical_note_id": "uuid",
  "status": "saved",
  "message": "Nota de evolucion guardada exitosamente.",
  "clinical_record": {
    "id": "uuid",
    "patient_id": "uuid",
    "doctor_id": "uuid",
    "type": "evolution_note",
    "content": {},
    "tooth_numbers": [46],
    "template_id": "uuid | null",
    "created_at": "string (ISO 8601 datetime)"
  }
}
```

#### Business Logic

1. Fetch the `voice_clinical_notes` record. Must be in `structured` status.
2. Merge doctor edits with AI-generated note. Store the diff in `review_edits` for audit.
3. Build the `content` JSONB for the `clinical_records` row:
   - If template was used: map SOAP sections to template steps using `template_mapping`.
   - If no template: store SOAP sections directly as content keys.
4. Create `clinical_records` row with `type = 'evolution_note'`, `content`, `tooth_numbers`, `template_id`, `doctor_id`, `patient_id`.
5. Update `voice_clinical_notes`: `status = 'saved'`, `clinical_record_id`, `reviewed_at`, `reviewed_by`, `review_edits`.
6. Write audit log.
7. Return 201 with the created clinical record.

#### Error Responses

##### 400 Bad Request
**When:** Note is already saved (status = `saved`).

```json
{
  "error": "VOICE_note_already_saved",
  "message": "Esta nota clinica ya fue guardada como registro de evolucion.",
  "details": {
    "clinical_record_id": "uuid",
    "saved_at": "2026-03-13T10:35:00Z"
  }
}
```

##### 404 Not Found
**When:** clinical_note_id not found or does not belong to the patient.

---

## 4. SOAP Note Structuring Logic

### Prompt Engineering

The SOAP structuring prompt is stored as a versioned template in `app/voice/prompts/clinical_note_soap_v1.txt`. It is NOT stored in the database to prevent prompt injection.

```
[SYSTEM]
Eres un asistente dental clinico especializado en documentacion medica odontologica en Colombia. Tu tarea es estructurar la transcripcion de dictado de un odontologo en una nota de evolucion con formato SOAP.

Reglas estrictas:
1. Estructura la informacion en exactamente 5 secciones: subjective, objective, assessment, plan, additional_notes.
2. subjective: Lo que el paciente reporta — motivo de consulta, sintomas, duracion, factores agravantes/atenuantes, antecedentes relevantes mencionados.
3. objective: Lo que el odontologo observa — hallazgos del examen clinico, pruebas realizadas, resultados. Usa terminologia clinica precisa.
4. assessment: Diagnostico o impresion diagnostica. Incluye codigos CIE-10 si los puedes inferir con confianza.
5. plan: Tratamiento propuesto, procedimientos, prescripciones, citas de control. Incluye codigos CUPS si los puedes inferir.
6. additional_notes: Cualquier informacion adicional relevante (alergias mencionadas, consentimientos, observaciones especiales). Puede ser null si no aplica.

Reglas de procesamiento:
7. Usa numeracion FDI (11-48 para permanentes, 51-85 para deciduos). Convierte numeros hablados a formato FDI (cuarenta y seis -> 46).
8. Detecta y aplica auto-correcciones del hablante ("no, quise decir", "perdon", "mejor dicho").
9. Filtra instrucciones al asistente (aspira, luz, pasa, alcanzame) y conversacion no clinica.
10. Si el odontologo menciona codigos CIE-10 o CUPS explicitamente, incluyelos. Si no, infierelos del contexto clinico con un nivel de confianza.
11. Devuelve UNICAMENTE JSON valido. Sin texto adicional, sin markdown, sin explicaciones.
12. Todo el texto debe estar en espanol (es-419) con terminologia medica colombiana.

Codigos CIE-10 dentales frecuentes:
- K00: Trastornos del desarrollo y erupcion de los dientes
- K01: Dientes incluidos e impactados
- K02: Caries dental (K02.0 esmalte, K02.1 dentina, K02.2 cemento)
- K03: Otras enfermedades de los tejidos duros (abrasion, erosion)
- K04: Enfermedades de la pulpa y tejidos periapicales (K04.0 pulpitis, K04.1 necrosis)
- K05: Gingivitis y enfermedades periodontales
- K06: Otros trastornos de la encia y reborde alveolar
- K07: Anomalias dentofaciales
- K08: Otros trastornos de los dientes y estructuras de soporte
- S02: Fracturas de huesos del craneo y cara

Codigos CUPS odontologicos frecuentes:
- 232101: Obturacion con resina
- 232201: Obturacion con amalgama
- 232301: Endodoncia uniradicular
- 232302: Endodoncia biradicular
- 232303: Endodoncia multiradicular
- 232401: Exodoncia simple
- 232501: Cirugia de tercer molar
- 234101: Profilaxis dental
- 234201: Detartraje supragingival
- 234301: Alisado radicular
- 237101: Corona metal-porcelana
- 237201: Nucleo de reconstruccion

{template_instructions}

Tipo de denticion del paciente: {dentition_type}
Edad del paciente: {age_years} anios
Queja principal (si se proporciono): {chief_complaint}

[USER]
Transcripcion del dictado clinico:
{input_text}

Responde con este JSON exacto:
{
  "structured_note": {
    "subjective": "string",
    "objective": "string",
    "assessment": "string",
    "plan": "string",
    "additional_notes": "string | null"
  },
  "linked_teeth": [integer],
  "linked_cie10_codes": [{"code": "string", "description": "string", "tooth": integer|null, "confidence": float, "raw_phrase": "string"}],
  "linked_cups_codes": [{"code": "string", "description": "string", "tooth": integer|null, "confidence": float, "raw_phrase": "string"}],
  "warnings": ["string"]
}
```

### Template Instructions Injection

When `template_id` is provided, the system fetches the `EvolutionTemplate` with its steps and injects additional instructions into `{template_instructions}`:

```
La clinica usa la siguiente plantilla de nota de evolucion. Organiza tu respuesta para que las secciones SOAP se mapeen a los pasos de la plantilla:

Plantilla: "{template_name}"
Pasos:
1. {step_1_content} -> mapea desde: subjective
2. {step_2_content} -> mapea desde: objective
3. {step_3_content} -> mapea desde: assessment
4. {step_4_content} -> mapea desde: plan

Si la plantilla tiene variables ([nombre_variable]), intenta extraer los valores del dictado y reportalos en el campo template_mapping.variable_values.
```

When no template is provided, `{template_instructions}` is set to an empty string.

### Model Selection

- **Primary model:** Claude Sonnet (for clinical accuracy — higher quality than Haiku for medical structuring)
- **Fallback:** Claude Haiku (if Sonnet is unavailable or tenant has cost constraints)
- The model is configurable per tenant in voice settings (V-05 extension)

---

## 5. Auto-Linking: FDI, CIE-10, CUPS Extraction

### 5.1 FDI Tooth Number Detection

The same logic as V-03, adapted for the SOAP structuring context:

- Spanish number words converted to integers (cuarenta y seis -> 46)
- FDI validation: permanent 11-48, deciduous 51-85
- Mixed dentition allows both ranges
- Self-corrections handled ("diente 36... no, 46" -> uses 46)
- Invalid numbers flagged in `warnings`, not rejected

All detected tooth numbers are collected into `linked_teeth[]` and cross-referenced against the structured note sections.

### 5.2 CIE-10 Diagnosis Extraction

Claude is instructed to identify CIE-10 codes from the clinical description. The extraction process:

1. **Explicit mentions:** Doctor says "K04 punto cero" or "codigo CIE diez K cero cuatro" -> captured directly.
2. **Implicit inference:** Doctor describes "caries profunda con compromiso de dentina" -> Claude infers K02.1 with confidence score.
3. **Validation:** Extracted codes are validated against the CIE-10 catalog in the database. Invalid codes are flagged in `warnings`.
4. **Confidence threshold:** Codes with confidence < 0.6 are included but marked with a warning.

Each linked code includes:
- `code`: Validated CIE-10 code
- `description`: Standard description from the catalog
- `tooth`: FDI tooth number if applicable (null for general diagnoses)
- `confidence`: 0.0-1.0 (LLM-generated)
- `raw_phrase`: The exact speech segment that triggered this extraction

### 5.3 CUPS Procedure Extraction

Same pattern as CIE-10 but for procedure codes:

1. **Explicit mentions:** Doctor says "realizar una obturacion con resina" -> Claude infers CUPS 232101.
2. **Treatment plan references:** "Necesita endodoncia" -> 232301/232302/232303 depending on tooth type.
3. **Validation:** Against CUPS catalog in the database.
4. **Specificity:** If the tooth type is known (e.g., molar vs premolar), Claude selects the most specific CUPS code.

---

## 6. Template Integration

### Matching Logic

When `template_id` is provided:

1. Fetch `EvolutionTemplate` with steps and variables from the tenant schema.
2. Inject template structure into the Claude prompt (see section 4).
3. Claude maps its SOAP output to the template step structure.
4. The `template_mapping` response field contains the mapping so the frontend can render the structured note using the template's visual layout.

### Variable Extraction

If the template defines variables (e.g., `[diente_tratado]`, `[material]`, `[tecnica_anestesica]`), Claude attempts to extract their values from the dictation:

- Variable name matching is fuzzy (e.g., variable `diente_tratado` matches "el diente que se trato fue el 46").
- If a required variable cannot be extracted, it is reported in `warnings` as "Variable requerida no encontrada: {variable_name}".
- The doctor can fill missing variables during the review step.

### Auto-Template Selection (Optional)

If `template_id` is omitted but the tenant has active evolution templates:

1. The system queries active templates for the tenant.
2. Based on the dictation content (procedure type, CUPS codes mentioned), Claude suggests the most appropriate template.
3. The suggestion is returned in the response but NOT auto-applied. The doctor can accept it in the review step.

---

## 7. Worker Message Format

For the async structuring path (used when the system opts for async processing of long transcriptions):

**Queue:** `clinical`
**Job type:** `voice_notes.structure`

```json
{
  "message_id": "uuid-v4",
  "tenant_id": "tn_abc123",
  "job_type": "voice_notes.structure",
  "payload": {
    "clinical_note_id": "uuid",
    "session_id": "uuid",
    "patient_id": "uuid",
    "doctor_id": "uuid",
    "input_text": "...",
    "template_id": "uuid | null",
    "include_codes": true,
    "patient_context": {
      "dentition_type": "adult",
      "age_years": 35,
      "chief_complaint": "Dolor en molar"
    },
    "llm_model": "claude-sonnet-4-20250514",
    "prompt_version": "clinical_note_soap_v1"
  },
  "priority": 5,
  "retry_count": 0,
  "max_retries": 3
}
```

**Worker behavior:**

1. Set `search_path` to tenant schema.
2. Fetch the `voice_clinical_notes` record by `clinical_note_id`. If status != `processing`, skip (idempotency).
3. Build Claude prompt with template instructions (if `template_id` provided).
4. Call Claude API synchronously within the worker.
5. Parse JSON response. Retry once on malformed JSON.
6. Validate FDI tooth numbers, CIE-10 codes, CUPS codes against catalogs.
7. Update `voice_clinical_notes` with structured output, linked codes, LLM metadata, `status = 'structured'`.
8. If Claude API fails after max retries: set `status = 'failed'`.
9. Write audit log (action: update, resource: voice_clinical_note, PHI: yes).

**Note:** For MVP, the structuring is done **synchronously** within the HTTP request (same as V-03 parse). The async worker path is documented here for future use when structuring latency becomes a concern for very long transcriptions (> 5000 tokens input).

---

## 8. Error Codes

All errors use the `VOICE_*` domain prefix, extending the existing voice error set.

| Code | HTTP | When |
|------|------|------|
| `VOICE_addon_required` | 402 | Voice add-on or `ai_voice_notes` flag inactive |
| `VOICE_invalid_session_context` | 400 | Session context is not `evolution` |
| `VOICE_no_completed_transcriptions` | 409 | No completed transcriptions to structure |
| `VOICE_session_not_found` | 404 | Session does not exist in tenant |
| `VOICE_patient_not_found` | 404 | Patient does not exist or is inactive |
| `VOICE_clinical_note_not_found` | 404 | Clinical note ID not found |
| `VOICE_note_already_saved` | 400 | Note already saved as clinical record |
| `VOICE_template_not_found` | 422 | Specified template_id does not exist or is inactive |
| `VOICE_text_too_long` | 400 | override_text exceeds 15000 characters |
| `VOICE_llm_unavailable` | 502 | Claude API unreachable after retry |
| `VOICE_llm_malformed_response` | 502 | Claude returned non-JSON after retry |
| `VOICE_rate_limit_exceeded` | 429 | 30/hour per user limit exceeded |
| `VOICE_structuring_failed` | 500 | Unexpected failure during structuring |

---

## 9. Security

### Audio Retention Policy

- Audio files are managed by V-02 and deleted after 24 hours via S3 lifecycle rule. This spec does not change that policy.
- The `input_text` (transcription) is stored in `voice_clinical_notes.input_text` and retained as long as the clinical note exists (regulatory requirement for clinical documentation provenance).
- Once the note is saved as a `clinical_records` row, the `voice_clinical_notes` record serves as an audit trail of how the note was generated.

### PHI Handling

**PHI fields in this feature:**
- `input_text`: Contains patient clinical speech (symptoms, history, potentially identifiers spoken aloud)
- `structured_note`: Contains structured clinical documentation
- `linked_cie10_codes` / `linked_cups_codes`: Clinical diagnoses and procedures
- `review_edits`: Doctor's modifications to AI output

**LLM Data Transmission:**
- Input text is sent to Anthropic's Claude API. No patient name, document number, date of birth, or explicit identifiers are included in the prompt.
- The `session_id`, `patient_id`, and `tenant_id` are NOT sent to Anthropic.
- Tenants must accept the Voice AI terms of service (includes LLM data processing clause) when activating the add-on.

**Logging Rules:**
- Structured logging (JSON) includes: `tenant_id`, `user_id`, `session_id`, `clinical_note_id`, `status`, `llm_model`, `token_counts`.
- NEVER log: `input_text`, `structured_note` content, CIE-10/CUPS details, patient identifiers.
- Audit log stores: `clinical_note_id`, `session_id`, `patient_id`, `user_id`, `action`, `finding_count`, `code_count`. No PHI in audit log body.

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| session_id | Pydantic UUID v4 | Parameterized query |
| patient_id | Pydantic UUID v4 | Parameterized query |
| template_id | Pydantic UUID v4 (optional) | Parameterized query |
| override_text | strip() + max 15000 chars + strip `{}` and backtick sequences | Prompt injection prevention |
| patient_context fields | Pydantic enum + integer validators | Constrained values |

### Prompt Injection Prevention

Same approach as V-03:
- `input_text` placed inside a delimited `[USER]` block in the prompt.
- Override text has curly braces `{}` and backtick sequences stripped.
- LLM instruction-like patterns detected and flagged in `warnings` (not rejected).

---

## 10. Frontend Component Requirements

### 10.1 Voice Clinical Note Recorder

**Location:** `/patients/{id}/clinical-records` — new "Dictar Nota" button alongside "Nueva Nota".

**Component:** `VoiceClinicalNoteRecorder`

**Behavior:**
1. Doctor clicks "Dictar Nota" -> creates voice session with `context = "evolution"`.
2. Recording UI appears (reuses existing `VoiceRecorder` component from Voice-to-Odontogram).
3. Doctor speaks. Audio is chunked and uploaded via V-02.
4. When done, doctor clicks "Estructurar Nota".
5. System calls `POST /api/v1/patients/{patient_id}/voice/clinical-note`.
6. Loading indicator during Claude processing (target < 8s).
7. Structured SOAP note appears in the review panel.

### 10.2 SOAP Note Review Panel

**Component:** `SOAPNoteReviewPanel`

**Behavior:**
1. Displays structured note with editable fields for each SOAP section.
2. Each section uses a `TipTap` rich text editor (consistent with existing evolution note editing).
3. Linked teeth displayed as clickable FDI badges that highlight on the odontogram mini-view.
4. CIE-10 codes displayed as chips with checkboxes (doctor can accept/reject each).
5. CUPS codes displayed as chips with checkboxes.
6. Warnings displayed as yellow alert banners.
7. Template mapping shown if a template was used — doctor can see how SOAP maps to template steps.
8. "Guardar Nota" button calls the save endpoint. "Descartar" discards without saving.

### 10.3 Template Selector

**Component:** `EvolutionTemplateSelector`

**Behavior:**
1. Dropdown showing active evolution templates for the tenant.
2. If Claude suggested a template (auto-selection), it appears as the default with "(Sugerida por IA)" label.
3. Doctor can change or remove template selection before structuring.
4. Selected template's steps are shown as a preview alongside the SOAP output.

### 10.4 Integration Points

- **Patient clinical records page:** "Dictar Nota" button in the action bar.
- **Appointment detail page:** "Dictar Nota de Evolucion" shortcut that pre-fills `appointment_id` and `chief_complaint` from the appointment reason.
- **Odontogram view:** When `context = "evolution"`, the voice button in the odontogram header switches to "Nota de Evolucion" mode.

### 10.5 Mobile / Tablet UX

- The recording and review flow must work on tablet (min 768px).
- Recording uses `MediaRecorder` API (same as Voice-to-Odontogram).
- The SOAP review panel uses a stacked layout on tablet (sections vertically, not side-by-side).
- Offline: Recording can happen offline (cached via service worker). Structuring requires connectivity.

---

## 11. Test Plan

### Backend Tests

#### Unit Tests

##### Happy Path

1. **Structure simple dictation into SOAP note**
   - **Given:** Completed transcription: "El paciente llega por dolor en el diente cuarenta y seis. Se observa caries profunda oclusal. Diagnostico: pulpitis reversible. Plan: restauracion con resina."
   - **When:** Call `voice_clinical_notes_service.structure_note()`
   - **Then:** `structured_note.subjective` contains "dolor en el diente 46", `assessment` contains "pulpitis reversible", `linked_teeth` = [46], `linked_cie10_codes` includes K04.0 or K02.1, `status` = "structured"

2. **Structure with template mapping**
   - **Given:** Template "Nota de Evolucion - Operatoria" with 4 steps, transcription with relevant content
   - **When:** Call with `template_id`
   - **Then:** `template_mapping` is populated with step-to-SOAP mappings, `variable_values` extracted

3. **Structure with override_text**
   - **Given:** Session with transcriptions, override_text provided
   - **When:** Call with `override_text`
   - **Then:** `override_text` used as input, original transcriptions ignored

4. **Structure with include_codes=false**
   - **Given:** Transcription with clinical content
   - **When:** Call with `include_codes=false`
   - **Then:** `linked_cie10_codes` and `linked_cups_codes` are empty arrays

5. **Save structured note as evolution_note**
   - **Given:** Note in `structured` status
   - **When:** Call save endpoint with edits
   - **Then:** `clinical_records` row created with `type='evolution_note'`, `voice_clinical_notes.status` = "saved", `review_edits` captured

6. **Save with doctor edits to SOAP sections**
   - **Given:** Note in `structured` status, doctor modifies `assessment` field
   - **When:** Call save with `edited_note.assessment`
   - **Then:** Saved clinical record uses doctor's version, `review_edits` contains the diff

##### Edge Cases

7. **Empty transcription (silence)**
   - **Given:** Transcription text is empty
   - **When:** Structure
   - **Then:** 200 OK, all SOAP sections empty strings, `warnings` contains "La transcripcion esta vacia"

8. **Self-correction in tooth numbers**
   - **Given:** "Diente treinta y seis... no, cuarenta y seis"
   - **When:** Structure
   - **Then:** `linked_teeth` = [46], not [36]

9. **Multiple teeth mentioned across sections**
   - **Given:** "Revision del 11, 21, y 46"
   - **When:** Structure
   - **Then:** `linked_teeth` = [11, 21, 46]

10. **Template variable not extractable**
    - **Given:** Template with required variable `[tecnica_anestesica]`, dictation does not mention anesthesia
    - **When:** Structure with template
    - **Then:** Warning: "Variable requerida no encontrada: tecnica_anestesica"

11. **Re-structure same session**
    - **Given:** Session already has a structured note
    - **When:** Call structure again
    - **Then:** New `voice_clinical_notes` record created (old one remains for audit trail)

12. **Very long transcription (>10000 tokens)**
    - **Given:** 15-minute dictation producing long text
    - **When:** Structure
    - **Then:** Text truncated to 10000 tokens from the end, warning added

##### Error Cases

13. **Session context is not evolution**
    - **Given:** Session with `context = "odontogram"`
    - **When:** Call structure
    - **Then:** 400 with `VOICE_invalid_session_context`

14. **No completed transcriptions**
    - **Given:** Session with transcriptions all in `processing` status
    - **When:** Call structure
    - **Then:** 409 with `VOICE_no_completed_transcriptions`

15. **Template not found**
    - **Given:** `template_id` that does not exist
    - **When:** Call structure
    - **Then:** 422 with `VOICE_template_not_found`

16. **Claude returns malformed JSON twice**
    - **Given:** Mock Claude to return prose instead of JSON
    - **When:** Call structure
    - **Then:** 502 with `VOICE_llm_malformed_response`

17. **Note already saved (double-save attempt)**
    - **Given:** Note with `status = "saved"`
    - **When:** Call save
    - **Then:** 400 with `VOICE_note_already_saved`

18. **Rate limit exceeded**
    - **Given:** 30 structure calls in current hour
    - **When:** Call structure (31st)
    - **Then:** 429 with `VOICE_rate_limit_exceeded`

19. **Feature flag disabled**
    - **Given:** `voice_enabled` active but `ai_voice_notes` disabled
    - **When:** Call structure
    - **Then:** 402 with `VOICE_addon_required`

#### Integration Tests

20. **Full pipeline: capture -> transcribe -> structure -> save**
    - Create session (context=evolution) -> upload audio -> wait for transcription -> structure -> review -> save
    - Verify `clinical_records` row exists with correct content

21. **Concurrent structure requests for same session**
    - Two simultaneous structure requests
    - Both should succeed (each creates a separate `voice_clinical_notes` record)

22. **CIE-10 code validation against catalog**
    - Structure with text mentioning "caries"
    - Verify extracted CIE-10 code exists in the `cie10_catalog` table

### Frontend Tests

23. **VoiceClinicalNoteRecorder renders and starts session**
    - Mock API, verify session creation call with `context = "evolution"`

24. **SOAPNoteReviewPanel displays all sections**
    - Provide structured note data, verify S/O/A/P sections render as editable fields

25. **CIE-10 and CUPS chips render with accept/reject**
    - Verify clicking reject removes code from accepted list

26. **Template selector shows tenant templates**
    - Mock templates API, verify dropdown renders

27. **Save button calls correct endpoint with edits**
    - Edit a SOAP section, click save, verify API payload includes `edited_note`

### Test Data Requirements

**Users:** doctor (primary), assistant, receptionist (negative test)
**Patients:** Active patient with clinical history
**Sessions:** Voice sessions with context=evolution, completed transcriptions
**Templates:** 2-3 evolution templates with different step structures and variables
**Audio:** Sample WebM files with Spanish dental dictation
**Catalogs:** CIE-10 and CUPS dental entries seeded in test DB

### Mocking Strategy

- **Anthropic Claude API:** Mock with `respx`; return valid SOAP JSON for happy path; return malformed JSON for error test; return 529 for 502 test
- **Redis:** `fakeredis` for rate limit tests
- **S3/MinIO:** Not needed (audio is handled by V-02)
- **Database:** Real PostgreSQL via pytest-asyncio for integration tests; async session fixtures for unit tests
- **Whisper:** Not directly tested (V-02 responsibility); mock transcription status as "completed" with text

---

## Performance

### Expected Response Time

| Endpoint | Target | Maximum |
|----------|--------|---------|
| POST structure (3.3) | < 8000ms | < 15000ms |
| GET note (3.4) | < 100ms | < 300ms |
| POST save (3.5) | < 500ms | < 1500ms |

**Note:** The structuring endpoint is dominated by Claude Sonnet API latency (typically 3-8 seconds for dental notes). Frontend must show a loading indicator.

### Caching Strategy

- **Structure results:** Not cached (each call may have different input).
- **Saved clinical records:** Follow existing clinical record caching strategy.
- **Template fetches:** Cached in Redis for 5 minutes (existing template cache).
- **CIE-10/CUPS catalog:** Cached for 24 hours (existing catalog cache).

### Database Performance

**Indexes listed in section 2.**

**Queries per endpoint:**
- Structure: 5 (feature flag check, session fetch, transcription fetch, template fetch, note insert)
- Get note: 1 (single row by ID)
- Save: 3 (note fetch, clinical record insert, note update)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST structure returns 200 with valid SOAP-formatted `structured_note`
- [ ] FDI tooth numbers extracted and validated in `linked_teeth`
- [ ] CIE-10 codes extracted with confidence scores and validated against catalog
- [ ] CUPS codes extracted with confidence scores and validated against catalog
- [ ] Template mapping works when `template_id` provided
- [ ] Template variables extracted from dictation text
- [ ] Self-corrections in speech handled correctly
- [ ] Non-clinical speech filtered from structured note
- [ ] Doctor can edit all SOAP sections before saving
- [ ] Save creates `clinical_records` row with `type='evolution_note'`
- [ ] Save stores doctor edits in `review_edits` for audit
- [ ] Feature flag `ai_voice_notes` (+ `voice_enabled`) gating works
- [ ] Rate limit (30/hour per user) enforced
- [ ] LLM cost tracked in `llm_cost_usd` and `ai_usage_logs`
- [ ] Claude malformed JSON retried once; 502 on persistent failure
- [ ] Audit log entries written (no PHI in audit body)
- [ ] All VOICE_* error codes return correct HTTP status and message
- [ ] Frontend components: VoiceClinicalNoteRecorder, SOAPNoteReviewPanel, TemplateSelector
- [ ] Tablet-responsive layout (min 768px)
- [ ] Offline recording supported (structuring requires connectivity)
- [ ] All 27 test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Voice-to-Odontogram pipeline (V-03/V-04) — separate existing flow
- Voice Perio Charting (AI-07) — future feature
- Real-time streaming of LLM output to frontend (future enhancement)
- Automatic creation of diagnoses or treatment plan items from extracted codes (future — requires doctor explicit action)
- Multi-language support beyond Spanish (es-419)
- Custom CIE-10/CUPS code sets per tenant (uses global catalog)
- PDF generation of voice clinical notes (uses existing clinical record PDF flow)
- Patient portal visibility of voice-generated notes (inherits clinical record portal visibility settings)
- Fine-tuning Claude on dental vocabulary
- Speaker diarization (dentist vs patient voice separation)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant + feature flags)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (voice + clinical domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match project conventions (UUID PK, timestamps, soft delete)
- [x] Extends existing voice pipeline without modifying it

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant + feature flags)
- [x] Input sanitization defined (Pydantic + prompt injection prevention)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access
- [x] LLM data transmission policy stated (no patient identifiers sent)
- [x] Audio retention policy stated (24h, inherited from V-02)

### Hook 4: Performance & Scalability
- [x] Response time targets defined per endpoint
- [x] Caching strategy stated
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] LLM cost tracking per call
- [x] AI usage logging to `ai_usage_logs`

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error — 27 cases)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (Claude API)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial spec — AI Voice Clinical Notes (AI-03) |
