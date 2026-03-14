# AI Radiograph Analysis — Full API Spec (AI-01)

**Feature code:** `ai_radiograph`
**Add-on:** $20/doctor/mo (bundled with Radiograph Overlay + Smile Simulator)
**Feature flag:** `ai_radiograph` (tenant `features` JSONB)
**Sprint:** S35-36 (Tier 1 — Competitive Parity)
**Priority:** Critical

---

## 1. Overview

AI Radiograph Analysis allows doctors and assistants to upload a dental radiograph image (periapical, panoramic, bitewing, or cephalometric) and receive AI-generated findings within 15-30 seconds. The AI identifies clinical findings such as caries, bone loss, periapical lesions, restorations, impacted teeth, root fragments, and calculus. Each finding is mapped to a specific tooth (FDI notation), assigned a severity score, and optionally linked to a treatment suggestion.

The doctor reviews each finding and accepts, rejects, or modifies it. Accepted findings are linked to the patient's clinical record and can auto-create diagnoses with CIE-10 codes and treatment plan items with CUPS codes.

**Regulatory disclaimer (always shown in UI):**
> "Esta es una sugerencia de IA. El diagnostico final es responsabilidad del profesional."

### Architecture Diagram

```
┌──────────────┐     POST /radiograph-analyses     ┌──────────────────┐
│   Frontend   │ ──────────────────────────────────→│    FastAPI        │
│  (Upload +   │     202 Accepted (analysis_id)     │    Route          │
│   Poll)      │ ←──────────────────────────────────│                  │
│              │                                     │  1. Validate image│
│              │     GET /radiograph-analyses/{id}   │  2. Upload to S3  │
│              │ ──────────────────────────────────→│  3. Create record │
│              │     200 (status: processing|done)   │  4. Enqueue job   │
│              │ ←──────────────────────────────────│                  │
└──────────────┘                                     └────────┬─────────┘
                                                              │
                                                    RabbitMQ  │ radiograph.analyze
                                                              ▼
                                                    ┌──────────────────┐
                                                    │  Clinical Worker  │
                                                    │                  │
                                                    │  1. Fetch image   │
                                                    │     from S3      │
                                                    │  2. Strip DICOM   │
                                                    │     metadata     │
                                                    │  3. Call Claude   │
                                                    │     Vision API   │
                                                    │  4. Parse findings│
                                                    │  5. Update record │
                                                    │  6. Log AI usage  │
                                                    └──────────────────┘
```

---

## 2. Database Schema

### Table: `radiograph_analyses` (tenant schema `tn_*`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, `DEFAULT gen_random_uuid()` | |
| `patient_id` | `UUID` | FK → `patients.id`, NOT NULL | |
| `doctor_id` | `UUID` | FK → `users.id`, NOT NULL | Doctor who requested analysis |
| `document_id` | `UUID` | FK → `patient_documents.id`, NULL | Link to patient documents if stored there |
| `image_url` | `VARCHAR(500)` | NOT NULL | S3 path: `/{tenant_id}/{patient_id}/radiographs/{uuid}.{ext}` |
| `image_type` | `VARCHAR(20)` | NOT NULL, CHECK | `periapical`, `panoramic`, `bitewing`, `cephalometric`, `occlusal` |
| `status` | `VARCHAR(20)` | NOT NULL, DEFAULT `'pending'`, CHECK | `pending`, `processing`, `completed`, `failed`, `reviewed` |
| `findings` | `JSONB` | DEFAULT `'[]'` | Array of structured finding objects (see below) |
| `summary` | `TEXT` | NULL | AI-generated narrative summary in Spanish |
| `finding_count` | `INTEGER` | DEFAULT `0` | Denormalized count for list views |
| `review_status` | `VARCHAR(20)` | DEFAULT `'pending'`, CHECK | `pending`, `partial`, `completed` |
| `reviewed_by` | `UUID` | FK → `users.id`, NULL | Doctor who reviewed findings |
| `reviewed_at` | `TIMESTAMPTZ` | NULL | Timestamp of review completion |
| `model_used` | `VARCHAR(50)` | NULL | e.g. `claude-sonnet-4-20250514` |
| `input_tokens` | `INTEGER` | DEFAULT `0` | Token usage tracking |
| `output_tokens` | `INTEGER` | DEFAULT `0` | Token usage tracking |
| `processing_time_ms` | `INTEGER` | NULL | Wall-clock time for AI call |
| `error_message` | `TEXT` | NULL | Error details if `status = 'failed'` |
| `notes` | `TEXT` | NULL | Doctor's free-text notes on the analysis |
| `is_active` | `BOOLEAN` | DEFAULT `true` | Soft delete flag |
| `deleted_at` | `TIMESTAMPTZ` | NULL | Soft delete timestamp |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` | |

### Indexes

```sql
CREATE INDEX idx_radiograph_analyses_patient_id ON radiograph_analyses(patient_id);
CREATE INDEX idx_radiograph_analyses_doctor_id ON radiograph_analyses(doctor_id);
CREATE INDEX idx_radiograph_analyses_status ON radiograph_analyses(status);
CREATE INDEX idx_radiograph_analyses_created_at ON radiograph_analyses(created_at DESC);
CREATE INDEX idx_radiograph_analyses_findings ON radiograph_analyses USING GIN (findings);
```

### Findings JSONB Structure

Each element in the `findings` array:

```json
{
  "finding_id": "uuid-v4",
  "type": "caries",
  "tooth_number": "46",
  "surface": "mesial-occlusal",
  "severity": "moderate",
  "confidence": 0.87,
  "description": "Lesion cariosa en superficie mesio-oclusal del diente 46",
  "bounding_box": {
    "x": 0.45,
    "y": 0.32,
    "width": 0.08,
    "height": 0.06
  },
  "suggested_cie10": "K02.1",
  "suggested_cups": "232101",
  "suggested_treatment": "Restauracion resina compuesta clase II",
  "review_status": "pending",
  "accepted": null,
  "rejected_reason": null,
  "linked_diagnosis_id": null,
  "linked_treatment_item_id": null
}
```

#### Finding Types (enum)

| Type | Description |
|------|-------------|
| `caries` | Carious lesion |
| `bone_loss` | Alveolar bone loss (periodontal) |
| `periapical_lesion` | Periapical radiolucency |
| `restoration` | Existing restoration detected |
| `impacted_tooth` | Impacted or partially erupted tooth |
| `root_fragment` | Retained root fragment |
| `calculus` | Calculus / tarite deposits |
| `root_canal` | Existing root canal treatment |
| `crown` | Existing crown or bridge |
| `implant` | Existing dental implant |
| `fracture` | Tooth or root fracture |
| `resorption` | Root resorption (internal or external) |
| `cyst` | Cystic lesion |
| `supernumerary` | Supernumerary tooth |
| `missing_tooth` | Missing tooth identified |
| `widened_pdl` | Widened periodontal ligament space |
| `other` | Other finding not in categories |

#### Severity Levels

| Level | Code | Numeric Score | Description |
|-------|------|---------------|-------------|
| Normal | `normal` | 0 | Within normal limits (used for `restoration`, `crown`, `implant`, `root_canal`) |
| Low | `low` | 1 | Early/incipient, monitor |
| Moderate | `moderate` | 2 | Requires treatment, non-urgent |
| High | `high` | 3 | Requires prompt treatment |
| Critical | `critical` | 4 | Requires urgent/immediate intervention |

#### Review Status per Finding

| Status | Description |
|--------|-------------|
| `pending` | Not yet reviewed by doctor |
| `accepted` | Doctor confirmed the finding |
| `rejected` | Doctor rejected the finding |
| `modified` | Doctor accepted with modifications |

---

## 3. API Endpoints

**Base path:** `/api/v1/patients/{patient_id}/radiograph-analyses`

### 3.1 Create Radiograph Analysis

Upload an image and initiate async AI analysis.

```
POST /api/v1/patients/{patient_id}/radiograph-analyses
Content-Type: multipart/form-data
Authorization: Bearer {jwt}
```

**Request (multipart/form-data):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | file | Yes | JPEG, PNG, or DICOM. Max 10MB. |
| `image_type` | string | Yes | One of: `periapical`, `panoramic`, `bitewing`, `cephalometric`, `occlusal` |
| `notes` | string | No | Optional notes from the doctor |

**Auth:** `doctor`, `assistant` (assistant creates on behalf of a doctor)
**Feature gate:** `ai_radiograph` must be enabled for the tenant

**Response: 202 Accepted**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "patient_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "doctor_id": "8a9e6679-7425-40de-944b-e07fc1f90ae7",
  "image_url": "/tn_abc123/7c9e6679/radiographs/550e8400.jpg",
  "image_type": "periapical",
  "status": "pending",
  "findings": [],
  "summary": null,
  "finding_count": 0,
  "review_status": "pending",
  "reviewed_by": null,
  "reviewed_at": null,
  "model_used": null,
  "processing_time_ms": null,
  "notes": null,
  "created_at": "2026-03-13T10:30:00Z",
  "updated_at": "2026-03-13T10:30:00Z"
}
```

**Error responses:**

| Code | Error | Description |
|------|-------|-------------|
| 400 | `RADIOGRAPH_ANALYSIS_invalid_image` | Unsupported file type or corrupt image |
| 400 | `RADIOGRAPH_ANALYSIS_image_too_large` | File exceeds 10MB limit |
| 400 | `RADIOGRAPH_ANALYSIS_invalid_image_type` | Invalid `image_type` value |
| 403 | `RADIOGRAPH_ANALYSIS_feature_disabled` | `ai_radiograph` feature flag not enabled |
| 404 | `PATIENT_not_found` | Patient does not exist or is soft-deleted |
| 429 | `RADIOGRAPH_ANALYSIS_rate_limited` | Too many analyses in short period (max 10/hour per doctor) |

### 3.2 Get Radiograph Analysis

Retrieve a single analysis (used for polling during processing).

```
GET /api/v1/patients/{patient_id}/radiograph-analyses/{analysis_id}
Authorization: Bearer {jwt}
```

**Auth:** `doctor`, `assistant`, `clinic_owner`

**Response: 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "patient_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "doctor_id": "8a9e6679-7425-40de-944b-e07fc1f90ae7",
  "image_url": "https://s3.example.com/signed-url?expires=900",
  "image_type": "periapical",
  "status": "completed",
  "findings": [
    {
      "finding_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "type": "caries",
      "tooth_number": "46",
      "surface": "mesial-occlusal",
      "severity": "moderate",
      "confidence": 0.87,
      "description": "Lesion cariosa en superficie mesio-oclusal del diente 46",
      "bounding_box": {
        "x": 0.45,
        "y": 0.32,
        "width": 0.08,
        "height": 0.06
      },
      "suggested_cie10": "K02.1",
      "suggested_cups": "232101",
      "suggested_treatment": "Restauracion resina compuesta clase II",
      "review_status": "pending",
      "accepted": null,
      "rejected_reason": null,
      "linked_diagnosis_id": null,
      "linked_treatment_item_id": null
    }
  ],
  "summary": "Se identifican 3 hallazgos: caries moderada en diente 46 (MO), perdida osea leve en sector posterior inferior, y restauracion existente en diente 36.",
  "finding_count": 3,
  "review_status": "pending",
  "reviewed_by": null,
  "reviewed_at": null,
  "model_used": "claude-sonnet-4-20250514",
  "input_tokens": 4200,
  "output_tokens": 1800,
  "processing_time_ms": 18500,
  "notes": null,
  "created_at": "2026-03-13T10:30:00Z",
  "updated_at": "2026-03-13T10:30:25Z"
}
```

**Notes:**
- `image_url` in responses is a **signed S3 URL** (15-minute expiry). The raw path is stored in DB.
- Frontend polls this endpoint every 3 seconds while `status` is `pending` or `processing`. Stops polling on `completed` or `failed`.

### 3.3 List Radiograph Analyses

List analyses for a patient, paginated.

```
GET /api/v1/patients/{patient_id}/radiograph-analyses?page=1&page_size=20
Authorization: Bearer {jwt}
```

**Query parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 20 | Items per page (max 50) |
| `status` | string | (all) | Filter by status: `pending`, `processing`, `completed`, `failed`, `reviewed` |
| `image_type` | string | (all) | Filter by image type |
| `date_from` | date | (none) | Filter `created_at >= date_from` |
| `date_to` | date | (none) | Filter `created_at <= date_to` |

**Auth:** `doctor`, `assistant`, `clinic_owner`

**Response: 200 OK**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "patient_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "doctor_id": "8a9e6679-7425-40de-944b-e07fc1f90ae7",
      "image_type": "periapical",
      "status": "completed",
      "finding_count": 3,
      "review_status": "pending",
      "model_used": "claude-sonnet-4-20250514",
      "created_at": "2026-03-13T10:30:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

**Note:** List response uses a summary schema — no `findings` array, no `image_url`, no `summary` text. Use the GET detail endpoint for full data.

### 3.4 Review Findings

Doctor accepts, rejects, or modifies individual findings. Batch operation — all finding reviews submitted at once.

```
PUT /api/v1/patients/{patient_id}/radiograph-analyses/{analysis_id}/review
Authorization: Bearer {jwt}
Content-Type: application/json
```

**Auth:** `doctor` only (assistants cannot review)

**Request:**

```json
{
  "findings": [
    {
      "finding_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "review_status": "accepted",
      "create_diagnosis": true,
      "create_treatment_item": false,
      "modified_tooth_number": null,
      "modified_severity": null,
      "modified_type": null,
      "rejected_reason": null
    },
    {
      "finding_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "review_status": "rejected",
      "create_diagnosis": false,
      "create_treatment_item": false,
      "rejected_reason": "Artifact, not a real finding"
    },
    {
      "finding_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "review_status": "modified",
      "create_diagnosis": true,
      "create_treatment_item": true,
      "modified_tooth_number": "47",
      "modified_severity": "high",
      "modified_type": null,
      "rejected_reason": null
    }
  ],
  "notes": "Coincido con el hallazgo de caries en 46. El hallazgo 2 es un artefacto."
}
```

**Request fields per finding:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `finding_id` | UUID | Yes | Must match a finding in the analysis |
| `review_status` | string | Yes | `accepted`, `rejected`, `modified` |
| `create_diagnosis` | bool | No (default false) | If true, auto-creates a diagnosis record for this finding |
| `create_treatment_item` | bool | No (default false) | If true, auto-creates a treatment plan item |
| `modified_tooth_number` | string | No | Override tooth number (FDI format `^[1-8][1-8]$`) |
| `modified_severity` | string | No | Override severity level |
| `modified_type` | string | No | Override finding type |
| `rejected_reason` | string | No | Required when `review_status = 'rejected'` |

**Response: 200 OK**

Returns the full updated analysis (same schema as GET detail), with:
- Each finding's `review_status`, `accepted`, `rejected_reason` updated
- `review_status` on the analysis set to `completed` (if all findings reviewed) or `partial` (if some pending)
- `reviewed_by` and `reviewed_at` populated
- `linked_diagnosis_id` and `linked_treatment_item_id` populated for accepted/modified findings where `create_diagnosis`/`create_treatment_item` was true

**Error responses:**

| Code | Error | Description |
|------|-------|-------------|
| 400 | `RADIOGRAPH_ANALYSIS_invalid_finding_id` | `finding_id` does not exist in analysis |
| 400 | `RADIOGRAPH_ANALYSIS_already_reviewed` | Finding has already been reviewed |
| 400 | `RADIOGRAPH_ANALYSIS_not_completed` | Cannot review findings while status is `pending` or `processing` |
| 400 | `RADIOGRAPH_ANALYSIS_rejected_needs_reason` | `rejected_reason` required when `review_status = 'rejected'` |
| 400 | `VALIDATION_invalid_tooth_number` | `modified_tooth_number` does not match FDI pattern |
| 404 | `RADIOGRAPH_ANALYSIS_not_found` | Analysis does not exist or is soft-deleted |

### 3.5 Delete Radiograph Analysis (Soft Delete)

```
DELETE /api/v1/patients/{patient_id}/radiograph-analyses/{analysis_id}
Authorization: Bearer {jwt}
```

**Auth:** `doctor`, `clinic_owner`

**Response: 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted": true
}
```

Sets `is_active = false` and `deleted_at = now()`. Clinical data is never hard-deleted per regulatory requirements.

### 3.6 Retry Failed Analysis

Re-enqueue a failed analysis for another attempt.

```
POST /api/v1/patients/{patient_id}/radiograph-analyses/{analysis_id}/retry
Authorization: Bearer {jwt}
```

**Auth:** `doctor`, `assistant`

**Preconditions:** `status` must be `failed`. Max 3 retries total (tracked via worker retry count).

**Response: 200 OK**

Returns the updated analysis with `status` reset to `pending`.

**Error responses:**

| Code | Error | Description |
|------|-------|-------------|
| 400 | `RADIOGRAPH_ANALYSIS_not_failed` | Can only retry analyses with `status = 'failed'` |
| 400 | `RADIOGRAPH_ANALYSIS_max_retries` | Maximum retry count (3) exceeded |

### 3.7 Get Analysis Statistics (Aggregate)

Summary statistics for a patient's radiograph history.

```
GET /api/v1/patients/{patient_id}/radiograph-analyses/stats
Authorization: Bearer {jwt}
```

**Auth:** `doctor`, `clinic_owner`

**Response: 200 OK**

```json
{
  "total_analyses": 12,
  "total_findings": 38,
  "accepted_findings": 30,
  "rejected_findings": 5,
  "pending_review": 3,
  "findings_by_type": {
    "caries": 12,
    "bone_loss": 8,
    "periapical_lesion": 4,
    "restoration": 10,
    "other": 4
  },
  "avg_confidence": 0.82,
  "last_analysis_at": "2026-03-13T10:30:00Z"
}
```

---

## 4. Pydantic Schemas

Located in `backend/app/schemas/radiograph_analysis.py`.

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BoundingBox(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0, description="Relative X position (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Relative Y position (0-1)")
    width: float = Field(..., gt=0.0, le=1.0, description="Relative width (0-1)")
    height: float = Field(..., gt=0.0, le=1.0, description="Relative height (0-1)")


class RadiographFinding(BaseModel):
    finding_id: UUID
    type: str
    tooth_number: str | None = None
    surface: str | None = None
    severity: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str
    bounding_box: BoundingBox | None = None
    suggested_cie10: str | None = None
    suggested_cups: str | None = None
    suggested_treatment: str | None = None
    review_status: str = "pending"
    accepted: bool | None = None
    rejected_reason: str | None = None
    linked_diagnosis_id: UUID | None = None
    linked_treatment_item_id: UUID | None = None

    @field_validator("tooth_number")
    @classmethod
    def validate_tooth_number(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^[1-8][1-8]$", v):
                raise ValueError("tooth_number must be FDI notation (11-48, 51-85)")
        return v


class RadiographAnalysisCreate(BaseModel):
    image_type: str = Field(..., pattern="^(periapical|panoramic|bitewing|cephalometric|occlusal)$")
    notes: str | None = Field(None, max_length=2000)


class FindingReviewItem(BaseModel):
    finding_id: UUID
    review_status: str = Field(..., pattern="^(accepted|rejected|modified)$")
    create_diagnosis: bool = False
    create_treatment_item: bool = False
    modified_tooth_number: str | None = None
    modified_severity: str | None = None
    modified_type: str | None = None
    rejected_reason: str | None = None

    @field_validator("modified_tooth_number")
    @classmethod
    def validate_modified_tooth(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^[1-8][1-8]$", v):
                raise ValueError("modified_tooth_number must be FDI notation")
        return v


class RadiographReviewRequest(BaseModel):
    findings: list[FindingReviewItem] = Field(..., min_length=1)
    notes: str | None = Field(None, max_length=5000)


class RadiographAnalysisResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    image_url: str | None = None
    image_type: str
    status: str
    findings: list[RadiographFinding] = []
    summary: str | None = None
    finding_count: int = 0
    review_status: str = "pending"
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    model_used: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    processing_time_ms: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RadiographAnalysisListItem(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    image_type: str
    status: str
    finding_count: int = 0
    review_status: str = "pending"
    model_used: str | None = None
    created_at: datetime


class RadiographAnalysisListResponse(BaseModel):
    items: list[RadiographAnalysisListItem]
    total: int
    page: int
    page_size: int


class RadiographAnalysisStatsResponse(BaseModel):
    total_analyses: int
    total_findings: int
    accepted_findings: int
    rejected_findings: int
    pending_review: int
    findings_by_type: dict[str, int]
    avg_confidence: float
    last_analysis_at: datetime | None
```

---

## 5. Integration Adapter Interface

Located in `backend/app/integrations/radiograph_analysis/`.

### 5.1 Abstract Base (`base.py`)

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class RadiographAnalysisResult:
    """Result from a radiograph analysis provider."""

    def __init__(
        self,
        *,
        findings: list[dict[str, Any]],
        summary: str,
        model_used: str,
        input_tokens: int,
        output_tokens: int,
        processing_time_ms: int,
    ):
        self.findings = findings
        self.summary = summary
        self.model_used = model_used
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.processing_time_ms = processing_time_ms


class RadiographAnalysisProviderBase(ABC):
    """Contract for radiograph analysis AI providers.

    Security:
      - Image data MUST be stripped of DICOM/EXIF metadata containing PHI
        (patient name, DOB, facility name) before being passed to any method.
      - No patient identifiers (name, document number, phone) are ever sent
        to the AI provider.
      - Only anonymized clinical context (age, tooth chart summary) may be
        included in prompts.
    """

    @abstractmethod
    async def analyze(
        self,
        *,
        image_bytes: bytes,
        image_media_type: str,
        image_type: str,
        patient_age: int | None = None,
        existing_conditions: list[dict[str, Any]] | None = None,
    ) -> RadiographAnalysisResult:
        """Analyze a dental radiograph image and return structured findings.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG). DICOM must be
                pre-converted. All EXIF/DICOM PHI must be stripped.
            image_media_type: MIME type ('image/jpeg' or 'image/png').
            image_type: Type of radiograph ('periapical', 'panoramic',
                'bitewing', 'cephalometric', 'occlusal').
            patient_age: Patient age in years (for context, no PHI).
            existing_conditions: List of current odontogram conditions
                for context (tooth_number, condition_type only — no PHI).

        Returns:
            RadiographAnalysisResult with structured findings, summary,
            and token usage.

        Raises:
            RuntimeError: If the AI provider call fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the provider is reachable and operational.

        Returns:
            True if the provider is healthy, False otherwise.
        """
        ...
```

### 5.2 Claude Vision Implementation (`claude_service.py`)

Uses `ai_claude_client.py` with the Claude Vision API. Sends the image as a base64-encoded content block.

**System prompt** (stored as constant, version-controlled):

```
You are a dental radiograph analysis AI assistant. Analyze the provided dental
radiograph and identify all clinical findings.

For each finding, provide:
1. type: One of [caries, bone_loss, periapical_lesion, restoration, impacted_tooth,
   root_fragment, calculus, root_canal, crown, implant, fracture, resorption, cyst,
   supernumerary, missing_tooth, widened_pdl, other]
2. tooth_number: FDI notation (11-48 for permanent, 51-85 for deciduous), or null
   if the finding is not tooth-specific
3. surface: Affected surface(s) if applicable (mesial, distal, occlusal, buccal,
   lingual, or combinations like "mesial-occlusal")
4. severity: One of [normal, low, moderate, high, critical]
5. confidence: Your confidence in this finding (0.0 to 1.0)
6. description: Brief description in Spanish (1-2 sentences)
7. bounding_box: Approximate location on the image as {x, y, width, height} with
   values 0.0-1.0 relative to image dimensions, or null if not applicable
8. suggested_cie10: Relevant ICD-10 (CIE-10) code if applicable
9. suggested_cups: Relevant CUPS procedure code if applicable
10. suggested_treatment: Brief treatment suggestion in Spanish

Image type: {image_type}
Patient age: {patient_age or "Unknown"}

Respond with a JSON object with two keys:
- "findings": array of finding objects
- "summary": a brief narrative summary in Spanish (2-3 sentences)

Important:
- Be thorough but avoid false positives — only report findings you are
  reasonably confident about (confidence >= 0.5)
- For existing restorations, crowns, implants, and root canals, use
  severity "normal" unless there is pathology associated
- Always use FDI tooth numbering notation
- All text descriptions must be in Spanish
```

**Key implementation details:**
- Uses `call_claude()` with `model_override="claude-sonnet-4-20250514"` (Vision model)
- Passes image as base64 content block with `type: "image"` in the messages array
- Timeout: 90 seconds (extended from default 30s)
- Response parsed via `extract_json_object()` from `ai_claude_client.py`
- Each finding is assigned a `finding_id` (UUID4) server-side after parsing
- Findings with `confidence < 0.5` are filtered out

### 5.3 Mock Implementation (`mock_service.py`)

Returns deterministic findings for testing and development. Configurable via constructor to return specific scenarios (no findings, single finding, many findings, error).

---

## 6. Worker Message Format

Published to the `clinical` RabbitMQ queue.

### 6.1 Enqueue Message

```json
{
  "message_id": "uuid-v4",
  "tenant_id": "tn_abc123",
  "job_type": "radiograph.analyze",
  "payload": {
    "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
    "patient_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "image_s3_key": "tn_abc123/7c9e6679/radiographs/550e8400.jpg",
    "image_type": "periapical",
    "patient_age": 34,
    "existing_conditions": [
      {"tooth_number": "36", "condition_type": "restoration"},
      {"tooth_number": "45", "condition_type": "caries"}
    ]
  },
  "priority": 5,
  "retry_count": 0,
  "max_retries": 3
}
```

### 6.2 Worker Processing Steps

1. **Set tenant context:** `SET search_path TO tn_{schema_name}, public`
2. **Fetch image from S3** using the `image_s3_key`
3. **Strip DICOM/EXIF metadata** — remove patient name, DOB, facility info, any embedded PHI
4. **Update status** to `processing`
5. **Call adapter** `analyze()` with stripped image bytes
6. **Assign `finding_id`** (UUID4) to each returned finding
7. **Validate findings:**
   - Each `tooth_number` must match FDI pattern `^[1-8][1-8]$`
   - Each `severity` must be in allowed set
   - Each `type` must be in allowed set
   - Filter out findings with `confidence < 0.5`
8. **Update record** with `findings`, `summary`, `status = 'completed'`, token counts, processing time
9. **Log AI usage** to `ai_usage_logs` table
10. **On failure:** Set `status = 'failed'`, set `error_message`, increment `retry_count`
11. **Retry policy:** 3 retries with exponential backoff (5s, 15s, 45s) then dead-letter

---

## 7. Error Codes

Domain prefix: `RADIOGRAPH_ANALYSIS_`

| Error Code | HTTP | Description |
|------------|------|-------------|
| `RADIOGRAPH_ANALYSIS_not_found` | 404 | Analysis ID does not exist or is soft-deleted |
| `RADIOGRAPH_ANALYSIS_invalid_image` | 400 | Image file is not a valid JPEG, PNG, or DICOM |
| `RADIOGRAPH_ANALYSIS_image_too_large` | 400 | Image file exceeds 10MB limit |
| `RADIOGRAPH_ANALYSIS_invalid_image_type` | 400 | `image_type` value not in allowed set |
| `RADIOGRAPH_ANALYSIS_feature_disabled` | 403 | `ai_radiograph` feature flag not enabled for tenant |
| `RADIOGRAPH_ANALYSIS_rate_limited` | 429 | Exceeded 10 analyses per hour per doctor |
| `RADIOGRAPH_ANALYSIS_not_completed` | 400 | Cannot review findings while analysis is pending/processing |
| `RADIOGRAPH_ANALYSIS_already_reviewed` | 400 | Attempted to re-review an already-reviewed finding |
| `RADIOGRAPH_ANALYSIS_invalid_finding_id` | 400 | `finding_id` does not match any finding in the analysis |
| `RADIOGRAPH_ANALYSIS_rejected_needs_reason` | 400 | `rejected_reason` is required when rejecting a finding |
| `RADIOGRAPH_ANALYSIS_not_failed` | 400 | Retry only allowed on analyses with `status = 'failed'` |
| `RADIOGRAPH_ANALYSIS_max_retries` | 400 | Maximum retry count (3) exceeded |
| `RADIOGRAPH_ANALYSIS_ai_unavailable` | 503 | AI provider is temporarily unavailable |
| `RADIOGRAPH_ANALYSIS_processing_error` | 500 | Unexpected error during AI processing |

Error response format (per API conventions):

```json
{
  "error": "RADIOGRAPH_ANALYSIS_invalid_image",
  "message": "El archivo subido no es una imagen valida. Formatos aceptados: JPEG, PNG, DICOM.",
  "details": {
    "received_content_type": "application/pdf",
    "allowed_types": ["image/jpeg", "image/png", "application/dicom"]
  }
}
```

---

## 8. Security Considerations

### 8.1 PHI Protection

- **Image metadata stripping:** All DICOM tags and EXIF data containing PHI (patient name, date of birth, facility name, referring physician, study description with names) MUST be removed before the image is sent to the Claude API. Use `pydicom` for DICOM files and `Pillow` for JPEG/PNG EXIF stripping.
- **Prompt anonymization:** The AI prompt receives only: patient age (integer), existing tooth conditions (tooth number + condition type). No names, document numbers, phone numbers, or email addresses.
- **Logging:** Never log image contents, patient identifiers, or finding descriptions. Only log: `analysis_id`, `tenant_id`, `status`, `finding_count`, `model_used`, `token_counts`.
- **S3 isolation:** Images stored under `/{tenant_id}/{patient_id}/radiographs/{uuid}.{ext}`. Access via signed URLs (15-minute expiry) only.
- **No browser caching:** Response headers include `Cache-Control: no-store` for all endpoints returning image URLs or findings.

### 8.2 Image Sanitization Pipeline

```
Upload → Validate MIME type → Check file size (<=10MB)
       → Virus scan (ClamAV)
       → Strip EXIF/DICOM metadata
       → Re-encode image (strip embedded scripts)
       → Upload to S3 (tenant-isolated path)
       → Enqueue analysis job
```

### 8.3 Access Control

| Action | Roles Allowed |
|--------|---------------|
| Upload / create analysis | `doctor`, `assistant` |
| View analysis (own patient) | `doctor`, `assistant`, `clinic_owner` |
| Review findings | `doctor` only |
| Delete analysis | `doctor`, `clinic_owner` |
| Retry failed analysis | `doctor`, `assistant` |
| View statistics | `doctor`, `clinic_owner` |

Assistants can upload radiographs on behalf of a doctor but cannot review findings. The `doctor_id` is always the authenticated user for doctors, or must be specified by assistants (validated against active doctors in the tenant).

### 8.4 Rate Limiting

- **Per doctor:** Max 10 analyses per hour (prevents runaway costs)
- **Per tenant:** Max 100 analyses per day (configurable per plan)
- Rate limit tracked in Redis: `dentalos:{tid}:ai:radiograph:rate:{doctor_id}` (TTL 1 hour, counter)
- Rate limit response includes `Retry-After` header

### 8.5 Audit Trail

Every analysis action logged to `audit_logs`:

| Event | Logged Data |
|-------|-------------|
| `radiograph_analysis.created` | analysis_id, patient_id, doctor_id, image_type |
| `radiograph_analysis.completed` | analysis_id, finding_count, processing_time_ms |
| `radiograph_analysis.failed` | analysis_id, error_code (no error message details) |
| `radiograph_analysis.reviewed` | analysis_id, reviewed_by, accepted_count, rejected_count |
| `radiograph_analysis.deleted` | analysis_id, deleted_by |
| `radiograph_analysis.retried` | analysis_id, retry_count |

---

## 9. Feature Flag Gating

### Tenant Feature Check

The `ai_radiograph` flag is checked in the route handler before any processing:

```python
@router.post("", status_code=202)
async def create_radiograph_analysis(
    patient_id: UUID,
    image: UploadFile,
    image_type: str,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
) -> RadiographAnalysisResponse:
    if not tenant.features.get("ai_radiograph"):
        raise DentalOSError(
            error_code="RADIOGRAPH_ANALYSIS_feature_disabled",
            message="La funcion de analisis de radiografias con IA no esta habilitada.",
            status_code=403,
        )
    # ... proceed
```

### Plan Gating

The `ai_radiograph` feature flag is managed via the admin portal:
- Enabled when the tenant's subscription includes the AI Radiograph add-on ($20/doc/mo)
- Can also be enabled manually by superadmin for trials/demos
- Disabled automatically when subscription lapses or add-on is removed

### Graceful Degradation

If the AI provider is down (`health_check()` returns False):
- New analyses return `503 RADIOGRAPH_ANALYSIS_ai_unavailable`
- Existing completed analyses remain accessible
- In-progress analyses will fail and can be retried later
- The feature flag remains enabled — the degradation is at the provider level

---

## 10. Frontend Component Requirements

### 10.1 Pages

| Page | Path | Description |
|------|------|-------------|
| Analysis List | `/patients/{id}/radiograph-analyses` | Paginated list of analyses for the patient |
| Analysis Detail | `/patients/{id}/radiograph-analyses/{aid}` | Full analysis view with findings overlay |
| Upload Flow | Modal from patient record or analysis list | Upload image + select type |

### 10.2 Components

| Component | File | Description |
|-----------|------|-------------|
| `RadiographUploadModal` | `components/radiograph/upload-modal.tsx` | Drag-and-drop image upload with type selector. Max 10MB validation client-side. Shows upload progress. |
| `RadiographAnalysisList` | `components/radiograph/analysis-list.tsx` | Paginated table with status badges, image type icons, finding count, review status. Filter by status/type/date. |
| `RadiographAnalysisDetail` | `components/radiograph/analysis-detail.tsx` | Split view: image on left, findings list on right. Image with optional bounding box overlays. |
| `RadiographFindingCard` | `components/radiograph/finding-card.tsx` | Individual finding with severity badge, tooth number, confidence bar, accept/reject/modify buttons. |
| `RadiographReviewPanel` | `components/radiograph/review-panel.tsx` | Batch review interface. Checkboxes for `create_diagnosis` and `create_treatment_item`. Submit all reviews at once. |
| `RadiographProcessingState` | `components/radiograph/processing-state.tsx` | Loading animation shown while `status` is `pending` or `processing`. Polls every 3 seconds. Auto-transitions to detail on completion. |
| `RadiographStatsCard` | `components/radiograph/stats-card.tsx` | Summary stats widget for the patient profile page (total analyses, findings by type, acceptance rate). |
| `RadiographFeatureGate` | `components/radiograph/feature-gate.tsx` | Wrapper that checks `ai_radiograph` flag. Shows upgrade prompt if disabled. |

### 10.3 Hooks

| Hook | File | Description |
|------|------|-------------|
| `useRadiographAnalyses` | `lib/hooks/use-radiograph-analyses.ts` | TanStack Query hook for list endpoint with pagination + filters |
| `useRadiographAnalysis` | `lib/hooks/use-radiograph-analysis.ts` | TanStack Query hook for single analysis with polling (refetchInterval: 3000 while status is pending/processing) |
| `useRadiographUpload` | `lib/hooks/use-radiograph-upload.ts` | Mutation hook for upload (multipart/form-data) with progress tracking |
| `useRadiographReview` | `lib/hooks/use-radiograph-review.ts` | Mutation hook for the review endpoint |
| `useRadiographStats` | `lib/hooks/use-radiograph-stats.ts` | Query hook for statistics endpoint |

### 10.4 UI/UX Requirements

- **Upload feedback:** Progress bar during upload, then animated processing state with estimated time ("Analizando radiografia... esto puede tomar 15-30 segundos")
- **Finding severity colors:**
  - `normal`: gray (`slate-400`)
  - `low`: blue (`blue-500`)
  - `moderate`: yellow (`amber-500`)
  - `high`: orange (`orange-500`)
  - `critical`: red (`red-600`)
- **Confidence indicator:** Horizontal bar with percentage. Green >= 0.8, yellow >= 0.6, red < 0.6
- **Bounding boxes:** When the image is displayed, overlay semi-transparent colored rectangles on the image at the bounding box coordinates. Color matches severity. Toggle on/off per finding type.
- **Review flow:** Doctor clicks a finding → expand card with details → accept (green check) / reject (red X with reason textarea) / modify (edit fields) → after all findings reviewed, submit batch
- **Toast notifications:** Sonner toast on analysis completion ("Analisis completado: 3 hallazgos encontrados") and on review submission ("Revision guardada exitosamente")
- **Responsive:** Works on tablet (min 768px). Image viewer supports pinch-to-zoom on touch devices.
- **Dark mode:** Supported. Bounding box overlays must be visible in both light and dark modes.
- **Disclaimer:** Always visible at the top of the analysis detail view: "Esta es una sugerencia de IA. El diagnostico final es responsabilidad del profesional."

### 10.5 Zod Validation

Located in `frontend/lib/validations/radiograph-analysis.ts`. Mirrors the Pydantic schemas:

```typescript
import { z } from "zod";

export const radiographImageTypeSchema = z.enum([
  "periapical",
  "panoramic",
  "bitewing",
  "cephalometric",
  "occlusal",
]);

export const findingReviewSchema = z.object({
  finding_id: z.string().uuid(),
  review_status: z.enum(["accepted", "rejected", "modified"]),
  create_diagnosis: z.boolean().default(false),
  create_treatment_item: z.boolean().default(false),
  modified_tooth_number: z
    .string()
    .regex(/^[1-8][1-8]$/, "Debe ser notacion FDI (11-48, 51-85)")
    .nullable()
    .optional(),
  modified_severity: z
    .enum(["normal", "low", "moderate", "high", "critical"])
    .nullable()
    .optional(),
  modified_type: z.string().nullable().optional(),
  rejected_reason: z.string().max(500).nullable().optional(),
});

export const radiographReviewSchema = z.object({
  findings: z.array(findingReviewSchema).min(1),
  notes: z.string().max(5000).nullable().optional(),
});
```

---

## 11. Caching Strategy

| Key Pattern | TTL | Notes |
|-------------|-----|-------|
| `dentalos:{tid}:ai:radiograph:analysis:{id}` | 2 min | Single analysis cache (invalidated on status change) |
| `dentalos:{tid}:ai:radiograph:rate:{doctor_id}` | 1 hour | Rate limit counter (INCR + EXPIRE) |
| `dentalos:{tid}:ai:radiograph:stats:{patient_id}` | 5 min | Aggregated stats cache |

Cache invalidation events:
- Analysis status change → invalidate analysis cache + stats cache
- Review submitted → invalidate analysis cache + stats cache
- Analysis deleted → invalidate analysis cache + stats cache

---

## 12. AI Usage Tracking

Every analysis call is logged to the `ai_usage_logs` table:

```json
{
  "id": "uuid",
  "tenant_id": "tn_abc123",
  "feature": "radiograph_analysis",
  "user_id": "doctor-uuid",
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 4200,
  "output_tokens": 1800,
  "cost_cents": 3,
  "metadata": {
    "analysis_id": "550e8400-...",
    "image_type": "periapical",
    "finding_count": 3,
    "processing_time_ms": 18500
  },
  "created_at": "2026-03-13T10:30:25Z"
}
```

Cost calculation (approximate, for billing alerts):
- Input: ~$3/MTok for Sonnet Vision → `input_tokens * 0.003 / 1000` → convert to COP cents
- Output: ~$15/MTok for Sonnet → `output_tokens * 0.015 / 1000` → convert to COP cents
- Stored as USD cents for simplicity

---

## 13. Test Plan

### 13.1 Unit Tests (`tests/unit/services/test_radiograph_analysis_service.py`)

| Test | Description |
|------|-------------|
| `test_create_analysis_valid_image` | Upload valid JPEG, verify record created with status `pending` |
| `test_create_analysis_invalid_mime` | Upload PDF, expect `RADIOGRAPH_ANALYSIS_invalid_image` |
| `test_create_analysis_oversized` | Upload >10MB image, expect `RADIOGRAPH_ANALYSIS_image_too_large` |
| `test_create_analysis_feature_disabled` | Tenant without `ai_radiograph` flag, expect 403 |
| `test_create_analysis_rate_limited` | 11th analysis in 1 hour, expect 429 |
| `test_review_findings_accept` | Accept a finding, verify `review_status` and `accepted` fields |
| `test_review_findings_reject_without_reason` | Reject without reason, expect validation error |
| `test_review_findings_modify_tooth` | Modify tooth number, verify override applied |
| `test_review_findings_create_diagnosis` | Accept with `create_diagnosis=true`, verify diagnosis record created |
| `test_review_findings_create_treatment_item` | Accept with `create_treatment_item=true`, verify treatment plan item |
| `test_review_not_completed_analysis` | Review findings on `pending` analysis, expect error |
| `test_review_already_reviewed_finding` | Re-review a finding, expect error |
| `test_retry_failed_analysis` | Retry a failed analysis, verify status reset to `pending` |
| `test_retry_non_failed_analysis` | Retry a completed analysis, expect error |
| `test_retry_max_exceeded` | Retry after 3 attempts, expect error |
| `test_soft_delete` | Delete analysis, verify `is_active=false` and `deleted_at` set |
| `test_list_excludes_deleted` | List analyses, verify soft-deleted are excluded |
| `test_stats_aggregation` | Verify stats calculations (counts, averages, by-type) |

### 13.2 Unit Tests (`tests/unit/integrations/test_radiograph_adapter.py`)

| Test | Description |
|------|-------------|
| `test_mock_adapter_returns_findings` | Mock adapter returns deterministic findings |
| `test_mock_adapter_empty_image` | Mock adapter handles empty image |
| `test_claude_adapter_parses_response` | Verify JSON extraction from Claude response |
| `test_claude_adapter_filters_low_confidence` | Findings with confidence < 0.5 are filtered out |
| `test_claude_adapter_validates_fdi` | Invalid FDI numbers are rejected |
| `test_claude_adapter_timeout` | Verify 90s timeout behavior |

### 13.3 Unit Tests (`tests/unit/workers/test_radiograph_worker.py`)

| Test | Description |
|------|-------------|
| `test_worker_processes_message` | Valid message → image fetched, analyzed, record updated |
| `test_worker_strips_exif` | Verify EXIF/DICOM metadata is stripped |
| `test_worker_sets_failed_on_error` | AI error → status set to `failed` with error message |
| `test_worker_retries_on_failure` | Failed processing → message re-enqueued with incremented retry |
| `test_worker_dead_letters_after_max_retries` | 3rd failure → message sent to DLX |
| `test_worker_logs_ai_usage` | Verify `ai_usage_logs` entry created after processing |

### 13.4 Integration Tests (`tests/integration/test_radiograph_analysis_api.py`)

| Test | Description |
|------|-------------|
| `test_full_flow_upload_to_review` | Upload → poll → complete → review → verify linked records |
| `test_rbac_doctor_can_review` | Doctor can review findings |
| `test_rbac_assistant_cannot_review` | Assistant gets 403 on review endpoint |
| `test_rbac_receptionist_no_access` | Receptionist gets 403 on all endpoints |
| `test_tenant_isolation` | Analysis from tenant A not visible in tenant B |
| `test_pagination` | Create 25 analyses, verify pagination works |
| `test_filters` | Verify status, image_type, and date range filters |

### 13.5 Frontend Tests (`frontend/__tests__/radiograph/`)

| Test | Description |
|------|-------------|
| `test_upload_modal_validates_file_type` | Only JPEG/PNG/DICOM accepted |
| `test_upload_modal_validates_file_size` | >10MB shows error message |
| `test_processing_state_polls` | Component polls every 3s until completed |
| `test_finding_card_accept_reject` | Accept/reject buttons update state correctly |
| `test_review_panel_batch_submit` | All reviews submitted in single API call |
| `test_feature_gate_shows_upgrade` | Component shows upgrade prompt when feature disabled |
| `test_bounding_box_overlay` | Bounding boxes render at correct positions |
| `test_severity_colors` | Correct color applied per severity level |

### 13.6 Test Fixtures

- **Mock images:** `tests/fixtures/radiographs/` — valid JPEG periapical, panoramic, bitewing. One oversized file (>10MB). One invalid file (PDF renamed to .jpg).
- **Mock adapter responses:** Deterministic findings for each image type (periapical: 3 findings, panoramic: 8 findings, bitewing: 2 findings).
- **Factory:** `RadioGraphAnalysisFactory` in `tests/factories/` using factory_boy with `faker` locale `es_CO`.

---

## 14. Migration

Alembic tenant migration in `alembic_tenant/versions/`.

```python
"""Add radiograph_analyses table.

Revision ID: {auto}
Create Date: {auto}
"""

def upgrade() -> None:
    op.create_table(
        "radiograph_analyses",
        sa.Column("id", sa.dialects.postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", sa.dialects.postgresql.UUID(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", sa.dialects.postgresql.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.dialects.postgresql.UUID(), sa.ForeignKey("patient_documents.id"), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("image_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("findings", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("finding_count", sa.Integer(), server_default="0"),
        sa.Column("review_status", sa.String(20), server_default="pending"),
        sa.Column("reviewed_by", sa.dialects.postgresql.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_check_constraint(
        "chk_radiograph_analyses_image_type",
        "radiograph_analyses",
        "image_type IN ('periapical', 'panoramic', 'bitewing', 'cephalometric', 'occlusal')",
    )
    op.create_check_constraint(
        "chk_radiograph_analyses_status",
        "radiograph_analyses",
        "status IN ('pending', 'processing', 'completed', 'failed', 'reviewed')",
    )
    op.create_check_constraint(
        "chk_radiograph_analyses_review_status",
        "radiograph_analyses",
        "review_status IN ('pending', 'partial', 'completed')",
    )

    op.create_index("idx_radiograph_analyses_patient_id", "radiograph_analyses", ["patient_id"])
    op.create_index("idx_radiograph_analyses_doctor_id", "radiograph_analyses", ["doctor_id"])
    op.create_index("idx_radiograph_analyses_status", "radiograph_analyses", ["status"])
    op.create_index("idx_radiograph_analyses_created_at", "radiograph_analyses", ["created_at"], postgresql_using="btree")
    op.create_index("idx_radiograph_analyses_findings", "radiograph_analyses", ["findings"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("radiograph_analyses")
```

---

## 15. File Locations Summary

| Component | Path |
|-----------|------|
| **Spec** | `specs/ai/radiograph-analysis.md` |
| **Model** | `backend/app/models/tenant/radiograph_analysis.py` |
| **Schemas** | `backend/app/schemas/radiograph_analysis.py` |
| **Routes** | `backend/app/api/v1/radiograph_analyses.py` |
| **Service** | `backend/app/services/radiograph_analysis_service.py` |
| **Adapter base** | `backend/app/integrations/radiograph_analysis/base.py` |
| **Adapter Claude** | `backend/app/integrations/radiograph_analysis/claude_service.py` |
| **Adapter mock** | `backend/app/integrations/radiograph_analysis/mock_service.py` |
| **Worker handler** | `backend/app/workers/clinical_worker.py` (add `radiograph.analyze` handler) |
| **Error codes** | `backend/app/core/error_codes.py` (add `RadiographAnalysisErrors` class) |
| **Migration** | `backend/alembic_tenant/versions/016_add_radiograph_analyses.py` |
| **FE components** | `frontend/components/radiograph/*.tsx` |
| **FE hooks** | `frontend/lib/hooks/use-radiograph-*.ts` |
| **FE validations** | `frontend/lib/validations/radiograph-analysis.ts` |
| **FE pages** | `frontend/app/(dashboard)/patients/[id]/radiograph-analyses/page.tsx` |
| **Tests (unit)** | `backend/tests/unit/services/test_radiograph_analysis_service.py` |
| **Tests (adapter)** | `backend/tests/unit/integrations/test_radiograph_adapter.py` |
| **Tests (worker)** | `backend/tests/unit/workers/test_radiograph_worker.py` |
| **Tests (integration)** | `backend/tests/integration/test_radiograph_analysis_api.py` |
| **Tests (FE)** | `frontend/__tests__/radiograph/*.test.tsx` |
