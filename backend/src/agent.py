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

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

        # Check if session is an outbound call via job metadata or room name
        is_outbound = False
        outbound_metadata = {}
        if ctx.job and getattr(ctx.job, "metadata", None):
            try:
                outbound_metadata = json.loads(ctx.job.metadata)
                if outbound_metadata.get("call_type") in [
                    "outbound_weather_alert",
                    "weather_alert",
                ]:
                    is_outbound = True
            except Exception:
                pass
        if not is_outbound and ctx.room.name.startswith("bharat-outbound-"):
            is_outbound = True

        # Extract persistent participant identity (wait for participant to connect)
        participant_identity = None
        try:
            timeout_sec = 30.0 if is_outbound else 10.0
            participant = await asyncio.wait_for(
                ctx.wait_for_participant(), timeout=timeout_sec
            )
            if participant and participant.identity:
                participant_identity = participant.identity

        except Exception:
            logger.warning(
                "Timed out waiting for remote participant, checking room remote_participants..."
            )
            if ctx.room.remote_participants:
                p = next(iter(ctx.room.remote_participants.values()))
                if p and p.identity:
                    participant_identity = p.identity

        # Determine user_id
        meta_user_id = outbound_metadata.get("user_id")
        if meta_user_id:
            user_id = meta_user_id
        elif not participant_identity or participant_identity.startswith(
            "voice_assistant_room_"
        ):
            user_id = "default_user"
        else:
            user_id = participant_identity

        logger.info("[SESSION] IS OUTBOUND CALL = %s", is_outbound)
        logger.info("[MEMORY DEBUG] LIVEKIT IDENTITY = %s", participant_identity)
        logger.info("[MEMORY DEBUG] AGENT USER ID = %s", user_id)

        # Check SQLite database for caller profile
        db_memory = get_memory_service()
        caller_profile = db_memory.get_user(user_id) or {}
        name = caller_profile.get("name") or outbound_metadata.get(
            "user_name", "Gautam"
        )
        lang = (
            caller_profile.get("language_preference")
            or outbound_metadata.get("language")
            or "Gujarati"
        )

        if is_outbound:
            # Construct Outbound Prompt & Mandatory 3-Part Spoken Opening
            location = caller_profile.get("facts", {}).get("location", "Veraval")
            outbound_prompt_addon = (
                f"\n\n[OUTBOUND CALL MODE ENABLED]\n"
                f"You are placing an outbound call to {name} regarding a weather/rain alert for saved location '{location}'.\n"
                f"MANDATORY OPENING RULES:\n"
                f"Your FIRST spoken sentence MUST clearly state:\n"
                f"1. WHO is calling (Bharat Voice AI)\n"
                f"2. WHY you are calling (weather alert for {location})\n"
                f"3. HOW to stop future calls (tell you to stop/opt-out)\n\n"
                f"OPT-OUT HANDLING RULE:\n"
                f"If the user says 'Stop calling me', 'Don't call me again', 'મને ફરી ફોન ન કરશો', or 'मुझे दोबारा फोन मत करना', "
                f"you MUST call `update_outbound_consent(consent=False, opt_out=True)`, confirm politely, and then call `end_call()`."
            )
            agent_instructions = SYSTEM_PROMPT + outbound_prompt_addon

            if lang.lower() in ["gujarati", "gujlish"]:
                greeting = (
                    f"નમસ્તે {name}, હું Bharat Voice AI છું. "
                    f"તમારા સેવ કરેલા વિસ્તાર {location} માટે હવામાનની વરસાદી ચેતવણી આપવા કૉલ કરી રહ્યો છું. "
                    f"જો તમે આગળથી આ કૉલ્સ ન ઇચ્છતા હોવ તો મને કહેજો, હું તેને બંધ કરી દઈશ."
                )
            elif lang.lower() in ["hindi", "hinglish"]:
                greeting = (
                    f"नमस्ते {name}, मैं Bharat Voice AI हूँ। "
                    f"आपके सेव किए गए इलाके {location} के लिए मौसम की बारिश की चेतावनी देने के लिए कॉल कर रहा हूँ। "
                    f"अगर आप आगे ऐसे कॉल नहीं चाहते, तो मुझे बता दीजिए, मैं इसे बंद कर दूंगा।"
                )
            else:
                greeting = (
                    f"Hello {name}, this is Bharat Voice AI calling with a weather alert for your saved location {location}. "
                    f"If you don't want these alert calls in the future, just tell me and I'll stop them."
                )
            logger.info(
                "Outbound spoken mandatory opening prepared for '%s' (%s)", name, lang
            )
        else:
            # Inbound call setup
            if caller_profile and caller_profile.get("name"):
                facts = caller_profile.get("facts", {})
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
                    greeting = (
                        f"नमस्ते {name}! आपका स्वागत है। आज मैं आपकी क्या सहायता कर सकती हूँ?"
                    )
                elif lang and lang.lower() in ["gujarati", "gujlish"]:
                    greeting = f"કેમ છો {name}! તમારું સ્વાગત છે. આજે હું તમારી શું મદદ કરી શકું?"
                else:
                    greeting = (
                        f"Namaste {name}! Welcome back. How can I help you today?"
                    )
            else:
                agent_instructions = SYSTEM_PROMPT
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
        voice_agent._active_session = session
        voice_agent.room = ctx.room

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

        # Brief 1.5s pause to ensure SIP RTP media stream is fully established after answer
        await asyncio.sleep(1.5)
        await session.say(greeting)

    except Exception as exc:
        log_session_error(exc, context="pipeline setup")
        raise


if __name__ == "__main__":
    cli.run_app(server)
