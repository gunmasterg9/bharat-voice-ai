"""
Bharat Voice AI — LLM Service Factory

Factory for creating a configured LLM instance for the voice pipeline.
Delegates to services.gemini for Google Gemini integration.
"""

from __future__ import annotations

from agent.config import GeminiConfig
from agent.logger import COMPONENT_LLM, get_logger
from services.gemini import create_pipeline_llm

logger = get_logger(COMPONENT_LLM)


def create_llm(config: GeminiConfig):
    """
    Create an LLM instance for the voice pipeline.

    Args:
        config: Gemini configuration object.

    Returns:
        A LiveKit-compatible LLM instance.
    """
    try:
        logger.info("Creating LLM service: model=%s", config.model)
        llm_instance = create_pipeline_llm(config)
        logger.info("LLM service initialized successfully")
        return llm_instance
    except Exception as exc:
        logger.error("Failed to create LLM service: %s", str(exc))
        raise RuntimeError(f"LLM service initialization failed: {exc}") from exc
