"""
Bharat Voice AI — Gemini LLM Service Integration

Provides factory for LiveKit Gemini LLM pipeline and standalone API fallback with retry,
timeout handling, and latency tracking.
"""

from __future__ import annotations

import asyncio

from agent.config import GeminiConfig
from agent.logger import COMPONENT_LLM, get_logger, log_latency
from agent.prompts import FALLBACK_RESPONSE

try:
    from livekit.plugins import google
except ImportError:
    google = None

logger = get_logger(COMPONENT_LLM)


def create_pipeline_llm(config: GeminiConfig):
    """
    Create a LiveKit-compatible Gemini LLM instance for the voice pipeline.

    Args:
        config: Gemini configuration object.

    Returns:
        A livekit.plugins.google.LLM instance.
    """
    if google is None:
        logger.error(
            "Failed to import livekit.plugins.google. "
            "Ensure 'livekit-agents[google]' is installed."
        )
        raise ImportError("livekit-agents[google] is required for Gemini integration")

    try:
        logger.info("Creating Gemini LLM for pipeline: model=%s", config.model)
        return google.LLM(model=config.model)
    except Exception as exc:
        logger.error("Failed to create Gemini LLM: %s", str(exc))
        raise


async def generate_response(
    message: str,
    config: GeminiConfig,
    system_prompt: str | None = None,
) -> str:
    """
    Generate a response from Gemini using the standalone google-genai SDK.

    Args:
        message: User prompt text.
        config: Gemini configuration with API key and timeout.
        system_prompt: System prompt override.

    Returns:
        Generated text response or fallback message on failure.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("google-genai package is not installed.")
        return FALLBACK_RESPONSE

    client = genai.Client(api_key=config.api_key)
    contents = [message]
    gen_config = types.GenerateContentConfig(
        max_output_tokens=config.max_output_tokens,
        temperature=config.temperature,
    )
    if system_prompt:
        gen_config.system_instruction = system_prompt

    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            with log_latency(logger, f"Gemini generate (attempt {attempt + 1})"):
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=config.model,
                        contents=contents,
                        config=gen_config,
                    ),
                    timeout=config.timeout_seconds,
                )

            if response and response.text:
                text = response.text.strip()
                if text:
                    logger.info("Gemini response received: %d chars", len(text))
                    return text

            logger.warning("Gemini returned empty response (attempt %d)", attempt + 1)

        except asyncio.TimeoutError:
            logger.warning("Gemini timed out after %.1fs", config.timeout_seconds)
            last_exception = asyncio.TimeoutError("Gemini call timed out")
        except Exception as exc:
            logger.warning("Gemini error: %s", str(exc))
            last_exception = exc

        if attempt < config.max_retries:
            await asyncio.sleep(min(1.0 * (2**attempt), 10.0))

    logger.error("All Gemini retries failed. Error: %s", str(last_exception))
    return FALLBACK_RESPONSE
