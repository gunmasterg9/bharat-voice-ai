"""
Bharat Voice AI — Agent Entrypoint

Slim orchestrator that wires together modular components:
- Configuration (agent/config.py)
- Voice Agent (agent/voice_agent.py)
- Services (services/stt.py, services/tts.py, services/llm.py)
- Logging (agent/logger.py)
- Persistent SQLite Memory (memory/memory_service.py)

Run with:
    uv run python src/agent.py dev       # Development mode
    uv run python src/agent.py start     # Production mode
    uv run python src/agent.py console   # Terminal testing
"""

import asyncio
import json

from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agent.config import load_settings
from agent.logger import (
    COMPONENT_AGENT,
    get_logger,
    log_pipeline_config,
    log_session_connected,
    log_session_error,
    log_startup_banner,
    setup_logging,
)
from agent.prompts import SYSTEM_PROMPT, WELCOME_MESSAGE
from agent.voice_agent import BharatVoiceAgent
from memory.memory_service import get_memory_service
from services.llm import create_llm
from services.stt import create_stt
from services.tts import create_tts

# ---------------------------------------------------------------------------
# Initialize logging and configuration
# ---------------------------------------------------------------------------
setup_logging()
logger = get_logger(COMPONENT_AGENT)

# Load and validate all settings at import time — fail fast on missing keys
try:
    settings = load_settings()
except OSError as exc:
    logger.error(str(exc))
    raise SystemExit(1) from exc

# Log startup information
log_startup_banner()
log_pipeline_config(
    stt_model=settings.deepgram.model,
    llm_model=settings.gemini.model,
    tts_voice=settings.murf.voice,
    tts_locale=settings.murf.locale,
)

# ---------------------------------------------------------------------------
# Agent server setup
# ---------------------------------------------------------------------------
server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    """Pre-load Silero VAD model during process startup for lower latency."""
    logger.info("Pre-warming: loading Silero VAD model...")
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("Silero VAD model loaded successfully")
    except Exception as exc:
        logger.error("Failed to load Silero VAD: %s", str(exc))
        raise


server.setup_fnc = prewarm


@server.rtc_session(agent_name=settings.agent_name)
async def bharat_voice_session(ctx: JobContext) -> None:
    """Handle an incoming voice session with persistent caller memory."""
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    log_session_connected(ctx.room.name)

    try:
        await ctx.connect()
        logger.info("Connected to room: %s", ctx.room.name)

        # Extract persistent participant identity (wait for participant to connect)
        participant_identity = None
        try:
            participant = await asyncio.wait_for(ctx.wait_for_participant(), timeout=5.0)
            if participant and participant.identity:
                participant_identity = participant.identity
        except Exception:
            logger.warning("Timed out waiting for remote participant, checking room remote_participants...")
            if ctx.room.remote_participants:
                p = next(iter(ctx.room.remote_participants.values()))
                if p and p.identity:
                    participant_identity = p.identity

        # Crucial fix: NEVER fallback user_id to dynamic room.name (e.g. voice_assistant_room_XXXX)
        if not participant_identity or participant_identity.startswith("voice_assistant_room_"):
            user_id = "default_user"
        else:
            user_id = participant_identity

        logger.info("[MEMORY DEBUG] LIVEKIT IDENTITY = %s", participant_identity)
        logger.info("[MEMORY DEBUG] AGENT USER ID = %s", user_id)

        # Check SQLite database for returning caller profile
        db_memory = get_memory_service()
        logger.info("[MEMORY DEBUG] DATABASE = %s", db_memory.db.db_path)
        logger.info("[MEMORY DEBUG] LOOKUP USER ID = %s", user_id)

        caller_profile = db_memory.get_user(user_id)
        agent_instructions = SYSTEM_PROMPT

        if caller_profile and caller_profile.get("name"):
            name = caller_profile["name"]
            lang = caller_profile.get("language_preference", "")
            facts = caller_profile.get("facts", {})
            logger.info("[MEMORY DEBUG] LOOKUP RESULT = FOUND profile for user_id '%s': %s", user_id, json.dumps(caller_profile, ensure_ascii=False))

            profile_prompt_addon = (
                f"\n\n[RECOGNIZED RETURNING CALLER PROFILE]\n"
                f"Caller Name: {name}\n"
                f"Preferred Language: {lang or 'Not specified'}\n"
                f"Remembered Facts: {json.dumps(facts, ensure_ascii=False)}\n"
                f"INSTRUCTION: Address the user as {name}, speak in {lang or 'their preferred language'} using native script "
                f"(Gujarati script for Gujarati, Devanagari script for Hindi). ALWAYS respond in {lang or 'their preferred language'} "
                f"addressing {name} by name, even if the user greets you with a simple English word like 'Hello'!"
            )
            agent_instructions = SYSTEM_PROMPT + profile_prompt_addon

            if lang and lang.lower() in ["hindi", "hinglish"]:
                greeting = f"नमस्ते {name}! आपका स्वागत है। आज मैं आपकी क्या सहायता कर सकती हूँ?"
            elif lang and lang.lower() in ["gujarati", "gujlish"]:
                greeting = f"કેમ છો {name}! તમારું સ્વાગત છે. આજે હું તમારી શું મદદ કરી શકું?"
            else:
                greeting = f"Namaste {name}! Welcome back. How can I help you today?"
            logger.info("Spoken returning caller greeting for '%s' (%s)", name, lang)
        else:
            logger.info("[MEMORY DEBUG] LOOKUP RESULT = NOT FOUND for user_id '%s'", user_id)
            greeting = WELCOME_MESSAGE

        stt_service = create_stt(settings.deepgram)
        llm_service = create_llm(settings.gemini)
        tts_service = create_tts(settings.murf)

        session = AgentSession(
            stt=stt_service,
            llm=llm_service,
            tts=tts_service,
            turn_detection=MultilingualModel(),
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=True,
        )

        voice_agent = BharatVoiceAgent(
            session_id=ctx.room.name,
            user_id=user_id,
            instructions=agent_instructions,
        )

        await session.start(
            agent=voice_agent,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )

        await session.say(greeting)

    except Exception as exc:
        log_session_error(exc, context="pipeline setup")
        raise


if __name__ == "__main__":
    cli.run_app(server)
