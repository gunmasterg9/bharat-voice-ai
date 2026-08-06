"""
Bharat Voice AI — Agent Entrypoint

Slim orchestrator that wires together the modular components:
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
    """
    Pre-load models during process startup for faster first response.

    Loads the Silero VAD model into process-level userdata so it's
    available for all sessions without per-session loading overhead.

    Args:
        proc: The LiveKit JobProcess instance.
    """
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
    """
    Handle an incoming voice session.

    Creates the full voice pipeline (STT → LLM → TTS) using the
    modular service factories, then starts the BharatVoiceAgent.

    Args:
        ctx: The LiveKit JobContext with room and participant info.
    """
    # Add room context to all log entries for this session
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    log_session_connected(ctx.room.name)

    try:
        # Build the voice pipeline from configured services
        stt_service = create_stt(settings.deepgram)
        llm_service = create_llm(settings.gemini)
        tts_service = create_tts(settings.murf)

        session = AgentSession(
            # Deepgram Nova-3 STT — user speech → text
            stt=stt_service,
            # Google Gemini 2.5 Flash — text → response
            llm=llm_service,
            # Murf Falcon TTS — response → voice
            tts=tts_service,
            # Multilingual turn detection for Indian language support
            turn_detection=MultilingualModel(),
            # Pre-loaded Silero VAD from prewarm
            vad=ctx.proc.userdata["vad"],
            # Start generating before user finishes for lower latency
            preemptive_generation=True,
        )

        # Start the pipeline with BharatVoiceAgent
        await session.start(
            agent=BharatVoiceAgent(),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    # Adaptive noise cancellation based on connection type
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )

        # Connect to the LiveKit room
        await ctx.connect()
        logger.info("Session active in room: %s", ctx.room.name)

    except Exception as exc:
        log_session_error(exc, context="pipeline setup")
        raise


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cli.run_app(server)
