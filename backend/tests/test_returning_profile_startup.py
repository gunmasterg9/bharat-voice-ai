"""Regression checks for the returning-caller startup path."""

from pathlib import Path

import pytest


def test_returning_profile_path_imports_system_prompt() -> None:
    """The startup path must have the prompt it appends to a saved profile."""
    agent_entrypoint = Path(__file__).parents[1] / "src" / "agent.py"
    source = agent_entrypoint.read_text(encoding="utf-8")

    assert "from agent.prompts import SYSTEM_PROMPT, WELCOME_MESSAGE" in source
    assert "agent_instructions = SYSTEM_PROMPT + profile_prompt_addon" in source
    assert "instructions=agent_instructions" in source


@pytest.mark.asyncio
async def test_save_memory_uses_the_session_caller_id_when_omitted() -> None:
    """The LLM should not need access to the internal LiveKit caller ID."""
    from agent.voice_agent import BharatVoiceAgent

    user_id = "returning-profile-regression-user"
    agent = BharatVoiceAgent(session_id="returning-profile-regression", user_id=user_id)
    agent.db_memory.delete_user(user_id)

    try:
        result = await agent.save_caller_memory(
            context=None,
            name="Gautam",
            language_preference="Gujarati",
            user_consent=True,
        )
        assert "successfully saved" in result.lower()

        profile = agent.db_memory.get_user(user_id)
        assert profile is not None
        assert profile["name"] == "Gautam"
        assert profile["language_preference"] == "Gujarati"
    finally:
        agent.db_memory.delete_user(user_id)
