from __future__ import annotations

import os

import httpx

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
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    provider = os.environ.get("LLM_PROVIDER", "auto").strip().lower()
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip() or os.environ.get("NVIDIA_NIM_API_KEY", "").strip()
    nvidia_model = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct").strip()
    nvidia_timeout_seconds = float(os.environ.get("NVIDIA_TIMEOUT_SECONDS", "45"))
    google_key = os.environ.get("GOOGLE_API_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if provider == "gemini":
        logger.info(
            "Creating Gemini LLM service by explicit provider selection: model=%s",
            config.model,
        )
        return create_pipeline_llm(config)

    if provider == "openai":
        if not openai_key or openai is None:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY.")
        model_name = config.model if config.model.startswith("gpt") else "gpt-4o-mini"
        logger.info("Creating OpenAI LLM service by explicit provider selection: model=%s", model_name)
        return openai.LLM(model=model_name, api_key=openai_key)

    if provider in {"nvidia", "nvidia-nim"}:
        if not nvidia_key or openai is None:
            raise RuntimeError("LLM_PROVIDER=nvidia requires NVIDIA_API_KEY.")
        logger.info(
            "Creating NVIDIA NIM LLM service by explicit provider selection: model=%s",
            nvidia_model,
        )
        return openai.LLM(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_key,
            model=nvidia_model,
            timeout=httpx.Timeout(nvidia_timeout_seconds, connect=15.0),
        )

    # Priority 1: Groq LLM (Ultra-fast 120ms low latency — no cold-start timeouts)
    if groq_key and openai is not None:
        try:
            logger.info("Creating Groq LLM service: model=%s", groq_model)
            return openai.LLM(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                model=groq_model,
            )
        except Exception as exc:
            logger.warning("Failed to initialize Groq LLM: %s", str(exc))

    # Priority 2: NVIDIA NIM LLM (Fast 8B Instruct model)
    if nvidia_key and openai is not None:
        try:
            logger.info("Creating NVIDIA NIM LLM service: model=%s", nvidia_model)
            return openai.LLM(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia_key,
                model=nvidia_model,
                timeout=httpx.Timeout(nvidia_timeout_seconds, connect=15.0),
            )
        except Exception as exc:
            logger.warning("Failed to initialize NVIDIA NIM LLM: %s", str(exc))

    # Priority 3: Google Gemini if standard 'AIzaSy' key is present
    if google_key.startswith("AIzaSy") and google is not None:
        try:
            logger.info("Creating Gemini LLM service: model=%s", config.model)
            return create_pipeline_llm(config)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini LLM: %s", str(exc))

    # Priority 4: OpenAI LLM (requires active billing credits)
    if openai_key.startswith("sk-") and openai is not None:
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
