"""
Bharat Voice AI — Agent Entrypoint

Slim orchestrator that wires together modular components:
- Configuration (agent/config.py)
- Voice Agent (agent/voice_agent.py)
- Services (services/stt.py, services/tts.py, services/llm.py)
- Logging (agent/logger.py)

Run with:
    uv run python src/agent.py dev       # Development mode
    uv run python src/agent.py start     # Production mode
    uv run python src/agent.py console   # Terminal testing
"""

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
from agent.prompts import WELCOME_MESSAGE
from agent.voice_agent import BharatVoiceAgent
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
    """Handle an incoming voice session."""
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    log_session_connected(ctx.room.name)

    try:
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

        voice_agent = BharatVoiceAgent(session_id=ctx.room.name)

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

        await ctx.connect()
        logger.info("Session active in room: %s", ctx.room.name)

        # Greet user with official Day 2 welcome message
        await session.say(WELCOME_MESSAGE)

    except Exception as exc:
        log_session_error(exc, context="pipeline setup")
        raise


if __name__ == "__main__":
    cli.run_app(server)
