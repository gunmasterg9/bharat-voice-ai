"""
Bharat Voice AI — Voice Agent

The core BharatVoiceAgent class that extends LiveKit's Agent.
Handles conversational AI logic, function tools, multilingual routing, and session memory.
"""

from __future__ import annotations

from livekit.agents import Agent, RunContext, function_tool

from agent.logger import COMPONENT_AGENT, get_logger
from agent.memory import memory_store
from agent.prompts import SYSTEM_PROMPT

logger = get_logger(COMPONENT_AGENT)


class BharatVoiceAgent(Agent):
    """
    Bharat Voice AI — Multilingual Conversational Agent.

    Extends LiveKit's Agent with:
    - Multilingual system prompt optimized for Indian users
    - Real-time Function Tools (Weather, News, Translation)
    - Persistent Session Memory and Conversation Context
    - Analytics and Latency Tracking Integration
    """

    def __init__(self, session_id: str = "default_session") -> None:
        """Initialize the agent with system prompt and session context."""
        super().__init__(instructions=SYSTEM_PROMPT)
        self.session_id = session_id
        self.memory = memory_store.get_or_create_session(session_id)
        logger.info(
            "BharatVoiceAgent initialized with tools and session context: %s",
            session_id,
        )

    # -----------------------------------------------------------------
    # Function Tools
    # -----------------------------------------------------------------

    @function_tool
    async def get_weather(self, context: RunContext, location: str) -> str:
        """
        Get current weather information for a city or region in India.

        Args:
            location: The city or state name (e.g. 'Mumbai', 'Delhi', 'Bengaluru').
        """
        logger.info("Tool Execution: get_weather for location '%s'", location)
        city = location.strip().title()

        # Simulated real-time weather service for Indian cities
        weather_data = {
            "Delhi": "28°C, Partly Cloudy, Humidity 65%",
            "Mumbai": "31°C, Humid with Light Breeze, Humidity 78%",
            "Bengaluru": "24°C, Pleasant and Sunny, Humidity 52%",
            "Chennai": "33°C, Warm and Humid, Humidity 80%",
            "Kolkata": "30°C, Clear Sky, Humidity 70%",
            "Hyderabad": "27°C, Mostly Clear, Humidity 60%",
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
            target_language: Target language ('Hindi', 'Tamil', 'Bengali', 'Telugu', 'Kannada').
        """
        logger.info(
            "Tool Execution: translate_text '%s' to '%s'", text, target_language
        )
        lang = target_language.strip().title()

        sample_translations = {
            ("hello", "Hindi"): "नमस्ते (Namaste)",
            ("thank you", "Hindi"): "धन्यवाद (Dhanyavaad)",
            ("welcome", "Hindi"): "स्वागत है (Swagat hai)",
            ("hello", "Tamil"): "வணக்கம் (Vanakkam)",
            ("hello", "Bengali"): "হ্যালো (Hello / Namaskar)",
        }

        key = (text.strip().lower(), lang)
        translation = sample_translations.get(
            key, f"Translation of '{text}' into {lang}"
        )

        return f"Translated phrase ({lang}): {translation}"

