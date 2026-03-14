"""Mock radiograph analysis adapter for development/testing — AI-01."""

from app.integrations.radiograph_analysis.base import RadiographAnalysisServiceBase
from app.integrations.radiograph_analysis.schemas import (
    AnalysisResult,
    RadiographFinding,
)


class MockRadiographService(RadiographAnalysisServiceBase):
    """Deterministic mock that returns fixed findings for testing."""

    async def analyze_image(
        self,
        *,
        image_data: bytes,
        image_media_type: str,
        radiograph_type: str,
    ) -> AnalysisResult:
        return AnalysisResult(
            findings=[
                RadiographFinding(
                    tooth_number="46",
                    finding_type="caries",
                    severity="high",
                    description="Caries extensa en cara oclusal con compromiso de dentina profunda",
                    location_detail="occlusal",
                    confidence=0.92,
                    suggested_action="Restauración con resina compuesta o evaluación endodóntica",
                ),
                RadiographFinding(
                    tooth_number="36",
                    finding_type="restoration",
                    severity="low",
                    description="Restauración de amalgama en buen estado",
                    location_detail="occlusal",
                    confidence=0.95,
                    suggested_action="Monitoreo en próximo control",
                ),
                RadiographFinding(
                    tooth_number="45",
                    finding_type="bone_loss",
                    severity="medium",
                    description="Pérdida ósea horizontal leve en zona interproximal",
                    location_detail="mesial",
                    confidence=0.78,
                    suggested_action="Evaluación periodontal y profilaxis",
                ),
            ],
            summary=(
                "Radiografía periapical de sector posterior inferior derecho. "
                "Se observa caries extensa en diente 46, restauración en buen "
                "estado en diente 36, y pérdida ósea leve en zona del diente 45."
            ),
            radiograph_quality="good",
            recommendations=(
                "Se recomienda tratamiento prioritario de la caries en diente 46 "
                "y evaluación periodontal del sector."
            ),
        )

    def is_configured(self) -> bool:
        return True
