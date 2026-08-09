"""
Bharat Voice AI — Voice Agent

The core BharatVoiceAgent class extending LiveKit's Agent.
Handles conversational AI logic, guardrails, language detection & style mirroring,
silence management, Day 1 function tools, and Day 4 SQLite persistent memory tools.
"""

from __future__ import annotations

import json

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
from memory.memory_service import SENSITIVE_KEYWORDS, get_memory_service
from services.knowledge_base import get_knowledge_base_service

logger = get_logger(COMPONENT_AGENT)


class BharatVoiceAgent(Agent):
    """
    Bharat Voice AI — Multilingual Conversational Agent with Persistent Memory (Day 4 Architecture).

    Extends LiveKit's Agent with:
    - Structured Day 4 System Prompt with female persona & Hindi/Gujarati gender agreement
    - Input safety guardrails & prohibited claims filtering
    - Automatic language detection (English, Hindi, Gujarati, Hinglish, Gujlish) & style mirroring
    - Reusable escalation script handling
    - Session context & SQLite persistent memory store integration
    - Silence handling support ("Are you still there?")
    - Day 1 Function tools (Weather, News, Translation)
    - Day 4 Memory tools (lookup_caller, save_caller_memory, forget_caller)
    """

    def __init__(
        self,
        session_id: str = "default_session",
        user_id: str = "default_user",
        instructions: str | None = None,
    ) -> None:
        """Initialize the agent with system instructions, session context, and persistent SQLite memory."""
        super().__init__(instructions=instructions or SYSTEM_PROMPT)
        self.session_id = session_id
        self.user_id = user_id
        self.memory = memory_store.get_or_create_session(session_id, user_id=user_id)
        self.db_memory = get_memory_service()
        self.silence_count = 0

        # Update last interaction timestamp in SQLite for returning user
        self.db_memory.update_last_interaction(self.user_id)

        logger.info(
            "BharatVoiceAgent initialized for session: %s, user_id: %s",
            session_id,
            user_id,
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

        # 3. Store user turn in in-memory session history
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

        # Update session memory turn
        memory_store.add_turn(
            session_id=self.session_id,
            role="assistant",
            content=safe_response,
        )

        # Touch last_interaction in database
        self.db_memory.update_last_interaction(self.user_id)

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
    # Day 4 Persistent Memory Agent Tools
    # -----------------------------------------------------------------

    @function_tool
    async def lookup_caller(
        self,
        context: RunContext,
        user_id: str = "",
    ) -> str:
        """
        Retrieve stored caller profile from SQLite database.

        Args:
            user_id: The unique caller identifier.

        Returns:
            JSON summary of caller profile or 'PROFILE_NOT_FOUND'.
        """
        target_id = self.user_id
        logger.info("[MEMORY DEBUG] LOOKUP START for user_id = %s", target_id)

        user = self.db_memory.get_user(target_id)
        if not user:
            logger.info("[MEMORY DEBUG] LOOKUP RESULT = NOT FOUND for user_id = %s", target_id)
            return "PROFILE_NOT_FOUND"

        logger.info("[MEMORY DEBUG] LOOKUP RESULT = FOUND profile for user_id = %s: %s", target_id, json.dumps(user, ensure_ascii=False))
        profile_summary = {
            "name": user.get("name"),
            "language_preference": user.get("language_preference"),
            "relevant_facts": user.get("facts", {}),
            "last_interaction": user.get("last_interaction"),
        }
        return json.dumps(profile_summary, ensure_ascii=False)

    @function_tool
    async def save_caller_memory(
        self,
        context: RunContext,
        user_id: str = "",
        name: str | None = None,
        language_preference: str | None = None,
        facts: str | None = None,
        user_consent: bool = False,
    ) -> str:
        """
        Persist caller information to SQLite database after explicit user consent.

        Args:
            user_id: The persistent caller identifier.
            name: Caller's name if voluntarily provided and consented.
            language_preference: Preferred language (e.g. 'Hindi', 'Gujarati', 'English').
            facts: Non-sensitive caller facts as a string or JSON string (e.g. 'topic: technology').
            user_consent: MUST be set to True only after the caller explicitly grants permission.
        """
        target_id = self.user_id

        logger.info("[MEMORY DEBUG] SAVE START")
        logger.info("[MEMORY DEBUG] SAVE USER ID = %s, consent=%s", target_id, user_consent)

        if not user_consent:
            logger.warning("[MEMORY DEBUG] SAVE REJECTED: missing explicit user_consent")
            return "Action blocked: Caller information can only be saved after explicit user consent."

        # Enforce safety check against sensitive credentials
        combined_check = f"{name or ''} {facts or ''}".lower()
        if any(kw in combined_check for kw in SENSITIVE_KEYWORDS):
            logger.warning("[MEMORY DEBUG] SAVE REJECTED: sensitive information detected")
            return "Action blocked: Cannot save sensitive credentials (PINs, passwords, OTPs, bank/card details)."

        # Parse facts string into dict if JSON
        parsed_facts = {}
        if facts:
            try:
                parsed_facts = json.loads(facts)
            except Exception:
                parsed_facts = {"general_preference": facts}

        # Auto-detect language preference from recent user turns if not explicitly specified
        if not language_preference and self.memory and self.memory.turns:
            user_text_combined = " ".join([t.content.lower() for t in self.memory.turns if t.role == "user"])
            if "gujarati" in user_text_combined or "gujarat" in user_text_combined:
                language_preference = "Gujarati"
            elif "hindi" in user_text_combined:
                language_preference = "Hindi"
            elif "english" in user_text_combined:
                language_preference = "English"
            else:
                user_turns = [t for t in self.memory.turns if t.role == "user" and t.language]
                if user_turns:
                    last_lang = user_turns[-1].language
                    lang_map = {
                        "hi": "Hindi",
                        "gu": "Gujarati",
                        "hinglish": "Hinglish",
                        "gujlish": "Gujlish",
                        "en": "English",
                    }
                    language_preference = lang_map.get(last_lang, "Hindi")

        updated_user = self.db_memory.save_user(
            user_id=target_id,
            name=name,
            language_preference=language_preference,
            facts=parsed_facts,
        )

        if updated_user:
            logger.info("[MEMORY DEBUG] SAVE SUCCESS")
            logger.info("[MEMORY DEBUG] COMMIT SUCCESS")

            # Perform immediate lookup to verify write
            verify_read = self.db_memory.get_user(target_id)
            if verify_read:
                logger.info("[MEMORY DEBUG] VERIFY AFTER SAVE = FOUND: %s", json.dumps(verify_read, ensure_ascii=False))
            else:
                logger.error("[MEMORY DEBUG] VERIFY AFTER SAVE = FAILED for user_id = %s", target_id)

            return f"Successfully saved caller information for future conversations. Name: {name or 'Not specified'}, Language: {language_preference or 'Not specified'}."

        return "Failed to save caller profile due to a database error."

    @function_tool
    async def forget_caller(
        self,
        context: RunContext,
        user_id: str,
        user_confirmation: bool = False,
    ) -> str:
        """
        Delete stored caller profile completely from database upon explicit user confirmation.

        Args:
            user_id: The unique caller identifier.
            user_confirmation: MUST be set to True only after user explicitly confirms deletion.
        """
        logger.info(
            "Tool Execution: forget_caller for user_id '%s', confirmation=%s",
            user_id,
            user_confirmation,
        )

        if not user_confirmation:
            return "Action blocked: Deletion requires explicit user confirmation."

        if not user_id or str(user_id).lower() in ["anonymous", "user", "default_user", "caller"]:
            user_id = self.user_id

        success = self.db_memory.delete_user(user_id)
        if success:
            return "Done. I've removed your saved information."
        return "No stored profile found to delete or database operation failed."

    @function_tool
    async def query_knowledge_base(
        self,
        context: RunContext,
        query: str,
        track: str | None = None,
    ) -> str:
        """
        Search official RAG knowledge base for grounded scheme PDFs, crop advisories, and track documents.

        Args:
            query: The user's query topic (e.g. 'cotton pink bollworm spraying', 'PMJJBY eligibility').
            track: Optional domain track ('Farm & Field', 'Financial Services', 'Health Access', 'Learning & Literacy', 'Disaster Response').
        """
        logger.info("Tool Execution: query_knowledge_base for query '%s', track '%s'", query, track)
        kb_service = get_knowledge_base_service()
        results = kb_service.search(query=query, track=track, top_k=2)

        if not results:
            return f"No official knowledge base documents found for query: '{query}'."

        snippets = []
        for r in results:
            snippets.append(f"Document [{r['title']}] ({r['track']}): {r['grounded_content']}")

        return "\n\n".join(snippets)

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
