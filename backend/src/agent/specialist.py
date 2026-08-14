"""
Bharat Voice AI — Weather Specialist Agent (Day 9 Architecture)

Specialist agent focusing exclusively on detailed weather queries.
Reuses the real Open-Meteo weather service, enforces strict safety boundaries,
supports regional languages and native scripts (Hindi Devanagari, Gujarati script),
and preserves context across handoffs.
"""

from __future__ import annotations

import asyncio
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
)
from agent.memory import memory_store
from agent.prompts import WEATHER_SPECIALIST_PROMPT
from memory.memory_service import get_memory_service
from services.weather import get_weather_service

logger = get_logger(COMPONENT_AGENT)


class BharatWeatherSpecialist(Agent):
    """
    Bharat Weather Specialist — Specialist Weather Agent.

    Extends LiveKit's Agent with:
    - Dedicated weather persona and strict specialist boundary limits
    - Execution of live weather tool get_weather()
    - Native script enforcement (Devanagari for Hindi, Gujarati script for Gujarati)
    - Context inheritance (session_id, user_id, active_language, saved location)
    - Graceful weather API failure handling (never hallucinates)
    - Human escalation workflow preservation
    - Hand-back capability to main agent via handoff_to_main_agent
    """

    def __init__(
        self,
        session_id: str = "default_session",
        user_id: str = "default_user",
        active_language: str = "English",
        initial_request: str | None = None,
        location: str | None = None,
        instructions: str | None = None,
        db_memory: Any | None = None,
    ) -> None:
        """Initialize the weather specialist with context and tools."""
        agent_instructions = instructions or WEATHER_SPECIALIST_PROMPT
        super().__init__(instructions=agent_instructions)
        self.session_id = session_id
        self.user_id = user_id
        self.active_language = active_language
        self.initial_request = initial_request
        self.location = location
        self.memory = memory_store.get_or_create_session(session_id, user_id=user_id)
        self.db_memory = db_memory or get_memory_service()
        self.escalation_state: str = "IDLE"

        # Day 8 Call Context & Intent Tracking
        self.primary_intent: str = "weather"
        self.task_started: bool = True
        self.task_completed: bool = False
        self.task_failed: bool = False
        self.tool_used: str | None = "get_weather"
        self.tool_success: bool = False
        self.escalation_created: bool = False
        self.success_reason: str | None = None
        self.failure_reason: str | None = None

        logger.info(
            "[SPECIALIST] Weather specialist started | Session: %s | User ID: %s | Lang: %s | Loc: %s",
            session_id,
            user_id,
            active_language,
            location,
        )

    async def on_enter(self) -> None:
        """Called automatically by LiveKit when taking over as active agent in handoff."""
        logger.info(
            "[SPECIALIST] on_enter called | Session: %s | Lang: %s",
            self.session_id,
            self.active_language,
        )
        intro_msg = self.get_introduction_message(self.active_language)
        if hasattr(self, "session") and self.session:
            try:
                await self.session.say(intro_msg)
                if self.initial_request:
                    logger.info(
                        "[SPECIALIST] Generating reply for initial request: %s",
                        self.initial_request,
                    )
                    await self.session.generate_reply()
            except Exception as exc:
                logger.error("[SPECIALIST] Error in on_enter: %s", exc)

    def get_introduction_message(self, language: str | None = None) -> str:
        """
        Get the specialist introduction message matching the active language.

        Returns short spoken intro:
        - English: "Namaste, I'm the Bharat Weather Specialist..."
        - Hindi: "नमस्ते, मैं भारत वॉइस एआई की मौसम विशेषज्ञ हूँ..."
        - Gujarati: "નમસ્તે, હું ભારત વૉઇસ એઆઈની હવામાન નિષ્ણાત છું..."
        """
        lang = str(language or self.active_language).strip().lower()
        if "hind" in lang or "हिंदी" in lang or "हिन्दी" in lang:
            return "नमस्ते, मैं भारत वॉइस एआई की मौसम विशेषज्ञ हूँ। मैं आपके मौसम से जुड़े सवाल में मदद करूँगी।"
        elif "gujarat" in lang or "ગુજરાતી" in lang:
            return "નમસ્તે, હું ભારત વૉઇસ એઆઈની હવામાન નિષ્ણાત છું। હું તમારા હવામાન સંબંધિત પ્રશ્નમાં મદદ કરીશ।"
        else:
            return "Namaste, I'm the Bharat Weather Specialist. I'll help you with the weather information you requested."

    def set_active_language(self, language: str, update_db: bool = True) -> str:
        """Update active language preference."""
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
            "[SPECIALIST] Active language updated to '%s' for user_id '%s'",
            normalized,
            self.user_id,
        )
        if update_db:
            self.db_memory.update_language_preference(self.user_id, normalized)
        return normalized

    async def process_user_turn(self, user_text: str) -> str:
        """Process incoming turn through safety guardrails and language detection."""
        logger.info("[SPECIALIST] Processing request: %s", user_text)

        # 1. Guardrail input check
        guardrail_result = guardrail_engine.check_input(user_text)
        if not guardrail_result.is_safe:
            log_guardrail_event(
                category=guardrail_result.category or "unsafe",
                detail=user_text,
            )
            return guardrail_result.refusal_message or DEFAULT_ESCALATION_RESPONSE

        # 2. Detect language
        profile = language_detector.detect(user_text)
        log_language_detection(profile.code, profile.name)

        # Update in-memory session history
        memory_store.add_turn(
            session_id=self.session_id,
            role="user",
            content=user_text,
            language=profile.code,
        )
        return user_text

    def handle_assistant_turn(self, assistant_text: str) -> str:
        """Filter output claims and store assistant turn."""
        safe_response = guardrail_engine.filter_output_claims(assistant_text)
        memory_store.add_turn(
            session_id=self.session_id,
            role="assistant",
            content=safe_response,
        )
        logger.info("[SPECIALIST] Response generated")
        return safe_response

    # -----------------------------------------------------------------
    # Weather Specialist Function Tools
    # -----------------------------------------------------------------

    @function_tool
    async def get_weather(
        self,
        context: RunContext,
        location: str = "",
        forecast_days: int = 1,
    ) -> str:
        """
        Get real current and forecast weather for a specified location. Use this tool whenever the user asks about current weather, today's weather, temperature, rain, humidity, wind, or forecast. Never invent current weather information.

        Args:
            location: City or region name (e.g. 'Veraval', 'Ahmedabad', 'Mumbai').
            forecast_days: Days of forecast (default 1).
        """
        logger.info("[WEATHER] Tool called")
        logger.info("[WEATHER] Request location = %s", location)

        target_location = location.strip() if location else (self.location or "")

        # Fallback to saved caller location if not specified
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
                        "[WEATHER] Inferred location '%s' from saved caller profile for user_id '%s'",
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
            logger.warning("[WEATHER] Request failed: missing location")
            return json.dumps(
                {
                    "success": False,
                    "error": "missing_location",
                    "message": "Location not specified and not found in saved profile. Ask the user which city they want weather for.",
                },
                ensure_ascii=False,
            )

        logger.info(
            "[WEATHER] Executing get_weather for location '%s'", target_location
        )
        self.tool_used = "get_weather"
        self.task_started = True

        weather_svc = get_weather_service()
        result = await weather_svc.get_weather_data(
            location=target_location, forecast_days=forecast_days
        )

        if result.get("success"):
            logger.info("[SPECIALIST] get_weather successful for '%s'", target_location)
            self.tool_success = True
            self.task_completed = True
            self.success_reason = f"Weather data retrieved for '{target_location}'"
        else:
            logger.error(
                "[SPECIALIST] get_weather failed for '%s': %s",
                target_location,
                result.get("error"),
            )
            self.tool_success = False
            self.task_failed = True
            self.failure_reason = (
                result.get("message")
                or "Sorry, I couldn't retrieve the latest weather information right now."
            )

        return json.dumps(result, ensure_ascii=False)

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
        Create a human assistance request AFTER explicit caller permission.

        Args:
            reason: Reason why human help is needed.
            summary: Short summary of caller issue.
            what_was_checked: Checks already performed.
            urgency: Urgency level ('LOW', 'MEDIUM', 'HIGH').
            preferred_follow_up: Preferred follow up method.
            user_permission: MUST be set to True only after caller explicit permission.
            name: Caller name.
            language: Caller preferred language.
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
            language=language or self.active_language,
        )

    @function_tool
    async def handoff_to_main_agent(
        self,
        context: RunContext,
        reason: str = "general_query",
    ) -> tuple[Agent, str]:
        """
        Hand conversation back to the main Bharat Voice AI assistant when user asks non-weather questions.

        Args:
            reason: Reason for hand-back (e.g. 'general_query', 'identity_question').
        """
        logger.info(
            "[HANDOFF] Handing conversation back to main agent | Reason: %s", reason
        )
        from agent.voice_agent import BharatVoiceAgent

        main_agent = BharatVoiceAgent(
            session_id=self.session_id,
            user_id=self.user_id,
        )
        main_agent.set_active_language(self.active_language, update_db=False)

        handback_msg = (
            "I'm connecting you back to Bharat Voice AI for general questions."
        )
        if self.active_language.lower() in ["hindi", "hinglish"]:
            handback_msg = "मैं आपको सामान्य प्रश्नों के लिए भारत वॉइस एआई से वापस जोड़ रही हूँ।"
        elif self.active_language.lower() in ["gujarati", "gujlish"]:
            handback_msg = "હું તમને સામાન્ય પ્રશ્નો માટે ભારત વૉઇસ એઆઈ સાથે પાછી જોડું છું."

        return (main_agent, handback_msg)
