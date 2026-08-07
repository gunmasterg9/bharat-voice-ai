"""
Bharat Voice AI — Structured Logging & Observability

Provides structured logging with component tags, latency tracking, guardrail event logging,
and consistent formatting across all voice modules.
"""

import logging
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Log format constants
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Component logger names
COMPONENT_AGENT = "bharat.agent"
COMPONENT_STT = "bharat.stt"
COMPONENT_LLM = "bharat.llm"
COMPONENT_TTS = "bharat.tts"
COMPONENT_CONFIG = "bharat.config"
COMPONENT_SESSION = "bharat.session"
COMPONENT_GUARDRAIL = "bharat.guardrail"
COMPONENT_LANGUAGE = "bharat.language"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging for the entire application."""
    root_logger = logging.getLogger()

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
    """Get a named logger for a specific component."""
    return logging.getLogger(component)


@contextmanager
def log_latency(
    logger: logging.Logger,
    operation: str,
) -> Generator[None, None, None]:
    """Context manager that measures and logs the latency of an operation."""
    start_time = time.perf_counter()
    logger.info("Starting: %s", operation)

    try:
        yield
    except Exception:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error("Failed: %s (%.1fms elapsed)", operation, elapsed_ms)
        raise
    else:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Completed: %s (%.1fms)", operation, elapsed_ms)


def log_startup_banner() -> None:
    """Log the Bharat Voice AI startup banner."""
    logger = get_logger(COMPONENT_AGENT)
    logger.info("=" * 60)
    logger.info("  Bharat Voice AI — Starting Up (Day 2 Build)")
    logger.info("  Multilingual Voice Assistant for India")
    logger.info("=" * 60)


def log_pipeline_config(
    stt_model: str,
    llm_model: str,
    tts_voice: str,
    tts_locale: str,
) -> None:
    """Log the configured pipeline components at startup."""
    logger = get_logger(COMPONENT_AGENT)
    logger.info("Pipeline Configuration:")
    logger.info("  STT   : Deepgram %s", stt_model)
    logger.info("  LLM   : Google %s", llm_model)
    logger.info("  TTS   : Murf Falcon — %s (%s)", tts_voice, tts_locale)


def log_session_connected(room_name: str) -> None:
    """Log when a user session connects."""
    logger = get_logger(COMPONENT_SESSION)
    logger.info("User connected to room: %s", room_name)


def log_session_error(error: Exception, context: str = "") -> None:
    """Log a session-level error with optional context."""
    logger = get_logger(COMPONENT_SESSION)
    if context:
        logger.error("Session error (%s): %s", context, str(error))
    else:
        logger.error("Session error: %s", str(error))


def log_language_detection(language_code: str, language_name: str) -> None:
    """Log auto-detected language profile."""
    logger = get_logger(COMPONENT_LANGUAGE)
    logger.info("Language Detected: %s (%s)", language_name, language_code)


def log_guardrail_event(category: str, detail: str) -> None:
    """Log guardrail trigger or refusal event."""
    logger = get_logger(COMPONENT_GUARDRAIL)
    logger.warning("Guardrail Triggered [%s]: %s", category, detail)


def log_silence_event(stage: str) -> None:
    """Log silence handling prompt event."""
    logger = get_logger(COMPONENT_SESSION)
    logger.info("Silence Handling Event: stage=%s", stage)


def log_service_latency(service: str, latency_ms: float) -> None:
    """Log service latency metric."""
    logger = get_logger(COMPONENT_AGENT)
    logger.info("Service Latency [%s]: %.1fms", service, latency_ms)
