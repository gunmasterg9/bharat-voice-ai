"""
Bharat Voice AI — Multi-Agent Language Router (Re-exporter & Adapter)

Wraps agent.language for backwards compatibility and regional routing context generation.
"""

from __future__ import annotations

from agent.language import LanguageProfile, language_detector
from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)


class LanguageRouter:
    """Detects regional languages and routes agent prompt context."""

    def detect_language(self, text: str) -> LanguageProfile:
        """Detect language profile from text snippet using language_detector."""
        return language_detector.detect(text)

    def get_route_context(self, text: str) -> str:
        """Get contextual system prompt instruction based on detected language."""
        profile = self.detect_language(text)
        logger.info(
            "Language Router matched script/text to: %s (%s)",
            profile.name,
            profile.code,
        )
        return f"\n[Language Context: {profile.instruction}]"


# Global singleton instance
language_router = LanguageRouter()
