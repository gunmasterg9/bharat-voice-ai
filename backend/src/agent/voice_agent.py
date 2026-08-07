"""
Bharat Voice AI — Voice Agent

The core BharatVoiceAgent class extending LiveKit's Agent.
Handles conversational AI logic, guardrails, language detection & style mirroring,
silence management, function tools, and session memory.
"""

from __future__ import annotations

from livekit.agents import Agent, RunContext, function_tool

from agent.guardrails import DEFAULT_ESCALATION_RESPONSE, guardrail_engine
from agent.language import language_detector
from agent.logger import (
    COMPONENT_AGENT,
    get_logger,
    log_guardrail_event,
    log_language_detection,
    log_silence_event,
)
from agent.memory import memory_store
from agent.prompts import (
    SILENCE_PROMPT_1,
    SILENCE_PROMPT_2,
    SYSTEM_PROMPT,
)

logger = get_logger(COMPONENT_AGENT)


class BharatVoiceAgent(Agent):
    """
    Bharat Voice AI — Multilingual Conversational Agent (Day 2 Production Architecture).

    Extends LiveKit's Agent with:
    - Structured Day 2 System Prompt with female persona & Hindi/Gujarati gender agreement
    - Input safety guardrails & prohibited claims filtering
    - Automatic language detection (English, Hindi, Gujarati, Hinglish, Gujlish) & style mirroring
    - Reusable escalation script handling
    - Session context & memory store integration
    - Silence handling support ("Are you still there?")
    - Day 1 Function tools (Weather, News, Translation)
    """

    def __init__(self, session_id: str = "default_session") -> None:
        """Initialize the agent with system instructions and session context."""
        super().__init__(instructions=SYSTEM_PROMPT)
        self.session_id = session_id
        self.memory = memory_store.get_or_create_session(session_id)
        self.silence_count = 0
        logger.info(
            "BharatVoiceAgent initialized with Day 2 architecture for session: %s",
            session_id,
        )

    async def process_user_turn(self, user_text: str) -> str:
        """
        Process incoming user turn through safety guardrails, language detector, and memory.

        Args:
            user_text: Transcribed speech text from user.

        Returns:
            Instructions/context override or immediate refusal message if guardrails trigger.
        """
        self.silence_count = 0  # Reset silence counter on speech

        # 1. Evaluate input safety guardrails
        guardrail_result = guardrail_engine.check_input(user_text)
        if not guardrail_result.is_safe:
            log_guardrail_event(
                category=guardrail_result.category or "unsafe",
                detail=user_text,
            )
            return guardrail_result.refusal_message or DEFAULT_ESCALATION_RESPONSE

        # 2. Detect user language profile
        profile = language_detector.detect(user_text)
        log_language_detection(profile.code, profile.name)

        # 3. Store user turn in persistent memory
        memory_store.add_turn(
            session_id=self.session_id,
            role="user",
            content=user_text,
            language=profile.code,
        )

        return user_text

    def handle_assistant_turn(self, assistant_text: str) -> str:
        """
        Filter assistant output for prohibited claims and save to session memory.

        Args:
            assistant_text: Generated response from LLM.

        Returns:
            Scrubbed response or escalation script.
        """
        # Filter output for prohibited claims
        safe_response = guardrail_engine.filter_output_claims(assistant_text)

        # Update persistent memory
        memory_store.add_turn(
            session_id=self.session_id,
            role="assistant",
            content=safe_response,
        )
        return safe_response

    def handle_silence(self) -> str:
        """
        Handle user silence events.

        Returns:
            First prompt "Are you still there?" or second prompt "No problem... Goodbye."
        """
        self.silence_count += 1
        log_silence_event(stage=str(self.silence_count))

        if self.silence_count == 1:
            return SILENCE_PROMPT_1
        else:
            return SILENCE_PROMPT_2

    # -----------------------------------------------------------------
    # Day 1 Function Tools (Preserved 100%)
    # -----------------------------------------------------------------

    @function_tool
    async def get_weather(self, context: RunContext, location: str) -> str:
        """
        Get current weather information for a city or region in India.

        Args:
            location: The city or state name (e.g. 'Mumbai', 'Delhi', 'Bengaluru', 'Ahmedabad').
        """
        logger.info("Tool Execution: get_weather for location '%s'", location)
        city = location.strip().title()

        weather_data = {
            "Delhi": "28°C, Partly Cloudy, Humidity 65%",
            "Mumbai": "31°C, Humid with Light Breeze, Humidity 78%",
            "Bengaluru": "24°C, Pleasant and Sunny, Humidity 52%",
            "Chennai": "33°C, Warm and Humid, Humidity 80%",
            "Kolkata": "30°C, Clear Sky, Humidity 70%",
            "Hyderabad": "27°C, Mostly Clear, Humidity 60%",
            "Ahmedabad": "32°C, Warm and Sunny, Humidity 55%",
        }

        result = weather_data.get(city, f"26°C, Mild and Clear Sky in {city}")
        return f"Current weather in {city}: {result}."

    @function_tool
    async def get_latest_news(
        self, context: RunContext, category: str = "general"
    ) -> str:
        """
        Get latest top news headlines in India.

        Args:
            category: News category ('technology', 'business', 'sports', 'general').
        """
        logger.info("Tool Execution: get_latest_news category '%s'", category)
        cat = category.strip().lower()

        news_dict = {
            "technology": "India's AI ecosystem expands with native voice LLM initiatives.",
            "business": "Indian markets reach new highs amid strong economic growth.",
            "sports": "Indian Cricket team prepares for upcoming international series.",
            "general": "New infrastructure projects inaugurated across major metro cities.",
        }

        headline = news_dict.get(cat, news_dict["general"])
        return f"Latest India {cat.capitalize()} News: {headline}"

    @function_tool
    async def translate_text(
        self, context: RunContext, text: str, target_language: str
    ) -> str:
        """
        Translate a text phrase into a target Indian regional language.

        Args:
            text: The text to translate.
            target_language: Target language ('Hindi', 'Gujarati', 'Tamil', 'Bengali', 'Telugu').
        """
        logger.info(
            "Tool Execution: translate_text '%s' to '%s'", text, target_language
        )
        lang = target_language.strip().title()

        sample_translations = {
            ("hello", "Hindi"): "नमस्ते (Namaste)",
            ("hello", "Gujarati"): "કેમ છો (Kem Cho)",
            ("thank you", "Hindi"): "धन्यवाद (Dhanyavaad)",
            ("thank you", "Gujarati"): "આભાર (Aabhar)",
            ("welcome", "Hindi"): "स्वागत है (Swagat hai)",
        }

        key = (text.strip().lower(), lang)
        translation = sample_translations.get(
            key, f"Translation of '{text}' into {lang}"
        )

        return f"Translated phrase ({lang}): {translation}"
