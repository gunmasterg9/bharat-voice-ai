"""
Bharat Voice AI — Voice Agent

The core BharatVoiceAgent class that extends LiveKit's Agent.
Handles the conversational AI logic with multilingual support.
"""

from __future__ import annotations

from livekit.agents import Agent

from agent.logger import COMPONENT_AGENT, get_logger
from agent.prompts import SYSTEM_PROMPT

logger = get_logger(COMPONENT_AGENT)


class BharatVoiceAgent(Agent):
    """
    Bharat Voice AI — Multilingual Conversational Agent.

    Extends LiveKit's Agent with:
    - Multilingual system prompt optimized for Indian users
    - Concise, voice-friendly responses
    - Automatic language switching

    The agent is initialized with the Bharat Voice AI system prompt
    and connects to the voice pipeline (STT → LLM → TTS) via
    the AgentSession in the entrypoint.
    """

    def __init__(self) -> None:
        """Initialize the agent with the Bharat Voice AI system prompt."""
        super().__init__(instructions=SYSTEM_PROMPT)
        logger.info("BharatVoiceAgent initialized with multilingual prompt")

    # -----------------------------------------------------------------
    # Tool Integration
    # -----------------------------------------------------------------
    # To add tools, use the @function_tool decorator:
    #
    # from livekit.agents import function_tool, RunContext
    #
    # @function_tool
    # async def my_tool(self, context: RunContext, param: str):
    #     """Tool description for the LLM.
    #
    #     Args:
    #         param: Description of the parameter.
    #     """
    #     logger.info("Tool called with: %s", param)
    #     return "result"
