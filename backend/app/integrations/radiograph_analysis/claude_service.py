"""Claude Vision implementation for radiograph analysis — AI-01."""

import logging

from app.core.config import settings
from app.integrations.radiograph_analysis.base import RadiographAnalysisServiceBase
from app.integrations.radiograph_analysis.schemas import (
    AnalysisResult,
    RadiographFinding,
)
from app.services.ai_claude_client import call_claude_vision, extract_json_object

logger = logging.getLogger("dentalos.ai.radiograph")

_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

_SYSTEM_PROMPT = """\
You are an expert dental radiograph analyst. Analyze the provided dental \
radiograph image and identify all clinically significant findings.

For each finding, provide:
1. tooth_number: FDI notation (e.g. "11", "46") or null if general
2. finding_type: one of: caries, bone_loss, periapical_lesion, restoration, \
impacted_tooth, root_canal, crown, missing_tooth, calculus, root_resorption, \
supernumerary, other
3. severity: one of: low, medium, high, critical
4. description: brief clinical description in Spanish
5. location_detail: specific location (mesial, distal, occlusal, vestibular, \
lingual, cervical, apical) or null
6. confidence: your confidence 0.0-1.0
7. suggested_action: suggested clinical action in Spanish

Also provide:
- summary: overall summary of the radiograph in Spanish (2-3 sentences)
- radiograph_quality: "good", "adequate", or "poor"
- recommendations: general recommendations in Spanish

Respond ONLY with a JSON object in this exact format:
{
  "findings": [
    {
      "tooth_number": "46",
      "finding_type": "caries",
      "severity": "high",
      "description": "Caries extensa en cara oclusal con compromiso pulpar probable",
      "location_detail": "occlusal",
      "confidence": 0.92,
      "suggested_action": "Evaluación endodóntica y restauración"
    }
  ],
  "summary": "Radiografía periapical que muestra...",
  "radiograph_quality": "good",
  "recommendations": "Se recomienda..."
}

IMPORTANT:
- Use FDI tooth numbering system (11-48 for permanent, 51-85 for deciduous)
- All descriptions and recommendations in Spanish (es-419)
- Be thorough but avoid false positives — when unsure, use lower confidence
- Do NOT hallucinate findings — only report what is clearly visible
"""

_USER_TEXT_TEMPLATE = """\
Analyze this dental radiograph.
Type: {radiograph_type}

Identify all clinically significant findings visible in the image. \
Be thorough and precise with tooth identification using FDI notation.
"""

_VALID_RADIOGRAPH_TYPES = {
    "periapical",
    "bitewing",
    "panoramic",
    "cephalometric",
    "occlusal",
}

_VALID_FINDING_TYPES = {
    "caries",
    "bone_loss",
    "periapical_lesion",
    "restoration",
    "impacted_tooth",
    "root_canal",
    "crown",
    "missing_tooth",
    "calculus",
    "root_resorption",
    "supernumerary",
    "other",
}

_VALID_SEVERITIES = {"low", "medium", "high", "critical"}


class ClaudeRadiographService(RadiographAnalysisServiceBase):
    """Production adapter — calls Claude Vision API for radiograph analysis."""

    async def analyze_image(
        self,
        *,
        image_data: bytes,
        image_media_type: str,
        radiograph_type: str,
    ) -> AnalysisResult:
        if radiograph_type not in _VALID_RADIOGRAPH_TYPES:
            raise ValueError(
                f"Invalid radiograph_type: {radiograph_type}. "
                f"Allowed: {', '.join(sorted(_VALID_RADIOGRAPH_TYPES))}"
            )

        # Resize if image is too large (Claude Vision limit)
        if len(image_data) > _MAX_IMAGE_SIZE:
            image_data = await self._resize_image(image_data, image_media_type)

        user_text = _USER_TEXT_TEMPLATE.format(radiograph_type=radiograph_type)

        result = await call_claude_vision(
            system_prompt=_SYSTEM_PROMPT,
            user_text=user_text,
            image_data=image_data,
            image_media_type=image_media_type,
            max_tokens=4096,
            temperature=0.1,
            model_override=settings.anthropic_model_treatment,
        )

        parsed = extract_json_object(result["content"])
        findings = self._parse_findings(parsed.get("findings", []))

        return AnalysisResult(
            findings=findings,
            summary=parsed.get("summary", "No se pudo generar el resumen."),
            radiograph_quality=parsed.get("radiograph_quality", "adequate"),
            recommendations=parsed.get("recommendations"),
        )

    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    def _parse_findings(
        self, raw_findings: list[dict],
    ) -> list[RadiographFinding]:
        """Validate and sanitize AI-generated findings."""
        findings = []
        for raw in raw_findings:
            # Validate finding_type
            finding_type = raw.get("finding_type", "other")
            if finding_type not in _VALID_FINDING_TYPES:
                finding_type = "other"

            # Validate severity
            severity = raw.get("severity", "low")
            if severity not in _VALID_SEVERITIES:
                severity = "low"

            # Validate tooth number (FDI: 11-48, 51-85)
            tooth = raw.get("tooth_number")
            if tooth and not self._is_valid_fdi(tooth):
                logger.warning("Invalid FDI tooth number from AI: %s", tooth)
                tooth = None

            # Clamp confidence
            confidence = raw.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            confidence = max(0.0, min(1.0, float(confidence)))

            findings.append(
                RadiographFinding(
                    tooth_number=tooth,
                    finding_type=finding_type,
                    severity=severity,
                    description=raw.get("description", "Hallazgo detectado"),
                    location_detail=raw.get("location_detail"),
                    confidence=confidence,
                    suggested_action=raw.get("suggested_action"),
                )
            )
        return findings

    @staticmethod
    def _is_valid_fdi(tooth: str) -> bool:
        """Validate FDI tooth number (permanent: 11-48, deciduous: 51-85)."""
        if not tooth or not tooth.isdigit() or len(tooth) != 2:
            return False
        quadrant = int(tooth[0])
        number = int(tooth[1])
        if quadrant in (1, 2, 3, 4):
            return 1 <= number <= 8
        if quadrant in (5, 6, 7, 8):
            return 1 <= number <= 5
        return False

    @staticmethod
    async def _resize_image(image_data: bytes, media_type: str) -> bytes:
        """Resize image to fit within Claude Vision limits (5MB)."""
        try:
            from io import BytesIO

            from PIL import Image

            img = Image.open(BytesIO(image_data))

            # Reduce quality and size until under limit
            quality = 85
            while True:
                buffer = BytesIO()
                fmt = "JPEG" if media_type == "image/jpeg" else "PNG"
                if fmt == "JPEG":
                    img.save(buffer, format=fmt, quality=quality, optimize=True)
                else:
                    img.save(buffer, format=fmt, optimize=True)

                if buffer.tell() <= _MAX_IMAGE_SIZE:
                    return buffer.getvalue()

                # Reduce dimensions by 75%
                new_size = (int(img.width * 0.75), int(img.height * 0.75))
                img = img.resize(new_size, Image.LANCZOS)
                quality = max(60, quality - 10)

        except ImportError:
            logger.warning("Pillow not installed — cannot resize image")
            return image_data
