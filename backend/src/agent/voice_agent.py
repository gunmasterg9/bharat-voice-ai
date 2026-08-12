"""
Bharat Voice AI — Voice Agent

The core BharatVoiceAgent class extending LiveKit's Agent.
Handles conversational AI logic, guardrails, language detection & style mirroring,
silence management, Day 1 function tools, and Day 4 SQLite persistent memory tools.
"""

from __future__ import annotations

import json
from typing import Any

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
from services.weather import get_weather_service

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
        db_memory: Any | None = None,
    ) -> None:
        """Initialize the agent with system instructions, session context, and persistent SQLite memory."""
        super().__init__(instructions=instructions or SYSTEM_PROMPT)
        self.session_id = session_id
        self.user_id = user_id
        self.memory = memory_store.get_or_create_session(session_id, user_id=user_id)
        self.db_memory = db_memory or get_memory_service()
        self.silence_count = 0
        self.escalation_state: str = "IDLE"
        self.active_reference_id: str | None = None

        # Load caller's saved language preference if profile exists, else default to English
        caller_profile = self.db_memory.get_user(self.user_id) or {}
        self.active_language: str = (
            caller_profile.get("language_preference") or "English"
        )

        # Update last interaction timestamp in SQLite for returning user
        self.db_memory.update_last_interaction(self.user_id)

        logger.info(
            "BharatVoiceAgent initialized for session: %s, user_id: %s, active_language: %s, escalation_state: %s",
            session_id,
            user_id,
            self.active_language,
            self.escalation_state,
        )

    # Legacy property for backward compatibility with tools.py permission checks
    @property
    def permission_state(self) -> str:
        """Map escalation_state to legacy permission_state values for tool compatibility."""
        state_map = {
            "IDLE": "NOT_ASKED",
            "HUMAN_HELP_REQUESTED": "NOT_ASKED",
            "WAITING_FOR_PERMISSION": "WAITING_FOR_PERMISSION",
            "CREATING_ESCALATION": "APPROVED",
            "ESCALATION_CREATED": "APPROVED",
            "ESCALATION_DENIED": "DENIED",
            "ESCALATION_FAILED": "NOT_ASKED",
        }
        return state_map.get(self.escalation_state, "NOT_ASKED")

    @permission_state.setter
    def permission_state(self, value: str) -> None:
        """Map legacy permission_state setter to escalation_state for test compatibility."""
        reverse_map = {
            "NOT_ASKED": "IDLE",
            "WAITING_FOR_PERMISSION": "WAITING_FOR_PERMISSION",
            "APPROVED": "CREATING_ESCALATION",
            "DENIED": "ESCALATION_DENIED",
        }
        self.escalation_state = reverse_map.get(value, "IDLE")

    def update_permission_state_from_turn(self, user_text: str) -> None:
        """
        Deterministic escalation state machine.

        States: IDLE, HUMAN_HELP_REQUESTED, WAITING_FOR_PERMISSION,
                CREATING_ESCALATION, ESCALATION_CREATED, ESCALATION_DENIED,
                ESCALATION_FAILED.

        CRITICAL: Once ESCALATION_CREATED, the state is LOCKED.
        Post-creation acknowledgements ("Yes", "Okay", "Thanks") are ignored
        by the permission classifier — they do NOT trigger denial or re-creation.
        """
        import re

        text_lower = user_text.lower().strip()

        # ── LOCKED TERMINAL STATES ──────────────────────────────────
        # Once escalation is created, only explicit cancellation changes state
        if self.escalation_state == "ESCALATION_CREATED":
            cancel_patterns = [
                r"\bcancel (my |the |that )?request\b",
                r"\bdelete (my |the |that )?request\b",
                r"\bdon't send (it|that)\b",
                r"\bdo not send\b",
                r"अनुरोध रद्द",
                r"વિનંતી રદ કરો",
            ]
            is_cancel = any(re.search(pat, text_lower) for pat in cancel_patterns)
            if is_cancel:
                logger.info("[ESCALATION] Post-creation cancellation requested")
                # Cancellation is a separate action, not handled here
                return
            # All other messages (Yes, Okay, Thanks, etc.) — do nothing
            logger.info(
                "[ESCALATION] Post-creation acknowledgement (state locked at ESCALATION_CREATED)"
            )
            return

        # Once denied, only a new human help request re-enters the flow
        if self.escalation_state == "ESCALATION_DENIED":
            # Check for new escalation intent to allow re-entry
            escalation_keywords = [
                "human",
                "talk to human",
                "talk a human",
                "person",
                "support person",
                "human help",
                "human assistance",
                "connect to human",
                "speak to a human",
                "speak with someone",
                "talk to someone",
                "need help",
                "इंसान",
                "मानव",
                "व्यक्ति",
                "মানুষ",
                "માનવ",
                "વ્યક્તિ",
                "ઈન્સાન",
                "ઇન્સાન",
            ]
            has_new_intent = any(kw in text_lower for kw in escalation_keywords)
            if has_new_intent:
                self.escalation_state = "WAITING_FOR_PERMISSION"
                logger.info(
                    "[ESCALATION] Re-entry from DENIED: new human help requested"
                )
                logger.info("[ESCALATION] State: WAITING_FOR_PERMISSION")
            return

        # ── IDLE / HUMAN_HELP_REQUESTED — detect human escalation intent ──
        if self.escalation_state in [
            "IDLE",
            "HUMAN_HELP_REQUESTED",
            "ESCALATION_FAILED",
        ]:
            escalation_keywords = [
                "human",
                "talk to human",
                "talk a human",
                "person",
                "support person",
                "human help",
                "human assistance",
                "connect to human",
                "speak to a human",
                "speak with someone",
                "talk to someone",
                "need help",
                "इंसान",
                "मानव",
                "व्यक्ति",
                "মানুষ",
                "માનવ",
                "વ્યક્તિ",
                "ઈન્સાન",
                "ઇન્સાન",
            ]
            has_escalation_intent = any(kw in text_lower for kw in escalation_keywords)
            if has_escalation_intent:
                self.escalation_state = "WAITING_FOR_PERMISSION"
                logger.info("[ESCALATION] Human help requested")
                logger.info("[ESCALATION] State: WAITING_FOR_PERMISSION")
            return

        # ── WAITING_FOR_PERMISSION — classify YES / NO / AMBIGUOUS ──
        if self.escalation_state == "WAITING_FOR_PERMISSION":
            # 1. Questions & ambiguous patterns (MUST NEVER be treated as YES or NO)
            question_patterns = [
                r"\bwhy\b",
                r"\bwhy not\b",
                r"\bwhat information\b",
                r"\bhow does it work\b",
                r"\bwhat will you share\b",
                r"\bcan you create\b",
                r"\bplease explain\b",
                r"\bwhat happens\b",
                r"\btell me more\b",
                r"\bmaybe\b",
                r"\bnot sure\b",
                r"\bim not sure\b",
                r"કેમ",
                r"શા માટે",
                r"કઈ માહિતી",
                r"કેવી રીતે",
                r"क्यों",
                r"क्यों नहीं",
                r"क्या जानकारी",
            ]

            is_question_or_ambiguous = any(
                re.search(pat, text_lower) for pat in question_patterns
            ) or text_lower.endswith("?")

            if is_question_or_ambiguous:
                logger.info("[ESCALATION] User response classification: AMBIGUOUS")
                logger.info("[ESCALATION] State: WAITING_FOR_PERMISSION")
                return

            # 2. Refusal patterns
            no_patterns = [
                r"\bno\b",
                r"\bdon't\b",
                r"\bdont\b",
                r"\bdo not\b",
                r"\brefuse\b",
                r"\bcancel\b",
                r"\bnot share\b",
                r"\bnot create\b",
                r"नहीं",
                r"नही",
                r"साझा मत करो",
                r"शेयर मत करो",
                r"मत बनाओ",
                r"નહીં",
                r"નહિ",
                r"શેર ન કરો",
                r"નથી કરવું",
            ]

            # 3. Approval patterns
            yes_patterns = [
                r"\byes\b",
                r"\byeah\b",
                r"\bokay\b",
                r"\bok\b",
                r"\bgo ahead\b",
                r"\bcreate it\b",
                r"\bplease create\b",
                r"\bi agree\b",
                r"\bsure\b",
                r"\byep\b",
                r"हाँ",
                r"हां",
                r"कर दीजिए",
                r"ठीक है",
                r"बना दीजिए",
                r"હા",
                r"બરાબર",
                r"બનાવી દો",
            ]

            is_refusal = any(re.search(pat, text_lower) for pat in no_patterns)
            is_approval = (
                any(re.search(pat, text_lower) for pat in yes_patterns)
                and not is_refusal
            )

            if is_refusal:
                self.escalation_state = "ESCALATION_DENIED"
                logger.info("[ESCALATION] User response classification: DENIED")
                logger.info("[ESCALATION] State: ESCALATION_DENIED")
            elif is_approval:
                self.escalation_state = "CREATING_ESCALATION"
                logger.info("[ESCALATION] User response classification: APPROVED")
                logger.info("[ESCALATION] State: CREATING_ESCALATION")
            else:
                logger.info("[ESCALATION] User response classification: AMBIGUOUS")
                logger.info("[ESCALATION] State: WAITING_FOR_PERMISSION")
            return

        # ── CREATING_ESCALATION — waiting for tool call, allow last-moment denial ──
        if self.escalation_state == "CREATING_ESCALATION":
            no_patterns = [
                r"\bno\b",
                r"\bdon't\b",
                r"\bdont\b",
                r"\bdo not\b",
                r"\brefuse\b",
                r"\bcancel\b",
                r"\bnot share\b",
                r"\bnot create\b",
                r"नहीं",
                r"नही",
                r"નહીં",
                r"નહિ",
            ]
            is_refusal = any(re.search(pat, text_lower) for pat in no_patterns)
            if is_refusal:
                self.escalation_state = "ESCALATION_DENIED"
                logger.info(
                    "[ESCALATION] Last-moment denial during CREATING_ESCALATION"
                )
                logger.info("[ESCALATION] State: ESCALATION_DENIED")
            else:
                logger.info(
                    "[ESCALATION] State: CREATING_ESCALATION (awaiting tool call)"
                )
            return

    def set_active_language(self, language: str, update_db: bool = True) -> str:
        """
        Update the active conversation language and optionally persist to SQLite.

        Args:
            language: Target language ('Hindi', 'Gujarati', 'English').
            update_db: Whether to update language_preference in SQLite.
        """
        lang_clean = str(language or "").strip().lower()
        if "hind" in lang_clean or "हिंदी" in lang_clean or "हिन्दी" in lang_clean:
            normalized = "Hindi"
        elif "gujarat" in lang_clean or "ગુજરાતી" in lang_clean:
            normalized = "Gujarati"
        elif "eng" in lang_clean or "अंग्र" in lang_clean or "અંગ્રેજી" in lang_clean:
            normalized = "English"
        else:
            normalized = language.capitalize()

        self.active_language = normalized
        logger.info(
            "BharatVoiceAgent active_language updated to '%s' for user_id '%s'",
            normalized,
            self.user_id,
        )

        if update_db:
            user_profile = self.db_memory.get_user(self.user_id)
            if user_profile:
                self.db_memory.update_language_preference(self.user_id, normalized)

        return normalized

    async def process_user_turn(self, user_text: str) -> str:
        """
        Process incoming user turn through safety guardrails, language detector, and memory.

        Args:
            user_text: Transcribed speech text from user.

        Returns:
            Instructions/context override or immediate refusal message if guardrails trigger.
        """
        self.silence_count = 0  # Reset silence counter on speech
        self.update_permission_state_from_turn(user_text)

        # 1. Evaluate input safety guardrails
        guardrail_result = guardrail_engine.check_input(user_text)
        if not guardrail_result.is_safe:
            log_guardrail_event(
                category=guardrail_result.category or "unsafe",
                detail=user_text,
            )
            return guardrail_result.refusal_message or DEFAULT_ESCALATION_RESPONSE

        # 2. Check for explicit language switch requests
        lower_text = user_text.lower().strip()
        switch_phrases = [
            "change language",
            "switch language",
            "switch to",
            "speak in",
            "speak ",
            "ગુજરાતીમાં વાત કરો",
            "ગુજરાતી બોલો",
            "हिंदी में बात करें",
            "हिंदी में बोलिए",
            "हिंदी बोलो",
            "भाषा बदलो",
            "ભાષા બદલો",
        ]
        is_switch_intent = any(phrase in lower_text for phrase in switch_phrases)

        if (
            is_switch_intent
            or "gujarati" in lower_text
            or "ગુજરાતી" in lower_text
            or "hindi" in lower_text
            or "हिंदी" in lower_text
            or "हिन्दी" in lower_text
        ):
            if "gujarat" in lower_text or "ગુજરાતી" in lower_text:
                self.set_active_language("Gujarati")
            elif "hind" in lower_text or "हिंदी" in lower_text or "हिन्दी" in lower_text:
                self.set_active_language("Hindi")
            elif (
                "english" in lower_text
                or "अंग्रेजी" in lower_text
                or "અંગ્રેજી" in lower_text
            ):
                self.set_active_language("English")

        # 3. Detect user language profile
        profile = language_detector.detect(user_text)
        log_language_detection(profile.code, profile.name)

        # 4. Store user turn in in-memory session history
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
            logger.info(
                "[MEMORY DEBUG] LOOKUP RESULT = NOT FOUND for user_id = %s", target_id
            )
            return "PROFILE_NOT_FOUND"

        logger.info(
            "[MEMORY DEBUG] LOOKUP RESULT = FOUND profile for user_id = %s: %s",
            target_id,
            json.dumps(user, ensure_ascii=False),
        )
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
        logger.info(
            "[MEMORY DEBUG] SAVE USER ID = %s, consent=%s", target_id, user_consent
        )

        if not user_consent:
            logger.warning(
                "[MEMORY DEBUG] SAVE REJECTED: missing explicit user_consent"
            )
            return "Action blocked: Caller information can only be saved after explicit user consent."

        # Enforce safety check against sensitive credentials
        combined_check = f"{name or ''} {facts or ''}".lower()
        if any(kw in combined_check for kw in SENSITIVE_KEYWORDS):
            logger.warning(
                "[MEMORY DEBUG] SAVE REJECTED: sensitive information detected"
            )
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
            user_text_combined = " ".join(
                [t.content.lower() for t in self.memory.turns if t.role == "user"]
            )
            if "gujarati" in user_text_combined or "gujarat" in user_text_combined:
                language_preference = "Gujarati"
            elif "hindi" in user_text_combined:
                language_preference = "Hindi"
            elif "english" in user_text_combined:
                language_preference = "English"
            else:
                user_turns = [
                    t for t in self.memory.turns if t.role == "user" and t.language
                ]
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
                logger.info(
                    "[MEMORY DEBUG] VERIFY AFTER SAVE = FOUND: %s",
                    json.dumps(verify_read, ensure_ascii=False),
                )
            else:
                logger.error(
                    "[MEMORY DEBUG] VERIFY AFTER SAVE = FAILED for user_id = %s",
                    target_id,
                )

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

        if not user_id or str(user_id).lower() in [
            "anonymous",
            "user",
            "default_user",
            "caller",
        ]:
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
        logger.info(
            "Tool Execution: query_knowledge_base for query '%s', track '%s'",
            query,
            track,
        )
        kb_service = get_knowledge_base_service()
        results = kb_service.search(query=query, track=track, top_k=2)

        if not results:
            return f"No official knowledge base documents found for query: '{query}'."

        snippets = []
        for r in results:
            snippets.append(
                f"Document [{r['title']}] ({r['track']}): {r['grounded_content']}"
            )

        return "\n\n".join(snippets)

    # -----------------------------------------------------------------
    # Day 1 Function Tools (Preserved 100%)
    # -----------------------------------------------------------------

    @function_tool
    async def get_weather(
        self,
        context: RunContext,
        location: str = "",
        forecast_days: int = 1,
    ) -> str:
        """
        Retrieve live current or forecast weather data for a requested location in India or globally.

        Use this tool ALWAYS whenever the user asks about current, today's, tomorrow's, or upcoming weather,
        temperature, rain, precipitation, wind, or weather forecast for any location.
        Do NOT use general LLM knowledge for current weather.

        Args:
            location: The city or region name (e.g. 'Veraval', 'Ahmedabad', 'Mumbai', 'Delhi').
            forecast_days: Number of forecast days to retrieve (default: 1 for current/today).

        Returns:
            JSON string containing structured weather result or error status.
        """
        logger.info("[TOOL] get_weather called")
        logger.info("[TOOL] location = %s", location)

        target_location = location.strip() if location else ""

        # Day 4 Memory Fallback: If no location provided or generic term, check saved caller profile
        if not target_location or target_location.lower() in [
            "today",
            "current",
            "now",
            "here",
            "my city",
            "my location",
        ]:
            user_profile = self.db_memory.get_user(self.user_id)
            if user_profile:
                saved_facts = user_profile.get("facts", {})
                saved_loc = (
                    saved_facts.get("location")
                    or saved_facts.get("city")
                    or saved_facts.get("district")
                )
                if saved_loc:
                    logger.info(
                        "[TOOL] inferred location '%s' from saved caller profile for user_id '%s'",
                        saved_loc,
                        self.user_id,
                    )
                    target_location = str(saved_loc)

        if not target_location or target_location.lower() in [
            "today",
            "current",
            "now",
            "here",
            "my city",
            "my location",
        ]:
            logger.warning("[TOOL] weather request failed: missing location")
            return json.dumps(
                {
                    "success": False,
                    "error": "missing_location",
                    "message": "Location not specified and not found in saved profile. Ask the user which city they want weather for.",
                },
                ensure_ascii=False,
            )

        logger.info("[TOOL] weather request started for location '%s'", target_location)
        weather_svc = get_weather_service()
        result = await weather_svc.get_weather_data(
            location=target_location, forecast_days=forecast_days
        )

        if result.get("success"):
            logger.info("[TOOL] weather request successful for '%s'", target_location)
        else:
            logger.error(
                "[TOOL] weather request failed for '%s': %s",
                target_location,
                result.get("error"),
            )

        return json.dumps(result, ensure_ascii=False)

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

    @function_tool
    async def update_outbound_consent(
        self,
        context: RunContext,
        consent: bool,
        opt_out: bool = False,
    ) -> str:
        """
        Update caller's outbound call consent and opt-out preferences.

        Args:
            consent: True if caller agrees to receive proactive weather alert calls, False otherwise.
            opt_out: Set to True if user explicitly requests to stop future calls ("Stop calling me", "Don't call me again", "મને ફરી ફોન ન કરશો", "मुझे दोबारा फोन मत करना").
        """
        from memory.tools import update_outbound_consent_tool

        return await update_outbound_consent_tool(
            agent=self, context=context, consent=consent, opt_out=opt_out
        )

    @function_tool
    async def end_call(
        self,
        context: RunContext,
        reason: str = "task_complete",
    ) -> str:
        """
        Gracefully end the phone call when conversation finishes or after user opts out.

        Args:
            reason: Reason for call termination ('user_opt_out', 'task_complete', 'voicemail_delivered').
        """
        from memory.tools import end_call_tool

        return await end_call_tool(agent=self, context=context, reason=reason)

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        summary: str,
        what_was_checked: str | None = None,
        urgency: str = "LOW",
        preferred_follow_up: str | None = "phone",
        user_permission: bool = False,
        name: str | None = None,
        language: str | None = None,
    ) -> str:
        """
        Create a human-help request AFTER explicit caller permission.

        Args:
            reason: Reason why human help is needed (e.g. 'Weather data unavailable' or 'User explicitly requested human assistance').
            summary: Short concise human summary (WHO needs help, WHAT happened, WHAT agent checked, URGENCY, LANGUAGE, PREFERRED FOLLOW-UP METHOD).
            what_was_checked: Tools or checks already performed by agent.
            urgency: Urgency level ('LOW', 'MEDIUM', 'HIGH'). Default 'LOW'.
            preferred_follow_up: Preferred contact method (e.g. 'phone').
            user_permission: MUST be set to True only after the caller explicitly grants permission.
            name: Caller name if provided.
            language: Preferred language of caller.
        """
        from memory.tools import create_escalation_tool

        return await create_escalation_tool(
            agent=self,
            context=context,
            reason=reason,
            summary=summary,
            what_was_checked=what_was_checked,
            urgency=urgency,
            preferred_follow_up=preferred_follow_up,
            user_permission=user_permission,
            name=name,
            language=language,
        )

    @function_tool
    async def switch_language(
        self,
        context: RunContext,
        target_language: str,
    ) -> str:
        """
        Switch active conversation language when user explicitly requests a language change.

        Args:
            target_language: Target language ('Hindi', 'Gujarati', 'English').
        """
        from memory.tools import switch_language_tool

        return await switch_language_tool(
            agent=self, context=context, target_language=target_language
        )
