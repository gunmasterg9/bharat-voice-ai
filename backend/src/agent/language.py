"""
Bharat Voice AI — Language Detection & Style Mirroring

Supports auto-detection and mirroring for:
- English
- Hindi
- Gujarati
- Hinglish (Hindi-English code-mix)
- Gujlish / Gujarati-English (Gujarati-English code-mix)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)


@dataclass(frozen=True)
class LanguageProfile:
    """Language profile containing script, locale, and routing metadata."""

    code: str
    name: str
    native_name: str
    locale: str
    voice: str
    instruction: str


# Catalog of supported Indian language profiles for Bharat Voice AI
LANGUAGE_PROFILES: dict[str, LanguageProfile] = {
    "hi": LanguageProfile(
        code="hi",
        name="Hindi",
        native_name="हिन्दी",
        locale="hi-IN",
        voice="Pooja",
        instruction="User is speaking Hindi. Respond in warm, clear conversational Hindi using Devanagari script.",
    ),
    "gu": LanguageProfile(
        code="gu",
        name="Gujarati",
        native_name="ગુજરાતી",
        locale="gu-IN",
        voice="Pooja",
        instruction="User is speaking Gujarati. Respond in polite, friendly conversational Gujarati or Gujlish.",
    ),
    "hinglish": LanguageProfile(
        code="hinglish",
        name="Hinglish",
        native_name="Hinglish",
        locale="hi-IN",
        voice="Pooja",
        instruction="User is speaking Hinglish (Hindi-English mix). Mirror their style in clear Hinglish.",
    ),
    "gujlish": LanguageProfile(
        code="gujlish",
        name="Gujlish",
        native_name="Gujlish",
        locale="gu-IN",
        voice="Pooja",
        instruction="User is speaking Gujlish (Gujarati-English mix). Mirror their style in friendly Gujlish.",
    ),
    "en": LanguageProfile(
        code="en",
        name="English",
        native_name="English",
        locale="en-IN",
        voice="Pooja",
        instruction="User is speaking Indian English. Respond in clear, polite Indian English.",
    ),
}

# Regex patterns for script detection
GUJARATI_SCRIPT_PATTERN = re.compile(r"[\u0A80-\u0AFF]")
DEVANAGARI_SCRIPT_PATTERN = re.compile(r"[\u0900-\u097F]")

# Distinct transliterated keywords
GUJLISH_KEYWORDS = {
    "kem",
    "cho",
    "majama",
    "tamne",
    "su",
    "maru",
    "tamaru",
    "samjyo",
    "aabhar",
    "khub",
    "tame",
    "karo",
}
HINGLISH_KEYWORDS = {
    "namaste",
    "kaise",
    "haan",
    "nahi",
    "kya",
    "karne",
    "karna",
    "shukriya",
    "chahiye",
    "boliye",
    "batao",
    "mujhe",
    "hai",
    "bhai",
}


class LanguageDetector:
    """Detects spoken language, script, and code-mixed patterns from input text."""

    def detect(self, text: str) -> LanguageProfile:
        """
        Detect user language from speech text.

        Args:
            text: Transcribed user input text.

        Returns:
            The matching LanguageProfile.
        """
        clean = text.strip()
        lower = clean.lower()

        # 1. Native script matching
        if GUJARATI_SCRIPT_PATTERN.search(clean):
            logger.info("Language Detected: Gujarati (Script Match)")
            return LANGUAGE_PROFILES["gu"]

        if DEVANAGARI_SCRIPT_PATTERN.search(clean):
            logger.info("Language Detected: Hindi (Script Match)")
            return LANGUAGE_PROFILES["hi"]

        # 2. Transliterated Gujlish / Hinglish keyword matching
        words = set(re.findall(r"\b\w+\b", lower))

        guj_matches = words.intersection(GUJLISH_KEYWORDS)
        hin_matches = words.intersection(HINGLISH_KEYWORDS)

        if guj_matches and len(guj_matches) > len(hin_matches):
            logger.info("Language Detected: Gujlish (Keyword Matches: %s)", guj_matches)
            return LANGUAGE_PROFILES["gujlish"]

        if hin_matches:
            logger.info(
                "Language Detected: Hinglish (Keyword Matches: %s)", hin_matches
            )
            return LANGUAGE_PROFILES["hinglish"]

        if guj_matches:
            logger.info("Language Detected: Gujlish (Keyword Matches: %s)", guj_matches)
            return LANGUAGE_PROFILES["gujlish"]

        # 3. Default to Indian English
        logger.info("Language Detected: English (Default)")
        return LANGUAGE_PROFILES["en"]


# Global singleton instance
language_detector = LanguageDetector()
