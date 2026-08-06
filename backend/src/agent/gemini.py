"""
Bharat Voice AI — Gemini LLM Integration

Provides two integration modes:

1. **Pipeline mode** (primary): Factory function `create_pipeline_llm()`
   returns a LiveKit-compatible `google.LLM` instance for the voice pipeline.

2. **Standalone mode** (helper): `generate_response()` uses the `google-genai`
   SDK directly for non-pipeline use cases, with retry, timeout, and error handling.
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

    This is the primary integration path — it returns a `google.LLM` object
    that plugs directly into the `AgentSession` pipeline.

    Args:
        config: Gemini configuration with model and API key.

    Returns:
        A `livekit.plugins.google.LLM` instance.

    Raises:
        ImportError: If `livekit.plugins.google` is not installed.
        Exception: If LLM creation fails.
    """
    if google is None:
        logger.error(
            "Failed to import livekit.plugins.google. "
            "Ensure 'livekit-agents[google]' is installed."
        )
        raise ImportError(
            "livekit-agents[google] is required for Gemini integration"
        )

    try:
        logger.info(
            "Creating Gemini LLM for pipeline: model=%s", config.model
        )
        return google.LLM(model=config.model)

    except ImportError as exc:
        logger.error(
            "Failed to import livekit.plugins.google. "
            "Ensure 'livekit-agents[google]' is installed."
        )
        raise ImportError(
            "livekit-agents[google] is required for Gemini integration"
        ) from exc
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

    This is a helper for non-pipeline use cases (e.g., background processing,
    tool calls, or one-off generations). For the main voice pipeline, use
    `create_pipeline_llm()` instead.

    Features:
        - Configurable timeout
        - Automatic retry with exponential backoff
        - Empty response detection
        - Graceful fallback on failure

    Args:
        message: The user's message to respond to.
        config: Gemini configuration with model, API key, timeout, retries.
        system_prompt: Optional system prompt override.

    Returns:
        The generated response text, or a fallback message on failure.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error(
            "google-genai package is not installed. "
            "Run: uv add google-genai"
        )
        return FALLBACK_RESPONSE

    client = genai.Client(api_key=config.api_key)

    # Build the request contents
    contents = [message]

    # Build generation config
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

            # Validate response
            if response and response.text:
                text = response.text.strip()
                if text:
                    logger.info(
                        "Gemini response received: %d chars", len(text)
                    )
                    return text

            logger.warning("Gemini returned an empty response (attempt %d)", attempt + 1)

        except asyncio.TimeoutError:
            logger.warning(
                "Gemini timed out after %.1fs (attempt %d/%d)",
                config.timeout_seconds,
                attempt + 1,
                config.max_retries + 1,
            )
            last_exception = asyncio.TimeoutError(
                f"Gemini timed out after {config.timeout_seconds}s"
            )

        except Exception as exc:
            logger.warning(
                "Gemini error (attempt %d/%d): %s",
                attempt + 1,
                config.max_retries + 1,
                str(exc),
            )
            last_exception = exc

        # Exponential backoff before retry
        if attempt < config.max_retries:
            delay = min(1.0 * (2**attempt), 10.0)
            logger.info("Retrying in %.1fs...", delay)
            await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        "All %d Gemini retries exhausted. Last error: %s",
        config.max_retries,
        str(last_exception),
    )
    return FALLBACK_RESPONSE
