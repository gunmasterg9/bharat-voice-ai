"""
Bharat Voice AI — Murf Falcon TTS Service

Factory for creating a configured Murf Falcon Text-to-Speech instance.
"""

from __future__ import annotations

from livekit.agents import tokenize

from agent.config import MurfConfig
from agent.logger import COMPONENT_TTS, get_logger

try:
    from livekit.plugins import murf
except ImportError:
    murf = None

logger = get_logger(COMPONENT_TTS)


def create_tts(config: MurfConfig):
    """
    Create a Murf Falcon TTS instance for the voice pipeline.

    Configures the TTS with:
    - Voice selection (e.g., Anisha for Indian English)
    - Locale for regional accent
    - Conversational style
    - Sentence tokenization for natural pacing
    - Text pacing for smooth delivery

    Args:
        config: Murf TTS configuration with voice, locale, and style.

    Returns:
        A `livekit.plugins.murf.TTS` instance.

    Raises:
        ImportError: If `livekit-murf` is not installed.
        Exception: If TTS initialization fails.
    """
    if murf is None:
        logger.error(
            "Failed to import livekit.plugins.murf. Ensure 'livekit-murf' is installed."
        )
        raise ImportError("livekit-murf is required for Murf Falcon TTS")

    try:
        logger.info(
            "Creating Murf Falcon TTS: voice=%s, locale=%s, style=%s",
            config.voice,
            config.locale,
            config.style,
        )

        tts_instance = murf.TTS(
            voice=config.voice,
            locale=config.locale,
            style=config.style,
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=config.min_sentence_len,
            ),
            text_pacing=config.text_pacing,
        )

        logger.info("Murf Falcon TTS initialized successfully")
        return tts_instance

    except ImportError as exc:
        logger.error(
            "Failed to import livekit.plugins.murf. Ensure 'livekit-murf' is installed."
        )
        raise ImportError("livekit-murf is required for Murf Falcon TTS") from exc

    except Exception as exc:
        logger.error("Failed to create Murf Falcon TTS: %s", str(exc))
        raise RuntimeError(f"Murf Falcon TTS initialization failed: {exc}") from exc
