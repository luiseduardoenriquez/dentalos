# AI Smile Simulator — Full API Spec (AI-04)

**Feature code:** `ai_smile_sim`
**Add-on:** $20/doctor/mo (bundled with AI Radiograph + Radiograph Overlay)
**Feature flag:** `ai_smile_sim` (tenant `features` JSONB)
**Sprint:** S37-38 (Tier 2 — Differentiation)
**Priority:** High

---

## 1. Overview

AI Smile Simulator lets a doctor or assistant upload a patient's smile photo and receive AI-generated visualizations of the expected result after a specific dental treatment. The process is two-step: Claude Vision analyzes the current smile (tooth alignment, color, gum line, missing teeth, proportions) and produces a structured description of the changes required; then an image generation API (DALL-E 3 / Flux / Stable Diffusion) creates a realistic result photo preserving the patient's facial features.

Each simulation produces up to three variants — **conservative**, **moderate**, and **ideal** — so the doctor can walk the patient through realistic expectations. Simulations are linked to a treatment plan and/or quotation and can be shared with the patient via the portal.

**Treatment types supported:**
- `whitening` — shade change simulation
- `veneers` — shape, size, and color adjustment
- `orthodontics` — alignment correction
- `implants` — missing tooth replacement
- `crowns` — individual tooth restoration
- `gum_contouring` — gum line reshaping
- `full_rehabilitation` — combination of multiple treatments

**Regulatory disclaimer (always shown in UI):**
> "Esta simulacion es una proyeccion aproximada. Los resultados reales pueden variar segun la respuesta clinica individual."

### Architecture Diagram

```
┌──────────────┐     POST /smile-simulations          ┌──────────────────┐
│   Frontend   │ ────────────────────────────────────→│    FastAPI        │
│  (Upload +   │     202 Accepted (simulation_id)      │    Route          │
│   Poll)      │ ←────────────────────────────────────│                  │
│              │                                       │  1. Validate image│
│              │     GET /smile-simulations/{id}       │  2. Upload to S3  │
│              │ ────────────────────────────────────→│  3. Create record │
│              │     200 (status: processing|done)     │  4. Enqueue job   │
│              │ ←────────────────────────────────────│                  │
└──────────────┘                                       └────────┬─────────┘
                                                                │
                                                      RabbitMQ  │ smile.simulate
                                                                ▼
                                                      ┌──────────────────┐
                                                      │  Clinical Worker  │
                                                      │                  │
                                                      │  Step 1:          │
                                                      │  1. Fetch photo   │
                                                      │     from S3      │
                                                      │  2. Call Claude   │
                                                      │     Vision API   │
                                                      │  3. Analyze smile │
                                                      │  4. Generate      │
                                                      │     change desc   │
                                                      │                  │
                                                      │  Step 2:          │
                                                      │  5. Build image   │
                                                      │     gen prompt    │
                                                      │  6. Call image    │
                                                      │     gen API (x3)  │
                                                      │  7. Upload results│
                                                      │     to S3        │
                                                      │  8. Update record │
                                                      │  9. Log AI usage  │
                                                      └──────────────────┘
```

### Data Flow

1. **Upload** — Doctor uploads a patient smile photo (JPEG/PNG, front-facing, teeth visible).
2. **Validation** — API validates image format, size (max 10 MB), and minimum resolution (800x600).
3. **S3 storage** — Original photo stored at `/{tenant_id}/{patient_id}/smile-simulations/{uuid}/original.{ext}`.
4. **Enqueue** — Job published to `clinical` queue with type `smile.simulate`.
5. **Step 1: Claude Vision analysis** — Worker sends the photo to Claude Vision with a structured prompt. Claude returns a JSON description of the current smile (tooth positions, shade, gum line, missing teeth, asymmetries) and the changes needed for each variant.
6. **Step 2: Image generation** — Worker builds 3 image generation prompts (conservative/moderate/ideal) incorporating the change descriptions and the original photo as reference. Each prompt is sent to the image generation API.
7. **Storage** — Generated images stored at `/{tenant_id}/{patient_id}/smile-simulations/{uuid}/{variant}.png`.
8. **Completion** — Worker updates the database record with result URLs, status, and token usage.
9. **Frontend poll** — Client polls `GET /smile-simulations/{id}` until `status = 'completed'`.

---

## 2. Database Schema

### Table: `smile_simulations` (tenant schema `tn_*`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, `DEFAULT gen_random_uuid()` | |
| `patient_id` | `UUID` | FK → `patients.id`, NOT NULL | |
| `created_by` | `UUID` | FK → `users.id`, NOT NULL | Doctor/assistant who requested simulation |
| `treatment_plan_id` | `UUID` | FK → `treatment_plans.id`, NULL | Optional link to treatment plan |
| `quotation_id` | `UUID` | FK → `quotations.id`, NULL | Optional link to quotation |
| `treatment_type` | `VARCHAR(30)` | NOT NULL, CHECK | `whitening`, `veneers`, `orthodontics`, `implants`, `crowns`, `gum_contouring`, `full_rehabilitation` |
| `status` | `VARCHAR(20)` | NOT NULL, DEFAULT `'pending'`, CHECK | `pending`, `analyzing`, `generating`, `completed`, `failed` |
| `original_image_url` | `VARCHAR(500)` | NOT NULL | S3 path to original smile photo |
| `analysis_result` | `JSONB` | DEFAULT `'{}'` | Claude Vision structured analysis (see below) |
| `variants` | `JSONB` | DEFAULT `'[]'` | Array of generated variant objects (see below) |
| `selected_variant` | `VARCHAR(20)` | NULL, CHECK | `conservative`, `moderate`, `ideal` — doctor's pick |
| `notes` | `TEXT` | NULL | Doctor's free-text notes |
| `patient_instructions` | `TEXT` | NULL | Instructions shown to patient when shared |
| `is_shared` | `BOOLEAN` | DEFAULT `false` | Whether shared to patient portal |
| `shared_at` | `TIMESTAMPTZ` | NULL | When shared to portal |
| `share_token` | `VARCHAR(64)` | NULL, UNIQUE | Opaque token for portal link |
| `model_used` | `VARCHAR(50)` | NULL | Claude model version used for analysis |
| `image_model_used` | `VARCHAR(50)` | NULL | Image generation model (e.g. `dall-e-3`, `flux-1.1-pro`) |
| `input_tokens` | `INTEGER` | DEFAULT `0` | Claude Vision tokens |
| `output_tokens` | `INTEGER` | DEFAULT `0` | Claude Vision tokens |
| `image_gen_cost_cents` | `INTEGER` | DEFAULT `0` | Image generation cost in USD cents |
| `processing_time_ms` | `INTEGER` | NULL | Total wall-clock processing time |
| `error_message` | `TEXT` | NULL | Error details if `status = 'failed'` |
| `consent_given` | `BOOLEAN` | DEFAULT `false` | Patient consented to photo processing |
| `consent_at` | `TIMESTAMPTZ` | NULL | Timestamp of consent |
| `is_active` | `BOOLEAN` | DEFAULT `true` | Soft delete flag |
| `deleted_at` | `TIMESTAMPTZ` | NULL | Soft delete timestamp |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` | |

### Indexes

```sql
CREATE INDEX idx_smile_simulations_patient_id ON smile_simulations(patient_id);
CREATE INDEX idx_smile_simulations_created_by ON smile_simulations(created_by);
CREATE INDEX idx_smile_simulations_treatment_plan_id ON smile_simulations(treatment_plan_id);
CREATE INDEX idx_smile_simulations_status ON smile_simulations(status);
CREATE INDEX idx_smile_simulations_share_token ON smile_simulations(share_token) WHERE share_token IS NOT NULL;
CREATE INDEX idx_smile_simulations_created_at ON smile_simulations(created_at DESC);
```

### Analysis Result JSONB Structure

Stored in `analysis_result` after Claude Vision step:

```json
{
  "smile_analysis": {
    "teeth_visible": ["11", "12", "13", "14", "21", "22", "23", "24"],
    "shade_current": "A3",
    "shade_uniformity": "uneven",
    "alignment": "mild_crowding",
    "midline_deviation": "1mm_left",
    "gum_line": "slightly_uneven",
    "missing_teeth": [],
    "existing_restorations": ["16_amalgam", "26_composite"],
    "smile_line": "medium",
    "lip_line": "average",
    "facial_symmetry_score": 0.85,
    "teeth_proportions": "slightly_narrow_laterals"
  },
  "recommended_changes": {
    "conservative": {
      "description": "Minimal intervention focusing on shade improvement only",
      "changes": [
        {"area": "all_visible", "change": "shade_improvement", "from": "A3", "to": "A2"}
      ]
    },
    "moderate": {
      "description": "Shade improvement plus minor alignment correction",
      "changes": [
        {"area": "all_visible", "change": "shade_improvement", "from": "A3", "to": "A1"},
        {"area": "11_21", "change": "alignment_correction", "detail": "close_diastema"}
      ]
    },
    "ideal": {
      "description": "Complete smile makeover with optimal aesthetics",
      "changes": [
        {"area": "all_visible", "change": "shade_improvement", "from": "A3", "to": "B1"},
        {"area": "all_anterior", "change": "alignment_correction", "detail": "perfect_arch"},
        {"area": "12_22", "change": "proportion_correction", "detail": "widen_laterals"},
        {"area": "gum_line", "change": "gum_contouring", "detail": "symmetrical_scallop"}
      ]
    }
  },
  "confidence_score": 0.87,
  "quality_warnings": []
}
```

### Variants JSONB Structure

Stored in `variants` after image generation step:

```json
[
  {
    "variant": "conservative",
    "image_url": "/{tenant_id}/{patient_id}/smile-simulations/{uuid}/conservative.png",
    "prompt_used": "...(stored for audit/debugging)...",
    "generation_time_ms": 12500,
    "description_es": "Mejora sutil del tono de los dientes, manteniendo la naturalidad de la sonrisa."
  },
  {
    "variant": "moderate",
    "image_url": "/{tenant_id}/{patient_id}/smile-simulations/{uuid}/moderate.png",
    "prompt_used": "...",
    "generation_time_ms": 13200,
    "description_es": "Blanqueamiento notable y correccion menor de alineacion para una sonrisa mas armonica."
  },
  {
    "variant": "ideal",
    "image_url": "/{tenant_id}/{patient_id}/smile-simulations/{uuid}/ideal.png",
    "prompt_used": "...",
    "generation_time_ms": 14100,
    "description_es": "Transformacion completa con alineacion perfecta, proporcion ideal y tono optimo."
  }
]
```

---

## 3. API Endpoints

**Base path:** `/api/v1/patients/{patient_id}/smile-simulations`

### 3.1 Create Simulation

```
POST /api/v1/patients/{patient_id}/smile-simulations
Content-Type: multipart/form-data
Auth: JWT (doctor, assistant, clinic_owner)
```

**Form fields:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `photo` | File (JPEG/PNG) | Yes | Max 10 MB, min 800x600 |
| `treatment_type` | string | Yes | One of the supported types |
| `treatment_plan_id` | UUID | No | Link to existing treatment plan |
| `quotation_id` | UUID | No | Link to existing quotation |
| `notes` | string | No | Doctor notes |
| `consent_given` | boolean | Yes | Must be `true` |

**Response: `202 Accepted`**

```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "treatment_type": "veneers",
  "status": "pending",
  "original_image_url": "/signed-url/...",
  "created_at": "2026-03-13T10:00:00Z",
  "created_by": "uuid"
}
```

**Errors:**

| Code | HTTP | Message |
|------|------|---------|
| `SMILE_SIMULATOR_feature_disabled` | 403 | Feature not enabled for this tenant |
| `SMILE_SIMULATOR_invalid_image` | 400 | Image must be JPEG or PNG, max 10 MB |
| `SMILE_SIMULATOR_resolution_too_low` | 400 | Minimum resolution is 800x600 pixels |
| `SMILE_SIMULATOR_consent_required` | 400 | Patient consent is required for photo processing |
| `SMILE_SIMULATOR_patient_not_found` | 404 | Patient not found |
| `SMILE_SIMULATOR_invalid_treatment_type` | 400 | Invalid treatment type |
| `SMILE_SIMULATOR_quota_exceeded` | 429 | Monthly simulation quota exceeded |

### 3.2 Get Simulation

```
GET /api/v1/patients/{patient_id}/smile-simulations/{simulation_id}
Auth: JWT (doctor, assistant, clinic_owner)
```

**Response: `200 OK`**

```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "created_by": "uuid",
  "treatment_type": "veneers",
  "treatment_plan_id": "uuid | null",
  "quotation_id": "uuid | null",
  "status": "completed",
  "original_image_url": "/signed-url/...",
  "analysis_result": { "...see JSONB structure above..." },
  "variants": [
    {
      "variant": "conservative",
      "image_url": "/signed-url/...",
      "description_es": "Mejora sutil del tono...",
      "generation_time_ms": 12500
    },
    {
      "variant": "moderate",
      "image_url": "/signed-url/...",
      "description_es": "Blanqueamiento notable...",
      "generation_time_ms": 13200
    },
    {
      "variant": "ideal",
      "image_url": "/signed-url/...",
      "description_es": "Transformacion completa...",
      "generation_time_ms": 14100
    }
  ],
  "selected_variant": "moderate",
  "notes": "Patient prefers moderate result",
  "is_shared": true,
  "shared_at": "2026-03-13T10:30:00Z",
  "consent_given": true,
  "processing_time_ms": 45000,
  "created_at": "2026-03-13T10:00:00Z",
  "updated_at": "2026-03-13T10:01:00Z"
}
```

**Errors:**

| Code | HTTP | Message |
|------|------|---------|
| `SMILE_SIMULATOR_not_found` | 404 | Simulation not found |

### 3.3 List Simulations

```
GET /api/v1/patients/{patient_id}/smile-simulations?page=1&page_size=20
Auth: JWT (doctor, assistant, clinic_owner)
```

**Query parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `page` | int | 1 | |
| `page_size` | int | 20 | Max 50 |
| `status` | string | — | Filter by status |
| `treatment_type` | string | — | Filter by treatment type |

**Response: `200 OK`**

```json
{
  "items": [
    {
      "id": "uuid",
      "treatment_type": "veneers",
      "status": "completed",
      "original_image_url": "/signed-url/...",
      "selected_variant": "moderate",
      "is_shared": true,
      "created_at": "2026-03-13T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### 3.4 Select Variant

```
PUT /api/v1/patients/{patient_id}/smile-simulations/{simulation_id}/select
Auth: JWT (doctor, clinic_owner)
```

**Request body:**

```json
{
  "variant": "moderate"
}
```

**Response: `200 OK`** — Returns the updated simulation object.

**Errors:**

| Code | HTTP | Message |
|------|------|---------|
| `SMILE_SIMULATOR_not_completed` | 400 | Simulation must be completed before selecting a variant |
| `SMILE_SIMULATOR_invalid_variant` | 400 | Variant must be conservative, moderate, or ideal |

### 3.5 Share to Portal

```
POST /api/v1/patients/{patient_id}/smile-simulations/{simulation_id}/share
Auth: JWT (doctor, clinic_owner)
```

**Request body:**

```json
{
  "patient_instructions": "Estos son los resultados proyectados de tu tratamiento de carillas."
}
```

**Response: `200 OK`**

```json
{
  "id": "uuid",
  "is_shared": true,
  "shared_at": "2026-03-13T10:30:00Z",
  "share_token": "abc123...",
  "portal_url": "/portal/smile-simulations/{share_token}"
}
```

Sharing creates a notification to the patient (in-app + WhatsApp if enabled).

**Errors:**

| Code | HTTP | Message |
|------|------|---------|
| `SMILE_SIMULATOR_not_completed` | 400 | Simulation must be completed before sharing |
| `SMILE_SIMULATOR_already_shared` | 400 | Simulation is already shared |
| `SMILE_SIMULATOR_no_portal_access` | 400 | Patient does not have portal access enabled |

### 3.6 Unshare from Portal

```
POST /api/v1/patients/{patient_id}/smile-simulations/{simulation_id}/unshare
Auth: JWT (doctor, clinic_owner)
```

**Response: `200 OK`** — Returns updated simulation with `is_shared: false`.

### 3.7 Delete Simulation (Soft Delete)

```
DELETE /api/v1/patients/{patient_id}/smile-simulations/{simulation_id}
Auth: JWT (doctor, clinic_owner)
```

**Response: `200 OK`** — Sets `is_active = false`, `deleted_at = now()`.

**Errors:**

| Code | HTTP | Message |
|------|------|---------|
| `SMILE_SIMULATOR_not_found` | 404 | Simulation not found |

### 3.8 Portal — View Shared Simulation (Patient)

```
GET /api/v1/portal/smile-simulations/{share_token}
Auth: JWT (patient)
```

Returns the simulation with signed image URLs. Patient sees original + all variants + doctor's selected variant highlighted + patient instructions. Does NOT expose `analysis_result`, `notes`, `processing_time_ms`, or cost fields.

**Response: `200 OK`**

```json
{
  "id": "uuid",
  "treatment_type": "veneers",
  "original_image_url": "/signed-url/...",
  "variants": [
    {
      "variant": "conservative",
      "image_url": "/signed-url/...",
      "description_es": "Mejora sutil del tono..."
    },
    {
      "variant": "moderate",
      "image_url": "/signed-url/...",
      "description_es": "Blanqueamiento notable..."
    },
    {
      "variant": "ideal",
      "image_url": "/signed-url/...",
      "description_es": "Transformacion completa..."
    }
  ],
  "selected_variant": "moderate",
  "patient_instructions": "Estos son los resultados proyectados...",
  "disclaimer": "Esta simulacion es una proyeccion aproximada. Los resultados reales pueden variar segun la respuesta clinica individual.",
  "shared_at": "2026-03-13T10:30:00Z"
}
```

**Errors:**

| Code | HTTP | Message |
|------|------|---------|
| `SMILE_SIMULATOR_share_not_found` | 404 | Shared simulation not found or revoked |
| `SMILE_SIMULATOR_unauthorized` | 403 | You can only view simulations shared with your account |

---

## 4. Pydantic Schemas

```python
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field


class TreatmentType(str, Enum):
    whitening = "whitening"
    veneers = "veneers"
    orthodontics = "orthodontics"
    implants = "implants"
    crowns = "crowns"
    gum_contouring = "gum_contouring"
    full_rehabilitation = "full_rehabilitation"


class SimulationStatus(str, Enum):
    pending = "pending"
    analyzing = "analyzing"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class VariantType(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    ideal = "ideal"


class SmileSimulationCreate(BaseModel):
    treatment_type: TreatmentType
    treatment_plan_id: UUID | None = None
    quotation_id: UUID | None = None
    notes: str | None = Field(None, max_length=2000)
    consent_given: bool


class SmileSimulationVariant(BaseModel):
    variant: VariantType
    image_url: str
    description_es: str
    generation_time_ms: int | None = None


class SmileSimulationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    created_by: UUID
    treatment_type: TreatmentType
    treatment_plan_id: UUID | None
    quotation_id: UUID | None
    status: SimulationStatus
    original_image_url: str
    analysis_result: dict | None = None
    variants: list[SmileSimulationVariant]
    selected_variant: VariantType | None
    notes: str | None
    is_shared: bool
    shared_at: datetime | None
    consent_given: bool
    processing_time_ms: int | None
    created_at: datetime
    updated_at: datetime


class SmileSimulationListItem(BaseModel):
    id: UUID
    treatment_type: TreatmentType
    status: SimulationStatus
    original_image_url: str
    selected_variant: VariantType | None
    is_shared: bool
    created_at: datetime


class SmileSimulationSelectVariant(BaseModel):
    variant: VariantType


class SmileSimulationShare(BaseModel):
    patient_instructions: str | None = Field(None, max_length=1000)


class SmileSimulationShareResponse(BaseModel):
    id: UUID
    is_shared: bool
    shared_at: datetime
    share_token: str
    portal_url: str


class SmileSimulationPortalResponse(BaseModel):
    id: UUID
    treatment_type: TreatmentType
    original_image_url: str
    variants: list[SmileSimulationVariant]
    selected_variant: VariantType | None
    patient_instructions: str | None
    disclaimer: str
    shared_at: datetime
```

---

## 5. Integration Adapter Interface

Located in `backend/app/integrations/smile_simulator/`.

### 5.1 Base Adapter

```python
# backend/app/integrations/smile_simulator/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SmileAnalysisInput:
    image_bytes: bytes
    image_format: str  # "jpeg" | "png"
    treatment_type: str
    patient_age: int | None = None
    patient_sex: str | None = None  # "M" | "F"


@dataclass
class SmileAnalysisResult:
    smile_analysis: dict
    recommended_changes: dict
    confidence_score: float
    quality_warnings: list[str]
    model_used: str
    input_tokens: int
    output_tokens: int
    processing_time_ms: int


@dataclass
class ImageGenerationInput:
    original_image_bytes: bytes
    original_image_format: str
    variant: str  # "conservative" | "moderate" | "ideal"
    change_description: dict
    treatment_type: str


@dataclass
class ImageGenerationResult:
    image_bytes: bytes
    image_format: str  # always "png"
    prompt_used: str
    description_es: str
    model_used: str
    generation_time_ms: int
    cost_cents: int  # USD cents


class SmileSimulatorAdapter(ABC):
    """Abstract base for smile simulation providers."""

    @abstractmethod
    async def analyze_smile(self, input: SmileAnalysisInput) -> SmileAnalysisResult:
        """Step 1: Analyze current smile using vision AI."""
        ...

    @abstractmethod
    async def generate_variant(self, input: ImageGenerationInput) -> ImageGenerationResult:
        """Step 2: Generate a single variant image."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the adapter services are reachable."""
        ...
```

### 5.2 Production Adapter

```python
# backend/app/integrations/smile_simulator/claude_dalle_service.py

class ClaudeDalleSmileSimulator(SmileSimulatorAdapter):
    """
    Production adapter using:
    - Claude Vision (Sonnet) for smile analysis
    - DALL-E 3 for image generation

    Can be swapped for Flux or Stable Diffusion by changing the
    image generation calls without touching the analysis step.
    """

    def __init__(self, claude_client, openai_client, config):
        self.claude_client = claude_client
        self.openai_client = openai_client
        self.config = config

    async def analyze_smile(self, input: SmileAnalysisInput) -> SmileAnalysisResult:
        # 1. Build Claude Vision prompt (see Section 6)
        # 2. Send image + prompt to Claude
        # 3. Extract JSON from response
        # 4. Validate structure
        ...

    async def generate_variant(self, input: ImageGenerationInput) -> ImageGenerationResult:
        # 1. Build image generation prompt (see Section 6)
        # 2. Call DALL-E 3 API
        # 3. Download generated image
        # 4. Return bytes + metadata
        ...
```

### 5.3 Mock Adapter

```python
# backend/app/integrations/smile_simulator/mock_service.py

class MockSmileSimulator(SmileSimulatorAdapter):
    """
    Mock adapter for dev/test environments.
    Returns a predefined analysis and generates placeholder images
    (copies the original with a tint overlay applied via Pillow).
    """

    async def analyze_smile(self, input: SmileAnalysisInput) -> SmileAnalysisResult:
        # Returns a realistic but static analysis result
        # Processing time simulated at 500ms
        ...

    async def generate_variant(self, input: ImageGenerationInput) -> ImageGenerationResult:
        # Returns the original image with a slight color shift
        # to visually differentiate variants in tests
        ...

    async def health_check(self) -> bool:
        return True
```

### 5.4 Adapter Selection

```python
# In backend/app/core/dependencies.py or similar

def get_smile_simulator() -> SmileSimulatorAdapter:
    if settings.ENVIRONMENT == "production":
        return ClaudeDalleSmileSimulator(
            claude_client=get_claude_client(),
            openai_client=get_openai_client(),
            config=settings.SMILE_SIMULATOR_CONFIG,
        )
    return MockSmileSimulator()
```

---

## 6. Image Generation Prompt Engineering

### 6.1 Claude Vision Analysis Prompt

```
You are an expert dental aesthetics analyst. Analyze this smile photo and return a structured JSON assessment.

Patient context:
- Age: {age or "unknown"}
- Sex: {sex or "unknown"}
- Treatment type requested: {treatment_type}

Analyze the following aspects of the visible smile:
1. Which teeth are visible (FDI notation)
2. Current shade (Vita shade guide approximation)
3. Shade uniformity across visible teeth
4. Alignment (perfect, mild crowding, moderate crowding, severe crowding, spacing)
5. Midline deviation (if any, direction and estimated mm)
6. Gum line symmetry
7. Missing teeth visible
8. Existing restorations visible
9. Smile line (low, medium, high, gummy)
10. Lip line position
11. Facial symmetry score (0-1)
12. Teeth proportions (width-to-height ratios)

Then, based on the treatment type "{treatment_type}", propose three levels of changes:
- conservative: minimal intervention, subtle improvement
- moderate: noticeable improvement, balanced approach
- ideal: optimal result with comprehensive changes

For each level, describe specific changes as a list with: area affected, type of change, from value, to value.

Return ONLY valid JSON matching this schema:
{
  "smile_analysis": { ... },
  "recommended_changes": {
    "conservative": { "description": "...", "changes": [...] },
    "moderate": { "description": "...", "changes": [...] },
    "ideal": { "description": "...", "changes": [...] }
  },
  "confidence_score": 0.0-1.0,
  "quality_warnings": ["list of any issues with the photo quality"]
}
```

### 6.2 Image Generation Prompt Template

The image generation prompt is constructed dynamically per variant:

```
Professional dental photography of a patient smiling.
Photorealistic, high quality, natural lighting, clinical dental documentation style.

This is a dental treatment simulation showing the AFTER result of {treatment_type_label} treatment.

CRITICAL: Preserve the patient's exact facial features, skin tone, lip shape, face shape,
hair, and all non-dental features. ONLY modify the teeth and gum area as described below.

Changes to apply:
{change_list_from_analysis}

Specific modifications:
- {change_1_description}
- {change_2_description}
- ...

The result should look completely natural and realistic, as if the patient had actually
completed the dental treatment. No artificial look, no overly perfect "Hollywood" smile
unless the variant is "ideal".

Variant level: {variant} — {variant_description}
```

**Treatment-type specific additions:**

| Treatment Type | Prompt Addition |
|---------------|-----------------|
| `whitening` | "Focus on shade change only. Do not modify tooth shape, alignment, or gum line. Change shade from {from} to {to}." |
| `veneers` | "Modify anterior teeth shape, size, and color as specified. Maintain natural proportions. Show porcelain-like translucency." |
| `orthodontics` | "Show teeth in corrected alignment. Close any specified gaps. Correct specified rotations. Midline centered." |
| `implants` | "Add natural-looking replacement teeth in positions {teeth_list}. Match shade and size to adjacent teeth." |
| `crowns` | "Show restored teeth at positions {teeth_list} with natural crown appearance matching adjacent teeth." |
| `gum_contouring` | "Modify gum line to be symmetrical. Adjust crown-to-gum ratio as specified." |
| `full_rehabilitation` | "Apply all specified changes comprehensively. Balance aesthetics with natural appearance." |

### 6.3 Quality Safeguards

- If `confidence_score < 0.5`, the analysis is flagged and the simulation still runs but a warning is attached.
- If `quality_warnings` includes `"face_not_detected"`, `"mouth_closed"`, or `"too_dark"`, the simulation fails immediately with `SMILE_SIMULATOR_poor_photo_quality`.
- Generated images are checked for minimum resolution (1024x1024) and not blank/corrupted.

---

## 7. Worker Message Format

### Queue: `clinical`
### Job type: `smile.simulate`

**Message envelope:**

```json
{
  "message_id": "uuid-v4",
  "tenant_id": "tn_abc123",
  "job_type": "smile.simulate",
  "payload": {
    "simulation_id": "uuid",
    "patient_id": "uuid",
    "original_image_s3_key": "/{tenant_id}/{patient_id}/smile-simulations/{uuid}/original.jpg",
    "treatment_type": "veneers",
    "patient_age": 35,
    "patient_sex": "F"
  },
  "priority": 5,
  "retry_count": 0,
  "max_retries": 2
}
```

**Worker processing steps:**

1. Set tenant context (`SET search_path TO tn_{schema}, public`).
2. Update simulation status to `analyzing`.
3. Fetch original image from S3.
4. Call `adapter.analyze_smile()`.
5. Store `analysis_result` in DB.
6. Update status to `generating`.
7. For each variant (`conservative`, `moderate`, `ideal`):
   a. Call `adapter.generate_variant()`.
   b. Upload generated image to S3.
   c. Append variant data to `variants` JSONB array.
8. Update status to `completed`, set `processing_time_ms`.
9. ACK message.

**Failure handling:**

- If Step 4 fails (Claude API error): set status `failed`, error message, retry via DLX.
- If Step 7 partially fails (1 or 2 variants succeed): store successful variants, set status `completed` with a `quality_warnings` note. Do not retry — partial results are useful.
- If all Step 7 calls fail: set status `failed`, retry via DLX.
- Max 2 retries with exponential backoff (5s, 30s).

---

## 8. Error Codes

**Domain prefix:** `SMILE_SIMULATOR_`

| Error Code | HTTP | Description |
|------------|------|-------------|
| `SMILE_SIMULATOR_feature_disabled` | 403 | Feature flag `ai_smile_sim` not enabled for tenant |
| `SMILE_SIMULATOR_invalid_image` | 400 | Image must be JPEG or PNG, max 10 MB |
| `SMILE_SIMULATOR_resolution_too_low` | 400 | Minimum resolution 800x600 pixels |
| `SMILE_SIMULATOR_consent_required` | 400 | `consent_given` must be `true` |
| `SMILE_SIMULATOR_patient_not_found` | 404 | Patient ID does not exist or is inactive |
| `SMILE_SIMULATOR_not_found` | 404 | Simulation ID does not exist or is inactive |
| `SMILE_SIMULATOR_invalid_treatment_type` | 400 | Treatment type not in allowed list |
| `SMILE_SIMULATOR_not_completed` | 400 | Action requires status `completed` |
| `SMILE_SIMULATOR_invalid_variant` | 400 | Variant must be `conservative`, `moderate`, or `ideal` |
| `SMILE_SIMULATOR_already_shared` | 400 | Simulation already shared to portal |
| `SMILE_SIMULATOR_no_portal_access` | 400 | Patient has no portal access |
| `SMILE_SIMULATOR_share_not_found` | 404 | Share token invalid or simulation unshared |
| `SMILE_SIMULATOR_unauthorized` | 403 | Insufficient permissions |
| `SMILE_SIMULATOR_quota_exceeded` | 429 | Monthly simulation limit exceeded for plan |
| `SMILE_SIMULATOR_poor_photo_quality` | 400 | Photo quality insufficient (face not detected, mouth closed, too dark) |
| `SMILE_SIMULATOR_processing_failed` | 500 | AI processing failed after retries |
| `SMILE_SIMULATOR_provider_unavailable` | 503 | Image generation service unavailable |

---

## 9. Security

### 9.1 Patient Photo Handling

- Patient photos are PHI. Never log image URLs, S3 keys, or image content.
- All S3 paths are tenant-isolated: `/{tenant_id}/{patient_id}/smile-simulations/...`.
- Images served via signed URLs with 15-minute expiration.
- Original photos and generated images inherit the same access controls as patient documents.

### 9.2 Consent

- `consent_given = true` is **required** at creation time. The API rejects requests where `consent_given` is false.
- The consent timestamp is recorded in `consent_at`.
- Consent text displayed in the UI: "Autorizo el procesamiento de mi fotografia facial con inteligencia artificial para generar una simulacion estetica dental. Entiendo que los resultados son aproximados."
- If the tenant has digital consent forms enabled, the simulation creation should reference the signed consent document.

### 9.3 Access Control

| Action | Roles |
|--------|-------|
| Create simulation | `doctor`, `assistant`, `clinic_owner` |
| View simulation | `doctor`, `assistant`, `clinic_owner` |
| List simulations | `doctor`, `assistant`, `clinic_owner` |
| Select variant | `doctor`, `clinic_owner` |
| Share to portal | `doctor`, `clinic_owner` |
| Unshare from portal | `doctor`, `clinic_owner` |
| Delete simulation | `doctor`, `clinic_owner` |
| View shared (portal) | `patient` (own data only, via share_token) |

### 9.4 Rate Limiting & Quotas

| Plan | Simulations/month/doctor |
|------|--------------------------|
| Starter + add-on | 10 |
| Pro + add-on | 30 |
| Clinica + add-on | 50 per clinic |
| Enterprise | Unlimited |

Quota tracked via Redis counter: `dentalos:{tid}:ai:smile_sim:monthly:{year_month}`.

### 9.5 Data Retention

- Completed simulations and images retained for 2 years.
- Failed simulations cleaned up after 30 days (original image retained, generated images deleted).
- When a patient is fully deleted (GDPR/Habeas Data request), all simulation images are purged from S3.

### 9.6 Image Generation Safety

- The image generation prompt explicitly instructs "dental photography" context to avoid inappropriate outputs.
- Generated images are validated for minimum dimensions and non-blank content before storage.
- Prompts are stored in the `variants` JSONB for audit purposes.

---

## 10. Feature Flag Gating

### Tenant Feature Check

```python
async def require_smile_simulator(tenant: TenantContext = Depends(resolve_tenant)):
    if not tenant.features.get("ai_smile_sim", False):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "SMILE_SIMULATOR_feature_disabled",
                "message": "AI Smile Simulator is not enabled for this clinic. Contact support to enable the AI Radiograph add-on.",
                "details": {"required_addon": "ai_radiograph", "price": "$20/doctor/mo"}
            }
        )
```

### Frontend Feature Check

```typescript
// In the smile simulation components
const { data: tenant } = useTenant();
const isSmileSimEnabled = tenant?.features?.ai_smile_sim === true;

// Conditionally render menu item / page content
if (!isSmileSimEnabled) {
  return <UpgradePrompt feature="Simulador de Sonrisa IA" addon="ai_radiograph" />;
}
```

---

## 11. Frontend Components

### 11.1 Component Tree

```
app/(dashboard)/patients/[id]/smile-simulations/
  page.tsx                          # Gallery page — list all simulations
  [simulationId]/
    page.tsx                        # Detail page — before/after view

components/smile-simulator/
  smile-upload-dialog.tsx           # Upload photo + select treatment type
  smile-gallery.tsx                 # Grid of simulation thumbnails
  smile-gallery-card.tsx            # Single simulation card (thumbnail + status badge)
  smile-before-after.tsx            # Side-by-side before/after with slider
  smile-variant-selector.tsx        # Tab/button group to switch variants
  smile-share-dialog.tsx            # Dialog to share to portal + add instructions
  smile-processing-status.tsx       # Progress indicator during AI processing
  smile-analysis-panel.tsx          # Expandable panel showing analysis details (staff only)
  smile-portal-view.tsx             # Patient portal view (read-only)
  smile-disclaimer.tsx              # Regulatory disclaimer component

lib/hooks/
  use-smile-simulations.ts          # React Query hooks for CRUD operations
```

### 11.2 Upload Dialog (`smile-upload-dialog.tsx`)

- Triggered from patient profile or treatment plan page.
- Dropzone for photo upload with preview.
- Treatment type selector (radio group with icons per type).
- Optional links to treatment plan / quotation (searchable dropdowns).
- Consent checkbox with full text visible.
- Submit button disabled until consent is checked and photo is uploaded.
- On submit: POST multipart/form-data, show processing status.

### 11.3 Before/After Slider (`smile-before-after.tsx`)

- Side-by-side layout with a draggable divider.
- Left: original photo. Right: selected variant.
- Slider handle with "Antes | Despues" label.
- Touch-friendly (works on tablets).
- Variant selector tabs above the slider to switch between conservative/moderate/ideal.
- Full-screen toggle for detailed viewing.

```typescript
interface SmileBeforeAfterProps {
  originalImageUrl: string;
  variants: SmileSimulationVariant[];
  selectedVariant: VariantType | null;
  onVariantChange: (variant: VariantType) => void;
}
```

### 11.4 Gallery Page

- Grid layout showing all simulations for a patient.
- Each card shows: thumbnail (original), treatment type badge, status indicator, date.
- Click to open detail view.
- "Nueva Simulacion" button at top (opens upload dialog).
- Filter by treatment type and status.

### 11.5 Processing Status (`smile-processing-status.tsx`)

- Shown after upload while worker processes the simulation.
- Three-step progress:
  1. "Analizando sonrisa..." (status: `analyzing`)
  2. "Generando simulaciones..." (status: `generating`)
  3. "Listo" (status: `completed`)
- Auto-polls GET endpoint every 3 seconds.
- On completion, transitions to the before/after view.
- On failure, shows error message with retry option.

### 11.6 React Query Hooks (`use-smile-simulations.ts`)

```typescript
// List simulations for a patient
export function useSmileSimulations(patientId: string, params?: ListParams) {
  return useQuery({
    queryKey: ["patients", patientId, "smile-simulations", params],
    queryFn: () => apiClient.get(`/patients/${patientId}/smile-simulations`, { params }),
  });
}

// Get a single simulation
export function useSmileSimulation(patientId: string, simulationId: string) {
  return useQuery({
    queryKey: ["patients", patientId, "smile-simulations", simulationId],
    queryFn: () => apiClient.get(`/patients/${patientId}/smile-simulations/${simulationId}`),
    refetchInterval: (data) =>
      data?.status === "completed" || data?.status === "failed" ? false : 3000,
  });
}

// Create simulation (multipart upload)
export function useCreateSmileSimulation(patientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      apiClient.post(`/patients/${patientId}/smile-simulations`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries(["patients", patientId, "smile-simulations"]);
    },
  });
}

// Select variant
export function useSelectVariant(patientId: string, simulationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variant: VariantType) =>
      apiClient.put(
        `/patients/${patientId}/smile-simulations/${simulationId}/select`,
        { variant }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries(["patients", patientId, "smile-simulations", simulationId]);
    },
  });
}

// Share to portal
export function useShareSimulation(patientId: string, simulationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { patient_instructions?: string }) =>
      apiClient.post(
        `/patients/${patientId}/smile-simulations/${simulationId}/share`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries(["patients", patientId, "smile-simulations", simulationId]);
    },
  });
}

// Delete simulation
export function useDeleteSmileSimulation(patientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (simulationId: string) =>
      apiClient.delete(`/patients/${patientId}/smile-simulations/${simulationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries(["patients", patientId, "smile-simulations"]);
    },
  });
}
```

---

## 12. Portal Integration

### 12.1 Patient Portal Page

```
app/(portal)/smile-simulations/
  [shareToken]/
    page.tsx                        # Shared simulation view
```

- Patient navigates from notification or portal dashboard.
- Shows the before/after slider with all three variants.
- Doctor's selected variant is highlighted with a "Recomendado por tu doctor" badge.
- Patient instructions displayed above the slider.
- Disclaimer always visible at the bottom.
- No editing capabilities — read-only.
- Download button for the selected variant image (with disclaimer watermark).

### 12.2 Notification on Share

When a doctor shares a simulation, the system creates:

1. **In-app notification** to the patient: "Tu doctor ha compartido una simulacion de tu sonrisa. Haz clic para verla."
2. **WhatsApp notification** (if WhatsApp channel enabled for the patient): "Hola {patient_name}, tu doctor ha compartido una simulacion de tu futura sonrisa. Ingresa al portal para verla: {portal_link}"

Notification sent via the `notifications` queue with job type `notification.send`.

### 12.3 Link to Quotation

When a simulation is linked to a quotation and shared via portal, the patient portal shows a "Ver Presupuesto" button below the simulation that navigates to the linked quotation page. This drives treatment acceptance.

---

## 13. Configuration

### Settings (`backend/app/core/config.py`)

```python
class SmileSimulatorConfig(BaseModel):
    enabled: bool = False
    claude_model: str = "claude-sonnet-4-20250514"
    image_model: str = "dall-e-3"
    image_size: str = "1024x1024"
    image_quality: str = "hd"
    max_image_size_mb: int = 10
    min_resolution_width: int = 800
    min_resolution_height: int = 600
    analysis_max_tokens: int = 2000
    monthly_quota_starter: int = 10
    monthly_quota_pro: int = 30
    monthly_quota_clinica: int = 50
    poll_interval_seconds: int = 3
    result_retention_days: int = 730  # 2 years
    failed_cleanup_days: int = 30
```

### Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `SMILE_SIM_ENABLED` | `false` | Master kill switch |
| `SMILE_SIM_CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model for analysis |
| `SMILE_SIM_IMAGE_MODEL` | `dall-e-3` | Image generation model |
| `SMILE_SIM_IMAGE_SIZE` | `1024x1024` | Generated image resolution |
| `OPENAI_API_KEY` | — | Required for DALL-E 3 |

---

## 14. Test Plan

### 14.1 Unit Tests

| Test | File | What |
|------|------|------|
| Schema validation | `tests/unit/test_smile_simulation_schemas.py` | Pydantic models accept valid input, reject invalid |
| Treatment type enum | `tests/unit/test_smile_simulation_schemas.py` | All 7 treatment types accepted, unknown rejected |
| Consent validation | `tests/unit/test_smile_simulation_schemas.py` | `consent_given=false` raises validation error at service level |
| Quota calculation | `tests/unit/test_smile_simulation_service.py` | Quota enforced per plan tier |
| Variant JSONB structure | `tests/unit/test_smile_simulation_schemas.py` | Variants array validates correctly |
| Prompt construction | `tests/unit/test_smile_simulation_prompts.py` | Analysis and generation prompts built correctly per treatment type |
| Share token generation | `tests/unit/test_smile_simulation_service.py` | Token is unique, 64 chars, URL-safe |

### 14.2 Integration Tests

| Test | File | What |
|------|------|------|
| Create simulation | `tests/integration/test_smile_simulation_api.py` | POST → 202, record created, message enqueued |
| Get simulation | `tests/integration/test_smile_simulation_api.py` | GET → 200, returns correct data |
| List simulations | `tests/integration/test_smile_simulation_api.py` | Pagination, filters work |
| Select variant | `tests/integration/test_smile_simulation_api.py` | PUT → 200, variant stored |
| Share to portal | `tests/integration/test_smile_simulation_api.py` | POST → 200, share_token generated, notification enqueued |
| Unshare | `tests/integration/test_smile_simulation_api.py` | POST → 200, `is_shared` set to false |
| Soft delete | `tests/integration/test_smile_simulation_api.py` | DELETE → 200, `is_active = false` |
| Portal view | `tests/integration/test_smile_simulation_portal.py` | GET with share_token → 200, no internal fields exposed |
| Feature flag disabled | `tests/integration/test_smile_simulation_api.py` | All endpoints → 403 when flag off |
| RBAC | `tests/integration/test_smile_simulation_api.py` | Receptionist cannot create, patient cannot access staff endpoints |
| Tenant isolation | `tests/integration/test_smile_simulation_api.py` | Tenant A cannot see Tenant B simulations |
| Quota enforcement | `tests/integration/test_smile_simulation_api.py` | Returns 429 when monthly quota exceeded |

### 14.3 Worker Tests

| Test | File | What |
|------|------|------|
| Happy path | `tests/integration/test_smile_simulation_worker.py` | Full pipeline: analyze → generate 3 variants → update DB |
| Analysis failure | `tests/integration/test_smile_simulation_worker.py` | Claude API error → status `failed`, retry queued |
| Partial generation | `tests/integration/test_smile_simulation_worker.py` | 1 of 3 variants fails → status `completed` with 2 variants |
| All generation fails | `tests/integration/test_smile_simulation_worker.py` | All 3 fail → status `failed`, retry queued |
| Poor photo quality | `tests/integration/test_smile_simulation_worker.py` | Low confidence → warning attached, simulation completes |
| S3 upload failure | `tests/integration/test_smile_simulation_worker.py` | S3 error → status `failed` |

### 14.4 Mock Adapter Tests

| Test | File | What |
|------|------|------|
| Mock analysis | `tests/unit/test_smile_simulator_mock.py` | Returns valid structure |
| Mock generation | `tests/unit/test_smile_simulator_mock.py` | Returns image bytes |
| Health check | `tests/unit/test_smile_simulator_mock.py` | Returns `True` |

### 14.5 Frontend Tests

| Test | File | What |
|------|------|------|
| Upload dialog | `__tests__/smile-upload-dialog.test.tsx` | Renders, validates consent, submits form |
| Before/after slider | `__tests__/smile-before-after.test.tsx` | Renders images, slider interaction, variant switching |
| Gallery | `__tests__/smile-gallery.test.tsx` | Renders cards, handles empty state |
| Processing status | `__tests__/smile-processing-status.test.tsx` | Shows correct step, polls, transitions on completion |
| Portal view | `__tests__/smile-portal-view.test.tsx` | Read-only, disclaimer visible, download button |
| Feature flag gate | `__tests__/smile-simulator-gate.test.tsx` | Shows upgrade prompt when flag disabled |

### 14.6 E2E Tests

| Test | What |
|------|------|
| Full flow | Upload photo → wait for processing → view result → select variant → share → patient views in portal |
| Treatment plan link | Create simulation linked to treatment plan → verify link in both directions |
| Quota limit | Create simulations up to quota → verify 429 on next attempt |

---

## 15. Dentalink Comparison

| Capability | Dentalink | DentalOS |
|-----------|-----------|----------|
| Basic smile simulation | Yes (single result) | Yes (3 variants) |
| Treatment-type specific | Unknown | Yes (7 types with specialized prompts) |
| Multiple variants | No | Yes (conservative, moderate, ideal) |
| Before/after slider | Basic | Yes (draggable, touch-friendly, full-screen) |
| Linked to treatment plan | No | Yes (bidirectional link) |
| Linked to quotation | No | Yes (drives acceptance) |
| Patient portal sharing | Unknown | Yes (with instructions + notifications) |
| WhatsApp notification | No | Yes (via notification system) |
| Doctor variant selection | No | Yes (recommended variant highlighted in portal) |
| Audit trail | Unknown | Yes (prompts stored, token usage tracked) |
| Consent tracking | Unknown | Yes (explicit consent required, timestamped) |

**Key differentiator:** DentalOS ties the simulation to the treatment plan and quotation, creating a direct path from "here is what your smile could look like" to "here is the treatment plan and cost." This is designed to increase treatment acceptance rates.
