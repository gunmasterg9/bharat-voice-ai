"""
Bharat Voice AI — LLM Service

Factory for creating a configured LLM instance for the voice pipeline.
Delegates to the Gemini module for Google Gemini integration.
"""

from __future__ import annotations

from agent.config import GeminiConfig
from agent.gemini import create_pipeline_llm
from agent.logger import COMPONENT_LLM, get_logger

logger = get_logger(COMPONENT_LLM)


def create_llm(config: GeminiConfig):
    """
    Create an LLM instance for the voice pipeline.

    Currently uses Google Gemini via the LiveKit plugin.
    This factory provides a clean abstraction point for
    swapping LLM providers in the future.

    Args:
        config: Gemini configuration with model and API key.

    Returns:
        A LiveKit-compatible LLM instance.

    Raises:
        ImportError: If required packages are not installed.
        RuntimeError: If LLM initialization fails.
    """
    try:
        logger.info("Creating LLM service: model=%s", config.model)
        llm_instance = create_pipeline_llm(config)
        logger.info("LLM service initialized successfully")
        return llm_instance

    except Exception as exc:
        logger.error("Failed to create LLM service: %s", str(exc))
        raise RuntimeError(
            f"LLM service initialization failed: {exc}"
        ) from exc
