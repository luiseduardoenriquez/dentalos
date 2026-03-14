"""Abstract base for radiograph analysis services — AI-01."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.radiograph_analysis.schemas import AnalysisResult


class RadiographAnalysisServiceBase(ABC):
    """Contract that all radiograph analysis implementations must satisfy.

    Implementations:
        ClaudeRadiographService  — production, uses Claude Vision API.
        MockRadiographService    — development/testing, deterministic fixtures.
    """

    @abstractmethod
    async def analyze_image(
        self,
        *,
        image_data: bytes,
        image_media_type: str,
        radiograph_type: str,
    ) -> AnalysisResult:
        """Analyze a dental radiograph image.

        Args:
            image_data: Raw image bytes (JPEG or PNG).
            image_media_type: MIME type of the image.
            radiograph_type: Type of radiograph (periapical, bitewing,
                panoramic, cephalometric, occlusal).

        Returns:
            AnalysisResult with findings, summary, and quality assessment.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the service has the credentials needed."""
        ...
