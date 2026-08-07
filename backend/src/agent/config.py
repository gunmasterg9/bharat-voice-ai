"""
Bharat Voice AI — Centralized Configuration

All configuration is loaded from environment variables and validated
at startup. Missing required keys cause an immediate, clear failure.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from agent.logger import COMPONENT_CONFIG, get_logger

logger = get_logger(COMPONENT_CONFIG)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_STT_MODEL = "nova-3"
DEFAULT_LLM_MODEL = "gemini-2.0-flash"
DEFAULT_TTS_VOICE = "Pooja"
DEFAULT_TTS_LOCALE = "en-IN"
DEFAULT_TTS_STYLE = "Conversation"
DEFAULT_AGENT_NAME = "bharat-voice-ai"
DEFAULT_MIN_SENTENCE_LEN = 1

# Catalog of verified Indian voices supported on Murf Falcon
INDIAN_VOICE_PRESETS = {
    "pooja": {
        "voice": "Pooja",
        "locale": "en-IN",
        "style": "Conversation",
        "gender": "Female",
    },
    "samar": {
        "voice": "Samar",
        "locale": "en-IN",
        "style": "Conversation",
        "gender": "Male",
    },
    "anisha": {
        "voice": "Anisha",
        "locale": "en-IN",
        "style": "Conversation",
        "gender": "Female",
    },
    "female": {
        "voice": "Pooja",
        "locale": "en-IN",
        "style": "Conversation",
        "gender": "Female",
    },
    "male": {
        "voice": "Samar",
        "locale": "en-IN",
        "style": "Conversation",
        "gender": "Male",
    },
}


@dataclass(frozen=True)
class LiveKitConfig:
    """LiveKit real-time transport configuration."""

    url: str
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class DeepgramConfig:
    """Deepgram STT configuration."""

    api_key: str
    model: str = DEFAULT_STT_MODEL


@dataclass(frozen=True)
class GeminiConfig:
    """Google Gemini LLM configuration."""

    api_key: str
    model: str = DEFAULT_LLM_MODEL
    temperature: float = 0.5
    max_output_tokens: int = 120
    timeout_seconds: float = 15.0
    max_retries: int = 2


@dataclass(frozen=True)
class MurfConfig:
    """Murf Falcon TTS configuration."""

    api_key: str
    voice: str = DEFAULT_TTS_VOICE
    locale: str = DEFAULT_TTS_LOCALE
    style: str = DEFAULT_TTS_STYLE
    min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN
    text_pacing: bool = True


@dataclass(frozen=True)
class Settings:
    """
    Top-level application settings.

    Aggregates all service configurations and validates that
    required environment variables are present.
    """

    agent_name: str = DEFAULT_AGENT_NAME
    livekit: LiveKitConfig = field(default_factory=lambda: LiveKitConfig("", "", ""))
    deepgram: DeepgramConfig = field(default_factory=lambda: DeepgramConfig(""))
    gemini: GeminiConfig = field(default_factory=lambda: GeminiConfig(""))
    murf: MurfConfig = field(default_factory=lambda: MurfConfig(""))


def _get_required_env(key: str) -> str:
    """Retrieve a required environment variable."""
    value = os.environ.get(key, "").strip()
    if not value:
        raise OSError(
            f"\n{'=' * 60}\n"
            f"  MISSING REQUIRED ENVIRONMENT VARIABLE: {key}\n"
            f"  Please set it in your .env.local file.\n"
            f"{'=' * 60}"
        )
    return value


def _get_optional_env(key: str, default: str = "") -> str:
    """Retrieve an optional environment variable with a default."""
    return os.environ.get(key, default).strip()


def load_settings(env_file: str = ".env.local") -> Settings:
    """
    Load and validate all application settings from environment variables.
    """
    load_dotenv(env_file)
    load_dotenv(".env")

    logger.info("Loading configuration from environment...")

    missing_keys: list[str] = []

    def _require(key: str) -> str:
        value = os.environ.get(key, "").strip()
        if not value:
            missing_keys.append(key)
            return ""
        return value

    lk_url = _require("LIVEKIT_URL")
    lk_api_key = _require("LIVEKIT_API_KEY")
    lk_api_secret = _require("LIVEKIT_API_SECRET")

    dg_api_key = _require("DEEPGRAM_API_KEY")

    gemini_api_key = (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if not gemini_api_key:
        missing_keys.append("GOOGLE_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY")

    murf_api_key = _require("MURF_API_KEY")

    if missing_keys:
        keys_str = "\n  - ".join(missing_keys)
        raise OSError(
            f"\n{'=' * 60}\n"
            f"  MISSING REQUIRED ENVIRONMENT VARIABLES:\n"
            f"  - {keys_str}\n\n"
            f"  Please add them to your .env.local file.\n"
            f"  See .env.example for reference.\n"
            f"{'=' * 60}"
        )

    voice_input = _get_optional_env("MURF_VOICE", DEFAULT_TTS_VOICE)
    preset = INDIAN_VOICE_PRESETS.get(voice_input.lower())

    if preset:
        final_voice = preset["voice"]
        final_locale = _get_optional_env("MURF_LOCALE", preset["locale"])
        final_style = _get_optional_env("MURF_STYLE", preset["style"])
    else:
        final_voice = voice_input
        final_locale = _get_optional_env("MURF_LOCALE", DEFAULT_TTS_LOCALE)
        final_style = _get_optional_env("MURF_STYLE", DEFAULT_TTS_STYLE)

    settings = Settings(
        agent_name=_get_optional_env("AGENT_NAME", DEFAULT_AGENT_NAME),
        livekit=LiveKitConfig(
            url=lk_url,
            api_key=lk_api_key,
            api_secret=lk_api_secret,
        ),
        deepgram=DeepgramConfig(
            api_key=dg_api_key,
            model=_get_optional_env("DEEPGRAM_MODEL", DEFAULT_STT_MODEL),
        ),
        gemini=GeminiConfig(
            api_key=gemini_api_key,
            model=_get_optional_env("GEMINI_MODEL", DEFAULT_LLM_MODEL),
        ),
        murf=MurfConfig(
            api_key=murf_api_key,
            voice=final_voice,
            locale=final_locale,
            style=final_style,
        ),
    )

    logger.info("Configuration loaded successfully.")
    return settings
