"""
Bharat Voice AI — Multi-Agent Language Router

Detects input language across Indian regional languages and configures optimal
system prompt, voice selection, and locale settings per participant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)


@dataclass
class LanguageProfile:
    """Language routing profile for regional Indian languages."""

    code: str
    name: str
    native_name: str
    default_voice: str
    locale: str
    system_hint: str


INDIAN_LANGUAGES: dict[str, LanguageProfile] = {
    "hi": LanguageProfile(
        code="hi",
        name="Hindi",
        native_name="हिन्दी",
        default_voice="Pooja",
        locale="hi-IN",
        system_hint="User prefers Hindi. Respond in clear, natural conversational Hindi.",
    ),
    "ta": LanguageProfile(
        code="ta",
        name="Tamil",
        native_name="தமிழ்",
        default_voice="Anisha",
        locale="ta-IN",
        system_hint="User prefers Tamil. Respond politely in simple Tamil or Indian English.",
    ),
    "bn": LanguageProfile(
        code="bn",
        name="Bengali",
        native_name="বাংলা",
        default_voice="Pooja",
        locale="bn-IN",
        system_hint="User prefers Bengali. Respond in friendly, conversational Bengali or English.",
    ),
    "te": LanguageProfile(
        code="te",
        name="Telugu",
        native_name="తెలుగు",
        default_voice="Samar",
        locale="te-IN",
        system_hint="User prefers Telugu. Respond in clear Telugu or Indian English.",
    ),
    "kn": LanguageProfile(
        code="kn",
        name="Kannada",
        native_name="கன்னட",
        default_voice="Anisha",
        locale="kn-IN",
        system_hint="User prefers Kannada. Respond in polite Kannada or Indian English.",
    ),
    "en": LanguageProfile(
        code="en",
        name="English (India)",
        native_name="English",
        default_voice="Pooja",
        locale="en-IN",
        system_hint="User prefers Indian English. Respond in clear, concise English.",
    ),
}

# Devanagari script regex pattern for Hindi/Marathi/Sanskrit detection
DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")
TAMIL_PATTERN = re.compile(r"[\u0B80-\u0BFF]")
BENGALI_PATTERN = re.compile(r"[\u0980-\u09FF]")
TELUGU_PATTERN = re.compile(r"[\u0C00-\u0C7F]")
KANNADA_PATTERN = re.compile(r"[\u0C80-\u0CFF]")


class LanguageRouter:
    """Detects regional languages and routes agent prompt context."""

    def detect_language(self, text: str) -> LanguageProfile:
        """Detect language profile from text snippet."""
        if DEVANAGARI_PATTERN.search(text):
            return INDIAN_LANGUAGES["hi"]
        elif TAMIL_PATTERN.search(text):
            return INDIAN_LANGUAGES["ta"]
        elif BENGALI_PATTERN.search(text):
            return INDIAN_LANGUAGES["bn"]
        elif TELUGU_PATTERN.search(text):
            return INDIAN_LANGUAGES["te"]
        elif KANNADA_PATTERN.search(text):
            return INDIAN_LANGUAGES["kn"]

        # Check Hinglish keywords
        lower_text = text.lower()
        hinglish_words = {"namaste", "kaise", "bhai", "shukriya", "kya", "haan", "nahi"}
        if any(word in lower_text for word in hinglish_words):
            return INDIAN_LANGUAGES["hi"]

        return INDIAN_LANGUAGES["en"]

    def get_route_context(self, text: str) -> str:
        """Get contextual system prompt instruction based on detected language."""
        profile = self.detect_language(text)
        logger.info(
            "Language Router matched script/text to: %s (%s)",
            profile.name,
            profile.code,
        )
        return f"\n[Language Context: {profile.system_hint}]"


# Global singleton instance
language_router = LanguageRouter()
