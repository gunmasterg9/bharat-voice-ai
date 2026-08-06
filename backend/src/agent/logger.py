"""
Bharat Voice AI — Structured Logging

Provides structured logging with component tags, latency tracking,
and consistent formatting across all modules.
"""

import logging
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Log format constants
# ---------------------------------------------------------------------------
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Component logger names
COMPONENT_AGENT = "bharat.agent"
COMPONENT_STT = "bharat.stt"
COMPONENT_LLM = "bharat.llm"
COMPONENT_TTS = "bharat.tts"
COMPONENT_CONFIG = "bharat.config"
COMPONENT_SESSION = "bharat.session"


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure structured logging for the entire application.

    Sets up a consistent log format with timestamps, log levels,
    and component names. Call this once at startup.

    Args:
        level: The minimum log level to display.
    """
    root_logger = logging.getLogger()

    # Avoid adding duplicate handlers on repeated calls
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def get_logger(component: str) -> logging.Logger:
    """
    Get a named logger for a specific component.

    Args:
        component: The component name (use COMPONENT_* constants).

    Returns:
        A configured Logger instance.
    """
    return logging.getLogger(component)


@contextmanager
def log_latency(
    logger: logging.Logger,
    operation: str,
) -> Generator[None, None, None]:
    """
    Context manager that measures and logs the latency of an operation.

    Usage:
        with log_latency(logger, "Gemini response"):
            response = await llm.generate(...)

    Args:
        logger: The logger instance to use.
        operation: A human-readable description of the operation.

    Yields:
        None — use as a context manager.
    """
    start_time = time.perf_counter()
    logger.info("Starting: %s", operation)

    try:
        yield
    except Exception:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Failed: %s (%.1fms elapsed)",
            operation,
            elapsed_ms,
        )
        raise
    else:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Completed: %s (%.1fms)",
            operation,
            elapsed_ms,
        )


def log_startup_banner() -> None:
    """Log the Bharat Voice AI startup banner."""
    logger = get_logger(COMPONENT_AGENT)
    logger.info("=" * 60)
    logger.info("  Bharat Voice AI — Starting Up")
    logger.info("  Multilingual Voice Assistant for India")
    logger.info("=" * 60)


def log_pipeline_config(
    stt_model: str,
    llm_model: str,
    tts_voice: str,
    tts_locale: str,
) -> None:
    """
    Log the configured pipeline components at startup.

    Args:
        stt_model: The STT model name (e.g., 'nova-3').
        llm_model: The LLM model name (e.g., 'gemini-2.5-flash').
        tts_voice: The TTS voice ID (e.g., 'Anisha').
        tts_locale: The TTS locale (e.g., 'en-IN').
    """
    logger = get_logger(COMPONENT_AGENT)
    logger.info("Pipeline Configuration:")
    logger.info("  STT   : Deepgram %s", stt_model)
    logger.info("  LLM   : Google %s", llm_model)
    logger.info("  TTS   : Murf Falcon — %s (%s)", tts_voice, tts_locale)


def log_session_connected(room_name: str) -> None:
    """
    Log when a user session connects.

    Args:
        room_name: The LiveKit room name.
    """
    logger = get_logger(COMPONENT_SESSION)
    logger.info("User connected to room: %s", room_name)


def log_session_error(error: Exception, context: str = "") -> None:
    """
    Log a session-level error with optional context.

    Args:
        error: The exception that occurred.
        context: Additional context about what was happening.
    """
    logger = get_logger(COMPONENT_SESSION)
    if context:
        logger.error("Session error (%s): %s", context, str(error))
    else:
        logger.error("Session error: %s", str(error))
