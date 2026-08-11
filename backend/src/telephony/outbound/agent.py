"""
Bharat Voice AI — Outbound Voice Agent Entrypoint

Outbound AI Voice Agent pipeline for automated alerts & notifications.
Reuses existing core voice pipeline components:
- STT: Deepgram Nova-3 (Multilingual)
- LLM: Google Gemini
- TTS: Murf Falcon (Anisha voice)
- Memory: Day 4 persistent SQLite storage
- Weather: Day 5 Open-Meteo weather service integration

Run with:
    uv run python src/telephony/outbound/agent.py dev
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import json
from pathlib import Path

# Ensure src directory is at position 0 of sys.path and remove local directory to avoid module shadowing
SRC_DIR = Path(__file__).resolve().parent.parent.parent
current_dir = str(Path(__file__).resolve().parent)
while current_dir in sys.path:
    sys.path.remove(current_dir)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from livekit import rtc  # noqa: E402
from livekit.agents import (  # noqa: E402
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import noise_cancellation, silero  # noqa: E402
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # noqa: E402

from agent.config import load_settings  # noqa: E402
from agent.logger import (  # noqa: E402
    COMPONENT_AGENT,
    get_logger,
    log_session_connected,
    log_session_error,
    setup_logging,
)
from agent.prompts import SYSTEM_PROMPT  # noqa: E402
from agent.voice_agent import BharatVoiceAgent  # noqa: E402
from memory.memory_service import get_memory_service  # noqa: E402
from services.llm import create_llm  # noqa: E402
from services.stt import create_stt  # noqa: E402
from services.tts import create_tts  # noqa: E402
from services.weather import get_weather_service  # noqa: E402

# Initialize logging and settings
setup_logging()
logger = get_logger(COMPONENT_AGENT)

try:
    settings = load_settings()
except OSError as exc:
    logger.error(str(exc))
    raise SystemExit(1) from exc

server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    """Pre-load Silero VAD model for low latency."""
    logger.info("[OUTBOUND AGENT] Pre-warming Silero VAD model...")
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("[OUTBOUND AGENT] Silero VAD model pre-warmed successfully.")
    except Exception as exc:
        logger.error("[OUTBOUND AGENT] VAD loading failed: %s", str(exc))
        raise


server.setup_fnc = prewarm


@server.rtc_session(agent_name=settings.agent_name)
async def outbound_voice_session(ctx: JobContext) -> None:
    """Handle outbound voice call session."""
    ctx.log_context_fields = {"room": ctx.room.name}
    log_session_connected(ctx.room.name)
    logger.info("[OUTBOUND AGENT] Connected to room: %s", ctx.room.name)

    try:
        await ctx.connect()

        # Parse outbound metadata from job
        outbound_metadata = {}
        if ctx.job and getattr(ctx.job, "metadata", None):
            with contextlib.suppress(Exception):
                outbound_metadata = json.loads(ctx.job.metadata)

        user_id = outbound_metadata.get("user_id", "gautammax")

        logger.info("[OUTBOUND DEBUG] ROOM NAME = %s", ctx.room.name)
        logger.info("[OUTBOUND DEBUG] WAITING FOR SIP IDENTITY = %s", user_id)
        logger.info("[OUTBOUND] SIP participant creation started")

        logger.info(
            "[OUTBOUND AGENT] Waiting for Linphone participant to answer call in room '%s'...",
            ctx.room.name,
        )
        participant_identity = None
        participant = None
        try:
            participant = await asyncio.wait_for(
                ctx.wait_for_participant(), timeout=45.0
            )
            if participant and participant.identity:
                participant_identity = participant.identity
            logger.info("[OUTBOUND] Call answered")
            logger.info(
                "[OUTBOUND] SIP participant joined: %s (%s)",
                getattr(participant, "identity", "unknown"),
                getattr(participant, "name", "Linphone User"),
            )
        except TimeoutError:
            logger.warning(
                "[OUTBOUND DEBUG] Timed out waiting for SIP participant to join room '%s'. Exiting.",
                ctx.room.name,
            )
            logger.info("[DEBUG] RETURN FROM OUTBOUND SESSION")
            return

        # Audio Track & Participant Verification
        if participant:
            kind_str = str(getattr(participant, "kind", "unknown"))
            tracks = getattr(participant, "track_publications", {})
            logger.info("[OUTBOUND AUDIO] SIP participant kind = %s", kind_str)
            logger.info("[OUTBOUND AUDIO] Track publications = %d", len(tracks))
            logger.info(
                "[OUTBOUND AUDIO] Audio track available = %s",
                "YES" if len(tracks) > 0 or "sip" in kind_str.lower() else "NO",
            )
            logger.info("[AUDIO] SIP audio input available")

        user_id = (
            outbound_metadata.get("user_id")
            or participant_identity
            or user_id
        )


        user_name = outbound_metadata.get("user_name", "Gautam")
        language = outbound_metadata.get("language", "Gujarati")

        db_memory = get_memory_service()
        caller_profile = (
            db_memory.get_user(user_id) or db_memory.get_user("gautam") or {}
        )

        # Ensure caller profile fields are initialized
        name = caller_profile.get("name") or user_name or "Gautam"
        lang = caller_profile.get("language_preference") or language or "Gujarati"
        facts = caller_profile.get("facts", {})
        location = facts.get("location", "Veraval")

        # Consent check
        has_consent = caller_profile.get("outbound_call_consent", True)
        if not has_consent:
            logger.warning(
                "[OUTBOUND AGENT] Outbound calling is not enabled for user '%s'. Ending session.",
                user_id,
            )
            logger.info("[DEBUG] RETURN FROM OUTBOUND SESSION — CONSENT FALSE")
            return

        # Fetch Weather Data from Day 5 Weather Service
        weather_service = get_weather_service()
        weather_result = await weather_service.get_weather_data(location)

        weather_text = ""
        if weather_result.get("success"):
            w_data = weather_result.get("data", {})
            temp = w_data.get("temperature_c", 28)
            cond = w_data.get("condition", "Partly cloudy")
            precip = w_data.get("precipitation_probability", 80)
            weather_text = f"Current weather in {location}: {temp}°C, {cond}, rain probability {precip}%."
        else:
            weather_text = (
                "Sorry, I couldn't retrieve the latest weather information right now."
            )

        # Construct Outbound Spoken Greeting & Instructions
        if lang.lower() in ["gujarati", "gujlish"]:
            greeting = (
                f"નમસ્તે {name}, હું Bharat Voice AI છું. "
                f"તમારા સેવ કરેલા વિસ્તાર {location} માટે હવામાનની માહિતી આપવા માટે હું તમને કૉલ કરી રહ્યો છું. "
                f"અત્યારે {location} માં તાપમાન {weather_result.get('data', {}).get('temperature_c', 28)} ડિગ્રી સેલ્સિયસ અને {weather_result.get('data', {}).get('condition', 'વરસાદની શક્યતા')} છે. "
                f"જો તમે આવા કૉલ્સ આગળથી ન ઇચ્છતા હોવ તો મને કહો, હું તેને બંધ કરી દઈશ."
            )
        elif lang.lower() in ["hindi", "hinglish"]:
            greeting = (
                f"नमस्ते {name}, मैं Bharat Voice AI हूँ। "
                f"आपके सेव किए गए इलाके {location} के मौसम की जानकारी देने के लिए मैं आपको कॉल कर रहा हूँ। "
                f"अभी {location} में तापमान {weather_result.get('data', {}).get('temperature_c', 28)} डिग्री सेल्सियस और {weather_result.get('data', {}).get('condition', 'मौसम')} है। "
                f"अगर आप आगे ऐसे कॉल नहीं चाहते, तो मुझे बता दीजिए, मैं इसे बंद कर दूंगा।"
            )
        else:
            greeting = (
                f"Hello {name}, this is Bharat Voice AI. I'm calling with a weather update for your saved location {location}. "
                f"{weather_text} "
                f"If you don't want these calls in the future, just tell me and I'll stop them."
            )

        outbound_prompt_addon = (
            f"\n\n[OUTBOUND CALL MODE ACTIVE]\n"
            f"Target User: {name}\n"
            f"Preferred Language: {lang}\n"
            f"Saved Location: {location}\n"
            f"Weather Status: {weather_text}\n\n"
            f"MANDATORY OUTBOUND RULES:\n"
            f"1. You are speaking to {name} via phone call.\n"
            f"2. You MUST speak in {lang} using native script (Gujarati script for Gujarati, Devanagari script for Hindi).\n"
            f"3. FOLLOW-UP QUESTIONS: If the user asks follow-up questions about weather, forecast, or saved profile, answer helpfully using your tools (such as `get_weather`).\n"
            f"4. OPT-OUT RULE: If the caller says stop, don't call, 'મને ફરી ફોન ન કરશો', or 'मुझे दोबारा फोन मत करना', "
            f"you MUST call `update_outbound_consent(consent=False, opt_out=True)`, speak a polite goodbye response confirming opt-out, AND call `end_call()` to disconnect.\n"
        )

        agent_instructions = SYSTEM_PROMPT + outbound_prompt_addon

        # Configure pipeline (use Murf Falcon Anisha voice for outbound)
        stt_service = create_stt(settings.deepgram)
        llm_service = create_llm(settings.gemini)

        # Override TTS voice to preferred "Anisha" for outbound call
        murf_cfg = settings.murf
        from agent.config import MurfConfig

        outbound_murf_cfg = MurfConfig(
            api_key=murf_cfg.api_key,
            voice="Anisha",
            locale="en-IN",
            style="Conversation",
        )
        tts_service = create_tts(outbound_murf_cfg)

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

        logger.info("[AGENT] AgentSession starting")
        print("\n" + "=" * 60)
        print("[OUTBOUND AGENT] STEP 1: Connected to Room:", ctx.room.name)
        print("[OUTBOUND AGENT] STEP 2: Callee Answered Call. Initializing Audio...")
        print("=" * 60 + "\n")

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
        logger.info("[AGENT] AgentSession started")

        # Brief 1.5s pause to ensure Linphone SIP RTP media stream is fully established after answer
        await asyncio.sleep(1.5)

        print("[OUTBOUND AGENT] STEP 3: Speaking Opening Greeting via Murf TTS...")
        logger.info("[OUTBOUND AGENT] Speaking mandatory opening greeting...")
        await session.say(greeting)
        print("[OUTBOUND AGENT] STEP 4: Greeting Spoken Successfully! Listening for User Speech...")
        logger.info("[OUTPUT] Agent audio published")
        logger.info("[OUTBOUND] Conversation active")

        # Keep agent session alive until callee hangs up or room disconnects
        disconnect_event = asyncio.Event()

        @ctx.room.on("participant_disconnected")
        def _on_participant_disconnected(p: rtc.RemoteParticipant):
            logger.info("[OUTBOUND] SIP participant disconnected: %s", getattr(p, "identity", "unknown"))
            logger.info("[DEBUG] SIP DISCONNECT EVENT")
            disconnect_event.set()

        @ctx.room.on("disconnected")
        def _on_room_disconnected():
            logger.info("[OUTBOUND] Room disconnected")
            logger.info("[DEBUG] ROOM DISCONNECTED EVENT")
            disconnect_event.set()

        logger.info("[OUTBOUND] Waiting for conversation completion / participant hangup...")
        try:
            await disconnect_event.wait()
        finally:
            logger.info("[DEBUG] ENTRYPOINT EXIT")
            logger.info("[OUTBOUND] Call ended")

    except Exception as exc:
        logger.error("[DEBUG] EXCEPTION: %s: %s", type(exc).__name__, str(exc))
        log_session_error(exc, context="outbound pipeline setup")
        raise



if __name__ == "__main__":
    cli.run_app(server)
