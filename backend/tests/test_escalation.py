"""
Bharat Voice AI — Tests for Day 7 Human Help & Escalation Architecture

Tests:
1. Normal conversation does not escalate.
2. Explicit human request triggers permission flow.
3. Weather failure triggers escalation option.
4. Permission YES creates request.
5. Permission NO does not create request.
6. Reference ID generation (ESC-YYYYMMDD-XXXX).
7. Duplicate request handling.
8. Sensitive information filtering.
9. Tool failure handling.
10. Database failure handling.
11. Status updates (OPEN -> IN_PROGRESS -> RESOLVED).
12. Dashboard list & status update operations.
13. Gujarati escalation handling.
14. Hindi escalation handling.
15. English escalation handling.
"""

import json
import tempfile
from pathlib import Path

import pytest

from agent.prompts import SYSTEM_PROMPT
from agent.voice_agent import BharatVoiceAgent
from memory.database import Database
from memory.memory_service import MemoryService, scrub_sensitive_text
from memory.tools import create_escalation_tool


@pytest.fixture
def temp_db():
    """Fixture providing a temporary SQLite database for escalation testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_escalation_bharat_voice.db"
        db = Database(db_path)
        yield db


@pytest.fixture
def memory_service(temp_db):
    """Fixture providing MemoryService linked to temp_db."""
    return MemoryService(temp_db)


# 1. Normal Conversation Test: No Escalation
@pytest.mark.asyncio
async def test_normal_conversation_no_escalation(memory_service):
    """Test that a normal conversation does not create any escalation records."""
    user_id = "user_normal_001"
    memory_service.save_user(
        user_id=user_id, name="Rahul", language_preference="Gujarati"
    )
    escalations = memory_service.get_escalations()
    assert len(escalations) == 0


# 2. Explicit Human Request & 4. Permission YES Creates Request
@pytest.mark.asyncio
async def test_explicit_human_request_permission_yes(memory_service):
    """Test explicit human request where user grants permission."""
    user_id = "user_explicit_yes"
    res = memory_service.create_escalation(
        user_id=user_id,
        reason="User requested human assistance",
        summary="User asked: Can I talk to a person?",
        what_was_checked="Agent initial conversation",
        urgency="LOW",
        preferred_follow_up="phone",
        name="Kavita",
        language="Hindi",
        user_permission=True,
    )

    assert res["success"] is True
    assert "reference_id" in res
    assert res["reference_id"].startswith("ESC-")
    assert res["status"] == "OPEN"

    # Verify record in DB
    record = memory_service.get_escalation_by_ref(res["reference_id"])
    assert record is not None
    assert record["user_id"] == user_id
    assert record["name"] == "Kavita"
    assert record["language"] == "Hindi"
    assert record["status"] == "OPEN"


# 3. Weather Failure Triggers Escalation Option
@pytest.mark.asyncio
async def test_weather_failure_escalation(memory_service):
    """Test weather service failure triggering human help creation."""
    user_id = "user_weather_fail"
    res = memory_service.create_escalation(
        user_id=user_id,
        reason="Weather data unavailable",
        summary="User requested weather for Veraval, but Open-Meteo API timed out.",
        what_was_checked="Open-Meteo Geocoding & Forecast API",
        urgency="LOW",
        preferred_follow_up="phone",
        name="Jitesh",
        language="Gujarati",
        user_permission=True,
    )

    assert res["success"] is True
    assert res["status"] == "OPEN"
    assert res["reference_id"].startswith("ESC-")


# 5. Permission NO Does Not Create Request
@pytest.mark.asyncio
async def test_permission_no_prevents_escalation(memory_service):
    """Test that denying permission prevents escalation creation."""
    user_id = "user_permission_no"
    res = memory_service.create_escalation(
        user_id=user_id,
        reason="User requested human help",
        summary="User asked for support but denied permission to share info",
        user_permission=False,
    )

    assert res["success"] is False
    assert res["error"] == "permission_denied"

    # Verify NO record in DB
    escalations = memory_service.get_escalations()
    assert len(escalations) == 0


# 6. Dynamic Reference ID Generation Format
def test_reference_id_generation_format(memory_service):
    """Test reference ID generation matches format ESC-YYYYMMDD-XXXX."""
    user_id = "user_ref_fmt"
    res1 = memory_service.create_escalation(
        user_id=user_id,
        reason="Reason A",
        summary="Summary A",
        user_permission=True,
    )
    res2 = memory_service.create_escalation(
        user_id="user_ref_fmt_2",
        reason="Reason B",
        summary="Summary B",
        user_permission=True,
    )

    ref1 = res1["reference_id"]
    ref2 = res2["reference_id"]

    assert ref1.startswith("ESC-")
    assert ref2.startswith("ESC-")
    assert ref1 != ref2
    # Check 4-digit sequence format
    parts1 = ref1.split("-")
    assert len(parts1) == 3
    assert len(parts1[1]) == 8  # YYYYMMDD
    assert len(parts1[2]) == 4  # XXXX


# 7. Duplicate Request Prevention
def test_duplicate_escalation_prevention(memory_service):
    """Test that creating a second OPEN escalation with same reason returns the existing reference ID."""
    user_id = "user_dup_check"
    reason = "Weather service unavailable for Veraval"

    res1 = memory_service.create_escalation(
        user_id=user_id,
        reason=reason,
        summary="First request",
        user_permission=True,
    )

    res2 = memory_service.create_escalation(
        user_id=user_id,
        reason=reason,
        summary="Second request attempt",
        user_permission=True,
    )

    assert res1["success"] is True
    assert res2["success"] is True
    assert res2["reference_id"] == res1["reference_id"]
    assert res2.get("is_duplicate") is True


# 8. Sensitive Information Filtering
def test_sensitive_info_filtering():
    """Test that passwords, PINs, OTPs, API keys, and card numbers are scrubbed."""
    text_with_secrets = (
        "User password: mySecretPassword123, OTP is 987654, card: 4111-2222-3333-4444"
    )
    clean = scrub_sensitive_text(text_with_secrets)

    assert "mySecretPassword123" not in clean
    assert "987654" not in clean
    assert "4111-2222-3333-4444" not in clean
    assert "[REDACTED]" in clean or "[REDACTED_CARD]" in clean


# 9. Tool Failure Handling
@pytest.mark.asyncio
async def test_create_escalation_tool_no_permission():
    """Test create_escalation_tool rejection when user_permission is False."""
    agent = BharatVoiceAgent(session_id="test_tool_fail")
    tool_raw = await create_escalation_tool(
        agent=agent,
        context=None,
        reason="Test tool",
        summary="Test summary",
        user_permission=False,
    )
    data = json.loads(tool_raw)
    assert data["success"] is False
    assert data["error"] == "permission_denied"


# 10. Database Failure Handling
def test_database_failure_handling(memory_service, monkeypatch):
    """Test graceful failure handling when database fails."""

    def mock_write_error(*args, **kwargs):
        raise Exception("Database transaction failed")

    monkeypatch.setattr(memory_service.db, "execute_write", mock_write_error)

    res = memory_service.create_escalation(
        user_id="user_db_fail",
        reason="Test DB Fail",
        summary="Summary DB Fail",
        user_permission=True,
    )
    assert res["success"] is False
    assert res["error"] == "database_error"


# 11. Status Updates (OPEN -> IN_PROGRESS -> RESOLVED)
def test_status_transitions(memory_service):
    """Test status updates from OPEN to IN_PROGRESS to RESOLVED."""
    res = memory_service.create_escalation(
        user_id="user_status_test",
        reason="Status transition test",
        summary="Testing status workflow",
        user_permission=True,
    )
    ref_id = res["reference_id"]
    assert res["status"] == "OPEN"

    # Transition to IN_PROGRESS
    updated1 = memory_service.update_escalation_status(ref_id, "IN_PROGRESS")
    assert updated1 is not None
    assert updated1["status"] == "IN_PROGRESS"

    # Transition to RESOLVED
    updated2 = memory_service.update_escalation_status(ref_id, "RESOLVED")
    assert updated2 is not None
    assert updated2["status"] == "RESOLVED"

    # Invalid status transition rejected
    updated_invalid = memory_service.update_escalation_status(ref_id, "INVALID_STATUS")
    assert updated_invalid is None


# 12. Dashboard List & Filter Operations
def test_dashboard_list_and_filter(memory_service):
    """Test fetching and filtering escalations for human dashboard."""
    memory_service.create_escalation(
        user_id="user_dash_1",
        reason="Reason 1",
        summary="Summary 1",
        user_permission=True,
    )
    res2 = memory_service.create_escalation(
        user_id="user_dash_2",
        reason="Reason 2",
        summary="Summary 2",
        user_permission=True,
    )
    memory_service.update_escalation_status(res2["reference_id"], "RESOLVED")

    open_items = memory_service.get_escalations(status="OPEN")
    resolved_items = memory_service.get_escalations(status="RESOLVED")
    all_items = memory_service.get_escalations()

    assert len(open_items) == 1
    assert len(resolved_items) == 1
    assert len(all_items) == 2


# 13. Gujarati Escalation Prompt & Tool Integration
@pytest.mark.asyncio
async def test_gujarati_escalation_flow(memory_service):
    """Test Gujarati language escalation creation."""
    user_id = "user_gujarati_esc"
    res = memory_service.create_escalation(
        user_id=user_id,
        reason="વેરાવળમાં હવામાન ડેટા ઉપલબ્ધ નથી",
        summary="ગ્રાહકે વેરાવળ હવામાન વિશે પૂછ્યું પણ સેવા ઉપલબ્ધ ન હતી.",
        what_was_checked="Open-Meteo API",
        urgency="LOW",
        preferred_follow_up="phone",
        name="જયેશ",
        language="Gujarati",
        user_permission=True,
    )

    assert res["success"] is True
    record = memory_service.get_escalation_by_ref(res["reference_id"])
    assert record["language"] == "Gujarati"
    assert record["name"] == "જયેશ"


# 14. Hindi Escalation Flow
@pytest.mark.asyncio
async def test_hindi_escalation_flow(memory_service):
    """Test Hindi language escalation creation."""
    user_id = "user_hindi_esc"
    res = memory_service.create_escalation(
        user_id=user_id,
        reason="मौसम की जानकारी उपलब्ध नहीं है",
        summary="उपयोगकर्ता ने मौसम की जानकारी मांगी पर सेवा उपलब्ध नहीं थी।",
        what_was_checked="Open-Meteo API",
        urgency="LOW",
        preferred_follow_up="phone",
        name="राजेश",
        language="Hindi",
        user_permission=True,
    )

    assert res["success"] is True
    record = memory_service.get_escalation_by_ref(res["reference_id"])
    assert record["language"] == "Hindi"
    assert record["name"] == "राजेश"


# 15. English Escalation Flow & Prompt Instructions Check
def test_english_escalation_prompt_check():
    """Test that SYSTEM_PROMPT contains mandatory Day 7 Human Help instructions."""
    assert "[HUMAN HELP & ESCALATION]" in SYSTEM_PROMPT
    assert "create_escalation" in SYSTEM_PROMPT
    assert "never assume permission" in SYSTEM_PROMPT.lower()
    assert "never assume denial" in SYSTEM_PROMPT.lower()
    assert "reference id" in SYSTEM_PROMPT.lower()


# 16. Permission State Machine: Explicit YES
@pytest.mark.asyncio
async def test_permission_state_explicit_yes(memory_service):
    """Test explicit YES transitions state to APPROVED."""
    agent = BharatVoiceAgent(session_id="test_perm_yes", db_memory=memory_service)
    assert agent.permission_state == "NOT_ASKED"

    await agent.process_user_turn("Want to talk a human. I need some help.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("Yes, create it.")
    assert agent.permission_state == "APPROVED"


# 17. Permission State Machine: Explicit NO
@pytest.mark.asyncio
async def test_permission_state_explicit_no(memory_service):
    """Test explicit NO transitions state to DENIED."""
    agent = BharatVoiceAgent(session_id="test_perm_no", db_memory=memory_service)
    await agent.process_user_turn("I want to talk to a human.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("No, don't share my information.")
    assert agent.permission_state == "DENIED"


# 18. Permission State Machine: Ambiguous "Why not create?"
@pytest.mark.asyncio
async def test_permission_state_why_not_create(memory_service):
    """Test 'Why not create?' is NOT treated as DENIED."""
    agent = BharatVoiceAgent(session_id="test_why_not", db_memory=memory_service)
    await agent.process_user_turn("Want to talk a human. I need some help.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("Why not create")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"
    assert agent.permission_state != "DENIED"


# 19. Permission State Machine: Ambiguous "Why?" and "What information?"
@pytest.mark.asyncio
async def test_permission_state_questions(memory_service):
    """Test questions like 'Why?' and 'What information will you share?' remain WAITING_FOR_PERMISSION."""
    agent = BharatVoiceAgent(session_id="test_questions", db_memory=memory_service)
    await agent.process_user_turn("I need human help.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("Why?")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("What information will you share?")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"


# 20. Permission State Machine: Ambiguous Responses "Maybe" / "I'm not sure"
@pytest.mark.asyncio
async def test_permission_state_unclear(memory_service):
    """Test unclear responses remain in WAITING_FOR_PERMISSION without triggering DENIED."""
    agent = BharatVoiceAgent(session_id="test_unclear", db_memory=memory_service)
    await agent.process_user_turn("I want to talk to a human.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("Maybe")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("I'm not sure")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"


# 21. Hindi Permission Flow (YES and NO)
@pytest.mark.asyncio
async def test_hindi_permission_states(memory_service):
    """Test Hindi explicit YES and NO permission state transitions."""
    agent_yes = BharatVoiceAgent(session_id="test_hindi_yes", db_memory=memory_service)
    await agent_yes.process_user_turn("आप मुझे किसी इंसान से जोड़ सकते हैं?")
    assert agent_yes.permission_state == "WAITING_FOR_PERMISSION"
    await agent_yes.process_user_turn("हाँ, अनुरोध बना दीजिए।")
    assert agent_yes.permission_state == "APPROVED"

    agent_no = BharatVoiceAgent(session_id="test_hindi_no", db_memory=memory_service)
    await agent_no.process_user_turn("आप मुझे किसी इंसान से जोड़ सकते हैं?")
    assert agent_no.permission_state == "WAITING_FOR_PERMISSION"
    await agent_no.process_user_turn("नहीं, मेरी जानकारी साझा मत करें।")
    assert agent_no.permission_state == "DENIED"


# 22. Gujarati Permission Flow (YES and NO)
@pytest.mark.asyncio
async def test_gujarati_permission_states(memory_service):
    """Test Gujarati explicit YES and NO permission state transitions."""
    agent_yes = BharatVoiceAgent(session_id="test_guj_yes", db_memory=memory_service)
    await agent_yes.process_user_turn("મારે કોઈ વ્યક્તિ સાથે વાત કરવી છે")
    assert agent_yes.permission_state == "WAITING_FOR_PERMISSION"
    await agent_yes.process_user_turn("હા, વિનંતી બનાવી દો.")
    assert agent_yes.permission_state == "APPROVED"

    agent_no = BharatVoiceAgent(session_id="test_guj_no", db_memory=memory_service)
    await agent_no.process_user_turn("મારે કોઈ વ્યક્તિ સાથે વાત કરવી છે")
    assert agent_no.permission_state == "WAITING_FOR_PERMISSION"
    await agent_no.process_user_turn("નહીં, મારી માહિતી શેર ન કરો.")
    assert agent_no.permission_state == "DENIED"


# 23. Mind Change: YES -> NO
@pytest.mark.asyncio
async def test_user_changes_mind_yes_to_no(memory_service):
    """Test user approving then changing mind to NO transitions to DENIED."""
    agent = BharatVoiceAgent(session_id="test_mind_change", db_memory=memory_service)
    await agent.process_user_turn("Want to talk a human.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("Yes, create it.")
    assert agent.permission_state == "APPROVED"

    await agent.process_user_turn("No, wait. Don't create it.")
    assert agent.permission_state == "DENIED"


# 24. Backend Safety Check Blocks Tool Call Without APPROVED State
@pytest.mark.asyncio
async def test_create_escalation_blocked_without_approved_state(memory_service):
    """Test create_escalation tool fails if permission_state is not APPROVED."""
    agent = BharatVoiceAgent(session_id="test_safety_block", db_memory=memory_service)
    agent.permission_state = "WAITING_FOR_PERMISSION"

    res_raw = await agent.create_escalation(
        context=None,
        reason="User needs support",
        summary="Summary test",
        user_permission=True,
    )
    res = json.loads(res_raw)
    assert res["success"] is False
    assert res["reason"] == "USER_PERMISSION_REQUIRED"
    assert res["error"] == "permission_denied"

    # Verify database has NO records
    escalations = memory_service.get_escalations()
    assert len(escalations) == 0


# 25. Normal Weather Conversation Does Not Escalate
@pytest.mark.asyncio
async def test_normal_weather_no_escalation(memory_service):
    """Test normal weather question does not trigger escalation permission flow."""
    agent = BharatVoiceAgent(session_id="test_normal_weather", db_memory=memory_service)
    await agent.process_user_turn("What is the weather in Veraval?")
    assert agent.permission_state == "NOT_ASKED"


# 26. Human Request with 'I need help' Trigger Check
@pytest.mark.asyncio
async def test_human_request_with_i_need_help(memory_service):
    """Test 'I want to talk to a human. I need help.' sets WAITING_FOR_PERMISSION and is not safety refused."""
    agent = BharatVoiceAgent(session_id="test_need_help", db_memory=memory_service)
    res = await agent.process_user_turn("I want to talk to a human. I need help.")

    # Must NOT be safety refusal message
    assert "I'm sorry, I can't safely help with that" not in res
    assert agent.permission_state == "WAITING_FOR_PERMISSION"


# 27. Explicit Approval via 'Yeah'
@pytest.mark.asyncio
async def test_permission_state_yeah(memory_service):
    """Test 'Yeah' sets permission_state to APPROVED."""
    agent = BharatVoiceAgent(session_id="test_yeah", db_memory=memory_service)
    await agent.process_user_turn("I need human help.")
    assert agent.permission_state == "WAITING_FOR_PERMISSION"

    await agent.process_user_turn("Yeah")
    assert agent.permission_state == "APPROVED"


# 28. Dynamic Real Reference ID Generation & Dashboard Retrieval
@pytest.mark.asyncio
async def test_real_dynamic_reference_id_persistence(memory_service):
    """Test real dynamic reference ID (ESC-YYYYMMDD-XXXX) generation, database persistence, and dashboard retrieval."""
    agent = BharatVoiceAgent(session_id="test_real_ref_id", db_memory=memory_service)
    await agent.process_user_turn("I want to talk to a human.")
    await agent.process_user_turn("Yes, create it.")
    assert agent.permission_state == "APPROVED"

    res_raw = await agent.create_escalation(
        context=None,
        reason="User requested human assistance",
        summary="User asked for person to help",
        urgency="MEDIUM",
        preferred_follow_up="phone",
        user_permission=True,
    )
    res = json.loads(res_raw)
    assert res["success"] is True
    ref_id = res["reference_id"]

    # Verify ID is dynamic and NOT placeholder ESC-XXXXXXXX-XXXX
    assert ref_id != "ESC-XXXXXXXX-XXXX"
    assert ref_id.startswith("ESC-")
    parts = ref_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 4  # XXXX (e.g. 0001)

    # Verify retrieval from database matches dashboard query
    record = memory_service.get_escalation_by_ref(ref_id)
    assert record is not None
    assert record["reference_id"] == ref_id
    assert record["status"] == "OPEN"
    assert record["urgency"] == "MEDIUM"


# 29. Weather Location Speech Alias Normalization
@pytest.mark.asyncio
async def test_weather_normalization_veraval():
    """Test weather service normalizes speech variations like 'Vedawal' to Veraval."""
    from services.weather import get_weather_service

    svc = get_weather_service()
    res = await svc.get_weather_data("Vedawal")
    assert res["success"] is True
    assert "ver" in res["data"]["location"].lower()


# 30. Reference ID Uniqueness Test
@pytest.mark.asyncio
async def test_reference_id_uniqueness(memory_service):
    """Test multiple escalations receive unique sequential reference IDs."""
    res1 = memory_service.create_escalation(
        user_id="user_a",
        reason="Reason 1",
        summary="Summary 1",
        user_permission=True,
    )
    res2 = memory_service.create_escalation(
        user_id="user_b",
        reason="Reason 2",
        summary="Summary 2",
        user_permission=True,
    )
    assert res1["success"] is True
    assert res2["success"] is True
    assert res1["reference_id"] != res2["reference_id"]


# 31. Database Failure Handling Test
@pytest.mark.asyncio
async def test_database_write_failure_handling(monkeypatch, memory_service):
    """Test create_escalation returns database_error cleanly if SQLite write fails."""

    def mock_write_error(*args, **kwargs):
        raise RuntimeError("Simulated SQLite write error")

    monkeypatch.setattr(memory_service.db, "execute_write", mock_write_error)

    res = memory_service.create_escalation(
        user_id="user_err",
        reason="Test fail",
        summary="Test summary",
        user_permission=True,
    )
    assert res["success"] is False
    assert res["error"] == "database_error"


# 32. Tool Failure Handling Test
@pytest.mark.asyncio
async def test_tool_failure_handling(monkeypatch, memory_service):
    """Test create_escalation_tool handles exception safely without crashing."""
    agent = BharatVoiceAgent(session_id="test_tool_err", db_memory=memory_service)
    agent.permission_state = "APPROVED"

    def mock_svc_error(*args, **kwargs):
        return {"success": False, "error": "db_error", "message": "DB failed"}

    monkeypatch.setattr(memory_service, "create_escalation", mock_svc_error)

    res_raw = await agent.create_escalation(
        context=None,
        reason="Tool error test",
        summary="Summary error",
        user_permission=True,
    )
    res = json.loads(res_raw)
    assert res["success"] is False
    assert res["error"] == "db_error"


# ============================================================
# CRITICAL: Post-creation state lock tests
# ============================================================


# 33. Post-creation "Yes. That's okay." does NOT cancel or deny
@pytest.mark.asyncio
async def test_acknowledgement_after_escalation_does_not_cancel(memory_service):
    """
    MOST IMPORTANT TEST.

    Scenario:
    1. User: "I want to talk to a human."
    2. Agent asks permission.
    3. User: "Yes."  → CREATING_ESCALATION
    4. Tool creates escalation → ESCALATION_CREATED, active_reference_id set.
    5. User: "Yes. That's okay."

    Expected: state remains ESCALATION_CREATED, NOT denied, NOT re-created.
    """
    agent = BharatVoiceAgent(session_id="test_ack_lock", db_memory=memory_service)

    # Step 1: Human help request
    await agent.process_user_turn("I want to talk to a human.")
    assert agent.escalation_state == "WAITING_FOR_PERMISSION"

    # Step 2: Permission granted
    await agent.process_user_turn("Yes.")
    assert agent.escalation_state == "CREATING_ESCALATION"

    # Step 3: Simulate tool creating escalation successfully
    agent.escalation_state = "ESCALATION_CREATED"
    agent.active_reference_id = "ESC-20260812-0001"

    # Step 4: User acknowledges after creation
    await agent.process_user_turn("Yes. That's okay.")

    # MUST remain ESCALATION_CREATED — NOT denied, NOT re-created
    assert agent.escalation_state == "ESCALATION_CREATED"
    assert agent.active_reference_id == "ESC-20260812-0001"


# 34. Post-creation "Okay" does NOT cancel or deny
@pytest.mark.asyncio
async def test_okay_after_escalation_does_not_cancel(memory_service):
    """Test 'Okay' after escalation creation does not change state."""
    agent = BharatVoiceAgent(session_id="test_ok_lock", db_memory=memory_service)
    agent.escalation_state = "ESCALATION_CREATED"
    agent.active_reference_id = "ESC-20260812-0002"

    await agent.process_user_turn("Okay.")
    assert agent.escalation_state == "ESCALATION_CREATED"
    assert agent.active_reference_id == "ESC-20260812-0002"


# 35. Post-creation "Thanks" does NOT cancel or deny
@pytest.mark.asyncio
async def test_thanks_after_escalation_does_not_cancel(memory_service):
    """Test 'Thanks' after escalation creation does not change state."""
    agent = BharatVoiceAgent(session_id="test_thx_lock", db_memory=memory_service)
    agent.escalation_state = "ESCALATION_CREATED"
    agent.active_reference_id = "ESC-20260812-0003"

    await agent.process_user_turn("Thank you.")
    assert agent.escalation_state == "ESCALATION_CREATED"


# 36. Post-creation Gujarati "હા, બરાબર." does NOT cancel or deny
@pytest.mark.asyncio
async def test_gujarati_ack_after_escalation_does_not_cancel(memory_service):
    """Test Gujarati 'હા, બરાબર.' after creation does not change state."""
    agent = BharatVoiceAgent(session_id="test_guj_lock", db_memory=memory_service)
    agent.escalation_state = "ESCALATION_CREATED"
    agent.active_reference_id = "ESC-20260812-0004"

    await agent.process_user_turn("હા, બરાબર.")
    assert agent.escalation_state == "ESCALATION_CREATED"


# 37. Duplicate prevention after ESCALATION_CREATED
@pytest.mark.asyncio
async def test_no_duplicate_after_creation(memory_service):
    """Test that normal conversation after creation doesn't trigger new escalation."""
    agent = BharatVoiceAgent(session_id="test_no_dup", db_memory=memory_service)
    agent.escalation_state = "ESCALATION_CREATED"
    agent.active_reference_id = "ESC-20260812-0005"

    await agent.process_user_turn("Great, thanks.")
    assert agent.escalation_state == "ESCALATION_CREATED"

    # Even saying "human" shouldn't re-trigger when already created
    await agent.process_user_turn("The human will call me back?")
    assert agent.escalation_state == "ESCALATION_CREATED"
