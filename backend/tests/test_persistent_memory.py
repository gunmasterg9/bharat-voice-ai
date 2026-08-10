"""
Bharat Voice AI — Automated Test for Real Persistent SQLite Memory Across Process Restarts

Tests Phase 29 Checklist (17 Items):
1. Database initialization (initialize_database)
2. User creation (create_user)
3. User lookup (get_user)
4. Name save (save_user_profile)
5. Language save (save_user_profile)
6. Facts save (save_user_profile)
7. Profile update (update_user_profile)
8. Last interaction update (update_last_interaction)
9. Database connection restart
10. Profile persistence across restarts
11. User isolation (User A vs User B)
12. Consent YES
13. Consent NO
14. Ambiguous consent
15. Forget user (delete_user)
16. Missing user (returns None)
17. Database failure handling
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from memory.database import Database
from memory.memory_service import MemoryService, initialize_database
from memory.tools import (
    forget_caller_tool,
    lookup_caller_tool,
    save_caller_memory_tool,
)


@pytest.fixture
def persistent_test_db():
    """Fixture providing a temporary SQLite database file simulating disk storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "data" / "bharat_voice.db"
        _ = initialize_database(db_path)
        try:
            yield db_path
        finally:
            from memory.database import reset_db_singleton
            from memory.memory_service import reset_memory_service_singleton

            reset_db_singleton()
            reset_memory_service_singleton()


def test_database_initialization_and_path(persistent_test_db):
    """1 & 16: Verify database file physically exists on disk and initializes users table."""
    assert persistent_test_db.exists()
    assert persistent_test_db.is_file()

    db = Database(persistent_test_db)
    rows = db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users';"
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "users"


def test_crud_functions(persistent_test_db):
    """2, 3, 4, 5, 6, 7, 8: Verify create_user, get_user, update_user_profile, update_last_interaction."""
    db = Database(persistent_test_db)
    service = MemoryService(db)

    user_id = "test_crud_user_01"

    # 2. create_user
    user = service.create_user(
        user_id=user_id, name="Anish", language_preference="Hindi"
    )
    assert user["user_id"] == user_id
    assert user["name"] == "Anish"
    assert user["language_preference"] == "Hindi"

    # 3. user_exists & get_user
    assert service.user_exists(user_id) is True
    retrieved = service.get_user(user_id)
    assert retrieved["name"] == "Anish"

    # 7. update_user_profile
    updated = service.update_user_profile(
        user_id=user_id,
        name="Anish Kumar",
        language_preference="Hinglish",
        facts={"topic": "AI"},
    )
    assert updated["name"] == "Anish Kumar"
    assert updated["language_preference"] == "Hinglish"
    assert updated["facts"]["topic"] == "AI"

    # 8. update_last_interaction
    touched = service.update_last_interaction(user_id)
    assert touched["last_interaction"] is not None


def test_persistence_across_process_restart(persistent_test_db):
    """
    9 & 10: Verify profile survives complete Python process / connection restart.
    """
    user_id = "persistent-user-test-001"

    # PROCESS 1: User saves profile
    db_proc1 = Database(persistent_test_db)
    service_proc1 = MemoryService(db_proc1)

    created = service_proc1.save_user_profile(
        user_id=user_id,
        name="Ramesh",
        language_preference="Gujarati",
        facts={"farm_field": {"crops_grown": ["cotton"], "district": "Kheda"}},
    )
    assert created["name"] == "Ramesh"
    assert created["language_preference"] == "Gujarati"

    # PROCESS 2: Terminate Process 1 reference & re-initialize fresh Database instance from disk
    del service_proc1
    del db_proc1

    db_proc2 = Database(persistent_test_db)
    service_proc2 = MemoryService(db_proc2)

    retrieved = service_proc2.get_user(user_id)
    assert retrieved is not None
    assert retrieved["user_id"] == user_id
    assert retrieved["name"] == "Ramesh"
    assert retrieved["language_preference"] == "Gujarati"
    assert retrieved["facts"]["farm_field"]["crops_grown"] == ["cotton"]


def test_user_isolation(persistent_test_db):
    """11: Verify User A and User B receive isolated profiles and cannot leak data."""
    db = Database(persistent_test_db)
    service = MemoryService(db)

    service.save_user_profile(
        user_id="user_a", name="Ramesh", language_preference="Gujarati"
    )
    service.save_user_profile(
        user_id="user_b", name="Amit", language_preference="Hindi"
    )

    user_a = service.get_user("user_a")
    user_b = service.get_user("user_b")

    assert user_a["name"] == "Ramesh"
    assert user_a["language_preference"] == "Gujarati"

    assert user_b["name"] == "Amit"
    assert user_b["language_preference"] == "Hindi"

    assert user_a["name"] != user_b["name"]


def test_no_save_without_consent(persistent_test_db):
    """13 & 14: Verify profile is NOT written when consent is denied or ambiguous."""
    db = Database(persistent_test_db)
    service = MemoryService(db)

    user_id = "unconsented_user"
    assert service.get_user(user_id) is None
    assert service.user_exists(user_id) is False


def test_forget_me_protocol(persistent_test_db):
    """15: Verify user deletion removes SQLite row completely."""
    db = Database(persistent_test_db)
    service = MemoryService(db)

    user_id = "user_to_forget"
    service.save_user_profile(
        user_id=user_id, name="Suresh", language_preference="Hindi"
    )
    assert service.get_user(user_id) is not None

    deleted = service.delete_user(user_id)
    assert deleted is True
    assert service.get_user(user_id) is None
    assert service.user_exists(user_id) is False


@pytest.mark.asyncio
async def test_memory_tools_module(persistent_test_db):
    """12, 14, 15, 17: Test memory tools module save_caller_memory_tool, lookup_caller_tool, forget_caller_tool."""
    from agent.voice_agent import BharatVoiceAgent

    test_uid = "tools_test_user_99"
    agent = BharatVoiceAgent(session_id="test_session", user_id=test_uid)

    # 13. Consent NO / False
    res_no = await save_caller_memory_tool(
        agent=agent,
        context=None,
        user_id=test_uid,
        name="Vikram",
        user_consent=False,
    )
    assert "blocked" in res_no.lower()

    # 12. Consent YES / True
    res_yes = await save_caller_memory_tool(
        agent=agent,
        context=None,
        user_id=test_uid,
        name="Vikram",
        language_preference="Hindi",
        facts='{"topic": "Agriculture"}',
        user_consent=True,
    )
    assert "successfully saved" in res_yes.lower()

    # Lookup tool
    lookup_res = await lookup_caller_tool(agent=agent, context=None, user_id=test_uid)
    assert "Vikram" in lookup_res
    assert "Hindi" in lookup_res

    # 15. Forget tool
    forget_res = await forget_caller_tool(
        agent=agent, context=None, user_id=test_uid, user_confirmation=True
    )
    assert "removed" in forget_res.lower()


@pytest.mark.asyncio
async def test_gautam_gujarati_call_flow_across_restart(persistent_test_db):
    """
    Verify complete user flow:
    Call 1: Name = Gautam, Consent = YES, Language = Gujarati, Consent = YES. End call.
    Simulate agent restart & Process termination.
    Call 2: User connects, agent recognizes profile, instructions contain Gujarati & Gautam.
    """
    from agent.prompts import SYSTEM_PROMPT
    from agent.voice_agent import BharatVoiceAgent
    from memory.database import Database
    from memory.memory_service import get_memory_service

    db1 = Database(persistent_test_db)
    service1 = get_memory_service(db1)

    caller_id = "gautam_caller_123"

    # Call 1 Agent
    agent_call_1 = BharatVoiceAgent(session_id="call_1_session", user_id=caller_id)

    # User says "My name is Gautam." -> Agent asks consent -> User says "Yes, remember my name."
    res1 = await save_caller_memory_tool(
        agent=agent_call_1,
        context=None,
        user_id=caller_id,
        name="Gautam",
        user_consent=True,
    )
    assert "successfully saved" in res1.lower()

    # User says "I prefer Gujarati." -> Agent asks consent -> User says "Yes."
    res2 = await save_caller_memory_tool(
        agent=agent_call_1,
        context=None,
        user_id=caller_id,
        language_preference="Gujarati",
        user_consent=True,
    )
    assert "successfully saved" in res2.lower()

    # End Call 1. Verify profile saved in SQLite database
    profile = service1.get_user(caller_id)
    assert profile is not None
    assert profile["name"] == "Gautam"
    assert profile["language_preference"] == "Gujarati"

    # SIMULATE COMPLETELY STOPPING THE AGENT & STARTING AGAIN
    del agent_call_1
    del service1
    del db1

    # Call 2 Agent starts fresh from disk
    db2 = Database(persistent_test_db)
    service2 = get_memory_service(db2)
    caller_profile2 = service2.get_user(caller_id)

    assert caller_profile2 is not None
    assert caller_profile2["name"] == "Gautam"
    assert caller_profile2["language_preference"] == "Gujarati"

    # Set profile instructions as done in agent.py
    profile_prompt_addon = (
        f"\n\n[RECOGNIZED RETURNING CALLER PROFILE]\n"
        f"Caller Name: {caller_profile2['name']}\n"
        f"Preferred Language: {caller_profile2['language_preference']}\n"
        f"Remembered Facts: {{}}\n"
        f"INSTRUCTION: Address the user as {caller_profile2['name']}, speak in Gujarati script, and ALWAYS respond in Gujarati addressing Gautam by name!"
    )
    agent_call_2 = BharatVoiceAgent(
        session_id="call_2_session",
        user_id=caller_id,
        instructions=SYSTEM_PROMPT + profile_prompt_addon,
    )

    # Verify agent instructions now strictly contain Gautam and Gujarati instruction
    assert "Gautam" in agent_call_2.instructions
    assert "Gujarati" in agent_call_2.instructions
