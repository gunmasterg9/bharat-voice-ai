"""
Bharat Voice AI — Tests for Explicit Language Switching Architecture

Tests:
1. Agent initializes active_language from SQLite caller profile or defaults to 'English'.
2. Explicit request 'Switch to Hindi' / 'हिंदी में बात करें' updates active_language to 'Hindi' and confirms in Devanagari script.
3. Explicit request 'Speak Gujarati' / 'ગુજરાતીમાં વાત કરો' updates active_language to 'Gujarati' and confirms in Gujarati script.
4. Explicit request 'Switch to English' updates active_language to 'English'.
5. Switching language updates language_preference in SQLite database when user profile exists.
6. process_user_turn detects explicit language switch phrases dynamically.
7. System prompt enforces mandatory native script and non-hardcoded dynamic language state rules.
"""

import json
import tempfile
from pathlib import Path

import pytest

from agent.prompts import SYSTEM_PROMPT
from agent.voice_agent import BharatVoiceAgent
from memory.database import Database
from memory.memory_service import MemoryService, reset_memory_service_singleton
from memory.tools import switch_language_tool


@pytest.fixture
def temp_db():
    """Fixture providing a clean temporary SQLite database for language switching tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_lang_switch.db"
        db = Database(db_path)
        yield db


@pytest.fixture
def memory_service(temp_db):
    """Fixture providing MemoryService linked to temp_db."""
    reset_memory_service_singleton()
    return MemoryService(temp_db)


@pytest.mark.asyncio
async def test_initial_active_language_default(memory_service):
    """Test that agent defaults active_language to English for new callers."""
    agent = BharatVoiceAgent(
        session_id="session_lang_1", user_id="user_new_lang_1", db_memory=memory_service
    )
    assert agent.active_language == "English"


@pytest.mark.asyncio
async def test_initial_active_language_from_profile(memory_service):
    """Test that agent initializes active_language from existing saved caller profile in SQLite."""
    user_id = "user_saved_lang_pref"
    memory_service.save_user(
        user_id=user_id, name="Jayesh", language_preference="Gujarati"
    )

    agent = BharatVoiceAgent(
        session_id="session_lang_2", user_id=user_id, db_memory=memory_service
    )
    assert agent.active_language == "Gujarati"


@pytest.mark.asyncio
async def test_switch_language_to_hindi(memory_service):
    """Test explicit language switch to Hindi updates state and returns Devanagari confirmation."""
    agent = BharatVoiceAgent(
        session_id="session_lang_3", user_id="user_lang_hi", db_memory=memory_service
    )

    raw_res = await switch_language_tool(
        agent=agent, context=None, target_language="Hindi"
    )
    res = json.loads(raw_res)

    assert res["success"] is True
    assert res["active_language"] == "Hindi"
    assert "हिंदी" in res["confirmation"] or "ठीक है" in res["confirmation"]
    assert agent.active_language == "Hindi"


@pytest.mark.asyncio
async def test_switch_language_to_gujarati(memory_service):
    """Test explicit language switch to Gujarati updates state and returns Gujarati script confirmation."""
    agent = BharatVoiceAgent(
        session_id="session_lang_4", user_id="user_lang_gu", db_memory=memory_service
    )

    raw_res = await switch_language_tool(
        agent=agent, context=None, target_language="Gujarati"
    )
    res = json.loads(raw_res)

    assert res["success"] is True
    assert res["active_language"] == "Gujarati"
    assert "ગુજરાતીમાં" in res["confirmation"] or "બરાબર" in res["confirmation"]
    assert agent.active_language == "Gujarati"


@pytest.mark.asyncio
async def test_switch_language_to_english(memory_service):
    """Test explicit language switch back to English."""
    agent = BharatVoiceAgent(
        session_id="session_lang_5", user_id="user_lang_en", db_memory=memory_service
    )
    agent.set_active_language("Hindi")

    raw_res = await switch_language_tool(
        agent=agent, context=None, target_language="English"
    )
    res = json.loads(raw_res)

    assert res["success"] is True
    assert res["active_language"] == "English"
    assert "English" in res["confirmation"]
    assert agent.active_language == "English"


@pytest.mark.asyncio
async def test_language_switch_persists_to_sqlite(memory_service):
    """Test that switching language updates language_preference in SQLite for saved profile."""
    user_id = "user_persist_lang"
    memory_service.save_user(
        user_id=user_id, name="Rahul", language_preference="English"
    )

    agent = BharatVoiceAgent(
        session_id="session_lang_6", user_id=user_id, db_memory=memory_service
    )

    await switch_language_tool(agent=agent, context=None, target_language="Hindi")

    updated_profile = memory_service.get_user(user_id)
    assert updated_profile["language_preference"] == "Hindi"


@pytest.mark.asyncio
async def test_process_user_turn_detects_explicit_switch_phrase(memory_service):
    """Test process_user_turn detecting explicit language switch triggers."""
    agent = BharatVoiceAgent(
        session_id="session_lang_7",
        user_id="user_turn_switch",
        db_memory=memory_service,
    )

    await agent.process_user_turn("हिंदी में बात करें")
    assert agent.active_language == "Hindi"

    await agent.process_user_turn("ગુજરાતીમાં વાત કરો")
    assert agent.active_language == "Gujarati"

    await agent.process_user_turn("Switch to English")
    assert agent.active_language == "English"


def test_system_prompt_contains_language_switching_rules():
    """Test that SYSTEM_PROMPT contains mandatory language switching and native script rules."""
    assert "[EXPLICIT LANGUAGE SWITCHING RULES]" in SYSTEM_PROMPT
    assert "switch_language" in SYSTEM_PROMPT
    assert "Devanagari" in SYSTEM_PROMPT
    assert "Gujarati script" in SYSTEM_PROMPT
    assert "Do NOT hardcode user language preference." in SYSTEM_PROMPT
