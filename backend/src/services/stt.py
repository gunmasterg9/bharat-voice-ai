"""
Bharat Voice AI — Deepgram STT Service

Factory for creating a configured Deepgram Speech-to-Text instance.
"""

from __future__ import annotations

from agent.config import DeepgramConfig
from agent.logger import COMPONENT_STT, get_logger

try:
    from livekit.plugins import deepgram
except ImportError:
    deepgram = None

logger = get_logger(COMPONENT_STT)


def create_stt(config: DeepgramConfig):
    """
    Create a Deepgram STT instance for the voice pipeline.

    Uses the Deepgram Nova-3 model by default, which provides
    excellent accuracy for Indian English and multilingual input.

    Args:
        config: Deepgram configuration with API key and model.

    Returns:
        A `livekit.plugins.deepgram.STT` instance.

    Raises:
        ImportError: If `livekit.plugins.deepgram` is not installed.
        Exception: If STT initialization fails.
    """
    if deepgram is None:
        logger.error(
            "Failed to import livekit.plugins.deepgram. "
            "Ensure 'livekit-agents[deepgram]' is installed."
        )
        raise ImportError(
            "livekit-agents[deepgram] is required for Deepgram STT"
        )

    try:
        logger.info("Creating Deepgram STT: model=%s", config.model)
        stt_instance = deepgram.STT(model=config.model)
        logger.info("Deepgram STT initialized successfully")
        return stt_instance

    except ImportError as exc:
        logger.error(
            "Failed to import livekit.plugins.deepgram. "
            "Ensure 'livekit-agents[deepgram]' is installed."
        )
        raise ImportError(
            "livekit-agents[deepgram] is required for Deepgram STT"
        ) from exc

    except Exception as exc:
        logger.error("Failed to create Deepgram STT: %s", str(exc))
        raise RuntimeError(
            f"Deepgram STT initialization failed: {exc}"
        ) from exc
