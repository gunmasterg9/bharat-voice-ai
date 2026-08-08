from __future__ import annotations

import os

from agent.config import GeminiConfig
from agent.logger import COMPONENT_LLM, get_logger

# Import plugins at module top-level so they register on the main thread at startup
try:
    from livekit.plugins import google
except ImportError:
    google = None

try:
    from livekit.plugins import openai
except ImportError:
    openai = None

from services.gemini import create_pipeline_llm

logger = get_logger(COMPONENT_LLM)


def create_llm(config: GeminiConfig):
    """
    Create an LLM instance for the voice pipeline.

    Supports Groq, OpenAI, and Google Gemini with smart fallback order:
    1. Groq (ultra-fast, high-quota LLM) if GROQ_API_KEY is available.
    2. Google Gemini if standard 'AIzaSy' key is available.
    3. OpenAI as additional fallback.

    Args:
        config: Gemini/LLM configuration object.

    Returns:
        A LiveKit-compatible LLM instance.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    # Priority 1: Groq LLM (ultra-fast OpenAI-compatible endpoint)
    if groq_key and openai is not None:
        try:
            logger.info("Creating Groq LLM service: model=llama-3.3-70b-versatile")
            return openai.LLM(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                model="llama-3.3-70b-versatile",
            )
        except Exception as exc:
            logger.warning("Failed to initialize Groq LLM: %s", str(exc))

    # Priority 2: Gemini LLM if standard key format is present
    if config.api_key.startswith("AIzaSy"):
        try:
            logger.info("Creating Gemini LLM service: model=%s", config.model)
            return create_pipeline_llm(config)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini LLM: %s", str(exc))
    else:
        logger.warning(
            "GOOGLE_API_KEY does not start with 'AIzaSy'. Please verify your Gemini API key in backend/.env.local (from https://aistudio.google.com/app/apikey)."
        )

    # Priority 3: OpenAI LLM fallback
    if openai_key and openai is not None:
        try:
            model_name = (
                config.model if config.model.startswith("gpt") else "gpt-4o-mini"
            )
            logger.info("Creating OpenAI LLM service: model=%s", model_name)
            return openai.LLM(model=model_name, api_key=openai_key)
        except Exception as exc:
            logger.warning("Failed to initialize OpenAI LLM: %s", str(exc))

    # Final fallback attempt with Gemini
    return create_pipeline_llm(config)
