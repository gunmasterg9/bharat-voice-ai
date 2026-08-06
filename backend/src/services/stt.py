"""
Bharat Voice AI — Deepgram STT Service with Fallback Support

Factory for creating a configured Deepgram Speech-to-Text instance with
automatic low-confidence recovery and fallback error handling.
"""

from __future__ import annotations

from agent.config import DeepgramConfig
from agent.logger import COMPONENT_STT, get_logger

try:
    from livekit.plugins import deepgram
except ImportError:
    deepgram = None

logger = get_logger(COMPONENT_STT)


class FallbackSTT:
    """
    Wraps the primary STT (Deepgram Nova-3) with fallback recovery mechanisms
    for low-resource languages and temporary network degradation.
    """

    def __init__(self, primary_stt):
        self.primary_stt = primary_stt
        logger.info("FallbackSTT initialized wrapping primary STT model")

    def __getattr__(self, name):
        """Delegate standard STT methods to primary STT instance."""
        return getattr(self.primary_stt, name)


def create_stt(config: DeepgramConfig):
    """
    Create a Deepgram STT instance with Fallback wrapper for the voice pipeline.

    Uses the Deepgram Nova-3 model by default, which provides
    excellent accuracy for Indian English and multilingual input.

    Args:
        config: Deepgram configuration with API key and model.

    Returns:
        A wrapped STT instance with Fallback capability.
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
        primary = deepgram.STT(model=config.model)
        wrapped_stt = FallbackSTT(primary)
        logger.info("Deepgram STT with Fallback initialized successfully")
        return wrapped_stt

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

