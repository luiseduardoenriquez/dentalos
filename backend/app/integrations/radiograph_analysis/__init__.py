"""AI Radiograph Analysis integration adapter (AI-01).

Singleton selector: returns Claude adapter if API key is set, else mock.
"""

from app.core.config import settings


def get_radiograph_analysis_service():
    """Return the appropriate radiograph analysis adapter."""
    if settings.anthropic_api_key:
        from app.integrations.radiograph_analysis.claude_service import (
            ClaudeRadiographService,
        )
        return ClaudeRadiographService()
    from app.integrations.radiograph_analysis.mock_service import (
        MockRadiographService,
    )
    return MockRadiographService()
